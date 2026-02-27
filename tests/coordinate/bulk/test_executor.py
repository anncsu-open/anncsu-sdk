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


class TestBulkExecutorMaxRecords:
    """Test max_records limiting."""

    def test_max_records_limits_processing(self, tmp_path):
        """Executor processes only max_records rows when specified."""
        csv = (
            "codcom,progr_civico,x,y,z,metodo\n"
            "A062,100,13.1,41.8,,3\n"
            "A062,200,14.0,42.0,,2\n"
            "A062,300,13.5,41.5,,1\n"
            "A062,400,14.2,42.2,,4\n"
            "A062,500,13.8,41.9,,2\n"
        )
        db, result = _setup_db_with_csv(tmp_path, csv)
        mock_sdk = MagicMock()
        mock_sdk.json_post.gestionecoordinate.return_value = _make_success_response()

        executor = BulkExecutor(
            db=db, run_id=result.run_id, sdk=mock_sdk, max_records=2
        )
        exec_result = executor.execute()

        assert exec_result.processed == 2
        assert exec_result.succeeded == 2
        assert mock_sdk.json_post.gestionecoordinate.call_count == 2

        # 3 rows should still be valid (not processed)
        remaining = db.get_rows_by_status(run_id=result.run_id, status=RowStatus.VALID)
        assert len(remaining) == 3
        db.close()

    def test_max_records_none_processes_all(self, tmp_path):
        """Without max_records (None), all rows are processed."""
        csv = (
            "codcom,progr_civico,x,y,z,metodo\n"
            "A062,100,13.1,41.8,,3\n"
            "A062,200,14.0,42.0,,2\n"
            "A062,300,13.5,41.5,,1\n"
        )
        db, result = _setup_db_with_csv(tmp_path, csv)
        mock_sdk = MagicMock()
        mock_sdk.json_post.gestionecoordinate.return_value = _make_success_response()

        executor = BulkExecutor(db=db, run_id=result.run_id, sdk=mock_sdk)
        exec_result = executor.execute()

        assert exec_result.processed == 3
        assert exec_result.succeeded == 3
        db.close()

    def test_max_records_greater_than_rows(self, tmp_path):
        """max_records larger than available rows processes all rows."""
        csv = (
            "codcom,progr_civico,x,y,z,metodo\n"
            "A062,100,13.1,41.8,,3\n"
            "A062,200,14.0,42.0,,2\n"
        )
        db, result = _setup_db_with_csv(tmp_path, csv)
        mock_sdk = MagicMock()
        mock_sdk.json_post.gestionecoordinate.return_value = _make_success_response()

        executor = BulkExecutor(
            db=db, run_id=result.run_id, sdk=mock_sdk, max_records=100
        )
        exec_result = executor.execute()

        assert exec_result.processed == 2
        assert exec_result.succeeded == 2
        db.close()

    def test_max_records_with_progress_callback(self, tmp_path):
        """Progress callback reports correct total when max_records is set."""
        csv = (
            "codcom,progr_civico,x,y,z,metodo\n"
            "A062,100,13.1,41.8,,3\n"
            "A062,200,14.0,42.0,,2\n"
            "A062,300,13.5,41.5,,1\n"
            "A062,400,14.2,42.2,,4\n"
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
            max_records=2,
            on_progress=on_progress,
        )
        executor.execute()

        assert len(progress_calls) == 2
        # total in callback should reflect the capped count
        assert progress_calls[-1] == (2, 2, 2, 0)
        db.close()

    def test_max_records_updates_run_counts(self, tmp_path):
        """Run counts in DB reflect only the processed subset."""
        csv = (
            "codcom,progr_civico,x,y,z,metodo\n"
            "A062,100,13.1,41.8,,3\n"
            "A062,200,14.0,42.0,,2\n"
            "A062,300,13.5,41.5,,1\n"
        )
        db, result = _setup_db_with_csv(tmp_path, csv)
        mock_sdk = MagicMock()
        mock_sdk.json_post.gestionecoordinate.return_value = _make_success_response()

        executor = BulkExecutor(
            db=db, run_id=result.run_id, sdk=mock_sdk, max_records=1
        )
        executor.execute()

        summary = db.get_run_summary(result.run_id)
        assert summary["processed"] == 1
        assert summary["succeeded"] == 1
        db.close()


