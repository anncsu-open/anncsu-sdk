"""CSV import and SQL validation into DuckDB for bulk coordinate updates."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from anncsu.coordinate.bulk.db import BulkDB

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
    """Import a CSV file into DuckDB and validate all rows with SQL.

    Uses DuckDB's native read_csv_auto() for fast bulk loading and SQL
    CASE/WHEN expressions for validation, replacing the row-by-row
    Pydantic approach.

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
    validate_csv_header(csv_path, separator=separator)

    # Load CSV into staging table (single DuckDB operation)
    staging_columns = db.create_staging_from_csv(str(csv_path), separator=separator)

    # Extract codcom from first row
    codcom = db.get_staging_codcom()

    # Create run
    run_id = db.create_run(
        codcom=codcom,
        csv_path=str(csv_path),
        db_path=db.db_path,
        mode=mode,
    )

    # Insert with SQL-based validation (single INSERT...SELECT)
    total_rows, valid_count, invalid_count = db.insert_validated_from_staging(
        run_id=run_id,
        staging_columns=staging_columns,
    )

    # Update run counts
    db.update_run_counts(
        run_id=run_id,
        total_rows=total_rows,
        valid_rows=valid_count,
        invalid_rows=invalid_count,
    )

    return CSVImportResult(
        run_id=run_id,
        codcom=codcom,
        total_rows=total_rows,
        valid_rows=valid_count,
        invalid_rows=invalid_count,
    )
