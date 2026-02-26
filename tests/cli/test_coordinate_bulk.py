"""Tests for CLI coordinate bulk commands."""

from __future__ import annotations

import json
import os
import time
from pathlib import Path
from unittest.mock import MagicMock, patch

from typer.testing import CliRunner

from anncsu.cli.app import app
from anncsu.coordinate.bulk.db import BulkDB, RowStatus
from anncsu.coordinate.bulk.importer import import_csv

runner = CliRunner()


def _write_csv(path: Path, content: str) -> Path:
    path.write_text(content, encoding="utf-8")
    return path


VALID_CSV = (
    "codcom,progr_civico,x,y,z,metodo\n"
    "A062,1370588,13.1022000,41.8847600,150,3\n"
    "A062,1370589,14.0,42.0,,2\n"
)

VALID_CSV_5_ROWS = (
    "codcom,progr_civico,x,y,z,metodo\n"
    "A062,1370588,13.1022000,41.8847600,150,3\n"
    "A062,1370589,14.0,42.0,,2\n"
    "A062,1370590,13.5,41.5,,1\n"
    "A062,1370591,14.2,42.2,100,4\n"
    "A062,1370592,13.8,41.9,,2\n"
)


def _make_api_response(esito="0", messaggio="OK", id_richiesta="5144"):
    """Create a mock API response matching AnncsuCoordinate shape."""
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


def _make_lookup_response(coord_x="12.0", coord_y="41.0", quota=None, metodo="3"):
    """Create a mock PA lookup response."""
    mock_data = MagicMock()
    mock_data.coord_x = coord_x
    mock_data.coord_y = coord_y
    mock_data.quota = quota
    mock_data.metodo = metodo
    mock_data.prognazacc = "1370588"
    mock_data.civico = "12"
    mock_response = MagicMock()
    mock_response.data = [mock_data]  # List, matching real PA API
    return mock_response


def _create_populated_db(db_path: str, csv_path: Path, mode: str = "update"):
    """Create a DB file with imported CSV data and return (db, import_result)."""
    db = BulkDB(db_path)
    result = import_csv(db=db, csv_path=csv_path, mode=mode)
    return db, result


# ---------------------------------------------------------------------------
# Existing test classes
# ---------------------------------------------------------------------------


class TestBulkValidate:
    """Test 'anncsu coordinate bulk validate' command."""

    def test_validate_valid_csv(self, tmp_path):
        csv_file = _write_csv(tmp_path / "valid.csv", VALID_CSV)
        result = runner.invoke(app, ["coordinate", "bulk", "validate", str(csv_file)])
        assert result.exit_code == 0
        assert "2" in result.output  # total rows
        assert "valid" in result.output.lower()

    def test_validate_invalid_rows(self, tmp_path):
        csv_file = _write_csv(
            tmp_path / "invalid.csv",
            "codcom,progr_civico,x,y,z,metodo\n"
            "A062,1370588,13.1,,,\n"  # x without y
            "A062,1370589,14.0,42.0,,2\n",
        )
        result = runner.invoke(app, ["coordinate", "bulk", "validate", str(csv_file)])
        assert result.exit_code == 0
        assert "invalid" in result.output.lower() or "1" in result.output

    def test_validate_missing_header(self, tmp_path):
        csv_file = _write_csv(
            tmp_path / "noheader.csv",
            "A062,1370588,13.1,41.8,150,3\n",
        )
        result = runner.invoke(app, ["coordinate", "bulk", "validate", str(csv_file)])
        assert result.exit_code != 0

    def test_validate_nonexistent_file(self):
        result = runner.invoke(
            app, ["coordinate", "bulk", "validate", "/tmp/nonexistent.csv"]
        )
        assert result.exit_code != 0

    def test_validate_json_output(self, tmp_path):
        csv_file = _write_csv(
            tmp_path / "valid.csv",
            "codcom,progr_civico,x,y,z,metodo\nA062,1370588,13.1022000,41.8847600,,3\n",
        )
        result = runner.invoke(
            app, ["coordinate", "bulk", "validate", str(csv_file), "--json"]
        )
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data["total_rows"] == 1
        assert data["valid_rows"] == 1

    def test_validate_semicolon_csv(self, tmp_path):
        csv_file = _write_csv(
            tmp_path / "semi.csv",
            "codcom;progr_civico;x;y;z;metodo\nA062;1370588;13.1;41.8;;3\n",
        )
        result = runner.invoke(app, ["coordinate", "bulk", "validate", str(csv_file)])
        assert result.exit_code == 0


class TestBulkHelp:
    """Test bulk subcommand help and structure."""

    def test_bulk_help(self):
        result = runner.invoke(app, ["coordinate", "bulk", "--help"])
        assert result.exit_code == 0
        assert "validate" in result.output
        assert "update" in result.output
        assert "dry-run" in result.output
        assert "resume" in result.output
        assert "status" in result.output
        assert "report" in result.output
        assert "list" in result.output
        assert "clean" in result.output

    def test_coordinate_help_shows_bulk(self):
        result = runner.invoke(app, ["coordinate", "--help"])
        assert result.exit_code == 0
        assert "bulk" in result.output


# ---------------------------------------------------------------------------
# Local-only command tests (status, report, list, clean)
# ---------------------------------------------------------------------------


class TestBulkStatus:
    """Test 'anncsu coordinate bulk status' command."""

    def test_status_run_not_found(self, tmp_path):
        with patch(
            "anncsu.cli.commands.bulk._get_bulk_dir", return_value=tmp_path / "bulk"
        ):
            result = runner.invoke(
                app, ["coordinate", "bulk", "status", "nonexistent-run-id"]
            )
            assert result.exit_code != 0
            assert "no db found" in result.output.lower() or result.exit_code == 1

    def test_status_shows_summary(self, tmp_path):
        bulk_dir = tmp_path / "bulk"
        bulk_dir.mkdir()
        csv_file = _write_csv(tmp_path / "test.csv", VALID_CSV)

        # Create a DB with a completed run
        db_path = str(bulk_dir / "A062_test-run-id.db")
        with BulkDB(db_path) as db:
            import_result = import_csv(db=db, csv_path=csv_file, mode="update")
            db.finish_run(import_result.run_id)
            run_id = import_result.run_id

        # Rename file to match the run_id
        actual_path = bulk_dir / f"A062_{run_id}.db"
        os.rename(db_path, actual_path)

        with patch("anncsu.cli.commands.bulk._get_bulk_dir", return_value=bulk_dir):
            result = runner.invoke(app, ["coordinate", "bulk", "status", run_id])
            assert result.exit_code == 0
            assert "A062" in result.output

    def test_status_json_output(self, tmp_path):
        bulk_dir = tmp_path / "bulk"
        bulk_dir.mkdir()
        csv_file = _write_csv(tmp_path / "test.csv", VALID_CSV)

        db_path = str(bulk_dir / "A062_test-run.db")
        with BulkDB(db_path) as db:
            import_result = import_csv(db=db, csv_path=csv_file, mode="update")
            run_id = import_result.run_id

        actual_path = bulk_dir / f"A062_{run_id}.db"
        os.rename(db_path, actual_path)

        with patch("anncsu.cli.commands.bulk._get_bulk_dir", return_value=bulk_dir):
            result = runner.invoke(
                app, ["coordinate", "bulk", "status", run_id, "--json"]
            )
            assert result.exit_code == 0
            data = json.loads(result.output)
            assert data["codcom"] == "A062"
            assert data["run_id"] == run_id