class TestBulkExecutorTiming:
    """Test per-call timing tracking."""

    def test_elapsed_ms_stored_in_results(self, tmp_path):
        """Each bulk_results row should have a non-negative elapsed_ms."""
        csv = (
            "codcom,progr_civico,x,y,z,metodo\n"
            "A062,100,13.1,41.8,,3\n"
            "A062,200,14.0,42.0,,2\n"
        )
        db, result = _setup_db_with_csv(tmp_path, csv)
        mock_sdk = MagicMock()
        mock_sdk.json_post.gestionecoordinate.return_value = _make_success_response()

        executor = BulkExecutor(db=db, run_id=result.run_id, sdk=mock_sdk)
        executor.execute()

        rows = db.con.execute(
            "SELECT elapsed_ms FROM bulk_results WHERE run_id = ?",
            [result.run_id],
        ).fetchall()
        assert len(rows) == 2
        for row in rows:
            assert row[0] is not None
            assert row[0] >= 0
        db.close()

    def test_elapsed_ms_stored_on_error(self, tmp_path):
        """Elapsed_ms is also recorded when API call raises an exception."""
        csv = "codcom,progr_civico,x,y,z,metodo\nA062,100,13.1,41.8,,3\n"
        db, result = _setup_db_with_csv(tmp_path, csv)
        mock_sdk = MagicMock()
        mock_sdk.json_post.gestionecoordinate.side_effect = Exception("timeout")

        executor = BulkExecutor(db=db, run_id=result.run_id, sdk=mock_sdk)
        executor.execute()

        rows = db.con.execute(
            "SELECT elapsed_ms FROM bulk_results WHERE run_id = ?",
            [result.run_id],
        ).fetchall()
        assert len(rows) == 1
        assert rows[0][0] is not None
        assert rows[0][0] >= 0
        db.close()

    def test_timing_stats_in_result(self, tmp_path):
        """BulkExecutorResult should include timing statistics."""
        csv = (
            "codcom,progr_civico,x,y,z,metodo\n"
            "A062,100,13.1,41.8,,3\n"
            "A062,200,14.0,42.0,,2\n"
            "A062,300,13.5,41.5,,1\n"
        )
        db, result = _setup_db_with_csv(tmp_path, csv)
        mock_sdk = MagicMock()
        mock_sdk.json_post.gestionecoordinate.return_value = _make_success_response()

        executor = BulkExecutor(db=db, run_id=result.run_id, sdk=mock_sdk)
        exec_result = executor.execute()

        assert exec_result.total_elapsed_ms >= 0
        assert exec_result.avg_elapsed_ms >= 0
        assert exec_result.min_elapsed_ms >= 0
        assert exec_result.max_elapsed_ms >= 0
        assert exec_result.min_elapsed_ms <= exec_result.avg_elapsed_ms
        assert exec_result.avg_elapsed_ms <= exec_result.max_elapsed_ms
        db.close()

    def test_timing_stats_estimate_50k(self, tmp_path):
        """Verify estimated time for 50k calls is computed from avg."""
        csv = "codcom,progr_civico,x,y,z,metodo\nA062,100,13.1,41.8,,3\n"
        db, result = _setup_db_with_csv(tmp_path, csv)
        mock_sdk = MagicMock()
        mock_sdk.json_post.gestionecoordinate.return_value = _make_success_response()

        executor = BulkExecutor(db=db, run_id=result.run_id, sdk=mock_sdk)
        exec_result = executor.execute()

        # estimated_50k_minutes should be avg_ms * 50000 / 60000
        expected = exec_result.avg_elapsed_ms * 50_000 / 60_000
        assert abs(exec_result.estimated_50k_minutes - expected) < 0.01
        db.close()


