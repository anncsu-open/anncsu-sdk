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
    elapsed_ms       DOUBLE,
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
        elapsed_ms: float | None = None,
    ) -> None:
        """Insert an API call result."""
        self.con.execute(
            "INSERT INTO bulk_results "
            "(row_id, run_id, operation, esito, messaggio, id_richiesta, "
            "api_response_json, http_status, error_detail, elapsed_ms) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
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
                elapsed_ms,
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

    # --- CSV staging helpers ---

    def create_staging_from_csv(
        self,
        csv_path: str,
        *,
        separator: str,
    ) -> list[str]:
        """Load a CSV into a temporary staging table using DuckDB read_csv_auto.

        Args:
            csv_path: Absolute path to the CSV file.
            separator: CSV delimiter character.

        Returns:
            List of column names found in the staging table (lowercased).
        """
        self.con.execute("DROP TABLE IF EXISTS _csv_staging")
        self.con.execute(
            "CREATE TEMP TABLE _csv_staging AS "
            "SELECT * FROM read_csv_auto(?, delim=?, all_varchar=true, "
            "header=true, null_padding=true)",
            [csv_path, separator],
        )
        desc = self.con.execute("SELECT * FROM _csv_staging LIMIT 0").description
        return [d[0].lower() for d in desc]

    def get_staging_codcom(self) -> str:
        """Get codcom from the first row of the staging table."""
        result = self.con.execute("SELECT codcom FROM _csv_staging LIMIT 1").fetchone()
        if result is None:
            return "UNKNOWN"
        return result[0] or "UNKNOWN"

    def insert_validated_from_staging(
        self,
        *,
        run_id: str,
        staging_columns: list[str],
    ) -> tuple[int, int, int]:
        """Insert rows from staging into bulk_input with SQL-based validation.

        Translates the 7 validation rules from ValidatedCoordinate into SQL
        CASE/WHEN expressions, preserving identical rule priority and Italian
        error messages.

        Args:
            run_id: The run identifier.
            staging_columns: Column names present in the staging table.

        Returns:
            Tuple of (total_rows, valid_count, invalid_count).
        """
        # Build column expressions - use NULL for missing optional columns
        x_expr = "NULLIF(TRIM(x), '')" if "x" in staging_columns else "NULL"
        y_expr = "NULLIF(TRIM(y), '')" if "y" in staging_columns else "NULL"
        z_expr = "NULLIF(TRIM(z), '')" if "z" in staging_columns else "NULL"
        metodo_expr = (
            "NULLIF(TRIM(metodo), '')" if "metodo" in staging_columns else "NULL"
        )

        sql = f"""
        INSERT INTO bulk_input
            (row_id, run_id, codcom, progr_civico, x, y, z, metodo,
             status, validation_error)
        SELECT
            row_id, run_id, codcom, progr_civico, _x, _y, _z, _metodo,
            CASE
                WHEN _x IS NOT NULL AND _y IS NULL THEN 'invalid'
                WHEN _y IS NOT NULL AND _x IS NULL THEN 'invalid'
                WHEN _x IS NOT NULL AND _y IS NOT NULL AND _metodo IS NULL
                    THEN 'invalid'
                WHEN _x IS NULL AND _y IS NULL AND _metodo IS NOT NULL
                    THEN 'invalid'
                WHEN _metodo IS NOT NULL
                    AND (TRY_CAST(_metodo AS INTEGER) IS NULL
                         OR TRY_CAST(_metodo AS INTEGER) NOT BETWEEN 1 AND 4)
                    THEN 'invalid'
                WHEN _x IS NOT NULL
                    AND (TRY_CAST(_x AS DOUBLE) IS NULL
                         OR TRY_CAST(_x AS DOUBLE) NOT BETWEEN 6.0 AND 18.0)
                    THEN 'invalid'
                WHEN _y IS NOT NULL
                    AND (TRY_CAST(_y AS DOUBLE) IS NULL
                         OR TRY_CAST(_y AS DOUBLE) NOT BETWEEN 36.0 AND 47.0)
                    THEN 'invalid'
                WHEN _z IS NOT NULL AND (_x IS NULL OR _y IS NULL)
                    THEN 'invalid'
                WHEN _x IS NOT NULL AND LENGTH(_x) > 12 THEN 'invalid'
                WHEN _y IS NOT NULL AND LENGTH(_y) > 12 THEN 'invalid'
                WHEN _z IS NOT NULL AND LENGTH(_z) > 7 THEN 'invalid'
                ELSE 'valid'
            END AS status,
            CASE
                WHEN _x IS NOT NULL AND _y IS NULL
                    THEN 'Coordinata Y obbligatoria se viene valorizzata X. '
                         || 'Fornire entrambe le coordinate X e Y.'
                WHEN _y IS NOT NULL AND _x IS NULL
                    THEN 'Coordinata X obbligatoria se viene valorizzata Y. '
                         || 'Fornire entrambe le coordinate X e Y.'
                WHEN _x IS NOT NULL AND _y IS NOT NULL AND _metodo IS NULL
                    THEN 'Il campo ''metodo'' e'' obbligatorio quando X e Y '
                         || 'sono valorizzati. Coordinate fornite: X='
                         || _x || ', Y=' || _y
                WHEN _x IS NULL AND _y IS NULL AND _metodo IS NOT NULL
                    THEN 'Il campo ''metodo'' non deve essere valorizzato in '
                         || 'assenza di X e Y. Metodo fornito: ' || _metodo
                WHEN _metodo IS NOT NULL
                    AND (TRY_CAST(_metodo AS INTEGER) IS NULL
                         OR TRY_CAST(_metodo AS INTEGER) NOT BETWEEN 1 AND 4)
                    THEN 'Il campo ''metodo'' deve essere compreso tra 1 e 4. '
                         || 'Valore fornito: ' || _metodo
                WHEN _x IS NOT NULL
                    AND (TRY_CAST(_x AS DOUBLE) IS NULL
                         OR TRY_CAST(_x AS DOUBLE) NOT BETWEEN 6.0 AND 18.0)
                    THEN 'Coordinata X fuori range. Valori ammessi in Italia: '
                         || '6.0 <= X <= 18.0. Valore fornito: ' || _x
                WHEN _y IS NOT NULL
                    AND (TRY_CAST(_y AS DOUBLE) IS NULL
                         OR TRY_CAST(_y AS DOUBLE) NOT BETWEEN 36.0 AND 47.0)
                    THEN 'Coordinata Y fuori range. Valori ammessi in Italia: '
                         || '36.0 <= Y <= 47.0. Valore fornito: ' || _y
                WHEN _z IS NOT NULL AND (_x IS NULL OR _y IS NULL)
                    THEN 'La quota (Z) non deve essere valorizzata in assenza '
                         || 'di X e Y. Quota fornita: ' || _z
                WHEN _x IS NOT NULL AND LENGTH(_x) > 12
                    THEN 'Il campo ''x'' supera la lunghezza massima consentita. '
                         || 'Massimo 12 caratteri, forniti '
                         || CAST(LENGTH(_x) AS VARCHAR) || '. Valore: ' || _x
                WHEN _y IS NOT NULL AND LENGTH(_y) > 12
                    THEN 'Il campo ''y'' supera la lunghezza massima consentita. '
                         || 'Massimo 12 caratteri, forniti '
                         || CAST(LENGTH(_y) AS VARCHAR) || '. Valore: ' || _y
                WHEN _z IS NOT NULL AND LENGTH(_z) > 7
                    THEN 'Il campo ''z'' supera la lunghezza massima consentita. '
                         || 'Massimo 7 caratteri, forniti '
                         || CAST(LENGTH(_z) AS VARCHAR) || '. Valore: ' || _z
                ELSE NULL
            END AS validation_error
        FROM (
            SELECT
                ROW_NUMBER() OVER () AS row_id,
                ? AS run_id,
                codcom,
                progr_civico,
                {x_expr} AS _x,
                {y_expr} AS _y,
                {z_expr} AS _z,
                {metodo_expr} AS _metodo
            FROM _csv_staging
        ) sub
        """
        self.con.execute(sql, [run_id])

        # Get counts in one query
        counts = self.con.execute(
            "SELECT "
            "  COUNT(*) AS total, "
            "  COUNT(*) FILTER (WHERE status = 'valid') AS valid_count, "
            "  COUNT(*) FILTER (WHERE status = 'invalid') AS invalid_count "
            "FROM bulk_input WHERE run_id = ?",
            [run_id],
        ).fetchone()

        return counts[0], counts[1], counts[2]

    # --- result query helpers ---

    def get_result_errors(self, *, run_id: str) -> list[tuple]:
        """Get error details for failed operations in a run.

        Returns list of (row_id, progr_civico, operation, http_status, error_detail).
        """
        return self.con.execute(
            "SELECT r.row_id, bi.progr_civico, r.operation, r.http_status, "
            "r.error_detail "
            "FROM bulk_results r "
            "JOIN bulk_input bi ON r.row_id = bi.row_id AND r.run_id = bi.run_id "
            "WHERE r.run_id = ? AND r.error_detail IS NOT NULL "
            "ORDER BY r.row_id, r.operation",
            [run_id],
        ).fetchall()

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