class TestBulkReport:
    """Test 'anncsu coordinate bulk report' command."""

    def test_report_run_not_found(self, tmp_path):
        with patch(
            "anncsu.cli.commands.bulk._get_bulk_dir", return_value=tmp_path / "bulk"
        ):
            result = runner.invoke(app, ["coordinate", "bulk", "report", "nonexistent"])
            assert result.exit_code != 0

    def test_report_csv_to_stdout(self, tmp_path):
        bulk_dir = tmp_path / "bulk"
        bulk_dir.mkdir()
        csv_file = _write_csv(tmp_path / "test.csv", VALID_CSV)

        db_path = str(bulk_dir / "A062_test.db")
        with BulkDB(db_path) as db:
            import_result = import_csv(db=db, csv_path=csv_file, mode="update")
            run_id = import_result.run_id

        actual_path = bulk_dir / f"A062_{run_id}.db"
        os.rename(db_path, actual_path)

        with patch("anncsu.cli.commands.bulk._get_bulk_dir", return_value=bulk_dir):
            result = runner.invoke(app, ["coordinate", "bulk", "report", run_id])
            assert result.exit_code == 0
            assert "codcom" in result.output  # CSV header

    def test_report_csv_to_file(self, tmp_path):
        bulk_dir = tmp_path / "bulk"
        bulk_dir.mkdir()
        csv_file = _write_csv(tmp_path / "test.csv", VALID_CSV)
        output_file = tmp_path / "results.csv"

        db_path = str(bulk_dir / "A062_test.db")
        with BulkDB(db_path) as db:
            import_result = import_csv(db=db, csv_path=csv_file, mode="update")
            run_id = import_result.run_id

        actual_path = bulk_dir / f"A062_{run_id}.db"
        os.rename(db_path, actual_path)

        with patch("anncsu.cli.commands.bulk._get_bulk_dir", return_value=bulk_dir):
            result = runner.invoke(
                app,
                ["coordinate", "bulk", "report", run_id, "--output", str(output_file)],
            )
            assert result.exit_code == 0
            assert output_file.exists()
            content = output_file.read_text()
            assert "codcom" in content

    def test_report_json_format(self, tmp_path):
        bulk_dir = tmp_path / "bulk"
        bulk_dir.mkdir()
        csv_file = _write_csv(tmp_path / "test.csv", VALID_CSV)

        db_path = str(bulk_dir / "A062_test.db")
        with BulkDB(db_path) as db:
            import_result = import_csv(db=db, csv_path=csv_file, mode="update")
            run_id = import_result.run_id

        actual_path = bulk_dir / f"A062_{run_id}.db"
        os.rename(db_path, actual_path)

        with patch("anncsu.cli.commands.bulk._get_bulk_dir", return_value=bulk_dir):
            result = runner.invoke(
                app, ["coordinate", "bulk", "report", run_id, "--format", "json"]
            )
            assert result.exit_code == 0
            data = json.loads(result.output)
            assert "results" in data
            assert "summary" in data

    def test_report_invalid_format(self, tmp_path):
        bulk_dir = tmp_path / "bulk"
        bulk_dir.mkdir()

        with patch("anncsu.cli.commands.bulk._get_bulk_dir", return_value=bulk_dir):
            result = runner.invoke(
                app, ["coordinate", "bulk", "report", "some-id", "--format", "xml"]
            )
            assert result.exit_code != 0


class TestBulkList:
    """Test 'anncsu coordinate bulk list' command."""

    def test_list_empty_no_bulk_dir(self, tmp_path):
        with patch(
            "anncsu.cli.commands.bulk._get_bulk_dir", return_value=tmp_path / "bulk"
        ):
            result = runner.invoke(app, ["coordinate", "bulk", "list"])
            assert result.exit_code == 0
            assert "no bulk runs" in result.output.lower()

    def test_list_shows_runs(self, tmp_path):
        bulk_dir = tmp_path / "bulk"
        bulk_dir.mkdir()
        csv_file = _write_csv(tmp_path / "test.csv", VALID_CSV)

        with BulkDB(str(bulk_dir / "A062_run1.db")) as db:
            import_csv(db=db, csv_path=csv_file, mode="update")

        with patch("anncsu.cli.commands.bulk._get_bulk_dir", return_value=bulk_dir):
            result = runner.invoke(app, ["coordinate", "bulk", "list"])
            assert result.exit_code == 0
            assert "A062" in result.output

    def test_list_json_output(self, tmp_path):
        bulk_dir = tmp_path / "bulk"
        bulk_dir.mkdir()
        csv_file = _write_csv(tmp_path / "test.csv", VALID_CSV)

        with BulkDB(str(bulk_dir / "A062_run1.db")) as db:
            import_csv(db=db, csv_path=csv_file, mode="update")

        with patch("anncsu.cli.commands.bulk._get_bulk_dir", return_value=bulk_dir):
            result = runner.invoke(app, ["coordinate", "bulk", "list", "--json"])
            assert result.exit_code == 0
            data = json.loads(result.output)
            assert isinstance(data, list)
            assert len(data) >= 1
            assert data[0]["codcom"] == "A062"

    def test_list_handles_corrupt_db(self, tmp_path):
        bulk_dir = tmp_path / "bulk"
        bulk_dir.mkdir()
        csv_file = _write_csv(tmp_path / "test.csv", VALID_CSV)

        # Create one valid DB
        with BulkDB(str(bulk_dir / "A062_valid.db")) as db:
            import_csv(db=db, csv_path=csv_file, mode="update")

        # Create one corrupt file
        (bulk_dir / "corrupt.db").write_text("not a real db")

        with patch("anncsu.cli.commands.bulk._get_bulk_dir", return_value=bulk_dir):
            result = runner.invoke(app, ["coordinate", "bulk", "list"])
            assert result.exit_code == 0
            assert "A062" in result.output


