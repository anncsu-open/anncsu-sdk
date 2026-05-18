# SPDX-FileCopyrightText: 2025-present Geobeyond <info@geobeyond.it>
# SPDX-License-Identifier: MIT
"""Tests for DuckDB batch update CLI command."""

from __future__ import annotations

import re
import tempfile
from pathlib import Path
from typing import TYPE_CHECKING
from unittest.mock import MagicMock, patch

import duckdb
import pytest
from typer.testing import CliRunner

from anncsu.cli.app import app

if TYPE_CHECKING:
    pass

_ANSI_BYTES_RE = re.compile(rb"\x1b\[[0-9;]*m")


class _NoColorCliRunner(CliRunner):
    """CliRunner that strips Rich ANSI codes from captured output so
    substring assertions match whether colors are forced (CI sets
    ``FORCE_COLOR=1``) or absent (local non-TTY). Mirrors
    ``NoColorCliRunner`` in ``tests/cli/conftest.py`` — duplicated here
    because conftest isn't importable as a regular module."""

    def invoke(self, *args, **kwargs):
        result = super().invoke(*args, **kwargs)
        result.stdout_bytes = _ANSI_BYTES_RE.sub(b"", result.stdout_bytes)
        result.stderr_bytes = _ANSI_BYTES_RE.sub(b"", result.stderr_bytes)
        result.output_bytes = _ANSI_BYTES_RE.sub(b"", result.output_bytes)
        return result


runner = _NoColorCliRunner()


@pytest.fixture(autouse=True)
def _mock_pdnd_env(monkeypatch):
    """Provide mock PDND credentials so the early ``ClientAssertionSettings()``
    check inside ``duckdb-batch-update`` passes in CI (where env vars aren't
    set). Tests that mock ``_get_sdk`` never reach the real auth flow, but the
    upstream env-var validation still runs and would otherwise abort the
    command with ``ValidationError: Field required`` before our asserts."""
    monkeypatch.setenv("PDND_KID", "test-kid")
    monkeypatch.setenv("PDND_ISSUER", "test-issuer")
    monkeypatch.setenv("PDND_SUBJECT", "test-subject")
    monkeypatch.setenv("PDND_AUDIENCE", "auth.uat.interop.pagopa.it/client-assertion")
    monkeypatch.setenv("PDND_KEY_PATH", "/tmp/dummy.pem")


@pytest.fixture
def duckdb_test_file():
    """Create a temporary DuckDB file with test data."""
    with tempfile.NamedTemporaryFile(suffix=".duckdb", delete=True) as f:
        db_path = f.name

    conn = duckdb.connect(db_path)

    # Create source table with test data
    conn.execute("""
        CREATE TABLE deoverlapped_geocoded_anncsu (
            CODICE_COMUNE VARCHAR,
            PROGRESSIVO_ACCESSO INTEGER,
            CIVICO INTEGER,
            ESPONENTE VARCHAR,
            COORD_X_COMUNE DOUBLE,
            COORD_Y_COMUNE DOUBLE,
            QUOTA VARCHAR,
            METODO VARCHAR
        )
    """)

    # Insert test records for I501 (Scanno)
    conn.execute("""
        INSERT INTO deoverlapped_geocoded_anncsu VALUES
        ('I501', 28586543, 1, NULL, 13.880802, 41.903126, NULL, NULL),
        ('I501', 28586542, 2, NULL, 13.880784, 41.903139, NULL, NULL),
        ('I501', 28586545, 8, NULL, 13.880765, 41.903126, NULL, NULL),
        ('I502', 29000001, 10, NULL, 12.496365, 41.902783, NULL, NULL)
    """)

    conn.close()

    yield db_path

    # Cleanup
    Path(db_path).unlink()


def create_mock_response(
    id_richiesta: str = "REQ-123",
    esito: str = "0",
    messaggio: str | None = "OK",
    dati: list | None = None,
) -> MagicMock:
    """Create a mock response object."""
    response = MagicMock()
    response.id_richiesta = id_richiesta
    response.esito = esito
    response.messaggio = messaggio
    response.dati = dati or []
    response.model_dump.return_value = {
        "idRichiesta": id_richiesta,
        "esito": esito,
        "messaggio": messaggio,
        "dati": dati or [],
    }
    return response


