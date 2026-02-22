"""End-to-end integration tests for bulk coordinate pipeline with DuckDB in-memory."""

from __future__ import annotations

import json
from io import StringIO
from pathlib import Path
from unittest.mock import MagicMock


from anncsu.coordinate.bulk.db import BulkDB, RowStatus
from anncsu.coordinate.bulk.dryrun import BulkDryRunner
from anncsu.coordinate.bulk.executor import BulkExecutor
from anncsu.coordinate.bulk.importer import import_csv
from anncsu.coordinate.bulk.reporter import BulkReporter, ReportFormat


def _write_csv(path: Path, content: str) -> Path:
    path.write_text(content, encoding="utf-8")
    return path


def _make_api_response(esito="0", messaggio="OK", id_richiesta="5144"):
    mock = MagicMock()
    mock.esito = esito
    mock.messaggio = messaggio
    mock.id_richiesta = id_richiesta
    mock.dati = None
    mock.model_dump.return_value = {
        "esito": esito,
        "messaggio": messaggio,
        "idRichiesta": id_richiesta,
    }
    mock.model_dump_json.return_value = json.dumps(mock.model_dump.return_value)
    return mock


def _make_lookup_response(coord_x=None, coord_y=None, quota=None, metodo=None):
    mock_data = MagicMock()
    mock_data.coord_x = coord_x
    mock_data.coord_y = coord_y
    mock_data.quota = quota
    mock_data.metodo = metodo
    mock_data.prognazacc = "1370588"
    mock_data.civico = "12"
    mock_response = MagicMock()
    mock_response.data = mock_data
    return mock_response