class TestBulkClean:
    """Test 'anncsu coordinate bulk clean' command."""

    def test_clean_requires_older_than_or_dry_run(self, tmp_path):
        with patch(
            "anncsu.cli.commands.bulk._get_bulk_dir", return_value=tmp_path / "bulk"
        ):
            result = runner.invoke(app, ["coordinate", "bulk", "clean"])
            assert result.exit_code != 0

    def test_clean_dry_run_shows_files(self, tmp_path):
        bulk_dir = tmp_path / "bulk"
        bulk_dir.mkdir()
        # Create a DB file
        db_file = bulk_dir / "old_run.db"
        db_file.write_text("data")
        # Set mtime to 40 days ago
        old_time = time.time() - (40 * 86400)
        os.utime(db_file, (old_time, old_time))

        with patch("anncsu.cli.commands.bulk._get_bulk_dir", return_value=bulk_dir):
            result = runner.invoke(
                app, ["coordinate", "bulk", "clean", "--older-than", "30", "--dry-run"]
            )
            assert result.exit_code == 0
            assert "would" in result.output.lower()
            assert db_file.exists()  # Not actually deleted

    def test_clean_removes_old_files(self, tmp_path):
        bulk_dir = tmp_path / "bulk"
        bulk_dir.mkdir()
        db_file = bulk_dir / "old_run.db"
        db_file.write_text("data")
        old_time = time.time() - (40 * 86400)
        os.utime(db_file, (old_time, old_time))

        with patch("anncsu.cli.commands.bulk._get_bulk_dir", return_value=bulk_dir):
            result = runner.invoke(
                app, ["coordinate", "bulk", "clean", "--older-than", "30"]
            )
            assert result.exit_code == 0
            assert not db_file.exists()  # Actually deleted

    def test_clean_keeps_recent_files(self, tmp_path):
        bulk_dir = tmp_path / "bulk"
        bulk_dir.mkdir()
        db_file = bulk_dir / "recent_run.db"
        db_file.write_text("data")
        # mtime is now (recent)

        with patch("anncsu.cli.commands.bulk._get_bulk_dir", return_value=bulk_dir):
            result = runner.invoke(
                app, ["coordinate", "bulk", "clean", "--older-than", "30"]
            )
            assert result.exit_code == 0
            assert db_file.exists()  # Not deleted

    def test_clean_empty_dir(self, tmp_path):
        bulk_dir = tmp_path / "bulk"
        bulk_dir.mkdir()

        with patch("anncsu.cli.commands.bulk._get_bulk_dir", return_value=bulk_dir):
            result = runner.invoke(
                app, ["coordinate", "bulk", "clean", "--older-than", "30"]
            )
            assert result.exit_code == 0
            assert (
                "nothing" in result.output.lower() or "no db" in result.output.lower()
            )


# ---------------------------------------------------------------------------
# COORDINATE_BULK API type tests
# ---------------------------------------------------------------------------


class TestBulkApiType:
    """Test that bulk commands use APIType.COORDINATE_BULK for authentication."""

    def test_get_coord_sdk_passes_coordinate_bulk_api_type(self):
        """_get_coord_sdk must pass APIType.COORDINATE_BULK to _get_sdk."""
        from anncsu.common.config import APIType

        with patch("anncsu.cli.commands.coordinate._get_sdk") as mock_get_sdk:
            mock_get_sdk.return_value = (MagicMock(), MagicMock())

            from anncsu.cli.commands.bulk import _get_coord_sdk

            _get_coord_sdk(
                token_endpoint="https://example.com/token",
                server_url="https://example.com/api",
                verify_ssl=True,
            )

            mock_get_sdk.assert_called_once()
            call_kwargs = mock_get_sdk.call_args[1]
            assert call_kwargs["api_type"] == APIType.COORDINATE_BULK

    def test_get_coord_sdk_does_not_use_coordinate_api_type(self):
        """Ensure bulk commands do NOT use the single-record COORDINATE purpose ID."""
        from anncsu.common.config import APIType

        with patch("anncsu.cli.commands.coordinate._get_sdk") as mock_get_sdk:
            mock_get_sdk.return_value = (MagicMock(), MagicMock())

            from anncsu.cli.commands.bulk import _get_coord_sdk

            _get_coord_sdk(
                token_endpoint="https://example.com/token",
                server_url="https://example.com/api",
                verify_ssl=True,
            )

            call_kwargs = mock_get_sdk.call_args[1]
            assert call_kwargs.get("api_type") != APIType.COORDINATE


# ---------------------------------------------------------------------------
# SDK-dependent command tests (update, dry-run, resume)
# ---------------------------------------------------------------------------