class TestBulkExecutorTokenRefresh:
    """Test token refresh on 401 errors during bulk execution."""

    def _make_401_error(self):
        """Create a mock 401 TokenExpired SDK exception."""
        err = Exception("TokenExpired")
        err.status_code = 401
        err.body = '{"detail":"Expired token"}'
        return err

    def _make_404_error(self):
        """Create a mock 404 NotFound SDK exception."""
        err = Exception("NotFound")
        err.status_code = 404
        err.body = '{"detail":"Unknown API Request"}'
        return err

    def test_401_without_refresher_counts_as_error(self, tmp_path):
        """Without token_refresher, 401 is a permanent error."""
        csv = (
            "codcom,progr_civico,x,y,z,metodo\n"
            "A062,100,13.1,41.8,,3\n"
            "A062,200,14.0,42.0,,2\n"
        )
        db, result = _setup_db_with_csv(tmp_path, csv)
        mock_sdk = MagicMock()
        mock_sdk.json_post.gestionecoordinate.side_effect = [
            _make_success_response(),
            self._make_401_error(),
        ]

        executor = BulkExecutor(db=db, run_id=result.run_id, sdk=mock_sdk)
        exec_result = executor.execute()

        assert exec_result.succeeded == 1
        assert exec_result.failed == 1
        db.close()

    def test_401_with_refresher_retries_and_succeeds(self, tmp_path):
        """With token_refresher, 401 triggers refresh + retry."""
        csv = (
            "codcom,progr_civico,x,y,z,metodo\n"
            "A062,100,13.1,41.8,,3\n"
            "A062,200,14.0,42.0,,2\n"
            "A062,300,13.5,41.5,,1\n"
        )
        db, result = _setup_db_with_csv(tmp_path, csv)
        mock_sdk = MagicMock()
        # Row 1: OK, Row 2: 401 then OK on retry, Row 3: OK
        mock_sdk.json_post.gestionecoordinate.side_effect = [
            _make_success_response(),
            self._make_401_error(),
            _make_success_response(),  # retry of row 2 after refresh
            _make_success_response(),  # row 3
        ]

        refresher = MagicMock(return_value="new-token-abc")

        executor = BulkExecutor(
            db=db,
            run_id=result.run_id,
            sdk=mock_sdk,
            token_refresher=refresher,
        )
        exec_result = executor.execute()

        assert exec_result.succeeded == 3
        assert exec_result.failed == 0
        refresher.assert_called_once()
        db.close()

    def test_401_refresher_called_only_once_per_token_expiry(self, tmp_path):
        """Refresh is called once, then subsequent calls use the new token."""
        csv = (
            "codcom,progr_civico,x,y,z,metodo\n"
            "A062,100,13.1,41.8,,3\n"
            "A062,200,14.0,42.0,,2\n"
            "A062,300,13.5,41.5,,1\n"
            "A062,400,14.2,42.2,,4\n"
        )
        db, result = _setup_db_with_csv(tmp_path, csv)
        mock_sdk = MagicMock()
        # Row 1: OK, Row 2: 401 → refresh → retry OK, Row 3: OK, Row 4: OK
        mock_sdk.json_post.gestionecoordinate.side_effect = [
            _make_success_response(),
            self._make_401_error(),
            _make_success_response(),  # retry row 2
            _make_success_response(),  # row 3
            _make_success_response(),  # row 4
        ]

        refresher = MagicMock(return_value="new-token-xyz")

        executor = BulkExecutor(
            db=db,
            run_id=result.run_id,
            sdk=mock_sdk,
            token_refresher=refresher,
        )
        exec_result = executor.execute()

        assert exec_result.succeeded == 4
        assert exec_result.failed == 0
        assert refresher.call_count == 1
        db.close()

    def test_401_retry_fails_again_counts_as_error(self, tmp_path):
        """If retry after refresh still fails, count as permanent error."""
        csv = "codcom,progr_civico,x,y,z,metodo\nA062,100,13.1,41.8,,3\n"
        db, result = _setup_db_with_csv(tmp_path, csv)
        mock_sdk = MagicMock()
        # 401 → refresh → retry → 401 again → permanent error
        mock_sdk.json_post.gestionecoordinate.side_effect = [
            self._make_401_error(),
            self._make_401_error(),  # retry also fails
        ]

        refresher = MagicMock(return_value="new-token-abc")

        executor = BulkExecutor(
            db=db,
            run_id=result.run_id,
            sdk=mock_sdk,
            token_refresher=refresher,
        )
        exec_result = executor.execute()

        assert exec_result.failed == 1
        assert exec_result.succeeded == 0
        refresher.assert_called_once()
        db.close()

    def test_401_refresher_exception_counts_as_error(self, tmp_path):
        """If token_refresher raises, the row is counted as error."""
        csv = "codcom,progr_civico,x,y,z,metodo\nA062,100,13.1,41.8,,3\n"
        db, result = _setup_db_with_csv(tmp_path, csv)
        mock_sdk = MagicMock()
        mock_sdk.json_post.gestionecoordinate.side_effect = self._make_401_error()

        refresher = MagicMock(side_effect=Exception("PDND auth failed"))

        executor = BulkExecutor(
            db=db,
            run_id=result.run_id,
            sdk=mock_sdk,
            token_refresher=refresher,
        )
        exec_result = executor.execute()

        assert exec_result.failed == 1
        db.close()

    def test_non_401_error_not_retried(self, tmp_path):
        """Non-401 errors (e.g. 404, 500) are not retried even with refresher."""
        csv = "codcom,progr_civico,x,y,z,metodo\nA062,100,13.1,41.8,,3\n"
        db, result = _setup_db_with_csv(tmp_path, csv)
        mock_sdk = MagicMock()
        mock_sdk.json_post.gestionecoordinate.side_effect = self._make_404_error()

        refresher = MagicMock(return_value="new-token-abc")

        executor = BulkExecutor(
            db=db,
            run_id=result.run_id,
            sdk=mock_sdk,
            token_refresher=refresher,
        )
        exec_result = executor.execute()

        assert exec_result.failed == 1
        refresher.assert_not_called()
        db.close()

    def test_multiple_401s_refresh_each_time(self, tmp_path):
        """If token expires again later, refresh is called again."""
        csv = (
            "codcom,progr_civico,x,y,z,metodo\n"
            "A062,100,13.1,41.8,,3\n"
            "A062,200,14.0,42.0,,2\n"
            "A062,300,13.5,41.5,,1\n"
        )
        db, result = _setup_db_with_csv(tmp_path, csv)
        mock_sdk = MagicMock()
        # Row 1: 401 → refresh → OK, Row 2: OK, Row 3: 401 → refresh → OK
        mock_sdk.json_post.gestionecoordinate.side_effect = [
            self._make_401_error(),
            _make_success_response(),  # retry row 1
            _make_success_response(),  # row 2
            self._make_401_error(),
            _make_success_response(),  # retry row 3
        ]

        refresher = MagicMock(return_value="refreshed-token")

        executor = BulkExecutor(
            db=db,
            run_id=result.run_id,
            sdk=mock_sdk,
            token_refresher=refresher,
        )
        exec_result = executor.execute()

        assert exec_result.succeeded == 3
        assert exec_result.failed == 0
        assert refresher.call_count == 2
        db.close()

    def test_401_retry_row_not_double_counted(self, tmp_path):
        """A retried row should be counted only once in processed."""
        csv = (
            "codcom,progr_civico,x,y,z,metodo\n"
            "A062,100,13.1,41.8,,3\n"
            "A062,200,14.0,42.0,,2\n"
        )
        db, result = _setup_db_with_csv(tmp_path, csv)
        mock_sdk = MagicMock()
        mock_sdk.json_post.gestionecoordinate.side_effect = [
            self._make_401_error(),
            _make_success_response(),  # retry row 1
            _make_success_response(),  # row 2
        ]

        refresher = MagicMock(return_value="new-token")

        executor = BulkExecutor(
            db=db,
            run_id=result.run_id,
            sdk=mock_sdk,
            token_refresher=refresher,
        )
        exec_result = executor.execute()

        # 2 rows processed, not 3
        assert exec_result.processed == 2
        assert exec_result.succeeded == 2
        db.close()

    def test_401_retried_row_ends_up_done_in_db(self, tmp_path):
        """Row that got 401 then succeeded on retry must be 'done' in DB."""
        csv = (
            "codcom,progr_civico,x,y,z,metodo\n"
            "A062,100,13.1,41.8,,3\n"
            "A062,200,14.0,42.0,,2\n"
        )
        db, result = _setup_db_with_csv(tmp_path, csv)
        mock_sdk = MagicMock()
        # Row 1: 401 → refresh → retry OK, Row 2: OK
        mock_sdk.json_post.gestionecoordinate.side_effect = [
            self._make_401_error(),
            _make_success_response(id_richiesta="RETRY-OK"),
            _make_success_response(id_richiesta="ROW2-OK"),
        ]

        refresher = MagicMock(return_value="new-token")

        executor = BulkExecutor(
            db=db,
            run_id=result.run_id,
            sdk=mock_sdk,
            token_refresher=refresher,
        )
        executor.execute()

        # Both rows should be 'done'
        done_rows = db.get_rows_by_status(run_id=result.run_id, status=RowStatus.DONE)
        assert len(done_rows) == 2

        # No rows should be in 'error'
        error_rows = db.get_rows_by_status(run_id=result.run_id, status=RowStatus.ERROR)
        assert len(error_rows) == 0

        # bulk_results should have the successful result for row 1 (retry), not the 401
        row1_results = db.con.execute(
            "SELECT esito, id_richiesta, http_status FROM bulk_results "
            "WHERE row_id = 1 AND run_id = ?",
            [result.run_id],
        ).fetchall()
        assert len(row1_results) == 1
        assert row1_results[0][0] == "0"  # esito OK
        assert row1_results[0][1] == "RETRY-OK"  # from the retry
        assert row1_results[0][2] is None  # no http error status
        db.close()

    def test_401_retry_failure_row_ends_up_error_in_db(self, tmp_path):
        """Row that got 401, refreshed, but retry also failed → 'error' in DB."""
        csv = "codcom,progr_civico,x,y,z,metodo\nA062,100,13.1,41.8,,3\n"
        db, result = _setup_db_with_csv(tmp_path, csv)
        mock_sdk = MagicMock()
        mock_sdk.json_post.gestionecoordinate.side_effect = [
            self._make_401_error(),
            self._make_404_error(),  # retry fails with different error
        ]

        refresher = MagicMock(return_value="new-token")

        executor = BulkExecutor(
            db=db,
            run_id=result.run_id,
            sdk=mock_sdk,
            token_refresher=refresher,
        )
        executor.execute()

        # Row should be in 'error'
        error_rows = db.get_rows_by_status(run_id=result.run_id, status=RowStatus.ERROR)
        assert len(error_rows) == 1

        # Result should record the retry failure (404), not the original 401
        results = db.con.execute(
            "SELECT http_status, error_detail FROM bulk_results "
            "WHERE row_id = 1 AND run_id = ?",
            [result.run_id],
        ).fetchall()
        assert len(results) == 1
        assert results[0][0] == 404
        db.close()

    def test_401_refresher_returns_none_no_retry(self, tmp_path):
        """If refresher returns None (token not expired), no retry is attempted."""
        csv = (
            "codcom,progr_civico,x,y,z,metodo\n"
            "A062,100,13.1,41.8,,3\n"
            "A062,200,14.0,42.0,,2\n"
        )
        db, result = _setup_db_with_csv(tmp_path, csv)
        mock_sdk = MagicMock()
        # Row 1: OK, Row 2: 401 but token is not expired
        mock_sdk.json_post.gestionecoordinate.side_effect = [
            _make_success_response(),
            self._make_401_error(),
        ]

        # Refresher returns None → token is not expired, 401 is due to other cause
        refresher = MagicMock(return_value=None)

        executor = BulkExecutor(
            db=db,
            run_id=result.run_id,
            sdk=mock_sdk,
            token_refresher=refresher,
        )
        exec_result = executor.execute()

        assert exec_result.succeeded == 1
        assert exec_result.failed == 1
        # SDK should NOT have been called a third time (no retry)
        assert mock_sdk.json_post.gestionecoordinate.call_count == 2
        refresher.assert_called_once()
        db.close()

    def test_401_refresher_returns_none_error_stored_in_db(self, tmp_path):
        """When refresher returns None, the original 401 error is stored."""
        csv = "codcom,progr_civico,x,y,z,metodo\nA062,100,13.1,41.8,,3\n"
        db, result = _setup_db_with_csv(tmp_path, csv)
        mock_sdk = MagicMock()
        mock_sdk.json_post.gestionecoordinate.side_effect = self._make_401_error()

        refresher = MagicMock(return_value=None)

        executor = BulkExecutor(
            db=db,
            run_id=result.run_id,
            sdk=mock_sdk,
            token_refresher=refresher,
        )
        executor.execute()

        error_rows = db.get_rows_by_status(run_id=result.run_id, status=RowStatus.ERROR)
        assert len(error_rows) == 1

        results = db.con.execute(
            "SELECT http_status, error_detail FROM bulk_results "
            "WHERE row_id = 1 AND run_id = ?",
            [result.run_id],
        ).fetchall()
        assert len(results) == 1
        assert results[0][0] == 401
        assert "Expired token" in results[0][1]
        db.close()


