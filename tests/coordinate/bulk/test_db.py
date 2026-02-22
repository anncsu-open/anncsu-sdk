"""Tests for bulk DuckDB schema, init, and query helpers."""

from __future__ import annotations


from anncsu.coordinate.bulk.db import (
    DAILY_RATE_LIMIT,
    BulkDB,
    RowStatus,
)


class TestBulkDBInit:
    """Test database initialization and schema creation."""

    def test_create_in_memory(self):
        db = BulkDB(":memory:")
        assert db.con is not None
        db.close()

    def test_create_on_disk(self, tmp_path):
        db_path = tmp_path / "test.db"
        db = BulkDB(str(db_path))
        assert db_path.exists()
        db.close()

    def test_tables_created(self):
        db = BulkDB(":memory:")
        tables = db.con.execute(
            "SELECT table_name FROM information_schema.tables "
            "WHERE table_schema = 'main' ORDER BY table_name"
        ).fetchall()
        table_names = [t[0] for t in tables]
        assert "bulk_input" in table_names
        assert "bulk_results" in table_names
        assert "bulk_runs" in table_names
        assert "dryrun_originals" in table_names
        db.close()

    def test_context_manager(self):
        with BulkDB(":memory:") as db:
            assert db.con is not None
        # After exiting context, connection should be closed

    def test_idempotent_init(self):
        """Creating BulkDB twice on the same file should not fail."""
        with BulkDB(":memory:") as db:
            # Call init_schema again - should be idempotent
            db.init_schema()
            tables = db.con.execute(
                "SELECT table_name FROM information_schema.tables "
                "WHERE table_schema = 'main'"
            ).fetchall()
            assert len(tables) == 4


class TestBulkInputSchema:
    """Test bulk_input table schema and constraints."""

    def test_bulk_input_columns(self):
        with BulkDB(":memory:") as db:
            cols = db.con.execute(
                "SELECT column_name FROM information_schema.columns "
                "WHERE table_name = 'bulk_input' ORDER BY ordinal_position"
            ).fetchall()
            col_names = [c[0] for c in cols]
            assert "row_id" in col_names
            assert "run_id" in col_names
            assert "codcom" in col_names
            assert "progr_civico" in col_names
            assert "x" in col_names
            assert "y" in col_names
            assert "z" in col_names
            assert "metodo" in col_names
            assert "status" in col_names
            assert "validation_error" in col_names
            assert "imported_at" in col_names
            assert "chunk_id" in col_names

    def test_chunk_id_calculated(self):
        """chunk_id should be (row_id - 1) / 50000."""
        with BulkDB(":memory:") as db:
            db.con.execute(
                "INSERT INTO bulk_input (row_id, run_id, codcom, progr_civico) "
                "VALUES (1, 'run1', 'A062', '1370588')"
            )
            db.con.execute(
                "INSERT INTO bulk_input (row_id, run_id, codcom, progr_civico) "
                "VALUES (50000, 'run1', 'A062', '1370589')"
            )
            db.con.execute(
                "INSERT INTO bulk_input (row_id, run_id, codcom, progr_civico) "
                "VALUES (50001, 'run1', 'A062', '1370590')"
            )

            results = db.con.execute(
                "SELECT row_id, chunk_id FROM bulk_input ORDER BY row_id"
            ).fetchall()

            assert results[0] == (1, 0)  # row 1 → chunk 0
            assert results[1] == (50000, 0)  # row 50000 → chunk 0
            assert results[2] == (50001, 1)  # row 50001 → chunk 1

    def test_default_status_is_pending(self):
        with BulkDB(":memory:") as db:
            db.con.execute(
                "INSERT INTO bulk_input (row_id, run_id, codcom, progr_civico) "
                "VALUES (1, 'run1', 'A062', '1370588')"
            )
            status = db.con.execute(
                "SELECT status FROM bulk_input WHERE row_id = 1"
            ).fetchone()[0]
            assert status == "pending"