class TestBulkUpdate:
    """Test 'anncsu coordinate bulk update' command."""

    def test_update_calls_get_coord_sdk(self, tmp_path):
        """Verify that bulk update calls _get_coord_sdk (which uses COORDINATE_BULK)."""
        csv_file = _write_csv(tmp_path / "test.csv", VALID_CSV)
        bulk_dir = tmp_path / "bulk"

        mock_sdk = MagicMock()
        mock_sdk.json_post.gestionecoordinate.return_value = _make_api_response()

        with (
            patch("anncsu.cli.commands.bulk._get_bulk_dir", return_value=bulk_dir),
            patch(
                "anncsu.cli.commands.bulk._get_coord_sdk",
                return_value=(mock_sdk, MagicMock()),
            ) as mock_get_sdk,
        ):
            result = runner.invoke(app, ["coordinate", "bulk", "update", str(csv_file)])
            assert result.exit_code == 0
            # Verify _get_coord_sdk was called (it internally uses COORDINATE_BULK)
            mock_get_sdk.assert_called_once()

    def test_update_succeeds_with_valid_csv(self, tmp_path):
        csv_file = _write_csv(tmp_path / "test.csv", VALID_CSV)
        bulk_dir = tmp_path / "bulk"

        mock_sdk = MagicMock()
        mock_sdk.json_post.gestionecoordinate.return_value = _make_api_response()

        with (
            patch("anncsu.cli.commands.bulk._get_bulk_dir", return_value=bulk_dir),
            patch(
                "anncsu.cli.commands.bulk._get_coord_sdk",
                return_value=(mock_sdk, MagicMock()),
            ),
        ):
            result = runner.invoke(app, ["coordinate", "bulk", "update", str(csv_file)])
            assert result.exit_code == 0
            assert "succeeded" in result.output.lower()

    def test_update_json_output(self, tmp_path):
        csv_file = _write_csv(tmp_path / "test.csv", VALID_CSV)
        bulk_dir = tmp_path / "bulk"

        mock_sdk = MagicMock()
        mock_sdk.json_post.gestionecoordinate.return_value = _make_api_response()

        with (
            patch("anncsu.cli.commands.bulk._get_bulk_dir", return_value=bulk_dir),
            patch(
                "anncsu.cli.commands.bulk._get_coord_sdk",
                return_value=(mock_sdk, MagicMock()),
            ),
        ):
            result = runner.invoke(
                app, ["coordinate", "bulk", "update", str(csv_file), "--json"]
            )
            assert result.exit_code == 0
            data = json.loads(result.output)
            assert "run_id" in data
            assert "processed" in data
            assert "succeeded" in data
            assert data["codcom"] == "A062"

    def test_update_creates_bulk_dir(self, tmp_path):
        csv_file = _write_csv(tmp_path / "test.csv", VALID_CSV)
        bulk_dir = tmp_path / "bulk"
        assert not bulk_dir.exists()

        mock_sdk = MagicMock()
        mock_sdk.json_post.gestionecoordinate.return_value = _make_api_response()

        with (
            patch("anncsu.cli.commands.bulk._get_bulk_dir", return_value=bulk_dir),
            patch(
                "anncsu.cli.commands.bulk._get_coord_sdk",
                return_value=(mock_sdk, MagicMock()),
            ),
        ):
            result = runner.invoke(app, ["coordinate", "bulk", "update", str(csv_file)])
            assert result.exit_code == 0
            assert bulk_dir.exists()

    def test_update_creates_db_file(self, tmp_path):
        csv_file = _write_csv(tmp_path / "test.csv", VALID_CSV)
        bulk_dir = tmp_path / "bulk"

        mock_sdk = MagicMock()
        mock_sdk.json_post.gestionecoordinate.return_value = _make_api_response()

        with (
            patch("anncsu.cli.commands.bulk._get_bulk_dir", return_value=bulk_dir),
            patch(
                "anncsu.cli.commands.bulk._get_coord_sdk",
                return_value=(mock_sdk, MagicMock()),
            ),
        ):
            result = runner.invoke(
                app, ["coordinate", "bulk", "update", str(csv_file), "--json"]
            )
            assert result.exit_code == 0
            data = json.loads(result.output)
            db_path = Path(data["db_path"])
            assert db_path.exists()

    def test_update_max_records_option(self, tmp_path):
        """Verify --max-records is passed to BulkExecutor."""
        csv_file = _write_csv(tmp_path / "test.csv", VALID_CSV_5_ROWS)
        bulk_dir = tmp_path / "bulk"

        mock_sdk = MagicMock()
        mock_sdk.json_post.gestionecoordinate.return_value = _make_api_response()

        from anncsu.coordinate.bulk.executor import BulkExecutorResult

        with (
            patch("anncsu.cli.commands.bulk._get_bulk_dir", return_value=bulk_dir),
            patch(
                "anncsu.cli.commands.bulk._get_coord_sdk",
                return_value=(mock_sdk, MagicMock()),
            ),
            patch("anncsu.cli.commands.bulk.BulkExecutor") as mock_executor_cls,
        ):
            mock_executor = MagicMock()
            mock_executor.execute.return_value = BulkExecutorResult(
                processed=2, succeeded=2, failed=0, run_id="test"
            )
            mock_executor_cls.return_value = mock_executor

            result = runner.invoke(
                app,
                [
                    "coordinate",
                    "bulk",
                    "update",
                    str(csv_file),
                    "--max-records",
                    "2",
                    "--json",
                ],
            )
            assert result.exit_code == 0
            # Verify BulkExecutor was instantiated with max_records=2
            call_kwargs = mock_executor_cls.call_args[1]
            assert call_kwargs["max_records"] == 2

    def test_update_max_records_json_output_shows_limit(self, tmp_path):
        """Verify JSON output includes max_records when specified."""
        csv_file = _write_csv(tmp_path / "test.csv", VALID_CSV_5_ROWS)
        bulk_dir = tmp_path / "bulk"

        mock_sdk = MagicMock()
        mock_sdk.json_post.gestionecoordinate.return_value = _make_api_response()

        from anncsu.coordinate.bulk.executor import BulkExecutorResult

        with (
            patch("anncsu.cli.commands.bulk._get_bulk_dir", return_value=bulk_dir),
            patch(
                "anncsu.cli.commands.bulk._get_coord_sdk",
                return_value=(mock_sdk, MagicMock()),
            ),
            patch("anncsu.cli.commands.bulk.BulkExecutor") as mock_executor_cls,
        ):
            mock_executor = MagicMock()
            mock_executor.execute.return_value = BulkExecutorResult(
                processed=3, succeeded=3, failed=0, run_id="test"
            )
            mock_executor_cls.return_value = mock_executor

            result = runner.invoke(
                app,
                [
                    "coordinate",
                    "bulk",
                    "update",
                    str(csv_file),
                    "--max-records",
                    "3",
                    "--json",
                ],
            )
            assert result.exit_code == 0
            data = json.loads(result.output)
            assert data["max_records"] == 3

    def test_update_without_max_records_processes_all(self, tmp_path):
        """Verify that without --max-records, all rows are processed (no max_records kwarg)."""
        csv_file = _write_csv(tmp_path / "test.csv", VALID_CSV)
        bulk_dir = tmp_path / "bulk"

        mock_sdk = MagicMock()
        mock_sdk.json_post.gestionecoordinate.return_value = _make_api_response()

        from anncsu.coordinate.bulk.executor import BulkExecutorResult

        with (
            patch("anncsu.cli.commands.bulk._get_bulk_dir", return_value=bulk_dir),
            patch(
                "anncsu.cli.commands.bulk._get_coord_sdk",
                return_value=(mock_sdk, MagicMock()),
            ),
            patch("anncsu.cli.commands.bulk.BulkExecutor") as mock_executor_cls,
        ):
            mock_executor = MagicMock()
            mock_executor.execute.return_value = BulkExecutorResult(
                processed=2, succeeded=2, failed=0, run_id="test"
            )
            mock_executor_cls.return_value = mock_executor

            result = runner.invoke(
                app, ["coordinate", "bulk", "update", str(csv_file), "--json"]
            )
            assert result.exit_code == 0
            # Verify BulkExecutor was NOT given max_records (or max_records=None)
            call_kwargs = mock_executor_cls.call_args[1]
            assert call_kwargs.get("max_records") is None

    def test_update_max_records_limits_actual_processing(self, tmp_path):
        """Integration test: max_records actually limits rows processed by executor."""
        csv_file = _write_csv(tmp_path / "test.csv", VALID_CSV_5_ROWS)
        bulk_dir = tmp_path / "bulk"

        mock_sdk = MagicMock()
        mock_sdk.json_post.gestionecoordinate.return_value = _make_api_response()

        with (
            patch("anncsu.cli.commands.bulk._get_bulk_dir", return_value=bulk_dir),
            patch(
                "anncsu.cli.commands.bulk._get_coord_sdk",
                return_value=(mock_sdk, MagicMock()),
            ),
        ):
            result = runner.invoke(
                app,
                [
                    "coordinate",
                    "bulk",
                    "update",
                    str(csv_file),
                    "--max-records",
                    "2",
                    "--json",
                ],
            )
            assert result.exit_code == 0
            data = json.loads(result.output)
            assert data["processed"] == 2
            assert data["succeeded"] == 2
            assert data["valid_rows"] == 5

    def test_update_json_includes_timing_stats(self, tmp_path):
        """JSON output should include timing statistics."""
        csv_file = _write_csv(tmp_path / "test.csv", VALID_CSV)
        bulk_dir = tmp_path / "bulk"

        mock_sdk = MagicMock()
        mock_sdk.json_post.gestionecoordinate.return_value = _make_api_response()

        with (
            patch("anncsu.cli.commands.bulk._get_bulk_dir", return_value=bulk_dir),
            patch(
                "anncsu.cli.commands.bulk._get_coord_sdk",
                return_value=(mock_sdk, MagicMock()),
            ),
        ):
            result = runner.invoke(
                app, ["coordinate", "bulk", "update", str(csv_file), "--json"]
            )
            assert result.exit_code == 0
            data = json.loads(result.output)
            assert "timing" in data
            timing = data["timing"]
            assert "total_elapsed_ms" in timing
            assert "avg_elapsed_ms" in timing
            assert "min_elapsed_ms" in timing
            assert "max_elapsed_ms" in timing
            assert "estimated_50k_minutes" in timing
            assert timing["avg_elapsed_ms"] >= 0

    def test_update_rate_limit_handled(self, tmp_path):
        csv_file = _write_csv(tmp_path / "test.csv", VALID_CSV)
        bulk_dir = tmp_path / "bulk"

        mock_sdk = MagicMock()
        mock_sdk.json_post.gestionecoordinate.return_value = _make_api_response()

        from anncsu.coordinate.bulk.executor import RateLimitReached

        with (
            patch("anncsu.cli.commands.bulk._get_bulk_dir", return_value=bulk_dir),
            patch(
                "anncsu.cli.commands.bulk._get_coord_sdk",
                return_value=(mock_sdk, MagicMock()),
            ),
            patch("anncsu.cli.commands.bulk.BulkExecutor") as mock_executor_cls,
        ):
            executor_instance = MagicMock()
            executor_instance.execute.side_effect = RateLimitReached(
                processed=1, remaining=1, run_id="test-run"
            )
            mock_executor_cls.return_value = executor_instance

            result = runner.invoke(
                app, ["coordinate", "bulk", "update", str(csv_file), "--json"]
            )
            assert result.exit_code == 1
            data = json.loads(result.output)
            assert data["rate_limited"] is True


