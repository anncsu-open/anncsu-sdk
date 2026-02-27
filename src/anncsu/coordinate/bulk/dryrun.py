"""Bulk dry-run: lookup originals, test update, restore for N records."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from anncsu.coordinate.bulk.db import BulkDB, RowStatus
from anncsu.coordinate.models.richiestaoperazione import (
    Accesso,
    Coordinate,
    Richiesta,
)

DEFAULT_MAX_RECORDS = 10


def _extract_http_error(e: Exception) -> tuple[int | None, str]:
    """Extract HTTP status and error detail from an SDK exception."""
    http_status = getattr(e, "status_code", None)
    error_detail = getattr(e, "body", None) or str(e)
    return http_status, error_detail


@dataclass
class DryRunResult:
    """Result of a bulk dry-run operation."""

    total_tested: int
    updates_succeeded: int
    updates_failed: int
    restores_succeeded: int
    restores_failed: int
    lookup_failures: int
    run_id: str


class BulkDryRunner:
    """Performs dry-run on N records: lookup → update → restore."""

    def __init__(
        self,
        *,
        db: BulkDB,
        run_id: str,
        coord_sdk: Any,
        consult_sdk: Any,
        max_records: int = DEFAULT_MAX_RECORDS,
    ) -> None:
        self.db = db
        self.run_id = run_id
        self.coord_sdk = coord_sdk
        self.consult_sdk = consult_sdk
        self.max_records = max_records

    def execute(self) -> DryRunResult:
        """Execute the dry-run cycle.

        For each selected record:
        1. Lookup current coordinates via PA API
        2. Save originals in dryrun_originals table
        3. Update with new coordinates from CSV
        4. Restore original coordinates

        Returns:
            DryRunResult with execution statistics.
        """
        rows = self.db.get_rows_by_status(
            run_id=self.run_id,
            status=RowStatus.VALID,
            limit=self.max_records,
        )

        tested = 0
        updates_succeeded = 0
        updates_failed = 0
        restores_succeeded = 0
        restores_failed = 0
        lookup_failures = 0

        # Track which rows were successfully updated (need restore)
        rows_to_restore: list[dict] = []

        # Phase 1: Lookup + Save originals + Update
        for row in rows:
            row_id = row["row_id"]
            progr_civico = row["progr_civico"]
            codcom = row["codcom"]

            # Step 1: Lookup current coordinates
            try:
                lookup_response = (
                    self.consult_sdk.queryparam.prognazacc_get_query_param(
                        prognazacc=progr_civico
                    )
                )
                # data is a List[PrognazaccGetQueryParamData]
                data_list = lookup_response.data
                if not data_list:
                    lookup_failures += 1
                    self.db.insert_result(
                        row_id=row_id,
                        run_id=self.run_id,
                        operation="dryrun_lookup",
                        error_detail="Lookup returned empty data",
                    )
                    continue
                lookup_data = data_list[0]
            except Exception as e:
                lookup_failures += 1
                http_status, error_detail = _extract_http_error(e)
                self.db.insert_result(
                    row_id=row_id,
                    run_id=self.run_id,
                    operation="dryrun_lookup",
                    http_status=http_status,
                    error_detail=f"Lookup failed: {error_detail}",
                )
                continue

            # Step 2: Save originals
            self.db.save_dryrun_original(
                row_id=row_id,
                run_id=self.run_id,
                progr_civico=progr_civico,
                codcom=codcom,
                original_x=lookup_data.coord_x,
                original_y=lookup_data.coord_y,
                original_z=lookup_data.quota,
                original_metodo=lookup_data.metodo,
            )

            # Step 3: Update with new coordinates from CSV
            try:
                response = self._call_update(row)
                esito = response.esito

                try:
                    response_json = response.model_dump_json()
                except Exception:
                    response_json = None

                self.db.insert_result(
                    row_id=row_id,
                    run_id=self.run_id,
                    operation="dryrun_update",
                    esito=esito,
                    messaggio=response.messaggio,
                    id_richiesta=response.id_richiesta,
                    api_response_json=response_json,
                )

                if esito == "0":
                    updates_succeeded += 1
                    rows_to_restore.append(row)
                    tested += 1
                else:
                    updates_failed += 1
            except Exception as e:
                updates_failed += 1
                http_status, error_detail = _extract_http_error(e)
                self.db.insert_result(
                    row_id=row_id,
                    run_id=self.run_id,
                    operation="dryrun_update",
                    http_status=http_status,
                    error_detail=error_detail,
                )

        # Phase 2: Restore originals (reverse order)
        for row in reversed(rows_to_restore):
            row_id = row["row_id"]
            orig = self.db.get_dryrun_original(row_id=row_id)
            if orig is None:
                restores_failed += 1
                continue

            try:
                response = self._call_restore(row, orig)
                esito = response.esito

                try:
                    response_json = response.model_dump_json()
                except Exception:
                    response_json = None

                self.db.insert_result(
                    row_id=row_id,
                    run_id=self.run_id,
                    operation="dryrun_restore",
                    esito=esito,
                    messaggio=response.messaggio,
                    id_richiesta=response.id_richiesta,
                    api_response_json=response_json,
                )

                if esito == "0":
                    restores_succeeded += 1
                else:
                    restores_failed += 1
            except Exception as e:
                restores_failed += 1
                http_status, error_detail = _extract_http_error(e)
                self.db.insert_result(
                    row_id=row_id,
                    run_id=self.run_id,
                    operation="dryrun_restore",
                    http_status=http_status,
                    error_detail=error_detail,
                )

        return DryRunResult(
            total_tested=tested,
            updates_succeeded=updates_succeeded,
            updates_failed=updates_failed,
            restores_succeeded=restores_succeeded,
            restores_failed=restores_failed,
            lookup_failures=lookup_failures,
            run_id=self.run_id,
        )

    def _call_update(self, row: dict) -> Any:
        """Call gestionecoordinate with CSV coordinate values."""
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
        return self.coord_sdk.json_post.gestionecoordinate(richiesta=richiesta)

    def _call_restore(self, row: dict, orig: dict) -> Any:
        """Call gestionecoordinate with original coordinate values."""
        coordinate = Coordinate(
            x=orig.get("original_x"),
            y=orig.get("original_y"),
            z=orig.get("original_z"),
            metodo=orig.get("original_metodo"),
        )
        accesso = Accesso(
            codcom=row["codcom"],
            progr_civico=row["progr_civico"],
            coordinate=coordinate,
        )
        richiesta = Richiesta(accesso=accesso)
        return self.coord_sdk.json_post.gestionecoordinate(richiesta=richiesta)
