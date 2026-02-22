"""CSV import and Pydantic validation into DuckDB for bulk coordinate updates."""

from __future__ import annotations

import csv
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from anncsu.coordinate.bulk.db import BulkDB, RowStatus
from anncsu.coordinate.errors.coordinate_validation import (
    CoordinateValidationError,
)
from anncsu.coordinate.models.validated import ValidatedCoordinate

REQUIRED_COLUMNS = {"codcom", "progr_civico"}
KNOWN_COLUMNS = {"codcom", "progr_civico", "x", "y", "z", "metodo"}


class CSVImportError(Exception):
    """Raised when CSV import fails due to format issues."""


@dataclass
class CSVImportResult:
    """Result of a CSV import operation."""

    run_id: str
    codcom: str
    total_rows: int
    valid_rows: int
    invalid_rows: int


def detect_separator(csv_path: Path) -> str:
    """Detect CSV separator by analyzing the header line.

    Supports comma (,) and semicolon (;).

    Args:
        csv_path: Path to the CSV file.

    Returns:
        Detected separator character.
    """
    with open(csv_path, encoding="utf-8") as f:
        header = f.readline()
    if ";" in header and header.count(";") >= header.count(","):
        return ";"
    return ","


def validate_csv_header(csv_path: Path, *, separator: str) -> list[str]:
    """Validate that the CSV header contains required columns.

    Args:
        csv_path: Path to the CSV file.
        separator: CSV separator character.

    Returns:
        List of column names from the header.

    Raises:
        CSVImportError: If header is missing or required columns are absent.
    """
    with open(csv_path, encoding="utf-8") as f:
        header_line = f.readline().strip()

    if not header_line:
        msg = f"Empty file or missing header in {csv_path}"
        raise CSVImportError(msg)

    columns = [col.strip().lower() for col in header_line.split(separator)]

    missing = REQUIRED_COLUMNS - set(columns)
    if missing:
        msg = (
            f"Missing required columns: {', '.join(sorted(missing))}. "
            f"Found: {', '.join(columns)}"
        )
        raise CSVImportError(msg)

    return columns


def import_csv(
    *,
    db: BulkDB,
    csv_path: Path,
    mode: str,
) -> CSVImportResult:
    """Import a CSV file into DuckDB and validate each row with Pydantic.

    Args:
        db: BulkDB instance.
        csv_path: Path to the CSV file.
        mode: Run mode ('update', 'dryrun', 'validate').

    Returns:
        CSVImportResult with import statistics.

    Raises:
        CSVImportError: If CSV format is invalid.
    """
    csv_path = Path(csv_path)
    separator = detect_separator(csv_path)
    columns = validate_csv_header(csv_path, separator=separator)

    # Read all data rows
    rows = _read_csv_rows(csv_path, columns=columns, separator=separator)

    if not rows:
        codcom = "UNKNOWN"
    else:
        codcom = rows[0].get("codcom", "UNKNOWN")

    # Create run
    run_id = db.create_run(
        codcom=codcom,
        csv_path=str(csv_path),
        db_path=db.db_path,
        mode=mode,
    )

    # Insert rows into DuckDB and validate
    valid_count = 0
    invalid_count = 0

    for idx, row in enumerate(rows, start=1):
        row_codcom = row.get("codcom", "")
        row_progr = row.get("progr_civico", "")
        row_x = _empty_to_none(row.get("x"))
        row_y = _empty_to_none(row.get("y"))
        row_z = _empty_to_none(row.get("z"))
        row_metodo = _empty_to_none(row.get("metodo"))

        # Insert into bulk_input
        db.con.execute(
            "INSERT INTO bulk_input "
            "(row_id, run_id, codcom, progr_civico, x, y, z, metodo) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            [idx, run_id, row_codcom, row_progr, row_x, row_y, row_z, row_metodo],
        )

        # Validate with Pydantic
        validation_error = _validate_row(x=row_x, y=row_y, z=row_z, metodo=row_metodo)

        if validation_error is None:
            db.update_row_status(row_id=idx, status=RowStatus.VALID)
            valid_count += 1
        else:
            db.update_row_status(
                row_id=idx,
                status=RowStatus.INVALID,
                validation_error=validation_error,
            )
            invalid_count += 1

    # Update run counts
    db.update_run_counts(
        run_id=run_id,
        total_rows=len(rows),
        valid_rows=valid_count,
        invalid_rows=invalid_count,
    )

    return CSVImportResult(
        run_id=run_id,
        codcom=codcom,
        total_rows=len(rows),
        valid_rows=valid_count,
        invalid_rows=invalid_count,
    )


def _read_csv_rows(
    csv_path: Path,
    *,
    columns: list[str],
    separator: str,
) -> list[dict[str, Any]]:
    """Read CSV rows using csv.DictReader."""
    rows = []
    with open(csv_path, encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f, delimiter=separator)
        for row in reader:
            # Normalize keys to lowercase
            normalized = {
                k.strip().lower(): v.strip() if v else ""
                for k, v in row.items()
                if k is not None
            }
            rows.append(normalized)
    return rows


def _empty_to_none(value: str | None) -> str | None:
    """Convert empty strings to None."""
    if value is None or value.strip() == "":
        return None
    return value.strip()


def _validate_row(
    *,
    x: str | None,
    y: str | None,
    z: str | None,
    metodo: str | None,
) -> str | None:
    """Validate a row's coordinate fields using ValidatedCoordinate.

    Returns:
        None if valid, error message string if invalid.
    """
    try:
        ValidatedCoordinate(
            x=x,
            y=y,
            z=z,
            metodo=metodo,
        )
        return None
    except CoordinateValidationError as e:
        return str(e)
    except Exception as e:
        return f"Validation error: {e}"