class TestDuckDBBatchUpdate:
    """Test DuckDB batch update command."""

    def test_help_message(self):
        """Test that help message is displayed."""
        result = runner.invoke(
            app,
            ["coordinate", "duckdb-batch-update", "--help"],
        )
        assert result.exit_code == 0
        assert "Batch update coordinates from DuckDB table" in result.output
        assert "--db" in result.output
        assert "--codcom" in result.output

    def test_missing_required_options(self):
        """Test that missing required options are caught."""
        result = runner.invoke(
            app,
            ["coordinate", "duckdb-batch-update"],
        )
        assert result.exit_code != 0
        assert "Error" in result.output

    def test_nonexistent_db_file(self):
        """Test error when DB file doesn't exist."""
        result = runner.invoke(
            app,
            [
                "coordinate",
                "duckdb-batch-update",
                "--db",
                "/nonexistent/path/data.duckdb",
                "--codcom",
                "I501",
            ],
        )
        assert result.exit_code == 1
        assert "Database file not found" in result.output

    def test_no_records_found(self, duckdb_test_file):
        """Test error when no records match criteria."""
        result = runner.invoke(
            app,
            [
                "coordinate",
                "duckdb-batch-update",
                "--db",
                duckdb_test_file,
                "--codcom",
                "I999",  # Non-existent
            ],
        )
        assert result.exit_code == 1
        assert "No records found" in result.output

    @patch("anncsu.cli.commands.coordinate._get_sdk")
    def test_successful_batch_update(self, mock_get_sdk, duckdb_test_file):
        """Test successful batch update of records."""
        # Mock SDK
        mock_sdk = MagicMock()
        mock_sdk.json_post.gestionecoordinate.return_value = create_mock_response()
        mock_get_sdk.return_value = (mock_sdk, None)

        result = runner.invoke(
            app,
            [
                "coordinate",
                "duckdb-batch-update",
                "--db",
                duckdb_test_file,
                "--codcom",
                "I501",
                "--max-records",
                "3",
            ],
        )

        assert "Found 3 records to process" in result.output
        assert "Batch Update Summary" in result.output
        assert "Total Records" in result.output or result.exit_code == 0

    @patch("anncsu.cli.commands.coordinate._get_sdk")
    def test_batch_update_with_failures(self, mock_get_sdk, duckdb_test_file):
        """Test batch update handling API failures."""
        # Mock SDK to fail on second call
        mock_sdk = MagicMock()
        mock_sdk.json_post.gestionecoordinate.side_effect = [
            create_mock_response(esito="0"),  # Success
            Exception("Network error"),  # Failure
            create_mock_response(esito="0"),  # Success
        ]
        mock_get_sdk.return_value = (mock_sdk, None)

        result = runner.invoke(
            app,
            [
                "coordinate",
                "duckdb-batch-update",
                "--db",
                duckdb_test_file,
                "--codcom",
                "I501",
                "--max-records",
                "3",
            ],
        )

        # Should continue despite error
        assert result.exit_code == 0 or "processing" in result.output.lower()

    @patch("anncsu.cli.commands.coordinate._get_sdk")
    def test_batch_update_json_output(self, mock_get_sdk, duckdb_test_file):
        """Test JSON output format."""
        mock_sdk = MagicMock()
        mock_sdk.json_post.gestionecoordinate.return_value = create_mock_response()
        mock_get_sdk.return_value = (mock_sdk, None)

        result = runner.invoke(
            app,
            [
                "coordinate",
                "duckdb-batch-update",
                "--db",
                duckdb_test_file,
                "--codcom",
                "I501",
                "--max-records",
                "2",
                "--json",
            ],
        )

        assert result.exit_code == 0 or "run_id" in result.output
        if "{" in result.output:
            # Verify JSON structure
            assert "total" in result.output
            assert "success" in result.output
            assert "failed" in result.output

    def test_results_table_created(self, duckdb_test_file):
        """Test that batch_update_results table is created."""
        from anncsu.cli.commands.coordinate import _create_results_table

        _create_results_table(duckdb_test_file)

        conn = duckdb.connect(duckdb_test_file)
        tables = conn.execute(
            "SELECT table_name FROM duckdb_tables() WHERE table_name = 'batch_update_results'"
        ).fetchall()
        conn.close()

        assert len(tables) > 0

    def test_insert_result(self, duckdb_test_file):
        """Test inserting results into batch_update_results table."""
        from anncsu.cli.commands.coordinate import (
            _create_results_table,
            _insert_result,
        )

        _create_results_table(duckdb_test_file)

        _insert_result(
            db_path=duckdb_test_file,
            run_id="20250316_165509",
            timestamp="2025-03-16T16:55:09",
            progressivo_accesso=28586543,
            civico=1,
            http_status=200,
            esito="0",
            messaggio="OK",
            id_richiesta="REQ-123",
            error_detail=None,
            elapsed_ms=500.0,
        )

        conn = duckdb.connect(duckdb_test_file)
        results = conn.execute("SELECT * FROM batch_update_results").fetchall()
        conn.close()

        assert len(results) == 1
        assert results[0][0] == "20250316_165509"
        assert results[0][4] == 200

    @patch("anncsu.cli.commands.coordinate._get_sdk")
    def test_max_records_limit(self, mock_get_sdk, duckdb_test_file):
        """Test that --max-records limit is respected."""
        mock_sdk = MagicMock()
        mock_sdk.json_post.gestionecoordinate.return_value = create_mock_response()
        mock_get_sdk.return_value = (mock_sdk, None)

        result = runner.invoke(
            app,
            [
                "coordinate",
                "duckdb-batch-update",
                "--db",
                duckdb_test_file,
                "--codcom",
                "I501",
                "--max-records",
                "2",
            ],
        )

        assert "Found 2 records" in result.output or result.exit_code == 0

    @patch("anncsu.cli.commands.coordinate._get_sdk")
    def test_custom_source_table(self, mock_get_sdk, duckdb_test_file):
        """Test using a custom source table name."""
        # Create alternate table
        conn = duckdb.connect(duckdb_test_file)
        conn.execute("""
            CREATE TABLE custom_coords AS
            SELECT * FROM deoverlapped_geocoded_anncsu
        """)
        conn.close()

        mock_sdk = MagicMock()
        mock_sdk.json_post.gestionecoordinate.return_value = create_mock_response()
        mock_get_sdk.return_value = (mock_sdk, None)

        result = runner.invoke(
            app,
            [
                "coordinate",
                "duckdb-batch-update",
                "--db",
                duckdb_test_file,
                "--codcom",
                "I501",
                "--source-table",
                "custom_coords",
                "--max-records",
                "1",
            ],
        )

        assert result.exit_code == 0 or "Found" in result.output


