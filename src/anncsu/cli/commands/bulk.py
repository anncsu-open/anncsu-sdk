"""CLI commands for bulk coordinate operations."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Annotated

import typer
from rich.console import Console
from rich.table import Table

from anncsu.coordinate.bulk.db import BulkDB
from anncsu.coordinate.bulk.importer import CSVImportError, import_csv
from anncsu.coordinate.bulk.reporter import BulkReporter

bulk_app = typer.Typer(
    name="bulk",
    help="Bulk coordinate operations with CSV input and DuckDB persistence.",
    no_args_is_help=True,
)

console = Console()
error_console = Console(stderr=True)


@bulk_app.command("validate")
def validate(
    csv_path: Annotated[
        Path,
        typer.Argument(
            help="Path to the CSV file to validate.",
            exists=True,
            readable=True,
        ),
    ],
    json_output: Annotated[
        bool,
        typer.Option("--json", help="Output results as JSON."),
    ] = False,
) -> None:
    """Validate a CSV file for bulk coordinate updates.

    Checks header format, required columns, and validates each row
    against ANNCSU business rules using Pydantic models.
    No API calls are made.

    Example:
        anncsu coordinate bulk validate input.csv
        anncsu coordinate bulk validate input.csv --json
    """
    try:
        with BulkDB(":memory:") as db:
            result = import_csv(db=db, csv_path=csv_path, mode="validate")

            if json_output:
                output = {
                    "total_rows": result.total_rows,
                    "valid_rows": result.valid_rows,
                    "invalid_rows": result.invalid_rows,
                    "codcom": result.codcom,
                }
                if result.invalid_rows > 0:
                    reporter = BulkReporter(db=db, run_id=result.run_id)
                    output["validation_errors"] = reporter.get_validation_errors()
                console.print(json.dumps(output, indent=2, default=str))
                return

            # Rich table output
            console.print("\n[bold]CSV Validation Report[/bold]\n")
            console.print(f"  File: {csv_path}")
            console.print(f"  Codice Comune: {result.codcom}")
            console.print(f"  Total rows: {result.total_rows}")
            console.print(f"  Valid: [green]{result.valid_rows}[/green]")

            if result.invalid_rows > 0:
                console.print(f"  Invalid: [red]{result.invalid_rows}[/red]\n")
                # Show validation errors
                reporter = BulkReporter(db=db, run_id=result.run_id)
                val_errors = reporter.get_validation_errors()
                if val_errors:
                    table = Table(title="Validation Errors")
                    table.add_column("Row", style="dim")
                    table.add_column("progr_civico")
                    table.add_column("Error", style="red")
                    for err in val_errors:
                        table.add_row(
                            str(err["row_id"]),
                            str(err["progr_civico"]),
                            str(err["validation_error"]),
                        )
                    console.print(table)
            else:
                console.print("  Invalid: 0\n")
                console.print("[green]All rows are valid.[/green]")

    except CSVImportError as e:
        error_console.print(f"[red]CSV Error:[/red] {e}")
        raise typer.Exit(1) from None
    except Exception as e:
        error_console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(1) from None