class TestFullPipeline:
    """Test the complete pipeline: import → validate → execute → report."""

    def test_import_execute_report(self, tmp_path):
        """Full pipeline with mixed valid/invalid rows and mock API."""
        csv_file = _write_csv(
            tmp_path / "input.csv",
            "codcom,progr_civico,x,y,z,metodo\n"
            "A062,100,13.1022000,41.8847600,150,3\n"
            "A062,200,14.0000000,42.0000000,,2\n"
            "A062,300,13.1,,,\n"  # invalid: x without y
            "A062,400,,,,,\n",  # valid: clear coordinates
        )

        with BulkDB(":memory:") as db:
            # Phase 1: Import + Validate
            import_result = import_csv(db=db, csv_path=csv_file, mode="update")
            assert import_result.total_rows == 4
            assert import_result.valid_rows == 3
            assert import_result.invalid_rows == 1
            assert import_result.codcom == "A062"

            # Phase 2: Execute
            mock_sdk = MagicMock()
            responses = [
                _make_api_response(id_richiesta="5001"),
                _make_api_response(id_richiesta="5002"),
                _make_api_response(esito="23", messaggio="Errore", id_richiesta="5003"),
            ]
            mock_sdk.json_post.gestionecoordinate.side_effect = responses

            executor = BulkExecutor(db=db, run_id=import_result.run_id, sdk=mock_sdk)
            exec_result = executor.execute()

            assert exec_result.processed == 3  # 3 valid rows
            assert exec_result.succeeded == 2
            assert exec_result.failed == 1

            # Phase 3: Report
            reporter = BulkReporter(db=db, run_id=import_result.run_id)
            summary = reporter.get_summary()
            assert summary.total_rows == 4
            assert summary.succeeded == 2
            assert summary.failed == 1

            # Export CSV report
            csv_output = StringIO()
            reporter.export_results(csv_output, fmt=ReportFormat.CSV)
            csv_output.seek(0)
            csv_lines = csv_output.read().strip().split("\n")
            assert len(csv_lines) == 5  # header + 4 data rows

            # Export JSON report
            json_output = StringIO()
            reporter.export_results(json_output, fmt=ReportFormat.JSON)
            json_output.seek(0)
            data = json.loads(json_output.read())
            assert len(data["results"]) == 4

            # Check errors
            errors = reporter.get_errors()
            assert len(errors) == 1
            assert errors[0]["esito"] == "23"

            # Check validation errors
            val_errors = reporter.get_validation_errors()
            assert len(val_errors) == 1
            assert val_errors[0]["progr_civico"] == "300"

    def test_import_dryrun_report(self, tmp_path):
        """Full dry-run pipeline: import → dry-run (10 records) → report."""
        csv_file = _write_csv(
            tmp_path / "dryrun.csv",
            "codcom,progr_civico,x,y,z,metodo\n"
            "A062,100,13.1022000,41.8847600,,3\n"
            "A062,200,14.0000000,42.0000000,,2\n",
        )

        with BulkDB(":memory:") as db:
            # Phase 1: Import
            import_result = import_csv(db=db, csv_path=csv_file, mode="dryrun")
            assert import_result.valid_rows == 2

            # Phase 2: Dry-run
            mock_consult_sdk = MagicMock()
            mock_consult_sdk.queryparam.prognazacc_get_query_param.return_value = (
                _make_lookup_response(coord_x="12.0", coord_y="40.0", metodo="1")
            )

            mock_coord_sdk = MagicMock()
            mock_coord_sdk.json_post.gestionecoordinate.return_value = (
                _make_api_response()
            )

            runner = BulkDryRunner(
                db=db,
                run_id=import_result.run_id,
                coord_sdk=mock_coord_sdk,
                consult_sdk=mock_consult_sdk,
                max_records=10,
            )
            dry_result = runner.execute()

            assert dry_result.total_tested == 2
            assert dry_result.updates_succeeded == 2
            assert dry_result.restores_succeeded == 2

            # Verify lookup + update + restore calls
            assert (
                mock_consult_sdk.queryparam.prognazacc_get_query_param.call_count == 2
            )
            # 2 updates + 2 restores = 4
            assert mock_coord_sdk.json_post.gestionecoordinate.call_count == 4

            # Verify originals were saved
            for row_id in [1, 2]:
                orig = db.get_dryrun_original(row_id=row_id)
                assert orig is not None
                assert orig["original_x"] == "12.0"

    def test_resume_after_interruption(self, tmp_path):
        """Simulate crash mid-execution, then resume."""
        csv_file = _write_csv(
            tmp_path / "resume.csv",
            "codcom,progr_civico,x,y,z,metodo\n"
            "A062,100,13.1,41.8,,3\n"
            "A062,200,14.0,42.0,,2\n"
            "A062,300,15.0,43.0,,1\n",
        )

        with BulkDB(":memory:") as db:
            import_result = import_csv(db=db, csv_path=csv_file, mode="update")

            # Simulate: first row completed, second was processing (crashed)
            mock_sdk = MagicMock()
            mock_sdk.json_post.gestionecoordinate.return_value = _make_api_response()

            # Mark first row as done manually
            db.update_row_status(row_id=1, status=RowStatus.DONE)
            db.insert_result(
                row_id=1,
                run_id=import_result.run_id,
                operation="update",
                esito="0",
                messaggio="OK",
            )
            # Mark second as processing (simulating crash mid-flight)
            db.update_row_status(row_id=2, status=RowStatus.PROCESSING)

            # Resume execution
            executor = BulkExecutor(db=db, run_id=import_result.run_id, sdk=mock_sdk)
            exec_result = executor.execute(resume=True)

            # Should process rows 2 and 3 (row 1 already done)
            assert exec_result.processed == 2
            assert exec_result.succeeded == 2

            # All 3 rows should now be done
            done_rows = db.get_rows_by_status(
                run_id=import_result.run_id, status=RowStatus.DONE
            )
            assert len(done_rows) == 3

    def test_semicolon_csv_full_pipeline(self, tmp_path):
        """Full pipeline with semicolon-separated CSV."""
        csv_file = _write_csv(
            tmp_path / "semi.csv",
            "codcom;progr_civico;x;y;z;metodo\n"
            "H501;1000;12.4922;41.8902;;4\n"
            "H501;2000;12.5000;41.9000;;3\n",
        )

        with BulkDB(":memory:") as db:
            import_result = import_csv(db=db, csv_path=csv_file, mode="update")
            assert import_result.total_rows == 2
            assert import_result.valid_rows == 2
            assert import_result.codcom == "H501"

            mock_sdk = MagicMock()
            mock_sdk.json_post.gestionecoordinate.return_value = _make_api_response()

            executor = BulkExecutor(db=db, run_id=import_result.run_id, sdk=mock_sdk)
            exec_result = executor.execute()
            assert exec_result.succeeded == 2

    def test_chunk_id_with_many_rows(self, tmp_path):
        """Verify chunk_id assignment with enough rows to span chunks."""
        # Create a CSV that would have rows in 2 chunks
        # We use row_ids that would land in different chunks
        with BulkDB(":memory:") as db:
            run_id = db.create_run(
                codcom="A062",
                csv_path="/tmp/test.csv",
                db_path=":memory:",
                mode="update",
            )
            # Insert rows at boundaries
            for row_id in [1, 49999, 50000, 50001, 100000]:
                db.con.execute(
                    "INSERT INTO bulk_input (row_id, run_id, codcom, progr_civico, status) "
                    "VALUES (?, ?, 'A062', ?, 'valid')",
                    [row_id, run_id, str(row_id)],
                )

            # Check chunk assignments
            chunks = db.con.execute(
                "SELECT row_id, chunk_id FROM bulk_input ORDER BY row_id"
            ).fetchall()

            assert chunks[0] == (1, 0)  # chunk 0
            assert chunks[1] == (49999, 0)  # chunk 0
            assert chunks[2] == (50000, 0)  # chunk 0 (last row)
            assert chunks[3] == (50001, 1)  # chunk 1
            assert chunks[4] == (100000, 1)  # chunk 1

    def test_db_persistence_on_disk(self, tmp_path):
        """Verify DB file can be reopened after closing."""
        db_path = str(tmp_path / "A062_test.db")
        csv_file = _write_csv(
            tmp_path / "test.csv",
            "codcom,progr_civico,x,y,z,metodo\nA062,100,13.1,41.8,,3\n",
        )

        # First session: import
        with BulkDB(db_path) as db:
            result = import_csv(db=db, csv_path=csv_file, mode="update")
            run_id = result.run_id

        # Second session: reopen and verify data persists
        with BulkDB(db_path) as db:
            summary = db.get_run_summary(run_id)
            assert summary is not None
            assert summary["codcom"] == "A062"
            assert summary["total_rows"] == 1

            rows = db.get_rows_by_status(run_id=run_id, status=RowStatus.VALID)
            assert len(rows) == 1