class TestBulkResultsSchema:
    """Test bulk_results table schema."""

    def test_bulk_results_columns(self):
        with BulkDB(":memory:") as db:
            cols = db.con.execute(
                "SELECT column_name FROM information_schema.columns "
                "WHERE table_name = 'bulk_results' ORDER BY ordinal_position"
            ).fetchall()
            col_names = [c[0] for c in cols]
            assert "result_id" in col_names
            assert "row_id" in col_names
            assert "run_id" in col_names
            assert "operation" in col_names
            assert "esito" in col_names
            assert "messaggio" in col_names
            assert "id_richiesta" in col_names
            assert "api_response_json" in col_names
            assert "http_status" in col_names
            assert "error_detail" in col_names
            assert "processed_at" in col_names

    def test_insert_result(self):
        with BulkDB(":memory:") as db:
            db.con.execute(
                "INSERT INTO bulk_input (row_id, run_id, codcom, progr_civico) "
                "VALUES (1, 'run1', 'A062', '1370588')"
            )
            db.insert_result(
                row_id=1,
                run_id="run1",
                operation="update",
                esito="0",
                messaggio="OK",
                id_richiesta="5144",
            )
            result = db.con.execute(
                "SELECT esito, messaggio, operation FROM bulk_results WHERE row_id = 1"
            ).fetchone()
            assert result == ("0", "OK", "update")


class TestBulkRunsSchema:
    """Test bulk_runs table schema and helpers."""

    def test_create_run(self):
        with BulkDB(":memory:") as db:
            run_id = db.create_run(
                codcom="A062",
                csv_path="/tmp/input.csv",
                db_path="/tmp/A062_run1.db",
                mode="update",
            )
            assert run_id is not None
            run = db.con.execute(
                "SELECT codcom, mode FROM bulk_runs WHERE run_id = ?", [run_id]
            ).fetchone()
            assert run == ("A062", "update")

    def test_update_run_counts(self):
        with BulkDB(":memory:") as db:
            run_id = db.create_run(
                codcom="A062",
                csv_path="/tmp/input.csv",
                db_path="/tmp/test.db",
                mode="update",
            )
            db.update_run_counts(
                run_id=run_id,
                total_rows=100,
                valid_rows=95,
                invalid_rows=5,
            )
            row = db.con.execute(
                "SELECT total_rows, valid_rows, invalid_rows FROM bulk_runs "
                "WHERE run_id = ?",
                [run_id],
            ).fetchone()
            assert row == (100, 95, 5)

    def test_finish_run(self):
        with BulkDB(":memory:") as db:
            run_id = db.create_run(
                codcom="A062",
                csv_path="/tmp/input.csv",
                db_path="/tmp/test.db",
                mode="update",
            )
            db.finish_run(run_id)
            finished_at = db.con.execute(
                "SELECT finished_at FROM bulk_runs WHERE run_id = ?", [run_id]
            ).fetchone()[0]
            assert finished_at is not None


class TestDryrunOriginalsSchema:
    """Test dryrun_originals table."""

    def test_save_and_retrieve_originals(self):
        with BulkDB(":memory:") as db:
            db.save_dryrun_original(
                row_id=1,
                run_id="run1",
                progr_civico="1370588",
                codcom="A062",
                original_x="13.1022",
                original_y="41.8847",
                original_z="150",
                original_metodo="3",
            )
            orig = db.get_dryrun_original(row_id=1)
            assert orig["original_x"] == "13.1022"
            assert orig["original_y"] == "41.8847"
            assert orig["original_z"] == "150"
            assert orig["original_metodo"] == "3"
            assert orig["codcom"] == "A062"

    def test_get_dryrun_original_not_found(self):
        with BulkDB(":memory:") as db:
            orig = db.get_dryrun_original(row_id=999)
            assert orig is None


class TestRowStatusEnum:
    """Test RowStatus enum values."""

    def test_status_values(self):
        assert RowStatus.PENDING == "pending"
        assert RowStatus.VALID == "valid"
        assert RowStatus.INVALID == "invalid"
        assert RowStatus.PROCESSING == "processing"
        assert RowStatus.DONE == "done"
        assert RowStatus.ERROR == "error"