class TestBulkDryRun:
    """Test 'anncsu coordinate bulk dry-run' command."""

    def test_dry_run_calls_get_coord_sdk(self, tmp_path):
        """Verify that bulk dry-run calls _get_coord_sdk (which uses COORDINATE_BULK)."""
        csv_file = _write_csv(tmp_path / "test.csv", VALID_CSV)
        bulk_dir = tmp_path / "bulk"

        mock_coord_sdk = MagicMock()
        mock_coord_sdk.json_post.gestionecoordinate.return_value = _make_api_response()
        mock_consult_sdk = MagicMock()
        mock_consult_sdk.queryparam.prognazacc_get_query_param.return_value = (
            _make_lookup_response()
        )

        with (
            patch("anncsu.cli.commands.bulk._get_bulk_dir", return_value=bulk_dir),
            patch(
                "anncsu.cli.commands.bulk._get_coord_sdk",
                return_value=(mock_coord_sdk, MagicMock()),
            ) as mock_get_coord,
            patch(
                "anncsu.cli.commands.bulk._get_consult_sdk_lazy",
                return_value=mock_consult_sdk,
            ),
        ):
            result = runner.invoke(
                app, ["coordinate", "bulk", "dry-run", str(csv_file)]
            )
            assert result.exit_code == 0
            # Verify _get_coord_sdk was called (it internally uses COORDINATE_BULK)
            mock_get_coord.assert_called_once()

    def test_dry_run_succeeds(self, tmp_path):
        csv_file = _write_csv(tmp_path / "test.csv", VALID_CSV)
        bulk_dir = tmp_path / "bulk"

        mock_coord_sdk = MagicMock()
        mock_coord_sdk.json_post.gestionecoordinate.return_value = _make_api_response()
        mock_consult_sdk = MagicMock()
        mock_consult_sdk.queryparam.prognazacc_get_query_param.return_value = (
            _make_lookup_response()
        )

        with (
            patch("anncsu.cli.commands.bulk._get_bulk_dir", return_value=bulk_dir),
            patch(
                "anncsu.cli.commands.bulk._get_coord_sdk",
                return_value=(mock_coord_sdk, MagicMock()),
            ),
            patch(
                "anncsu.cli.commands.bulk._get_consult_sdk_lazy",
                return_value=mock_consult_sdk,
            ),
        ):
            result = runner.invoke(
                app, ["coordinate", "bulk", "dry-run", str(csv_file)]
            )
            assert result.exit_code == 0

    def test_dry_run_json_output(self, tmp_path):
        csv_file = _write_csv(tmp_path / "test.csv", VALID_CSV)
        bulk_dir = tmp_path / "bulk"

        mock_coord_sdk = MagicMock()
        mock_coord_sdk.json_post.gestionecoordinate.return_value = _make_api_response()
        mock_consult_sdk = MagicMock()
        mock_consult_sdk.queryparam.prognazacc_get_query_param.return_value = (
            _make_lookup_response()
        )

        with (
            patch("anncsu.cli.commands.bulk._get_bulk_dir", return_value=bulk_dir),
            patch(
                "anncsu.cli.commands.bulk._get_coord_sdk",
                return_value=(mock_coord_sdk, MagicMock()),
            ),
            patch(
                "anncsu.cli.commands.bulk._get_consult_sdk_lazy",
                return_value=mock_consult_sdk,
            ),
        ):
            result = runner.invoke(
                app, ["coordinate", "bulk", "dry-run", str(csv_file), "--json"]
            )
            assert result.exit_code == 0
            data = json.loads(result.output)
            assert "total_tested" in data
            assert "updates_succeeded" in data
            assert "restores_succeeded" in data
            assert "run_id" in data

    def test_dry_run_max_records_option(self, tmp_path):
        csv_file = _write_csv(tmp_path / "test.csv", VALID_CSV)
        bulk_dir = tmp_path / "bulk"

        mock_coord_sdk = MagicMock()
        mock_coord_sdk.json_post.gestionecoordinate.return_value = _make_api_response()
        mock_consult_sdk = MagicMock()
        mock_consult_sdk.queryparam.prognazacc_get_query_param.return_value = (
            _make_lookup_response()
        )

        with (
            patch("anncsu.cli.commands.bulk._get_bulk_dir", return_value=bulk_dir),
            patch(
                "anncsu.cli.commands.bulk._get_coord_sdk",
                return_value=(mock_coord_sdk, MagicMock()),
            ),
            patch(
                "anncsu.cli.commands.bulk._get_consult_sdk_lazy",
                return_value=mock_consult_sdk,
            ),
            patch("anncsu.coordinate.bulk.dryrun.BulkDryRunner") as mock_runner_cls,
        ):
            from anncsu.coordinate.bulk.dryrun import DryRunResult

            mock_runner = MagicMock()
            mock_runner.execute.return_value = DryRunResult(
                total_tested=1,
                updates_succeeded=1,
                updates_failed=0,
                restores_succeeded=1,
                restores_failed=0,
                lookup_failures=0,
                run_id="test",
            )
            mock_runner_cls.return_value = mock_runner

            result = runner.invoke(
                app,
                [
                    "coordinate",
                    "bulk",
                    "dry-run",
                    str(csv_file),
                    "--max-records",
                    "3",
                    "--json",
                ],
            )
            assert result.exit_code == 0
            # Verify BulkDryRunner was instantiated with max_records=3
            call_kwargs = mock_runner_cls.call_args[1]
            assert call_kwargs["max_records"] == 3

    def test_dry_run_exits_1_on_restore_failure(self, tmp_path):
        csv_file = _write_csv(tmp_path / "test.csv", VALID_CSV)
        bulk_dir = tmp_path / "bulk"

        with (
            patch("anncsu.cli.commands.bulk._get_bulk_dir", return_value=bulk_dir),
            patch(
                "anncsu.cli.commands.bulk._get_coord_sdk",
                return_value=(MagicMock(), MagicMock()),
            ),
            patch(
                "anncsu.cli.commands.bulk._get_consult_sdk_lazy",
                return_value=MagicMock(),
            ),
            patch("anncsu.coordinate.bulk.dryrun.BulkDryRunner") as mock_runner_cls,
        ):
            from anncsu.coordinate.bulk.dryrun import DryRunResult

            mock_runner = MagicMock()
            mock_runner.execute.return_value = DryRunResult(
                total_tested=2,
                updates_succeeded=2,
                updates_failed=0,
                restores_succeeded=1,
                restores_failed=1,
                lookup_failures=0,
                run_id="test",
            )
            mock_runner_cls.return_value = mock_runner

            result = runner.invoke(
                app, ["coordinate", "bulk", "dry-run", str(csv_file), "--json"]
            )
            assert result.exit_code == 1