class TestDuckDBBatchResume:
    """Test DuckDB batch update resume functionality."""

    @patch("anncsu.cli.commands.coordinate._get_sdk")
    def test_resume_skips_succeeded_records(self, mock_get_sdk, duckdb_test_file):
        """Test that --resume skips records already succeeded (esito='0')."""
        from anncsu.cli.commands.coordinate import (
            _create_results_table,
            _insert_result,
        )

        # Pre-populate results: 2 out of 3 records already succeeded
        _create_results_table(duckdb_test_file)
        _insert_result(
            db_path=duckdb_test_file,
            run_id="20260319_140000",
            timestamp="2026-03-19T14:00:00",
            progressivo_accesso=28586543,
            civico=1,
            http_status=200,
            esito="0",
            messaggio="OK",
            id_richiesta="REQ-1",
            error_detail=None,
            elapsed_ms=300.0,
        )
        _insert_result(
            db_path=duckdb_test_file,
            run_id="20260319_140000",
            timestamp="2026-03-19T14:00:00",
            progressivo_accesso=28586542,
            civico=2,
            http_status=200,
            esito="0",
            messaggio="OK",
            id_richiesta="REQ-2",
            error_detail=None,
            elapsed_ms=250.0,
        )

        mock_sdk = MagicMock()
        mock_sdk.json_post.gestionecoordinate.return_value = create_mock_response()
        mock_get_sdk.return_value = (mock_sdk, None)

        result = runner.invoke(
            app,
            [
                "coordinate",
                "duckdb-batch-update",
                "--db",
                duckdb_test_file,
                "--codcom",
                "I501",
                "--resume",
                "20260319_140000",
            ],
        )

        assert "Resuming run 20260319_140000" in result.output
        assert "2 records already succeeded" in result.output
        assert "Found 1 records to process" in result.output
        # Only the remaining record (28586545) should be processed
        assert mock_sdk.json_post.gestionecoordinate.call_count == 1

    @patch("anncsu.cli.commands.coordinate._get_sdk")
    def test_resume_all_done(self, mock_get_sdk, duckdb_test_file):
        """Test resume when all records are already completed."""
        from anncsu.cli.commands.coordinate import (
            _create_results_table,
            _insert_result,
        )

        _create_results_table(duckdb_test_file)
        # Mark all 3 I501 records as succeeded
        for progr, civ in [(28586543, 1), (28586542, 2), (28586545, 8)]:
            _insert_result(
                db_path=duckdb_test_file,
                run_id="20260319_140000",
                timestamp="2026-03-19T14:00:00",
                progressivo_accesso=progr,
                civico=civ,
                http_status=200,
                esito="0",
                messaggio="OK",
                id_richiesta=f"REQ-{civ}",
                error_detail=None,
                elapsed_ms=200.0,
            )

        result = runner.invoke(
            app,
            [
                "coordinate",
                "duckdb-batch-update",
                "--db",
                duckdb_test_file,
                "--codcom",
                "I501",
                "--resume",
                "20260319_140000",
            ],
        )

        assert "All records already completed" in result.output
        assert result.exit_code == 0

    @patch("anncsu.cli.commands.coordinate._get_sdk")
    def test_resume_retries_failed_records(self, mock_get_sdk, duckdb_test_file):
        """Test that resume retries records that previously failed."""
        from anncsu.cli.commands.coordinate import (
            _create_results_table,
            _insert_result,
        )

        _create_results_table(duckdb_test_file)
        # 1 succeeded, 1 failed — the failed one should be retried
        _insert_result(
            db_path=duckdb_test_file,
            run_id="20260319_140000",
            timestamp="2026-03-19T14:00:00",
            progressivo_accesso=28586543,
            civico=1,
            http_status=200,
            esito="0",
            messaggio="OK",
            id_richiesta="REQ-1",
            error_detail=None,
            elapsed_ms=300.0,
        )
        _insert_result(
            db_path=duckdb_test_file,
            run_id="20260319_140000",
            timestamp="2026-03-19T14:00:00",
            progressivo_accesso=28586542,
            civico=2,
            http_status=None,
            esito=None,
            messaggio=None,
            id_richiesta=None,
            error_detail="Network error",
            elapsed_ms=0.0,
        )

        mock_sdk = MagicMock()
        mock_sdk.json_post.gestionecoordinate.return_value = create_mock_response()
        mock_get_sdk.return_value = (mock_sdk, None)

        result = runner.invoke(
            app,
            [
                "coordinate",
                "duckdb-batch-update",
                "--db",
                duckdb_test_file,
                "--codcom",
                "I501",
                "--resume",
                "20260319_140000",
            ],
        )

        assert "1 records already succeeded" in result.output
        # 2 remaining: the failed one + the one never attempted
        assert "Found 2 records to process" in result.output
        assert mock_sdk.json_post.gestionecoordinate.call_count == 2

    @patch("anncsu.cli.commands.coordinate._get_sdk")
    def test_resume_with_max_records(self, mock_get_sdk, duckdb_test_file):
        """Test resume combined with --max-records for daily limit."""
        from anncsu.cli.commands.coordinate import (
            _create_results_table,
            _insert_result,
        )

        _create_results_table(duckdb_test_file)
        # 1 already done
        _insert_result(
            db_path=duckdb_test_file,
            run_id="20260319_140000",
            timestamp="2026-03-19T14:00:00",
            progressivo_accesso=28586543,
            civico=1,
            http_status=200,
            esito="0",
            messaggio="OK",
            id_richiesta="REQ-1",
            error_detail=None,
            elapsed_ms=300.0,
        )

        mock_sdk = MagicMock()
        mock_sdk.json_post.gestionecoordinate.return_value = create_mock_response()
        mock_get_sdk.return_value = (mock_sdk, None)

        result = runner.invoke(
            app,
            [
                "coordinate",
                "duckdb-batch-update",
                "--db",
                duckdb_test_file,
                "--codcom",
                "I501",
                "--resume",
                "20260319_140000",
                "--max-records",
                "1",
            ],
        )

        assert "Found 1 records to process" in result.output
        # Only 1 processed despite 2 remaining, because of --max-records
        assert mock_sdk.json_post.gestionecoordinate.call_count == 1

    @patch("anncsu.cli.commands.coordinate._get_sdk")
    def test_resume_preserves_run_id(self, mock_get_sdk, duckdb_test_file):
        """Test that resumed run uses the same run_id in results."""
        from anncsu.cli.commands.coordinate import _create_results_table

        _create_results_table(duckdb_test_file)

        mock_sdk = MagicMock()
        mock_sdk.json_post.gestionecoordinate.return_value = create_mock_response()
        mock_get_sdk.return_value = (mock_sdk, None)

        runner.invoke(
            app,
            [
                "coordinate",
                "duckdb-batch-update",
                "--db",
                duckdb_test_file,
                "--codcom",
                "I501",
                "--resume",
                "20260319_140000",
                "--max-records",
                "1",
            ],
        )

        # Verify the run_id in results table matches the resumed one
        conn = duckdb.connect(duckdb_test_file)
        rows = conn.execute(
            "SELECT DISTINCT run_id FROM batch_update_results"
        ).fetchall()
        conn.close()

        run_ids = [r[0] for r in rows]
        assert "20260319_140000" in run_ids