class TestBulkExecutorTokenInjection:
    """Test that token refresh actually injects the new token into the SDK.

    These tests reproduce the production bug where:
    1. Token expires mid-execution → GovWay returns 401 TokenExpired
    2. Refresher obtains a new token but it's never set on the SDK
    3. Retry (and all subsequent calls) fail because the SDK
       still sends the expired token

    The key insight: the SDK object has a security.bearer attribute that
    holds the token. After refresh, executor MUST update sdk.sdk_configuration
    .security.bearer (or equivalent) so the SDK sends the new token.
    """

    def _make_401_error(self):
        err = Exception("TokenExpired")
        err.status_code = 401
        err.body = '{"detail":"Expired token"}'
        return err

    def _make_404_error(self):
        err = Exception("NotFound")
        err.status_code = 404
        err.body = '{"detail":"Unknown API Request"}'
        return err

    def _make_sdk_with_token_check(self):
        """Create a mock SDK that fails with 401 when token is expired
        and with 404 on retry if the token wasn't actually updated.

        This simulates real GovWay behavior:
        - Expired token → 401 TokenExpired
        - Refreshed token in auth_manager but NOT in SDK → 404 Unknown API
          (because GovWay sees a malformed/missing Authorization header)
        """
        sdk = MagicMock()
        sdk._current_token = "initial-token"

        def api_call(**kwargs):
            token = sdk._current_token
            if token == "expired":
                raise self._make_401_error()
            if token == "initial-token":
                # Token was never updated after refresh → still old/invalid
                raise self._make_404_error()
            # Token was properly updated → success
            return _make_success_response()

        sdk.json_post.gestionecoordinate.side_effect = api_call
        return sdk

    def test_refreshed_token_is_injected_into_sdk(self, tmp_path):
        """After 401 + refresh, the retry and subsequent calls must succeed.

        Simulates real production flow: the SDK uses a security callable
        that reads from auth_manager. The refresher clears the cached
        token in auth_manager, so the next get_access_token() call returns
        a fresh one. The SDK's callable security picks it up automatically.

        Test models this: refresher() updates auth_state, and api_call
        reads auth_state to decide success/failure — just like the real SDK
        reads from auth_manager via the callable.
        """
        csv = (
            "codcom,progr_civico,x,y,z,metodo\n"
            "A062,100,13.1,41.8,,3\n"
            "A062,200,14.0,42.0,,2\n"
            "A062,300,14.1,42.1,,2\n"
        )
        db, result = _setup_db_with_csv(tmp_path, csv)

        # Simulates auth_manager's internal state — the SDK callable reads
        # this on every request, refresher() updates it on 401.
        auth_state = {"token": "old-token"}
        call_number = {"n": 0}
        sdk = MagicMock()

        def api_call(**kwargs):
            call_number["n"] += 1
            token = auth_state["token"]
            if call_number["n"] <= 2:
                return _make_success_response()
            if token == "old-token":
                if call_number["n"] == 3:
                    raise self._make_401_error()
                raise self._make_404_error()
            return _make_success_response()

        sdk.json_post.gestionecoordinate.side_effect = api_call

        def refresher():
            auth_state["token"] = "new-token-123"
            return "new-token-123"

        executor = BulkExecutor(
            db=db,
            run_id=result.run_id,
            sdk=sdk,
            token_refresher=refresher,
        )
        exec_result = executor.execute()

        assert exec_result.succeeded == 3, (
            f"Expected 3 succeeded but got {exec_result.succeeded} succeeded, "
            f"{exec_result.failed} failed. "
            "Token refresh didn't propagate to SDK."
        )
        assert exec_result.failed == 0
        db.close()

    def test_all_rows_after_refresh_use_new_token(self, tmp_path):
        """After refresh, ALL subsequent rows must use the new token,
        not just the retried row."""
        csv = (
            "codcom,progr_civico,x,y,z,metodo\n"
            "A062,100,13.1,41.8,,3\n"
            "A062,200,14.0,42.0,,2\n"
            "A062,300,14.1,42.1,,2\n"
            "A062,400,14.2,42.2,,2\n"
        )
        db, result = _setup_db_with_csv(tmp_path, csv)

        auth_state = {"token": "old-token"}
        call_number = {"n": 0}
        sdk = MagicMock()

        def api_call(**kwargs):
            call_number["n"] += 1
            token = auth_state["token"]
            if call_number["n"] == 1:
                return _make_success_response()
            if token == "old-token":
                if call_number["n"] == 2:
                    raise self._make_401_error()
                raise self._make_404_error()
            return _make_success_response()

        sdk.json_post.gestionecoordinate.side_effect = api_call

        def refresher():
            auth_state["token"] = "new-token-456"
            return "new-token-456"

        executor = BulkExecutor(
            db=db,
            run_id=result.run_id,
            sdk=sdk,
            token_refresher=refresher,
        )
        exec_result = executor.execute()

        assert exec_result.succeeded == 4, (
            f"Expected 4 succeeded but got {exec_result.succeeded} succeeded, "
            f"{exec_result.failed} failed. "
            "Rows after refresh still sent old token."
        )
        assert exec_result.failed == 0
        db.close()

    def test_second_token_expiry_also_refreshes(self, tmp_path):
        """If the token expires again later, a second refresh also propagates."""
        csv = (
            "codcom,progr_civico,x,y,z,metodo\n"
            "A062,100,13.1,41.8,,3\n"
            "A062,200,14.0,42.0,,2\n"
            "A062,300,14.1,42.1,,2\n"
            "A062,400,14.2,42.2,,2\n"
        )
        db, result = _setup_db_with_csv(tmp_path, csv)

        auth_state = {"token": "old-token"}
        refresh_count = {"n": 0}
        call_number = {"n": 0}
        sdk = MagicMock()

        def api_call(**kwargs):
            call_number["n"] += 1
            token = auth_state["token"]
            if call_number["n"] == 1:
                return _make_success_response()
            if call_number["n"] == 2:
                raise self._make_401_error()  # first expiry
            if call_number["n"] == 3:
                if token == "token-v1":
                    return _make_success_response()
                raise self._make_404_error()
            if call_number["n"] == 4:
                return _make_success_response()
            if call_number["n"] == 5:
                raise self._make_401_error()  # second expiry
            if token == "token-v2":
                return _make_success_response()
            raise self._make_404_error()

        sdk.json_post.gestionecoordinate.side_effect = api_call

        def refresher():
            refresh_count["n"] += 1
            auth_state["token"] = f"token-v{refresh_count['n']}"
            return auth_state["token"]

        executor = BulkExecutor(
            db=db,
            run_id=result.run_id,
            sdk=sdk,
            token_refresher=refresher,
        )
        exec_result = executor.execute()

        assert exec_result.succeeded == 4, (
            f"Expected 4 succeeded but got {exec_result.succeeded} succeeded, "
            f"{exec_result.failed} failed."
        )
        assert exec_result.failed == 0
        db.close()


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