class TestBulkResume:
    """Test 'anncsu coordinate bulk resume' command."""

    def test_resume_calls_get_coord_sdk(self, tmp_path):
        """Verify that bulk resume calls _get_coord_sdk (which uses COORDINATE_BULK)."""
        bulk_dir = tmp_path / "bulk"
        bulk_dir.mkdir()
        csv_file = _write_csv(tmp_path / "test.csv", VALID_CSV)

        db_path = str(bulk_dir / "A062_test.db")
        with BulkDB(db_path) as db:
            import_result = import_csv(db=db, csv_path=csv_file, mode="update")
            run_id = import_result.run_id

        actual_path = bulk_dir / f"A062_{run_id}.db"
        os.rename(db_path, actual_path)

        mock_sdk = MagicMock()
        mock_sdk.json_post.gestionecoordinate.return_value = _make_api_response()

        with (
            patch("anncsu.cli.commands.bulk._get_bulk_dir", return_value=bulk_dir),
            patch(
                "anncsu.cli.commands.bulk._get_coord_sdk",
                return_value=(mock_sdk, MagicMock()),
            ) as mock_get_sdk,
        ):
            result = runner.invoke(app, ["coordinate", "bulk", "resume", run_id])
            assert result.exit_code == 0
            # Verify _get_coord_sdk was called (it internally uses COORDINATE_BULK)
            mock_get_sdk.assert_called_once()

    def test_resume_run_not_found(self, tmp_path):
        with patch(
            "anncsu.cli.commands.bulk._get_bulk_dir", return_value=tmp_path / "bulk"
        ):
            result = runner.invoke(
                app, ["coordinate", "bulk", "resume", "nonexistent-run-id"]
            )
            assert result.exit_code != 0

    def test_resume_succeeds(self, tmp_path):
        bulk_dir = tmp_path / "bulk"
        bulk_dir.mkdir()
        csv_file = _write_csv(tmp_path / "test.csv", VALID_CSV)

        # Create a DB with a partially completed run
        db_path = str(bulk_dir / "A062_test.db")
        with BulkDB(db_path) as db:
            import_result = import_csv(db=db, csv_path=csv_file, mode="update")
            run_id = import_result.run_id
            # Mark first row as done
            db.update_row_status(row_id=1, status=RowStatus.DONE)
            db.insert_result(
                row_id=1,
                run_id=run_id,
                operation="update",
                esito="0",
                messaggio="OK",
            )

        # Rename to match run_id
        actual_path = bulk_dir / f"A062_{run_id}.db"
        os.rename(db_path, actual_path)

        mock_sdk = MagicMock()
        mock_sdk.json_post.gestionecoordinate.return_value = _make_api_response()

        with (
            patch("anncsu.cli.commands.bulk._get_bulk_dir", return_value=bulk_dir),
            patch(
                "anncsu.cli.commands.bulk._get_coord_sdk",
                return_value=(mock_sdk, MagicMock()),
            ),
        ):
            result = runner.invoke(app, ["coordinate", "bulk", "resume", run_id])
            assert result.exit_code == 0
            assert "succeeded" in result.output.lower()

    def test_resume_fails_for_dryrun_mode(self, tmp_path):
        bulk_dir = tmp_path / "bulk"
        bulk_dir.mkdir()
        csv_file = _write_csv(tmp_path / "test.csv", VALID_CSV)

        db_path = str(bulk_dir / "A062_test.db")
        with BulkDB(db_path) as db:
            import_result = import_csv(db=db, csv_path=csv_file, mode="dryrun")
            run_id = import_result.run_id

        actual_path = bulk_dir / f"A062_{run_id}.db"
        os.rename(db_path, actual_path)

        with patch("anncsu.cli.commands.bulk._get_bulk_dir", return_value=bulk_dir):
            result = runner.invoke(app, ["coordinate", "bulk", "resume", run_id])
            assert result.exit_code != 0
            assert "cannot resume" in result.output.lower()

    def test_resume_json_output(self, tmp_path):
        """Resume JSON output must include timing stats like update does."""
        bulk_dir = tmp_path / "bulk"
        bulk_dir.mkdir()
        csv_file = _write_csv(tmp_path / "test.csv", VALID_CSV)

        db_path = str(bulk_dir / "A062_test.db")
        with BulkDB(db_path) as db:
            import_result = import_csv(db=db, csv_path=csv_file, mode="update")
            run_id = import_result.run_id

        actual_path = bulk_dir / f"A062_{run_id}.db"
        os.rename(db_path, actual_path)

        mock_sdk = MagicMock()
        mock_sdk.json_post.gestionecoordinate.return_value = _make_api_response()

        mock_refresher = MagicMock(return_value="new-token")

        with (
            patch("anncsu.cli.commands.bulk._get_bulk_dir", return_value=bulk_dir),
            patch(
                "anncsu.cli.commands.bulk._get_coord_sdk",
                return_value=(mock_sdk, mock_refresher),
            ),
        ):
            result = runner.invoke(
                app, ["coordinate", "bulk", "resume", run_id, "--json"]
            )
            assert result.exit_code == 0
            data = json.loads(result.output)
            assert data["run_id"] == run_id
            assert "processed" in data
            assert "succeeded" in data
            # Parity with update JSON output
            assert "db_path" in data
            assert "max_records" in data
            assert "timing" in data
            timing = data["timing"]
            assert "total_elapsed_ms" in timing
            assert "avg_elapsed_ms" in timing
            assert "min_elapsed_ms" in timing
            assert "max_elapsed_ms" in timing
            assert "estimated_50k_minutes" in timing

    def test_resume_max_records_option(self, tmp_path):
        """Verify --max-records is passed to BulkExecutor on resume."""
        bulk_dir = tmp_path / "bulk"
        bulk_dir.mkdir()
        csv_file = _write_csv(tmp_path / "test.csv", VALID_CSV_5_ROWS)

        db_path = str(bulk_dir / "A062_test.db")
        with BulkDB(db_path) as db:
            import_result = import_csv(db=db, csv_path=csv_file, mode="update")
            run_id = import_result.run_id

        actual_path = bulk_dir / f"A062_{run_id}.db"
        os.rename(db_path, actual_path)

        mock_sdk = MagicMock()

        from anncsu.coordinate.bulk.executor import BulkExecutorResult

        with (
            patch("anncsu.cli.commands.bulk._get_bulk_dir", return_value=bulk_dir),
            patch(
                "anncsu.cli.commands.bulk._get_coord_sdk",
                return_value=(mock_sdk, MagicMock()),
            ),
            patch("anncsu.cli.commands.bulk.BulkExecutor") as mock_executor_cls,
        ):
            mock_executor = MagicMock()
            mock_executor.execute.return_value = BulkExecutorResult(
                processed=2, succeeded=2, failed=0, run_id=run_id
            )
            mock_executor_cls.return_value = mock_executor

            result = runner.invoke(
                app,
                [
                    "coordinate",
                    "bulk",
                    "resume",
                    run_id,
                    "--max-records",
                    "2",
                    "--json",
                ],
            )
            assert result.exit_code == 0
            call_kwargs = mock_executor_cls.call_args[1]
            assert call_kwargs["max_records"] == 2

    def test_resume_without_max_records_passes_none(self, tmp_path):
        """Verify that without --max-records, max_records=None is passed."""
        bulk_dir = tmp_path / "bulk"
        bulk_dir.mkdir()
        csv_file = _write_csv(tmp_path / "test.csv", VALID_CSV)

        db_path = str(bulk_dir / "A062_test.db")
        with BulkDB(db_path) as db:
            import_result = import_csv(db=db, csv_path=csv_file, mode="update")
            run_id = import_result.run_id

        actual_path = bulk_dir / f"A062_{run_id}.db"
        os.rename(db_path, actual_path)

        mock_sdk = MagicMock()

        from anncsu.coordinate.bulk.executor import BulkExecutorResult

        with (
            patch("anncsu.cli.commands.bulk._get_bulk_dir", return_value=bulk_dir),
            patch(
                "anncsu.cli.commands.bulk._get_coord_sdk",
                return_value=(mock_sdk, MagicMock()),
            ),
            patch("anncsu.cli.commands.bulk.BulkExecutor") as mock_executor_cls,
        ):
            mock_executor = MagicMock()
            mock_executor.execute.return_value = BulkExecutorResult(
                processed=2, succeeded=2, failed=0, run_id=run_id
            )
            mock_executor_cls.return_value = mock_executor

            result = runner.invoke(
                app, ["coordinate", "bulk", "resume", run_id, "--json"]
            )
            assert result.exit_code == 0
            call_kwargs = mock_executor_cls.call_args[1]
            assert call_kwargs.get("max_records") is None