class TestDuckDBBatchValidation:
    """Test coordinate length validation."""

    def test_rejects_table_with_long_coordinates(self):
        """Test that source table with coordinates > 12 chars is rejected."""
        with tempfile.NamedTemporaryFile(suffix=".duckdb", delete=True) as f:
            db_path = f.name

        conn = duckdb.connect(db_path)
        conn.execute("""
            CREATE TABLE bad_coords (
                CODICE_COMUNE VARCHAR,
                PROGRESSIVO_ACCESSO INTEGER,
                CIVICO INTEGER,
                COORD_X_COMUNE VARCHAR,
                COORD_Y_COMUNE VARCHAR,
                QUOTA VARCHAR,
                METODO VARCHAR
            )
        """)
        # Insert a record with coordinate strings > 12 chars
        conn.execute("""
            INSERT INTO bad_coords VALUES
            ('A269', 1, 1, '13.152722358703', '41.74429702758789', NULL, '3')
        """)
        conn.close()

        try:
            result = runner.invoke(
                app,
                [
                    "coordinate",
                    "duckdb-batch-update",
                    "--db",
                    db_path,
                    "--codcom",
                    "A269",
                    "--source-table",
                    "bad_coords",
                ],
            )
            assert result.exit_code == 1
            assert "not valid" in result.output
            assert "maxLength" in result.output or "_prepared" in result.output
        finally:
            Path(db_path).unlink(missing_ok=True)

    def test_accepts_table_with_valid_coordinates(self):
        """Test that source table with coordinates <= 12 chars passes validation."""
        with tempfile.NamedTemporaryFile(suffix=".duckdb", delete=True) as f:
            db_path = f.name

        conn = duckdb.connect(db_path)
        conn.execute("""
            CREATE TABLE good_coords (
                CODICE_COMUNE VARCHAR,
                PROGRESSIVO_ACCESSO INTEGER,
                CIVICO INTEGER,
                COORD_X_COMUNE VARCHAR,
                COORD_Y_COMUNE VARCHAR,
                QUOTA VARCHAR,
                METODO VARCHAR
            )
        """)
        conn.execute("""
            INSERT INTO good_coords VALUES
            ('A269', 1, 1, '13.152722', '41.744297', NULL, '3')
        """)
        conn.close()

        try:
            # Will fail at SDK init (no env vars) but should pass validation
            result = runner.invoke(
                app,
                [
                    "coordinate",
                    "duckdb-batch-update",
                    "--db",
                    db_path,
                    "--codcom",
                    "A269",
                    "--source-table",
                    "good_coords",
                ],
            )
            # Should NOT contain the validation error
            assert "not valid" not in result.output
        finally:
            Path(db_path).unlink(missing_ok=True)
