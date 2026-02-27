"""Report generation from DuckDB bulk operation results."""

from __future__ import annotations

import csv
import json
from dataclasses import asdict, dataclass
from enum import Enum
from typing import IO, Any

from anncsu.coordinate.bulk.db import BulkDB


class ReportFormat(str, Enum):
    """Output format for reports."""

    CSV = "csv"
    JSON = "json"
    TABLE = "table"


@dataclass
class RunSummary:
    """Summary statistics for a bulk run."""

    run_id: str
    codcom: str
    mode: str
    total_rows: int
    valid_rows: int
    invalid_rows: int
    processed: int
    succeeded: int
    failed: int
    started_at: str | None
    finished_at: str | None


_RESULTS_QUERY = """
    SELECT
        bi.codcom,
        bi.progr_civico,
        bi.x AS input_x,
        bi.y AS input_y,
        bi.z AS input_z,
        bi.metodo AS input_metodo,
        br.esito,
        br.messaggio,
        br.id_richiesta,
        br.operation,
        br.error_detail,
        br.processed_at
    FROM bulk_input bi
    LEFT JOIN bulk_results br ON bi.row_id = br.row_id AND bi.run_id = br.run_id
    WHERE bi.run_id = ?
    ORDER BY bi.row_id
"""

_ERRORS_QUERY = """
    SELECT
        bi.row_id,
        bi.codcom,
        bi.progr_civico,
        br.esito,
        br.messaggio,
        br.id_richiesta,
        br.error_detail
    FROM bulk_input bi
    JOIN bulk_results br ON bi.row_id = br.row_id AND bi.run_id = br.run_id
    WHERE bi.run_id = ?
      AND (br.esito IS NULL OR br.esito != '0')
    ORDER BY bi.row_id
"""

_VALIDATION_ERRORS_QUERY = """
    SELECT
        row_id,
        codcom,
        progr_civico,
        x, y, z, metodo,
        validation_error
    FROM bulk_input
    WHERE run_id = ? AND status = 'invalid'
    ORDER BY row_id
"""


class BulkReporter:
    """Generates reports from bulk operation results in DuckDB."""

    def __init__(self, *, db: BulkDB, run_id: str) -> None:
        self.db = db
        self.run_id = run_id

    def get_summary(self) -> RunSummary | None:
        """Get run summary."""
        raw = self.db.get_run_summary(self.run_id)
        if raw is None:
            return None
        return RunSummary(
            run_id=raw["run_id"],
            codcom=raw["codcom"],
            mode=raw["mode"],
            total_rows=raw["total_rows"],
            valid_rows=raw["valid_rows"],
            invalid_rows=raw["invalid_rows"],
            processed=raw["processed"],
            succeeded=raw["succeeded"],
            failed=raw["failed"],
            started_at=str(raw["started_at"]) if raw["started_at"] else None,
            finished_at=str(raw["finished_at"]) if raw["finished_at"] else None,
        )

    def export_results(self, output: IO[str], *, fmt: ReportFormat) -> None:
        """Export results to a file-like object in the specified format."""
        if fmt == ReportFormat.CSV:
            self._export_csv(output)
        elif fmt == ReportFormat.JSON:
            self._export_json(output)

    def get_errors(self) -> list[dict[str, Any]]:
        """Get API errors (esito != '0')."""
        result = self.db.con.execute(_ERRORS_QUERY, [self.run_id])
        columns = [desc[0] for desc in result.description]
        return [dict(zip(columns, row, strict=False)) for row in result.fetchall()]

    def get_validation_errors(self) -> list[dict[str, Any]]:
        """Get rows that failed Pydantic validation."""
        result = self.db.con.execute(_VALIDATION_ERRORS_QUERY, [self.run_id])
        columns = [desc[0] for desc in result.description]
        return [dict(zip(columns, row, strict=False)) for row in result.fetchall()]

    def _export_csv(self, output: IO[str]) -> None:
        """Export results as CSV."""
        result = self.db.con.execute(_RESULTS_QUERY, [self.run_id])
        columns = [desc[0] for desc in result.description]
        rows = result.fetchall()

        writer = csv.DictWriter(output, fieldnames=columns)
        writer.writeheader()
        for row in rows:
            writer.writerow(dict(zip(columns, row, strict=False)))

    def _export_json(self, output: IO[str]) -> None:
        """Export results as JSON with summary."""
        summary = self.get_summary()
        result = self.db.con.execute(_RESULTS_QUERY, [self.run_id])
        columns = [desc[0] for desc in result.description]
        rows = [
            {
                k: str(v) if v is not None else None
                for k, v in zip(columns, row, strict=False)
            }
            for row in result.fetchall()
        ]

        data = {
            "summary": asdict(summary) if summary else None,
            "results": rows,
        }
        json.dump(data, output, indent=2, default=str)
