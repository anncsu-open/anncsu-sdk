"""DuckDB schema, initialization, and query helpers for bulk coordinate updates."""

from __future__ import annotations

import uuid
from enum import Enum
from typing import Any

import duckdb

DAILY_RATE_LIMIT = 50_000
CHUNK_SIZE = 50_000


class RowStatus(str, Enum):
    """Status values for bulk_input rows."""

    PENDING = "pending"
    VALID = "valid"
    INVALID = "invalid"
    PROCESSING = "processing"
    DONE = "done"
    ERROR = "error"


_SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS bulk_input (
    row_id           INTEGER PRIMARY KEY,
    run_id           VARCHAR NOT NULL,
    codcom           VARCHAR NOT NULL,
    progr_civico     VARCHAR NOT NULL,
    x                VARCHAR,
    y                VARCHAR,
    z                VARCHAR,
    metodo           VARCHAR,
    status           VARCHAR DEFAULT 'pending',
    validation_error VARCHAR,
    imported_at      TIMESTAMP DEFAULT current_timestamp,
    chunk_id         INTEGER GENERATED ALWAYS AS ((row_id - 1) // 50000)
);

CREATE TABLE IF NOT EXISTS bulk_results (
    result_id        INTEGER PRIMARY KEY DEFAULT nextval('bulk_results_seq'),
    row_id           INTEGER NOT NULL,
    run_id           VARCHAR NOT NULL,
    operation        VARCHAR NOT NULL,
    esito            VARCHAR,
    messaggio        VARCHAR,
    id_richiesta     VARCHAR,
    api_response_json VARCHAR,
    http_status      INTEGER,
    error_detail     VARCHAR,
    processed_at     TIMESTAMP DEFAULT current_timestamp
);

CREATE TABLE IF NOT EXISTS bulk_runs (
    run_id       VARCHAR PRIMARY KEY,
    codcom       VARCHAR NOT NULL,
    csv_path     VARCHAR NOT NULL,
    db_path      VARCHAR NOT NULL,
    mode         VARCHAR NOT NULL,
    started_at   TIMESTAMP DEFAULT current_timestamp,
    finished_at  TIMESTAMP,
    total_rows   INTEGER DEFAULT 0,
    valid_rows   INTEGER DEFAULT 0,
    invalid_rows INTEGER DEFAULT 0,
    processed    INTEGER DEFAULT 0,
    succeeded    INTEGER DEFAULT 0,
    failed       INTEGER DEFAULT 0,
    daily_api_calls INTEGER DEFAULT 0
);

CREATE TABLE IF NOT EXISTS dryrun_originals (
    row_id          INTEGER PRIMARY KEY,
    run_id          VARCHAR NOT NULL,
    progr_civico    VARCHAR NOT NULL,
    codcom          VARCHAR NOT NULL,
    original_x      VARCHAR,
    original_y      VARCHAR,
    original_z      VARCHAR,
    original_metodo VARCHAR,
    saved_at        TIMESTAMP DEFAULT current_timestamp
);
"""


class BulkDB:
    """DuckDB wrapper for bulk coordinate update state management."""

    def __init__(self, db_path: str) -> None:
        self.db_path = db_path
        self.con = duckdb.connect(db_path)
        self.init_schema()

    def __enter__(self) -> BulkDB:
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: Any,
    ) -> None:
        self.close()

    def close(self) -> None:
        """Close the DuckDB connection."""
        if self.con:
            self.con.close()
            self.con = None

    def init_schema(self) -> None:
        """Create tables if they don't exist. Idempotent."""
        self.con.execute("CREATE SEQUENCE IF NOT EXISTS bulk_results_seq START 1")
        self.con.execute(_SCHEMA_SQL)

    # --- bulk_runs helpers ---

    def create_run(
        self,
        *,
        codcom: str,
        csv_path: str,
        db_path: str,
        mode: str,
    ) -> str:
        """Create a new run entry and return the run_id."""
        run_id = str(uuid.uuid4())
        self.con.execute(
            "INSERT INTO bulk_runs (run_id, codcom, csv_path, db_path, mode) "
            "VALUES (?, ?, ?, ?, ?)",
            [run_id, codcom, csv_path, db_path, mode],
        )
        return run_id

    def update_run_counts(
        self,
        *,
        run_id: str,
        total_rows: int | None = None,
        valid_rows: int | None = None,
        invalid_rows: int | None = None,
        processed: int | None = None,
        succeeded: int | None = None,
        failed: int | None = None,
    ) -> None:
        """Update run counters. Only updates non-None fields."""
        updates = []
        params = []
        for field, value in [
            ("total_rows", total_rows),
            ("valid_rows", valid_rows),
            ("invalid_rows", invalid_rows),
            ("processed", processed),
            ("succeeded", succeeded),
            ("failed", failed),
        ]:
            if value is not None:
                updates.append(f"{field} = ?")
                params.append(value)
        if updates:
            params.append(run_id)
            self.con.execute(
                f"UPDATE bulk_runs SET {', '.join(updates)} WHERE run_id = ?",
                params,
            )

    def finish_run(self, run_id: str) -> None:
        """Mark a run as finished."""
        self.con.execute(
            "UPDATE bulk_runs SET finished_at = current_timestamp WHERE run_id = ?",
            [run_id],
        )

    def get_run_summary(self, run_id: str) -> dict[str, Any] | None:
        """Get run summary as a dict."""
        result = self.con.execute(
            "SELECT * FROM bulk_runs WHERE run_id = ?", [run_id]
        ).fetchone()
        if result is None:
            return None
        columns = [
            desc[0]
            for desc in self.con.execute("SELECT * FROM bulk_runs LIMIT 0").description
        ]
        return dict(zip(columns, result, strict=False))

    # --- bulk_input helpers ---

    def update_row_status(
        self,
        *,
        row_id: int,
        status: RowStatus,
        validation_error: str | None = None,
    ) -> None:
        """Update the status of a row in bulk_input."""
        if validation_error is not None:
            self.con.execute(
                "UPDATE bulk_input SET status = ?, validation_error = ? "
                "WHERE row_id = ?",
                [status.value, validation_error, row_id],
            )
        else:
            self.con.execute(
                "UPDATE bulk_input SET status = ? WHERE row_id = ?",
                [status.value, row_id],
            )

    def get_rows_by_status(
        self,
        *,
        run_id: str,
        status: RowStatus,
        chunk_id: int | None = None,
        limit: int | None = None,
    ) -> list[dict[str, Any]]:
        """Get rows filtered by status, optionally by chunk."""
        query = "SELECT * FROM bulk_input WHERE run_id = ? AND status = ?"
        params: list[Any] = [run_id, status.value]
        if chunk_id is not None:
            query += " AND chunk_id = ?"
            params.append(chunk_id)
        query += " ORDER BY row_id"
        if limit is not None:
            query += f" LIMIT {limit}"
        result = self.con.execute(query, params)
        columns = [desc[0] for desc in result.description]
        return [dict(zip(columns, row, strict=False)) for row in result.fetchall()]

    def reset_processing(self, *, run_id: str) -> int:
        """Reset rows stuck in 'processing' back to 'valid' (for resume)."""
        count = self.con.execute(
            "SELECT COUNT(*) FROM bulk_input WHERE run_id = ? AND status = ?",
            [run_id, RowStatus.PROCESSING.value],
        ).fetchone()[0]
        if count > 0:
            self.con.execute(
                "UPDATE bulk_input SET status = ? WHERE run_id = ? AND status = ?",
                [RowStatus.VALID.value, run_id, RowStatus.PROCESSING.value],
            )
        return count

    # --- bulk_results helpers ---

    def insert_result(
        self,
        *,
        row_id: int,
        run_id: str,
        operation: str,
        esito: str | None = None,
        messaggio: str | None = None,
        id_richiesta: str | None = None,
        api_response_json: str | None = None,
        http_status: int | None = None,
        error_detail: str | None = None,
    ) -> None:
        """Insert an API call result."""
        self.con.execute(
            "INSERT INTO bulk_results "
            "(row_id, run_id, operation, esito, messaggio, id_richiesta, "
            "api_response_json, http_status, error_detail) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            [
                row_id,
                run_id,
                operation,
                esito,
                messaggio,
                id_richiesta,
                api_response_json,
                http_status,
                error_detail,
            ],
        )

    # --- dryrun_originals helpers ---

    def save_dryrun_original(
        self,
        *,
        row_id: int,
        run_id: str,
        progr_civico: str,
        codcom: str,
        original_x: str | None = None,
        original_y: str | None = None,
        original_z: str | None = None,
        original_metodo: str | None = None,
    ) -> None:
        """Save original coordinates before a dry-run update."""
        self.con.execute(
            "INSERT INTO dryrun_originals "
            "(row_id, run_id, progr_civico, codcom, "
            "original_x, original_y, original_z, original_metodo) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            [
                row_id,
                run_id,
                progr_civico,
                codcom,
                original_x,
                original_y,
                original_z,
                original_metodo,
            ],
        )

    def get_dryrun_original(self, *, row_id: int) -> dict[str, Any] | None:
        """Get saved original coordinates for a dry-run row."""
        result = self.con.execute(
            "SELECT * FROM dryrun_originals WHERE row_id = ?", [row_id]
        ).fetchone()
        if result is None:
            return None
        columns = [
            desc[0]
            for desc in self.con.execute(
                "SELECT * FROM dryrun_originals LIMIT 0"
            ).description
        ]
        return dict(zip(columns, result, strict=False))

    # --- rate limiting helpers ---

    def count_daily_api_calls(self) -> int:
        """Count API calls made today across all runs."""
        result = self.con.execute(
            "SELECT COUNT(*) FROM bulk_results WHERE processed_at >= CURRENT_DATE"
        ).fetchone()
        return result[0]

    def can_make_api_call(self) -> bool:
        """Check if we haven't exceeded the daily rate limit."""
        return self.count_daily_api_calls() < DAILY_RATE_LIMIT