# ---------------------------------------------------------------------------
# Token refresh wiring tests
# ---------------------------------------------------------------------------


class TestBulkTokenRefreshWiring:
    """Test that bulk commands wire token_refresher into BulkExecutor."""

    def test_update_passes_token_refresher_to_executor(self, tmp_path):
        """bulk update must pass token_refresher from _get_coord_sdk to BulkExecutor."""
        csv_file = _write_csv(tmp_path / "test.csv", VALID_CSV)
        bulk_dir = tmp_path / "bulk"

        mock_sdk = MagicMock()
        mock_refresher = MagicMock(return_value="new-token")

        from anncsu.coordinate.bulk.executor import BulkExecutorResult

        with (
            patch("anncsu.cli.commands.bulk._get_bulk_dir", return_value=bulk_dir),
            patch(
                "anncsu.cli.commands.bulk._get_coord_sdk",
                return_value=(mock_sdk, mock_refresher),
            ),
            patch("anncsu.cli.commands.bulk.BulkExecutor") as mock_executor_cls,
        ):
            mock_executor = MagicMock()
            mock_executor.execute.return_value = BulkExecutorResult(
                processed=2, succeeded=2, failed=0, run_id="test"
            )
            mock_executor_cls.return_value = mock_executor

            result = runner.invoke(
                app,
                ["coordinate", "bulk", "update", str(csv_file), "--json"],
            )
            assert result.exit_code == 0
            call_kwargs = mock_executor_cls.call_args[1]
            assert call_kwargs["token_refresher"] is mock_refresher

    def test_update_non_json_passes_token_refresher(self, tmp_path):
        """bulk update (non-JSON mode with progress bar) must also pass token_refresher."""
        csv_file = _write_csv(tmp_path / "test.csv", VALID_CSV)
        bulk_dir = tmp_path / "bulk"

        mock_sdk = MagicMock()
        mock_refresher = MagicMock(return_value="new-token")

        from anncsu.coordinate.bulk.executor import BulkExecutorResult

        with (
            patch("anncsu.cli.commands.bulk._get_bulk_dir", return_value=bulk_dir),
            patch(
                "anncsu.cli.commands.bulk._get_coord_sdk",
                return_value=(mock_sdk, mock_refresher),
            ),
            patch("anncsu.cli.commands.bulk.BulkExecutor") as mock_executor_cls,
        ):
            mock_executor = MagicMock()
            mock_executor.execute.return_value = BulkExecutorResult(
                processed=2, succeeded=2, failed=0, run_id="test"
            )
            mock_executor_cls.return_value = mock_executor

            result = runner.invoke(
                app,
                ["coordinate", "bulk", "update", str(csv_file)],
            )
            assert result.exit_code == 0
            call_kwargs = mock_executor_cls.call_args[1]
            assert call_kwargs["token_refresher"] is mock_refresher

    def test_resume_passes_token_refresher_to_executor(self, tmp_path):
        """bulk resume must pass token_refresher from _get_coord_sdk to BulkExecutor."""
        bulk_dir = tmp_path / "bulk"
        bulk_dir.mkdir()
        csv_file = _write_csv(tmp_path / "test.csv", VALID_CSV)

        db_path = str(bulk_dir / "A062_test.db")
        with BulkDB(db_path) as db:
            import_result = import_csv(db=db, csv_path=csv_file, mode="update")
            run_id = import_result.run_id

        actual_path = bulk_dir / f"A062_{run_id}.db"
        os.rename(db_path, actual_path)

        mock_sdk = MagicMock()
        mock_refresher = MagicMock(return_value="new-token")

        from anncsu.coordinate.bulk.executor import BulkExecutorResult

        with (
            patch("anncsu.cli.commands.bulk._get_bulk_dir", return_value=bulk_dir),
            patch(
                "anncsu.cli.commands.bulk._get_coord_sdk",
                return_value=(mock_sdk, mock_refresher),
            ),
            patch("anncsu.cli.commands.bulk.BulkExecutor") as mock_executor_cls,
        ):
            mock_executor = MagicMock()
            mock_executor.execute.return_value = BulkExecutorResult(
                processed=1, succeeded=1, failed=0, run_id=run_id
            )
            mock_executor_cls.return_value = mock_executor

            result = runner.invoke(
                app, ["coordinate", "bulk", "resume", run_id, "--json"]
            )
            assert result.exit_code == 0
            call_kwargs = mock_executor_cls.call_args[1]
            assert call_kwargs["token_refresher"] is mock_refresher

    def test_resume_non_json_passes_token_refresher(self, tmp_path):
        """bulk resume (non-JSON mode) must also pass token_refresher."""
        bulk_dir = tmp_path / "bulk"
        bulk_dir.mkdir()
        csv_file = _write_csv(tmp_path / "test.csv", VALID_CSV)

        db_path = str(bulk_dir / "A062_test.db")
        with BulkDB(db_path) as db:
            import_result = import_csv(db=db, csv_path=csv_file, mode="update")
            run_id = import_result.run_id

        actual_path = bulk_dir / f"A062_{run_id}.db"
        os.rename(db_path, actual_path)

        mock_sdk = MagicMock()
        mock_refresher = MagicMock(return_value="new-token")

        from anncsu.coordinate.bulk.executor import BulkExecutorResult

        with (
            patch("anncsu.cli.commands.bulk._get_bulk_dir", return_value=bulk_dir),
            patch(
                "anncsu.cli.commands.bulk._get_coord_sdk",
                return_value=(mock_sdk, mock_refresher),
            ),
            patch("anncsu.cli.commands.bulk.BulkExecutor") as mock_executor_cls,
        ):
            mock_executor = MagicMock()
            mock_executor.execute.return_value = BulkExecutorResult(
                processed=1, succeeded=1, failed=0, run_id=run_id
            )
            mock_executor_cls.return_value = mock_executor

            result = runner.invoke(app, ["coordinate", "bulk", "resume", run_id])
            assert result.exit_code == 0
            call_kwargs = mock_executor_cls.call_args[1]
            assert call_kwargs["token_refresher"] is mock_refresher

    def test_get_coord_sdk_returns_tuple_with_refresher(self):
        """_get_coord_sdk must return (sdk, token_refresher) tuple."""
        with patch("anncsu.cli.commands.coordinate._get_sdk") as mock_get_sdk:
            mock_sdk = MagicMock()
            mock_manager = MagicMock()
            mock_manager.get_refresh_callback.return_value = lambda: "refreshed"
            mock_get_sdk.return_value = (mock_sdk, mock_manager)

            from anncsu.cli.commands.bulk import _get_coord_sdk

            result = _get_coord_sdk(
                token_endpoint="https://example.com/token",
                server_url="https://example.com/api",
                verify_ssl=True,
            )
            assert isinstance(result, tuple)
            assert len(result) == 2
            sdk, refresher = result
            assert sdk is mock_sdk
            assert callable(refresher)


