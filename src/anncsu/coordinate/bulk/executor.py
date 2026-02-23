"""Bulk API executor: loops over validated rows and calls gestionecoordinate."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable

from anncsu.coordinate.bulk.db import BulkDB, RowStatus
from anncsu.coordinate.models.richiestaoperazione import (
    Accesso,
    Coordinate,
    Richiesta,
)


def _extract_http_error(e: Exception) -> tuple[int | None, str]:
    """Extract HTTP status and error detail from an SDK exception."""
    http_status = getattr(e, "status_code", None)
    error_detail = getattr(e, "body", None) or str(e)
    return http_status, error_detail


class RateLimitReached(Exception):
    """Raised when daily API rate limit is reached."""

    def __init__(self, *, processed: int, remaining: int, run_id: str) -> None:
        self.processed = processed
        self.remaining = remaining
        self.run_id = run_id
        super().__init__(
            f"Daily rate limit reached after {processed} calls. "
            f"{remaining} rows remaining. Resume with: "
            f"anncsu coordinate bulk resume {run_id}"
        )


@dataclass
class BulkExecutorResult:
    """Result of a bulk execution."""

    processed: int
    succeeded: int
    failed: int
    run_id: str


ProgressCallback = Callable[[int, int, int, int], None]
"""Callback(processed, total, succeeded, failed)"""


class BulkExecutor:
    """Executes API calls for each valid row in bulk_input."""

    def __init__(
        self,
        *,
        db: BulkDB,
        run_id: str,
        sdk: Any,
        on_progress: ProgressCallback | None = None,
    ) -> None:
        self.db = db
        self.run_id = run_id
        self.sdk = sdk
        self.on_progress = on_progress

    def execute(self, *, resume: bool = False) -> BulkExecutorResult:
        """Execute API calls for all valid rows.

        Args:
            resume: If True, reset 'processing' rows to 'valid' first.

        Returns:
            BulkExecutorResult with execution statistics.

        Raises:
            RateLimitReached: When daily limit of 50,000 calls is reached.
        """
        if resume:
            self.db.reset_processing(run_id=self.run_id)

        rows = self.db.get_rows_by_status(run_id=self.run_id, status=RowStatus.VALID)

        total = len(rows)
        processed = 0
        succeeded = 0
        failed = 0

        for row in rows:
            # Check rate limit before each call
            if not self.db.can_make_api_call():
                remaining = total - processed
                raise RateLimitReached(
                    processed=processed,
                    remaining=remaining,
                    run_id=self.run_id,
                )

            row_id = row["row_id"]
            self.db.update_row_status(row_id=row_id, status=RowStatus.PROCESSING)

            try:
                response = self._call_api(row)
                esito = response.esito
                messaggio = response.messaggio
                id_richiesta = response.id_richiesta

                try:
                    response_json = response.model_dump_json()
                except Exception:
                    response_json = None

                self.db.insert_result(
                    row_id=row_id,
                    run_id=self.run_id,
                    operation="update",
                    esito=esito,
                    messaggio=messaggio,
                    id_richiesta=id_richiesta,
                    api_response_json=response_json,
                )

                if esito == "0":
                    self.db.update_row_status(row_id=row_id, status=RowStatus.DONE)
                    succeeded += 1
                else:
                    self.db.update_row_status(row_id=row_id, status=RowStatus.ERROR)
                    failed += 1

            except Exception as e:
                http_status, error_detail = _extract_http_error(e)
                self.db.insert_result(
                    row_id=row_id,
                    run_id=self.run_id,
                    operation="update",
                    http_status=http_status,
                    error_detail=error_detail,
                )
                self.db.update_row_status(row_id=row_id, status=RowStatus.ERROR)
                failed += 1

            processed += 1

            if self.on_progress:
                self.on_progress(processed, total, succeeded, failed)

        # Update run counters
        self.db.update_run_counts(
            run_id=self.run_id,
            processed=processed,
            succeeded=succeeded,
            failed=failed,
        )

        return BulkExecutorResult(
            processed=processed,
            succeeded=succeeded,
            failed=failed,
            run_id=self.run_id,
        )

    def _call_api(self, row: dict) -> Any:
        """Build request model and call gestionecoordinate."""
        coordinate = Coordinate(
            x=row.get("x"),
            y=row.get("y"),
            z=row.get("z"),
            metodo=row.get("metodo"),
        )

        accesso = Accesso(
            codcom=row["codcom"],
            progr_civico=row["progr_civico"],
            coordinate=coordinate,
        )

        richiesta = Richiesta(accesso=accesso)

        return self.sdk.json_post.gestionecoordinate(richiesta=richiesta)