class TestProgressTracking:
    """Test progress callback integration."""

    def test_progress_tracked_across_execution(self, tmp_path):
        csv_file = _write_csv(
            tmp_path / "progress.csv",
            "codcom,progr_civico,x,y,z,metodo\n"
            "A062,100,13.1,41.8,,3\n"
            "A062,200,14.0,42.0,,2\n"
            "A062,300,15.0,43.0,,1\n",
        )

        with BulkDB(":memory:") as db:
            import_result = import_csv(db=db, csv_path=csv_file, mode="update")

            mock_sdk = MagicMock()
            mock_sdk.json_post.gestionecoordinate.return_value = _make_api_response()

            progress_log = []

            def on_progress(processed, total, succeeded, failed):
                progress_log.append(
                    {
                        "processed": processed,
                        "total": total,
                        "succeeded": succeeded,
                        "failed": failed,
                    }
                )

            executor = BulkExecutor(
                db=db,
                run_id=import_result.run_id,
                sdk=mock_sdk,
                on_progress=on_progress,
            )
            executor.execute()

            assert len(progress_log) == 3
            # First callback
            assert progress_log[0] == {
                "processed": 1,
                "total": 3,
                "succeeded": 1,
                "failed": 0,
            }
            # Last callback
            assert progress_log[2] == {
                "processed": 3,
                "total": 3,
                "succeeded": 3,
                "failed": 0,
            }