class TestStatusUpdateHelpers:
    """Test helper methods for updating row status."""

    def test_update_row_status(self):
        with BulkDB(":memory:") as db:
            db.con.execute(
                "INSERT INTO bulk_input (row_id, run_id, codcom, progr_civico) "
                "VALUES (1, 'run1', 'A062', '1370588')"
            )
            db.update_row_status(row_id=1, status=RowStatus.VALID)
            status = db.con.execute(
                "SELECT status FROM bulk_input WHERE row_id = 1"
            ).fetchone()[0]
            assert status == "valid"

    def test_update_row_status_with_error(self):
        with BulkDB(":memory:") as db:
            db.con.execute(
                "INSERT INTO bulk_input (row_id, run_id, codcom, progr_civico) "
                "VALUES (1, 'run1', 'A062', '1370588')"
            )
            db.update_row_status(
                row_id=1,
                status=RowStatus.INVALID,
                validation_error="x and y must be provided together",
            )
            row = db.con.execute(
                "SELECT status, validation_error FROM bulk_input WHERE row_id = 1"
            ).fetchone()
            assert row == ("invalid", "x and y must be provided together")

    def test_get_pending_rows(self):
        with BulkDB(":memory:") as db:
            for i in range(1, 4):
                db.con.execute(
                    "INSERT INTO bulk_input (row_id, run_id, codcom, progr_civico, status) "
                    "VALUES (?, 'run1', 'A062', ?, ?)",
                    [i, str(1370587 + i), "valid" if i <= 2 else "invalid"],
                )
            rows = db.get_rows_by_status(run_id="run1", status=RowStatus.VALID)
            assert len(rows) == 2

    def test_get_rows_by_chunk(self):
        with BulkDB(":memory:") as db:
            # Insert rows in chunk 0
            db.con.execute(
                "INSERT INTO bulk_input (row_id, run_id, codcom, progr_civico, status) "
                "VALUES (1, 'run1', 'A062', '100', 'valid')"
            )
            # Insert row in chunk 1
            db.con.execute(
                "INSERT INTO bulk_input (row_id, run_id, codcom, progr_civico, status) "
                "VALUES (50001, 'run1', 'A062', '200', 'valid')"
            )
            chunk0 = db.get_rows_by_status(
                run_id="run1", status=RowStatus.VALID, chunk_id=0
            )
            chunk1 = db.get_rows_by_status(
                run_id="run1", status=RowStatus.VALID, chunk_id=1
            )
            assert len(chunk0) == 1
            assert len(chunk1) == 1
            assert chunk0[0]["row_id"] == 1
            assert chunk1[0]["row_id"] == 50001

    def test_reset_processing_to_valid(self):
        """For resume: rows stuck in 'processing' should be reset to 'valid'."""
        with BulkDB(":memory:") as db:
            db.con.execute(
                "INSERT INTO bulk_input (row_id, run_id, codcom, progr_civico, status) "
                "VALUES (1, 'run1', 'A062', '100', 'processing')"
            )
            db.con.execute(
                "INSERT INTO bulk_input (row_id, run_id, codcom, progr_civico, status) "
                "VALUES (2, 'run1', 'A062', '200', 'done')"
            )
            count = db.reset_processing(run_id="run1")
            assert count == 1
            status = db.con.execute(
                "SELECT status FROM bulk_input WHERE row_id = 1"
            ).fetchone()[0]
            assert status == "valid"


class TestDailyApiCallCounter:
    """Test daily API call counting for rate limiting."""

    def test_count_daily_calls_empty(self):
        with BulkDB(":memory:") as db:
            count = db.count_daily_api_calls()
            assert count == 0

    def test_count_daily_calls(self):
        with BulkDB(":memory:") as db:
            db.con.execute(
                "INSERT INTO bulk_input (row_id, run_id, codcom, progr_civico) "
                "VALUES (1, 'run1', 'A062', '100')"
            )
            db.insert_result(
                row_id=1,
                run_id="run1",
                operation="update",
                esito="0",
                messaggio="OK",
            )
            count = db.count_daily_api_calls()
            assert count == 1

    def test_daily_rate_limit_constant(self):
        assert DAILY_RATE_LIMIT == 50_000

    def test_can_make_api_call(self):
        with BulkDB(":memory:") as db:
            assert db.can_make_api_call() is True

    def test_get_run_summary(self):
        with BulkDB(":memory:") as db:
            run_id = db.create_run(
                codcom="A062",
                csv_path="/tmp/input.csv",
                db_path="/tmp/test.db",
                mode="update",
            )
            db.update_run_counts(
                run_id=run_id,
                total_rows=100,
                valid_rows=95,
                invalid_rows=5,
            )
            summary = db.get_run_summary(run_id)
            assert summary is not None
            assert summary["codcom"] == "A062"
            assert summary["total_rows"] == 100
            assert summary["valid_rows"] == 95
