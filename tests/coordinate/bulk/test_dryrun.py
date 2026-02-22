"""Tests for bulk dry-run: lookup + update + restore with DuckDB state."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock


from anncsu.coordinate.bulk.db import BulkDB
from anncsu.coordinate.bulk.dryrun import BulkDryRunner, DryRunResult
from anncsu.coordinate.bulk.importer import import_csv


def _write_csv(path: Path, content: str) -> Path:
    path.write_text(content, encoding="utf-8")
    return path


def _make_success_response(**kwargs):
    mock = MagicMock()
    mock.esito = "0"
    mock.messaggio = "OK"
    mock.id_richiesta = kwargs.get("id_richiesta", "5144")
    mock.dati = None
    mock.model_dump.return_value = {
        "esito": "0",
        "messaggio": "OK",
        "idRichiesta": mock.id_richiesta,
    }
    mock.model_dump_json.return_value = json.dumps(mock.model_dump.return_value)
    return mock


def _make_lookup_response(*, coord_x=None, coord_y=None, quota=None, metodo=None):
    """Create a mock PA lookup response with optional coordinates."""
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


def _setup_db_with_csv(tmp_path, csv_content):
    csv_file = _write_csv(tmp_path / "input.csv", csv_content)
    db = BulkDB(":memory:")
    result = import_csv(db=db, csv_path=csv_file, mode="dryrun")
    return db, result


class TestBulkDryRunnerInit:
    """Test dry-run initialization."""

    def test_create_dryrunner(self, tmp_path):
        csv = "codcom,progr_civico,x,y,z,metodo\nA062,100,13.1,41.8,,3\n"
        db, result = _setup_db_with_csv(tmp_path, csv)
        mock_coord_sdk = MagicMock()
        mock_consult_sdk = MagicMock()

        runner = BulkDryRunner(
            db=db,
            run_id=result.run_id,
            coord_sdk=mock_coord_sdk,
            consult_sdk=mock_consult_sdk,
        )
        assert runner.run_id == result.run_id
        db.close()


class TestBulkDryRunExecution:
    """Test the full dry-run cycle: lookup → update → restore."""

    def test_dryrun_full_cycle(self, tmp_path):
        csv = "codcom,progr_civico,x,y,z,metodo\nA062,1370588,14.0,42.0,,2\n"
        db, result = _setup_db_with_csv(tmp_path, csv)

        mock_consult_sdk = MagicMock()
        mock_consult_sdk.queryparam.prognazacc_get_query_param.return_value = (
            _make_lookup_response(coord_x="13.1022", coord_y="41.8847", metodo="3")
        )

        mock_coord_sdk = MagicMock()
        mock_coord_sdk.json_post.gestionecoordinate.return_value = (
            _make_success_response()
        )

        runner = BulkDryRunner(
            db=db,
            run_id=result.run_id,
            coord_sdk=mock_coord_sdk,
            consult_sdk=mock_consult_sdk,
            max_records=10,
        )
        dry_result = runner.execute()

        assert dry_result.total_tested == 1
        assert dry_result.updates_succeeded == 1
        assert dry_result.restores_succeeded == 1
        # 1 lookup + 1 update + 1 restore = 3 API calls
        assert mock_consult_sdk.queryparam.prognazacc_get_query_param.call_count == 1
        assert mock_coord_sdk.json_post.gestionecoordinate.call_count == 2
        db.close()

    def test_dryrun_saves_originals(self, tmp_path):
        csv = "codcom,progr_civico,x,y,z,metodo\nA062,1370588,14.0,42.0,,2\n"
        db, result = _setup_db_with_csv(tmp_path, csv)

        mock_consult_sdk = MagicMock()
        mock_consult_sdk.queryparam.prognazacc_get_query_param.return_value = (
            _make_lookup_response(
                coord_x="13.1022", coord_y="41.8847", quota="150", metodo="3"
            )
        )

        mock_coord_sdk = MagicMock()
        mock_coord_sdk.json_post.gestionecoordinate.return_value = (
            _make_success_response()
        )

        runner = BulkDryRunner(
            db=db,
            run_id=result.run_id,
            coord_sdk=mock_coord_sdk,
            consult_sdk=mock_consult_sdk,
        )
        runner.execute()

        # Verify originals were saved
        orig = db.get_dryrun_original(row_id=1)
        assert orig is not None
        assert orig["original_x"] == "13.1022"
        assert orig["original_y"] == "41.8847"
        assert orig["original_z"] == "150"
        assert orig["original_metodo"] == "3"
        db.close()

    def test_dryrun_respects_max_records(self, tmp_path):
        csv = (
            "codcom,progr_civico,x,y,z,metodo\n"
            "A062,100,13.1,41.8,,3\n"
            "A062,200,14.0,42.0,,2\n"
            "A062,300,15.0,43.0,,1\n"
        )
        db, result = _setup_db_with_csv(tmp_path, csv)

        mock_consult_sdk = MagicMock()
        mock_consult_sdk.queryparam.prognazacc_get_query_param.return_value = (
            _make_lookup_response(coord_x="13.0", coord_y="41.0", metodo="3")
        )

        mock_coord_sdk = MagicMock()
        mock_coord_sdk.json_post.gestionecoordinate.return_value = (
            _make_success_response()
        )

        runner = BulkDryRunner(
            db=db,
            run_id=result.run_id,
            coord_sdk=mock_coord_sdk,
            consult_sdk=mock_consult_sdk,
            max_records=2,
        )
        dry_result = runner.execute()

        assert dry_result.total_tested == 2
        # 2 lookups + 2 updates + 2 restores
        assert mock_consult_sdk.queryparam.prognazacc_get_query_param.call_count == 2
        assert mock_coord_sdk.json_post.gestionecoordinate.call_count == 4
        db.close()

    def test_dryrun_default_max_records_is_10(self, tmp_path):
        csv = "codcom,progr_civico,x,y,z,metodo\nA062,100,13.1,41.8,,3\n"
        db, result = _setup_db_with_csv(tmp_path, csv)
        mock_coord_sdk = MagicMock()
        mock_consult_sdk = MagicMock()

        runner = BulkDryRunner(
            db=db,
            run_id=result.run_id,
            coord_sdk=mock_coord_sdk,
            consult_sdk=mock_consult_sdk,
        )
        assert runner.max_records == 10
        db.close()

    def test_dryrun_handles_lookup_failure(self, tmp_path):
        csv = "codcom,progr_civico,x,y,z,metodo\nA062,1370588,14.0,42.0,,2\n"
        db, result = _setup_db_with_csv(tmp_path, csv)

        mock_consult_sdk = MagicMock()
        mock_consult_sdk.queryparam.prognazacc_get_query_param.side_effect = Exception(
            "Lookup failed"
        )

        mock_coord_sdk = MagicMock()

        runner = BulkDryRunner(
            db=db,
            run_id=result.run_id,
            coord_sdk=mock_coord_sdk,
            consult_sdk=mock_consult_sdk,
        )
        dry_result = runner.execute()

        assert dry_result.total_tested == 0
        assert dry_result.lookup_failures == 1
        # No update/restore calls if lookup fails
        assert mock_coord_sdk.json_post.gestionecoordinate.call_count == 0
        db.close()

    def test_dryrun_handles_update_failure(self, tmp_path):
        csv = "codcom,progr_civico,x,y,z,metodo\nA062,1370588,14.0,42.0,,2\n"
        db, result = _setup_db_with_csv(tmp_path, csv)

        mock_consult_sdk = MagicMock()
        mock_consult_sdk.queryparam.prognazacc_get_query_param.return_value = (
            _make_lookup_response(coord_x="13.0", coord_y="41.0", metodo="3")
        )

        mock_coord_sdk = MagicMock()
        mock_coord_sdk.json_post.gestionecoordinate.side_effect = Exception(
            "Update failed"
        )

        runner = BulkDryRunner(
            db=db,
            run_id=result.run_id,
            coord_sdk=mock_coord_sdk,
            consult_sdk=mock_consult_sdk,
        )
        dry_result = runner.execute()

        assert dry_result.updates_failed == 1
        # Even if update fails, no restore needed (nothing changed)
        assert dry_result.restores_succeeded == 0
        db.close()

    def test_dryrun_stores_results(self, tmp_path):
        csv = "codcom,progr_civico,x,y,z,metodo\nA062,1370588,14.0,42.0,,2\n"
        db, result = _setup_db_with_csv(tmp_path, csv)

        mock_consult_sdk = MagicMock()
        mock_consult_sdk.queryparam.prognazacc_get_query_param.return_value = (
            _make_lookup_response(coord_x="13.0", coord_y="41.0", metodo="3")
        )

        mock_coord_sdk = MagicMock()
        mock_coord_sdk.json_post.gestionecoordinate.return_value = (
            _make_success_response()
        )

        runner = BulkDryRunner(
            db=db,
            run_id=result.run_id,
            coord_sdk=mock_coord_sdk,
            consult_sdk=mock_consult_sdk,
        )
        runner.execute()

        results = db.con.execute(
            "SELECT operation FROM bulk_results WHERE run_id = ? ORDER BY result_id",
            [result.run_id],
        ).fetchall()
        operations = [r[0] for r in results]
        assert "dryrun_update" in operations
        assert "dryrun_restore" in operations
        db.close()

    def test_dryrun_no_coordinates_uses_test_values(self, tmp_path):
        """When original has no coordinates, dry-run uses test values for restore."""
        csv = "codcom,progr_civico,x,y,z,metodo\nA062,1370588,14.0,42.0,,2\n"
        db, result = _setup_db_with_csv(tmp_path, csv)

        mock_consult_sdk = MagicMock()
        # Lookup returns no coordinates
        mock_consult_sdk.queryparam.prognazacc_get_query_param.return_value = (
            _make_lookup_response(coord_x=None, coord_y=None, metodo=None)
        )

        mock_coord_sdk = MagicMock()
        mock_coord_sdk.json_post.gestionecoordinate.return_value = (
            _make_success_response()
        )

        runner = BulkDryRunner(
            db=db,
            run_id=result.run_id,
            coord_sdk=mock_coord_sdk,
            consult_sdk=mock_consult_sdk,
        )
        runner.execute()

        orig = db.get_dryrun_original(row_id=1)
        assert orig is not None
        assert orig["original_x"] is None
        assert orig["original_y"] is None
        db.close()


class TestDryRunResult:
    """Test DryRunResult dataclass."""

    def test_result_fields(self):
        result = DryRunResult(
            total_tested=10,
            updates_succeeded=8,
            updates_failed=2,
            restores_succeeded=8,
            restores_failed=0,
            lookup_failures=0,
            run_id="test-run",
        )
        assert result.total_tested == 10
        assert result.updates_succeeded == 8