# ---------------------------------------------------------------------------
# Run ID consistency tests (filename vs DB content)
# ---------------------------------------------------------------------------


class TestBulkRunIdConsistency:
    """Test that run_id in DB matches run_id in filename.

    Bug: bulk_update imports CSV twice — first to :memory: (run_id A used in
    filename), then to persistent DB (run_id B stored in DB). When user gets
    run_id B from JSON output, _find_db_for_run(B) can't find the file because
    the filename contains A.
    """

    def test_update_json_run_id_is_findable(self, tmp_path):
        """The run_id in JSON output must be findable by _find_db_for_run."""
        csv_file = _write_csv(tmp_path / "test.csv", VALID_CSV)
        bulk_dir = tmp_path / "bulk"

        mock_sdk = MagicMock()
        mock_sdk.json_post.gestionecoordinate.return_value = _make_api_response()

        with (
            patch("anncsu.cli.commands.bulk._get_bulk_dir", return_value=bulk_dir),
            patch(
                "anncsu.cli.commands.bulk._get_coord_sdk",
                return_value=(mock_sdk, MagicMock()),
            ),
        ):
            result = runner.invoke(
                app, ["coordinate", "bulk", "update", str(csv_file), "--json"]
            )
            assert result.exit_code == 0
            data = json.loads(result.output)
            run_id = data["run_id"]

            # The run_id from JSON output must be findable
            from anncsu.cli.commands.bulk import _find_db_for_run

            with patch("anncsu.cli.commands.bulk._get_bulk_dir", return_value=bulk_dir):
                found = _find_db_for_run(run_id)
                assert found is not None, (
                    f"run_id={run_id} from JSON output not found in "
                    f"bulk dir files: {list(bulk_dir.glob('*.db'))}"
                )

    def test_update_then_resume_works_end_to_end(self, tmp_path):
        """Run bulk update, get run_id from JSON, then resume with that run_id."""
        csv_file = _write_csv(tmp_path / "test.csv", VALID_CSV)
        bulk_dir = tmp_path / "bulk"

        mock_sdk = MagicMock()
        mock_sdk.json_post.gestionecoordinate.return_value = _make_api_response()

        # Step 1: run bulk update
        with (
            patch("anncsu.cli.commands.bulk._get_bulk_dir", return_value=bulk_dir),
            patch(
                "anncsu.cli.commands.bulk._get_coord_sdk",
                return_value=(mock_sdk, MagicMock()),
            ),
        ):
            update_result = runner.invoke(
                app, ["coordinate", "bulk", "update", str(csv_file), "--json"]
            )
            assert update_result.exit_code == 0
            data = json.loads(update_result.output)
            run_id = data["run_id"]

        # Step 2: resume with that run_id
        with (
            patch("anncsu.cli.commands.bulk._get_bulk_dir", return_value=bulk_dir),
            patch(
                "anncsu.cli.commands.bulk._get_coord_sdk",
                return_value=(mock_sdk, MagicMock()),
            ),
        ):
            resume_result = runner.invoke(
                app, ["coordinate", "bulk", "resume", run_id, "--json"]
            )
            assert resume_result.exit_code == 0, (
                f"Resume failed with: {resume_result.output}"
            )

    def test_update_then_status_works_end_to_end(self, tmp_path):
        """Run bulk update, get run_id from JSON, then check status."""
        csv_file = _write_csv(tmp_path / "test.csv", VALID_CSV)
        bulk_dir = tmp_path / "bulk"

        mock_sdk = MagicMock()
        mock_sdk.json_post.gestionecoordinate.return_value = _make_api_response()

        with (
            patch("anncsu.cli.commands.bulk._get_bulk_dir", return_value=bulk_dir),
            patch(
                "anncsu.cli.commands.bulk._get_coord_sdk",
                return_value=(mock_sdk, MagicMock()),
            ),
        ):
            update_result = runner.invoke(
                app, ["coordinate", "bulk", "update", str(csv_file), "--json"]
            )
            assert update_result.exit_code == 0
            data = json.loads(update_result.output)
            run_id = data["run_id"]

        with patch("anncsu.cli.commands.bulk._get_bulk_dir", return_value=bulk_dir):
            status_result = runner.invoke(
                app, ["coordinate", "bulk", "status", run_id, "--json"]
            )
            assert status_result.exit_code == 0, (
                f"Status failed with: {status_result.output}"
            )

    def test_dry_run_json_run_id_is_findable(self, tmp_path):
        """The run_id from dry-run JSON output must be findable."""
        csv_file = _write_csv(tmp_path / "test.csv", VALID_CSV)
        bulk_dir = tmp_path / "bulk"

        mock_coord_sdk = MagicMock()
        mock_coord_sdk.json_post.gestionecoordinate.return_value = _make_api_response()
        mock_consult_sdk = MagicMock()
        mock_consult_sdk.queryparam.prognazacc_get_query_param.return_value = (
            _make_lookup_response()
        )

        with (
            patch("anncsu.cli.commands.bulk._get_bulk_dir", return_value=bulk_dir),
            patch(
                "anncsu.cli.commands.bulk._get_coord_sdk",
                return_value=(mock_coord_sdk, MagicMock()),
            ),
            patch(
                "anncsu.cli.commands.bulk._get_consult_sdk_lazy",
                return_value=mock_consult_sdk,
            ),
        ):
            result = runner.invoke(
                app, ["coordinate", "bulk", "dry-run", str(csv_file), "--json"]
            )
            assert result.exit_code == 0
            data = json.loads(result.output)
            run_id = data["run_id"]

            from anncsu.cli.commands.bulk import _find_db_for_run

            with patch("anncsu.cli.commands.bulk._get_bulk_dir", return_value=bulk_dir):
                found = _find_db_for_run(run_id)
                assert found is not None, (
                    f"run_id={run_id} from dry-run JSON not found in "
                    f"bulk dir files: {list(bulk_dir.glob('*.db'))}"
                )
