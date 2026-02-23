"""Tests for bulk API executor with mock SDK calls."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from anncsu.coordinate.bulk.db import BulkDB, RowStatus
from anncsu.coordinate.bulk.executor import (
    BulkExecutor,
    BulkExecutorResult,
    RateLimitReached,
)
from anncsu.coordinate.bulk.importer import import_csv


def _write_csv(path: Path, content: str) -> Path:
    path.write_text(content, encoding="utf-8")
    return path


def _make_success_response(**kwargs):
    """Create a mock RispostaOperazione with esito='0'."""
    mock = MagicMock()
    mock.esito = "0"
    mock.messaggio = "OK"
    mock.id_richiesta = kwargs.get("id_richiesta", "5144")
    mock.model_dump_json = MagicMock(
        return_value=json.dumps(
            {
                "esito": "0",
                "messaggio": "OK",
                "idRichiesta": mock.id_richiesta,
            }
        )
    )
    return mock


def _make_error_response(**kwargs):
    """Create a mock RispostaOperazione with esito='23'."""
    mock = MagicMock()
    mock.esito = kwargs.get("esito", "23")
    mock.messaggio = kwargs.get("messaggio", "Errore di validazione")
    mock.id_richiesta = kwargs.get("id_richiesta", "5145")
    mock.model_dump_json = MagicMock(
        return_value=json.dumps(
            {
                "esito": mock.esito,
                "messaggio": mock.messaggio,
                "idRichiesta": mock.id_richiesta,
            }
        )
    )
    return mock


def _setup_db_with_csv(tmp_path, csv_content):
    """Helper to create a DB with imported CSV data."""
    csv_file = _write_csv(tmp_path / "input.csv", csv_content)
    db = BulkDB(":memory:")
    result = import_csv(db=db, csv_path=csv_file, mode="update")
    return db, result


class TestBulkExecutorInit:
    """Test BulkExecutor initialization."""

    def test_create_executor(self, tmp_path):
        csv = "codcom,progr_civico,x,y,z,metodo\nA062,100,13.1,41.8,,3\n"
        db, result = _setup_db_with_csv(tmp_path, csv)
        mock_sdk = MagicMock()
        executor = BulkExecutor(db=db, run_id=result.run_id, sdk=mock_sdk)
        assert executor.run_id == result.run_id
        db.close()


class TestBulkExecutorExecution:
    """Test API call execution loop."""

    def test_execute_all_success(self, tmp_path):
        csv = (
            "codcom,progr_civico,x,y,z,metodo\n"
            "A062,100,13.1,41.8,,3\n"
            "A062,200,14.0,42.0,,2\n"
        )
        db, result = _setup_db_with_csv(tmp_path, csv)
        mock_sdk = MagicMock()
        mock_sdk.json_post.gestionecoordinate.side_effect = [
            _make_success_response(id_richiesta="5144"),
            _make_success_response(id_richiesta="5145"),
        ]

        executor = BulkExecutor(db=db, run_id=result.run_id, sdk=mock_sdk)
        exec_result = executor.execute()

        assert exec_result.processed == 2
        assert exec_result.succeeded == 2
        assert exec_result.failed == 0
        assert mock_sdk.json_post.gestionecoordinate.call_count == 2
        db.close()

    def test_execute_with_errors(self, tmp_path):
        csv = (
            "codcom,progr_civico,x,y,z,metodo\n"
            "A062,100,13.1,41.8,,3\n"
            "A062,200,14.0,42.0,,2\n"
        )
        db, result = _setup_db_with_csv(tmp_path, csv)
        mock_sdk = MagicMock()
        mock_sdk.json_post.gestionecoordinate.side_effect = [
            _make_success_response(),
            _make_error_response(),
        ]

        executor = BulkExecutor(db=db, run_id=result.run_id, sdk=mock_sdk)
        exec_result = executor.execute()

        assert exec_result.processed == 2
        assert exec_result.succeeded == 1
        assert exec_result.failed == 1
        db.close()

    def test_execute_updates_row_status_done(self, tmp_path):
        csv = "codcom,progr_civico,x,y,z,metodo\nA062,100,13.1,41.8,,3\n"
        db, result = _setup_db_with_csv(tmp_path, csv)
        mock_sdk = MagicMock()
        mock_sdk.json_post.gestionecoordinate.return_value = _make_success_response()

        executor = BulkExecutor(db=db, run_id=result.run_id, sdk=mock_sdk)
        executor.execute()

        rows = db.get_rows_by_status(run_id=result.run_id, status=RowStatus.DONE)
        assert len(rows) == 1
        db.close()

    def test_execute_updates_row_status_error(self, tmp_path):
        csv = "codcom,progr_civico,x,y,z,metodo\nA062,100,13.1,41.8,,3\n"
        db, result = _setup_db_with_csv(tmp_path, csv)
        mock_sdk = MagicMock()
        mock_sdk.json_post.gestionecoordinate.return_value = _make_error_response()

        executor = BulkExecutor(db=db, run_id=result.run_id, sdk=mock_sdk)
        executor.execute()

        rows = db.get_rows_by_status(run_id=result.run_id, status=RowStatus.ERROR)
        assert len(rows) == 1
        db.close()

    def test_execute_stores_results(self, tmp_path):
        csv = "codcom,progr_civico,x,y,z,metodo\nA062,100,13.1,41.8,,3\n"
        db, result = _setup_db_with_csv(tmp_path, csv)
        mock_sdk = MagicMock()
        mock_sdk.json_post.gestionecoordinate.return_value = _make_success_response(
            id_richiesta="5144"
        )

        executor = BulkExecutor(db=db, run_id=result.run_id, sdk=mock_sdk)
        executor.execute()

        results = db.con.execute(
            "SELECT esito, messaggio, id_richiesta, operation "
            "FROM bulk_results WHERE run_id = ?",
            [result.run_id],
        ).fetchall()
        assert len(results) == 1
        assert results[0][0] == "0"  # esito
        assert results[0][1] == "OK"  # messaggio
        assert results[0][2] == "5144"  # id_richiesta
        assert results[0][3] == "update"  # operation
        db.close()

    def test_execute_skips_invalid_rows(self, tmp_path):
        csv = (
            "codcom,progr_civico,x,y,z,metodo\n"
            "A062,100,13.1,41.8,,3\n"
            "A062,200,13.1,,,\n"  # invalid: x without y
        )
        db, result = _setup_db_with_csv(tmp_path, csv)
        mock_sdk = MagicMock()
        mock_sdk.json_post.gestionecoordinate.return_value = _make_success_response()

        executor = BulkExecutor(db=db, run_id=result.run_id, sdk=mock_sdk)
        exec_result = executor.execute()

        assert exec_result.processed == 1  # only valid row
        assert mock_sdk.json_post.gestionecoordinate.call_count == 1
        db.close()

    def test_execute_handles_api_exception(self, tmp_path):
        csv = "codcom,progr_civico,x,y,z,metodo\nA062,100,13.1,41.8,,3\n"
        db, result = _setup_db_with_csv(tmp_path, csv)
        mock_sdk = MagicMock()
        mock_sdk.json_post.gestionecoordinate.side_effect = Exception(
            "Connection timeout"
        )

        executor = BulkExecutor(db=db, run_id=result.run_id, sdk=mock_sdk)
        exec_result = executor.execute()

        assert exec_result.processed == 1
        assert exec_result.failed == 1
        rows = db.get_rows_by_status(run_id=result.run_id, status=RowStatus.ERROR)
        assert len(rows) == 1
        db.close()

    def test_execute_stores_http_status_on_sdk_error(self, tmp_path):
        """When SDK raises an error with status_code, http_status is stored."""
        csv = "codcom,progr_civico,x,y,z,metodo\nA062,100,13.1,41.8,,3\n"
        db, result = _setup_db_with_csv(tmp_path, csv)

        sdk_error = Exception("API error occurred")
        sdk_error.status_code = 403
        sdk_error.body = '{"detail":"Insufficient token claims"}'

        mock_sdk = MagicMock()
        mock_sdk.json_post.gestionecoordinate.side_effect = sdk_error

        executor = BulkExecutor(db=db, run_id=result.run_id, sdk=mock_sdk)
        exec_result = executor.execute()

        assert exec_result.failed == 1
        results = db.con.execute(
            "SELECT http_status, error_detail FROM bulk_results "
            "WHERE run_id = ? AND operation = 'update'",
            [result.run_id],
        ).fetchall()
        assert len(results) == 1
        assert results[0][0] == 403
        assert "Insufficient token claims" in results[0][1]
        db.close()


class TestBulkExecutorRateLimit:
    """Test daily rate limit enforcement."""

    def test_rate_limit_stops_execution(self, tmp_path):
        csv = (
            "codcom,progr_civico,x,y,z,metodo\n"
            "A062,100,13.1,41.8,,3\n"
            "A062,200,14.0,42.0,,2\n"
        )
        db, result = _setup_db_with_csv(tmp_path, csv)
        mock_sdk = MagicMock()
        mock_sdk.json_post.gestionecoordinate.return_value = _make_success_response()

        executor = BulkExecutor(db=db, run_id=result.run_id, sdk=mock_sdk)

        # Patch can_make_api_call to return False after first call
        call_count = [0]

        def limited_can_make():
            call_count[0] += 1
            if call_count[0] > 1:
                return False
            return True

        db.can_make_api_call = limited_can_make

        with pytest.raises(RateLimitReached) as exc_info:
            executor.execute()

        assert exc_info.value.processed > 0
        assert exc_info.value.remaining > 0
        db.close()


class TestBulkExecutorResume:
    """Test resume after interruption."""

    def test_resume_skips_done_rows(self, tmp_path):
        csv = (
            "codcom,progr_civico,x,y,z,metodo\n"
            "A062,100,13.1,41.8,,3\n"
            "A062,200,14.0,42.0,,2\n"
        )
        db, result = _setup_db_with_csv(tmp_path, csv)

        # Simulate first row already done
        db.update_row_status(row_id=1, status=RowStatus.DONE)
        db.insert_result(
            row_id=1,
            run_id=result.run_id,
            operation="update",
            esito="0",
            messaggio="OK",
        )

        mock_sdk = MagicMock()
        mock_sdk.json_post.gestionecoordinate.return_value = _make_success_response()

        executor = BulkExecutor(db=db, run_id=result.run_id, sdk=mock_sdk)
        exec_result = executor.execute()

        # Only second row should be processed
        assert exec_result.processed == 1
        assert mock_sdk.json_post.gestionecoordinate.call_count == 1
        db.close()

    def test_resume_resets_processing_status(self, tmp_path):
        csv = (
            "codcom,progr_civico,x,y,z,metodo\n"
            "A062,100,13.1,41.8,,3\n"
            "A062,200,14.0,42.0,,2\n"
        )
        db, result = _setup_db_with_csv(tmp_path, csv)

        # Simulate crash: one row stuck in processing
        db.update_row_status(row_id=1, status=RowStatus.PROCESSING)

        mock_sdk = MagicMock()
        mock_sdk.json_post.gestionecoordinate.return_value = _make_success_response()

        executor = BulkExecutor(db=db, run_id=result.run_id, sdk=mock_sdk)
        # Resume should reset processing → valid, then process both
        exec_result = executor.execute(resume=True)

        assert exec_result.processed == 2
        db.close()


class TestBulkExecutorResult:
    """Test BulkExecutorResult dataclass."""

    def test_result_fields(self):
        result = BulkExecutorResult(
            processed=10, succeeded=8, failed=2, run_id="test-run"
        )
        assert result.processed == 10
        assert result.succeeded == 8
        assert result.failed == 2
        assert result.run_id == "test-run"


class TestBulkExecutorProgressCallback:
    """Test progress callback invocation."""

    def test_progress_callback_called(self, tmp_path):
        csv = (
            "codcom,progr_civico,x,y,z,metodo\n"
            "A062,100,13.1,41.8,,3\n"
            "A062,200,14.0,42.0,,2\n"
        )
        db, result = _setup_db_with_csv(tmp_path, csv)
        mock_sdk = MagicMock()
        mock_sdk.json_post.gestionecoordinate.return_value = _make_success_response()

        progress_calls = []

        def on_progress(processed, total, succeeded, failed):
            progress_calls.append((processed, total, succeeded, failed))

        executor = BulkExecutor(
            db=db,
            run_id=result.run_id,
            sdk=mock_sdk,
            on_progress=on_progress,
        )
        executor.execute()

        assert len(progress_calls) == 2
        assert progress_calls[-1] == (2, 2, 2, 0)  # final state
        db.close()
