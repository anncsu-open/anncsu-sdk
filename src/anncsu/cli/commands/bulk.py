"""CLI commands for bulk coordinate operations."""

from __future__ import annotations

import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Annotated

import typer
from rich.console import Console
from rich.progress import (
    BarColumn,
    Progress,
    SpinnerColumn,
    TaskProgressColumn,
    TextColumn,
)
from rich.table import Table

from anncsu.common.session import get_config_dir
from anncsu.coordinate.bulk.db import BulkDB
from anncsu.coordinate.bulk.executor import (
    BulkExecutor,
    BulkExecutorResult,
    RateLimitReached,
)
from anncsu.coordinate.bulk.importer import CSVImportError, import_csv
from anncsu.coordinate.bulk.reporter import BulkReporter, ReportFormat

bulk_app = typer.Typer(
    name="bulk",
    help="Bulk coordinate operations with CSV input and DuckDB persistence.",
    no_args_is_help=True,
)

console = Console()
error_console = Console(stderr=True)

# Server URLs for bulk coordinate API (dedicated e-service: grandi comuni).
# Different GovWay path from single-update, matching the PDND token audience.
BULK_SERVERS = {
    "production": "https://modipa.agenziaentrate.gov.it/govway/rest/in/AgenziaEntrate-PDND/anncsu-aggiornamento-coordinate-grandi-comuni/v1",
    "validation": "https://modipa-val.agenziaentrate.it/govway/rest/in/AgenziaEntrate-PDND/anncsu-aggiornamento-coordinate-grandi-comuni/v1",
}


# ---------------------------------------------------------------------------
# Private helpers
# ---------------------------------------------------------------------------


def _get_bulk_dir() -> Path:
    """Return ~/.anncsu/bulk/ directory path."""
    return get_config_dir() / "bulk"


def _build_db_path(codcom: str, run_id: str) -> Path:
    """Build the canonical DB file path for a given run."""
    return _get_bulk_dir() / f"{codcom}_{run_id}.db"


def _find_db_for_run(run_id: str) -> Path | None:
    """Search ~/.anncsu/bulk/ for a DB file containing the given run_id."""
    bulk_dir = _get_bulk_dir()
    if not bulk_dir.exists():
        return None
    for db_file in bulk_dir.glob("*.db"):
        if run_id in db_file.name:
            return db_file
    return None


def _get_coord_sdk(
    token_endpoint: str,
    server_url: str,
    verify_ssl: bool,
):
    """Lazy wrapper to avoid circular import with coordinate.py.

    Uses APIType.COORDINATE_BULK for authentication, which maps to
    PDND_PURPOSE_ID_COORDINATE_BULK (dedicated rate limit: 50k calls/day).

    Returns:
        Tuple of (SDK instance, token_refresher callable) for bulk operations.
        The token_refresher can be passed to BulkExecutor for automatic 401 retry.
    """
    from anncsu.cli.commands.coordinate import _get_sdk
    from anncsu.common.config import APIType

    sdk, manager = _get_sdk(
        token_endpoint=token_endpoint,
        server_url=server_url,
        verify_ssl=verify_ssl,
        modi_audience=server_url,
        api_type=APIType.COORDINATE_BULK,
    )

    return sdk, manager.get_refresh_callback()


def _get_consult_sdk_lazy(
    token_endpoint: str,
    server_url: str,
    verify_ssl: bool,
):
    """Lazy wrapper to avoid circular import with coordinate.py."""
    from anncsu.cli.commands.coordinate import _get_consult_sdk

    return _get_consult_sdk(
        token_endpoint=token_endpoint,
        server_url=server_url,
        verify_ssl=verify_ssl,
    )


def _resolve_servers(validation_env: bool, server_url: str | None):
    """Resolve coordinate and consultazione server URLs.

    Uses BULK_SERVERS (dedicated e-service) for coordinate updates,
    not the single-update SERVERS from coordinate.py.
    """
    from anncsu.cli.commands.coordinate import CONSULT_SERVERS

    coord_server = server_url or (
        BULK_SERVERS["validation"] if validation_env else BULK_SERVERS["production"]
    )
    consult_server = (
        CONSULT_SERVERS["validation"]
        if validation_env
        else CONSULT_SERVERS["production"]
    )
    return coord_server, consult_server


def _default_token_endpoint() -> str:
    from anncsu.cli.commands.coordinate import DEFAULT_TOKEN_ENDPOINT

    return DEFAULT_TOKEN_ENDPOINT


# ---------------------------------------------------------------------------
# Commands
# ---------------------------------------------------------------------------


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
                print(json.dumps(output, indent=2, default=str))
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


@bulk_app.command("update")
def bulk_update(
    csv_path: Annotated[
        Path,
        typer.Argument(
            help="Path to the CSV file with coordinate updates.",
            exists=True,
            readable=True,
        ),
    ],
    token_endpoint: Annotated[
        str,
        typer.Option("--token-endpoint", "-e", help="PDND token endpoint URL."),
    ] = "https://auth.uat.interop.pagopa.it/token.oauth2",
    server_url: Annotated[
        str | None,
        typer.Option("--server-url", "-s", help="API server URL."),
    ] = None,
    validation_env: Annotated[
        bool,
        typer.Option(
            "--validation/--production", help="Use validation (UAT) or production."
        ),
    ] = True,
    no_verify_ssl: Annotated[
        bool,
        typer.Option("--no-verify-ssl", help="Disable SSL certificate verification."),
    ] = False,
    json_output: Annotated[
        bool,
        typer.Option("--json", help="Output results as JSON."),
    ] = False,
    max_records: Annotated[
        int | None,
        typer.Option("--max-records", "-n", help="Maximum records to process."),
    ] = None,
) -> None:
    """Execute bulk coordinate update from a CSV file.

    Imports the CSV, validates rows, then calls the Coordinate API for each
    valid row. Progress is tracked in a local DuckDB database for resume
    capability.

    Example:
        anncsu coordinate bulk update input.csv
        anncsu coordinate bulk update input.csv --max-records 1000
        anncsu coordinate bulk update input.csv --json
    """
    coord_server, _ = _resolve_servers(validation_env, server_url)

    try:
        # Create bulk directory
        bulk_dir = _get_bulk_dir()
        bulk_dir.mkdir(parents=True, exist_ok=True)

        # Import CSV: first to :memory: for validation/codcom, then to persistent DB.
        with BulkDB(":memory:") as tmp_db:
            tmp_result = import_csv(db=tmp_db, csv_path=csv_path, mode="update")

        # Use codcom from validation pass for initial filename
        db_path = _build_db_path(tmp_result.codcom, tmp_result.run_id)
        with BulkDB(str(db_path)) as db:
            import_result = import_csv(db=db, csv_path=csv_path, mode="update")

        # Rename DB file to match the actual run_id from the persistent import
        if import_result.run_id != tmp_result.run_id:
            new_db_path = _build_db_path(import_result.codcom, import_result.run_id)
            db_path.rename(new_db_path)
            db_path = new_db_path

        with BulkDB(str(db_path)) as db:
            if not json_output:
                console.print("\n[bold]Bulk Update[/bold]")
                console.print(f"  CSV: {csv_path}")
                console.print(f"  Codice Comune: {import_result.codcom}")
                console.print(f"  Total rows: {import_result.total_rows}")
                console.print(f"  Valid: {import_result.valid_rows}")
                console.print(f"  Invalid: {import_result.invalid_rows}")
                if max_records is not None:
                    console.print(f"  Max records: {max_records}")
                console.print(f"  Run ID: {import_result.run_id}")
                console.print(f"  DB: {db_path}\n")

            # Create SDK and token refresher
            sdk, token_refresher = _get_coord_sdk(
                token_endpoint=token_endpoint,
                server_url=coord_server,
                verify_ssl=not no_verify_ssl,
            )

            rate_limited = False

            if not json_output:
                with Progress(
                    SpinnerColumn(),
                    TextColumn("[progress.description]{task.description}"),
                    BarColumn(),
                    TaskProgressColumn(),
                    console=console,
                ) as progress:
                    task = progress.add_task(
                        "Processing...", total=import_result.valid_rows
                    )

                    def on_progress(
                        processed: int, total: int, succeeded: int, failed: int
                    ) -> None:
                        progress.update(
                            task,
                            total=total,
                            completed=processed,
                            description=f"Processing: {processed}/{total} (ok={succeeded} err={failed})",
                        )

                    try:
                        executor = BulkExecutor(
                            db=db,
                            run_id=import_result.run_id,
                            sdk=sdk,
                            on_progress=on_progress,
                            max_records=max_records,
                            token_refresher=token_refresher,
                        )
                        exec_result = executor.execute()
                    except RateLimitReached as e:
                        rate_limited = True
                        exec_result = BulkExecutorResult(
                            processed=e.processed,
                            succeeded=0,
                            failed=0,
                            run_id=e.run_id,
                        )
                        error_console.print(
                            f"\n[yellow]Rate limit reached:[/yellow] {e}"
                        )
            else:
                try:
                    executor = BulkExecutor(
                        db=db,
                        run_id=import_result.run_id,
                        sdk=sdk,
                        max_records=max_records,
                        token_refresher=token_refresher,
                    )
                    exec_result = executor.execute()
                except RateLimitReached as e:
                    rate_limited = True
                    exec_result = BulkExecutorResult(
                        processed=e.processed,
                        succeeded=0,
                        failed=0,
                        run_id=e.run_id,
                    )

            db.finish_run(import_result.run_id)

            if json_output:
                output = {
                    "run_id": import_result.run_id,
                    "codcom": import_result.codcom,
                    "db_path": str(db_path),
                    "total_rows": import_result.total_rows,
                    "valid_rows": import_result.valid_rows,
                    "invalid_rows": import_result.invalid_rows,
                    "max_records": max_records,
                    "processed": exec_result.processed,
                    "succeeded": exec_result.succeeded,
                    "failed": exec_result.failed,
                    "rate_limited": rate_limited,
                    "timing": {
                        "total_elapsed_ms": round(exec_result.total_elapsed_ms, 2),
                        "avg_elapsed_ms": round(exec_result.avg_elapsed_ms, 2),
                        "min_elapsed_ms": round(exec_result.min_elapsed_ms, 2),
                        "max_elapsed_ms": round(exec_result.max_elapsed_ms, 2),
                        "estimated_50k_minutes": round(
                            exec_result.estimated_50k_minutes, 1
                        ),
                    },
                }
                print(json.dumps(output, indent=2, default=str))
            else:
                console.print("\n[bold]Results:[/bold]")
                console.print(f"  Processed: {exec_result.processed}")
                console.print(f"  Succeeded: [green]{exec_result.succeeded}[/green]")
                console.print(f"  Failed: [red]{exec_result.failed}[/red]")
                if exec_result.processed > 0:
                    console.print("\n[bold]Timing:[/bold]")
                    console.print(f"  Avg: {exec_result.avg_elapsed_ms:.0f} ms/call")
                    console.print(
                        f"  Min: {exec_result.min_elapsed_ms:.0f} ms  "
                        f"Max: {exec_result.max_elapsed_ms:.0f} ms"
                    )
                    console.print(
                        f"  Total: {exec_result.total_elapsed_ms / 1000:.1f} s"
                    )
                    console.print(
                        f"  Est. 50k calls: "
                        f"[cyan]{exec_result.estimated_50k_minutes:.1f} min[/cyan]"
                    )

            if rate_limited:
                raise typer.Exit(1) from None

    except CSVImportError as e:
        error_console.print(f"[red]CSV Error:[/red] {e}")
        raise typer.Exit(1) from None
    except typer.Exit:
        raise
    except Exception as e:
        error_console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(1) from None


@bulk_app.command("dry-run")
def bulk_dry_run(
    csv_path: Annotated[
        Path,
        typer.Argument(
            help="Path to the CSV file to dry-run.",
            exists=True,
            readable=True,
        ),
    ],
    max_records: Annotated[
        int,
        typer.Option("--max-records", "-n", help="Maximum records to test."),
    ] = 10,
    token_endpoint: Annotated[
        str,
        typer.Option("--token-endpoint", "-e", help="PDND token endpoint URL."),
    ] = "https://auth.uat.interop.pagopa.it/token.oauth2",
    server_url: Annotated[
        str | None,
        typer.Option("--server-url", "-s", help="API server URL."),
    ] = None,
    validation_env: Annotated[
        bool,
        typer.Option(
            "--validation/--production", help="Use validation (UAT) or production."
        ),
    ] = True,
    no_verify_ssl: Annotated[
        bool,
        typer.Option("--no-verify-ssl", help="Disable SSL certificate verification."),
    ] = False,
    json_output: Annotated[
        bool,
        typer.Option("--json", help="Output results as JSON."),
    ] = False,
) -> None:
    """Dry-run: validate CSV and simulate updates on a few records.

    Imports the CSV, validates rows, then for up to N records:
    1. Looks up current coordinates (PA API)
    2. Updates with CSV values (Coordinate API)
    3. Restores original coordinates

    Example:
        anncsu coordinate bulk dry-run input.csv
        anncsu coordinate bulk dry-run input.csv --max-records 5
    """
    from anncsu.coordinate.bulk.dryrun import BulkDryRunner

    coord_server, consult_server = _resolve_servers(validation_env, server_url)

    try:
        bulk_dir = _get_bulk_dir()
        bulk_dir.mkdir(parents=True, exist_ok=True)

        with BulkDB(":memory:") as tmp_db:
            tmp_result = import_csv(db=tmp_db, csv_path=csv_path, mode="dryrun")

        db_path = _build_db_path(tmp_result.codcom, tmp_result.run_id)
        with BulkDB(str(db_path)) as db:
            import_result = import_csv(db=db, csv_path=csv_path, mode="dryrun")

        # Rename DB file to match the actual run_id from the persistent import
        if import_result.run_id != tmp_result.run_id:
            new_db_path = _build_db_path(import_result.codcom, import_result.run_id)
            db_path.rename(new_db_path)
            db_path = new_db_path

        with BulkDB(str(db_path)) as db:
            if not json_output:
                console.print("\n[bold]Bulk Dry-Run[/bold]")
                console.print(f"  CSV: {csv_path}")
                console.print(f"  Codice Comune: {import_result.codcom}")
                console.print(f"  Valid rows: {import_result.valid_rows}")
                console.print(f"  Max records to test: {max_records}\n")

            coord_sdk, _ = _get_coord_sdk(
                token_endpoint=token_endpoint,
                server_url=coord_server,
                verify_ssl=not no_verify_ssl,
            )
            consult_sdk = _get_consult_sdk_lazy(
                token_endpoint=token_endpoint,
                server_url=consult_server,
                verify_ssl=not no_verify_ssl,
            )

            runner = BulkDryRunner(
                db=db,
                run_id=import_result.run_id,
                coord_sdk=coord_sdk,
                consult_sdk=consult_sdk,
                max_records=max_records,
            )

            if not json_output:
                with Progress(
                    SpinnerColumn(),
                    TextColumn("[progress.description]{task.description}"),
                    console=console,
                ) as progress:
                    progress.add_task("Running dry-run...", total=None)
                    dry_result = runner.execute()
            else:
                dry_result = runner.execute()

            # Fetch error details from DB
            errors = db.get_result_errors(run_id=dry_result.run_id)

            if json_output:
                output = {
                    "run_id": dry_result.run_id,
                    "total_tested": dry_result.total_tested,
                    "updates_succeeded": dry_result.updates_succeeded,
                    "updates_failed": dry_result.updates_failed,
                    "restores_succeeded": dry_result.restores_succeeded,
                    "restores_failed": dry_result.restores_failed,
                    "lookup_failures": dry_result.lookup_failures,
                    "errors": [
                        {
                            "row_id": e[0],
                            "progr_civico": e[1],
                            "operation": e[2],
                            "http_status": e[3],
                            "error_detail": e[4],
                        }
                        for e in errors
                    ],
                }
                print(json.dumps(output, indent=2, default=str))
            else:
                console.print("\n[bold]Dry-Run Results:[/bold]")
                table = Table(show_header=True, header_style="bold")
                table.add_column("Metric", style="cyan")
                table.add_column("Value")
                table.add_row("Total tested", str(dry_result.total_tested))
                table.add_row(
                    "Updates succeeded",
                    f"[green]{dry_result.updates_succeeded}[/green]",
                )
                table.add_row(
                    "Updates failed", f"[red]{dry_result.updates_failed}[/red]"
                )
                table.add_row(
                    "Restores succeeded",
                    f"[green]{dry_result.restores_succeeded}[/green]",
                )
                table.add_row(
                    "Restores failed", f"[red]{dry_result.restores_failed}[/red]"
                )
                table.add_row("Lookup failures", str(dry_result.lookup_failures))
                console.print(table)

                if errors:
                    console.print("\n[bold]Error Details:[/bold]")
                    err_table = Table(show_header=True, header_style="bold")
                    err_table.add_column("Row", style="dim")
                    err_table.add_column("progr_civico")
                    err_table.add_column("Operation")
                    err_table.add_column("HTTP")
                    err_table.add_column("Error", max_width=80)
                    for e in errors:
                        err_table.add_row(
                            str(e[0]),
                            str(e[1]),
                            str(e[2]),
                            str(e[3] or ""),
                            str(e[4] or "")[:120],
                        )
                    console.print(err_table)

            if dry_result.restores_failed > 0:
                error_console.print(
                    "\n[yellow]Warning:[/yellow] Some restores failed. "
                    "Manual intervention may be needed."
                )
                raise typer.Exit(1) from None

    except CSVImportError as e:
        error_console.print(f"[red]CSV Error:[/red] {e}")
        raise typer.Exit(1) from None
    except typer.Exit:
        raise
    except Exception as e:
        error_console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(1) from None


@bulk_app.command("resume")
def resume(
    run_id: Annotated[
        str,
        typer.Argument(help="Run ID to resume."),
    ],
    token_endpoint: Annotated[
        str,
        typer.Option("--token-endpoint", "-e", help="PDND token endpoint URL."),
    ] = "https://auth.uat.interop.pagopa.it/token.oauth2",
    server_url: Annotated[
        str | None,
        typer.Option("--server-url", "-s", help="API server URL."),
    ] = None,
    validation_env: Annotated[
        bool,
        typer.Option(
            "--validation/--production", help="Use validation (UAT) or production."
        ),
    ] = True,
    no_verify_ssl: Annotated[
        bool,
        typer.Option("--no-verify-ssl", help="Disable SSL certificate verification."),
    ] = False,
    json_output: Annotated[
        bool,
        typer.Option("--json", help="Output results as JSON."),
    ] = False,
    max_records: Annotated[
        int | None,
        typer.Option("--max-records", "-n", help="Maximum records to process."),
    ] = None,
) -> None:
    """Resume an interrupted bulk update execution.

    Finds the DuckDB file for the given run ID, resets any rows stuck
    in 'processing' state, and continues execution.

    Example:
        anncsu coordinate bulk resume abc123-def456
    """
    coord_server, _ = _resolve_servers(validation_env, server_url)

    db_file = _find_db_for_run(run_id)
    if db_file is None:
        error_console.print(f"[red]Error:[/red] No DB found for run_id={run_id}")
        raise typer.Exit(1) from None

    try:
        with BulkDB(str(db_file)) as db:
            summary = db.get_run_summary(run_id)
            if summary is None:
                error_console.print(f"[red]Error:[/red] Run {run_id} not found in DB.")
                raise typer.Exit(1) from None

            if summary["mode"] != "update":
                error_console.print(
                    f"[red]Error:[/red] Cannot resume a '{summary['mode']}' run. "
                    "Only 'update' runs can be resumed."
                )
                raise typer.Exit(1) from None

            if not json_output:
                console.print("\n[bold]Resuming Run[/bold]")
                console.print(f"  Run ID: {run_id}")
                console.print(f"  Codice Comune: {summary['codcom']}")
                console.print(f"  DB: {db_file}\n")

            sdk, token_refresher = _get_coord_sdk(
                token_endpoint=token_endpoint,
                server_url=coord_server,
                verify_ssl=not no_verify_ssl,
            )

            rate_limited = False

            if not json_output:
                with Progress(
                    SpinnerColumn(),
                    TextColumn("[progress.description]{task.description}"),
                    BarColumn(),
                    TaskProgressColumn(),
                    console=console,
                ) as progress:
                    task = progress.add_task("Resuming...", total=None)

                    def on_progress(
                        processed: int, total: int, succeeded: int, failed: int
                    ) -> None:
                        progress.update(
                            task,
                            total=total,
                            completed=processed,
                            description=f"Processing: {processed}/{total} (ok={succeeded} err={failed})",
                        )

                    try:
                        executor = BulkExecutor(
                            db=db,
                            run_id=run_id,
                            sdk=sdk,
                            on_progress=on_progress,
                            max_records=max_records,
                            token_refresher=token_refresher,
                        )
                        exec_result = executor.execute(resume=True)
                    except RateLimitReached as e:
                        rate_limited = True
                        exec_result = BulkExecutorResult(
                            processed=e.processed,
                            succeeded=0,
                            failed=0,
                            run_id=e.run_id,
                        )
                        error_console.print(
                            f"\n[yellow]Rate limit reached:[/yellow] {e}"
                        )
            else:
                try:
                    executor = BulkExecutor(
                        db=db,
                        run_id=run_id,
                        sdk=sdk,
                        max_records=max_records,
                        token_refresher=token_refresher,
                    )
                    exec_result = executor.execute(resume=True)
                except RateLimitReached as e:
                    rate_limited = True
                    exec_result = BulkExecutorResult(
                        processed=e.processed,
                        succeeded=0,
                        failed=0,
                        run_id=e.run_id,
                    )

            db.finish_run(run_id)

            if json_output:
                output = {
                    "run_id": run_id,
                    "codcom": summary["codcom"],
                    "db_path": str(db_file),
                    "max_records": max_records,
                    "processed": exec_result.processed,
                    "succeeded": exec_result.succeeded,
                    "failed": exec_result.failed,
                    "rate_limited": rate_limited,
                    "timing": {
                        "total_elapsed_ms": round(exec_result.total_elapsed_ms, 2),
                        "avg_elapsed_ms": round(exec_result.avg_elapsed_ms, 2),
                        "min_elapsed_ms": round(exec_result.min_elapsed_ms, 2),
                        "max_elapsed_ms": round(exec_result.max_elapsed_ms, 2),
                        "estimated_50k_minutes": round(
                            exec_result.estimated_50k_minutes, 1
                        ),
                    },
                }
                print(json.dumps(output, indent=2, default=str))
            else:
                console.print("\n[bold]Results:[/bold]")
                console.print(f"  Processed: {exec_result.processed}")
                console.print(f"  Succeeded: [green]{exec_result.succeeded}[/green]")
                console.print(f"  Failed: [red]{exec_result.failed}[/red]")
                if exec_result.processed > 0:
                    console.print("\n[bold]Timing:[/bold]")
                    console.print(f"  Avg: {exec_result.avg_elapsed_ms:.0f} ms/call")
                    console.print(
                        f"  Min: {exec_result.min_elapsed_ms:.0f} ms  "
                        f"Max: {exec_result.max_elapsed_ms:.0f} ms"
                    )
                    console.print(
                        f"  Total: {exec_result.total_elapsed_ms / 1000:.1f} s"
                    )
                    console.print(
                        f"  Est. 50k calls: "
                        f"[cyan]{exec_result.estimated_50k_minutes:.1f} min[/cyan]"
                    )

            if rate_limited:
                raise typer.Exit(1) from None

    except typer.Exit:
        raise
    except Exception as e:
        error_console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(1) from None


@bulk_app.command("status")
def bulk_status(
    run_id: Annotated[
        str,
        typer.Argument(help="Run ID to query."),
    ],
    json_output: Annotated[
        bool,
        typer.Option("--json", help="Output results as JSON."),
    ] = False,
) -> None:
    """Show status of a bulk execution run.

    Example:
        anncsu coordinate bulk status abc123-def456
        anncsu coordinate bulk status abc123-def456 --json
    """
    db_file = _find_db_for_run(run_id)
    if db_file is None:
        error_console.print(f"[red]Error:[/red] No DB found for run_id={run_id}")
        raise typer.Exit(1) from None

    try:
        with BulkDB(str(db_file)) as db:
            reporter = BulkReporter(db=db, run_id=run_id)
            summary = reporter.get_summary()

            if summary is None:
                error_console.print(f"[red]Error:[/red] Run {run_id} not found in DB.")
                raise typer.Exit(1) from None

            if json_output:
                from dataclasses import asdict

                print(json.dumps(asdict(summary), indent=2, default=str))
                return

            console.print("\n[bold]Bulk Run Status[/bold]\n")
            table = Table(show_header=True, header_style="bold")
            table.add_column("Field", style="cyan")
            table.add_column("Value")
            table.add_row("Run ID", summary.run_id[:8] + "...")
            table.add_row("Codice Comune", summary.codcom)
            table.add_row("Mode", summary.mode)
            table.add_row("Total rows", str(summary.total_rows))
            table.add_row("Valid", str(summary.valid_rows))
            table.add_row("Invalid", str(summary.invalid_rows))
            table.add_row("Processed", str(summary.processed))
            table.add_row("Succeeded", f"[green]{summary.succeeded}[/green]")
            table.add_row("Failed", f"[red]{summary.failed}[/red]")
            table.add_row("Started", summary.started_at or "N/A")
            table.add_row("Finished", summary.finished_at or "in progress")
            table.add_row("DB", str(db_file))
            console.print(table)

    except typer.Exit:
        raise
    except Exception as e:
        error_console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(1) from None


@bulk_app.command("report")
def report(
    run_id: Annotated[
        str,
        typer.Argument(help="Run ID to export."),
    ],
    output: Annotated[
        Path | None,
        typer.Option("--output", "-o", help="Output file path. Defaults to stdout."),
    ] = None,
    fmt: Annotated[
        str,
        typer.Option("--format", "-f", help="Output format: csv or json."),
    ] = "csv",
) -> None:
    """Export results of a bulk run as CSV or JSON.

    Example:
        anncsu coordinate bulk report abc123 --format csv
        anncsu coordinate bulk report abc123 --format json --output results.json
    """
    try:
        report_fmt = ReportFormat(fmt)
    except ValueError:
        error_console.print(
            f"[red]Error:[/red] Invalid format '{fmt}'. Use 'csv' or 'json'."
        )
        raise typer.Exit(1) from None

    db_file = _find_db_for_run(run_id)
    if db_file is None:
        error_console.print(f"[red]Error:[/red] No DB found for run_id={run_id}")
        raise typer.Exit(1) from None

    try:
        with BulkDB(str(db_file)) as db:
            reporter = BulkReporter(db=db, run_id=run_id)

            if output is not None:
                with open(output, "w", encoding="utf-8") as f:
                    reporter.export_results(f, fmt=report_fmt)
                error_console.print(f"Report written to {output}")
            else:
                reporter.export_results(sys.stdout, fmt=report_fmt)

    except typer.Exit:
        raise
    except Exception as e:
        error_console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(1) from None


@bulk_app.command("list")
def list_runs(
    json_output: Annotated[
        bool,
        typer.Option("--json", help="Output results as JSON."),
    ] = False,
) -> None:
    """List all past bulk execution runs.

    Example:
        anncsu coordinate bulk list
        anncsu coordinate bulk list --json
    """
    bulk_dir = _get_bulk_dir()
    if not bulk_dir.exists():
        if json_output:
            print("[]")
        else:
            console.print("No bulk runs found.")
        return

    db_files = sorted(
        bulk_dir.glob("*.db"), key=lambda f: f.stat().st_mtime, reverse=True
    )
    if not db_files:
        if json_output:
            print("[]")
        else:
            console.print("No bulk runs found.")
        return

    all_runs: list[dict] = []
    for db_file in db_files:
        try:
            with BulkDB(str(db_file)) as db:
                rows = db.con.execute(
                    "SELECT run_id, codcom, mode, started_at, finished_at, "
                    "total_rows, processed, succeeded, failed FROM bulk_runs "
                    "ORDER BY started_at DESC"
                ).fetchall()
                columns = [
                    "run_id",
                    "codcom",
                    "mode",
                    "started_at",
                    "finished_at",
                    "total_rows",
                    "processed",
                    "succeeded",
                    "failed",
                ]
                for row in rows:
                    run_dict = dict(zip(columns, row, strict=False))
                    run_dict["db_file"] = str(db_file)
                    all_runs.append(run_dict)
        except Exception:
            error_console.print(
                f"[yellow]Warning:[/yellow] Could not read {db_file.name}"
            )

    if json_output:
        print(json.dumps(all_runs, indent=2, default=str))
        return

    if not all_runs:
        console.print("No bulk runs found.")
        return

    console.print(f"\n[bold]Bulk Runs[/bold] ({len(all_runs)} total)\n")
    table = Table(show_header=True, header_style="bold")
    table.add_column("Run ID", style="dim")
    table.add_column("Codcom")
    table.add_column("Mode")
    table.add_column("Total")
    table.add_column("OK", style="green")
    table.add_column("Err", style="red")
    table.add_column("Started")
    table.add_column("Status")

    for run in all_runs:
        run_id_short = str(run["run_id"])[:8] + "..."
        status = "done" if run["finished_at"] else "in progress"
        table.add_row(
            run_id_short,
            str(run["codcom"]),
            str(run["mode"]),
            str(run["total_rows"]),
            str(run["succeeded"]),
            str(run["failed"]),
            str(run["started_at"] or "N/A")[:19],
            status,
        )

    console.print(table)


@bulk_app.command("clean")
def clean(
    older_than: Annotated[
        int | None,
        typer.Option("--older-than", help="Remove DB files older than N days."),
    ] = None,
    dry_run: Annotated[
        bool,
        typer.Option("--dry-run", help="Show what would be deleted without deleting."),
    ] = False,
    json_output: Annotated[
        bool,
        typer.Option("--json", help="Output results as JSON."),
    ] = False,
) -> None:
    """Remove old bulk DuckDB files.

    Example:
        anncsu coordinate bulk clean --older-than 30
        anncsu coordinate bulk clean --older-than 30 --dry-run
    """
    if older_than is None and not dry_run:
        error_console.print("[red]Error:[/red] Provide --older-than N or --dry-run.")
        raise typer.Exit(1) from None

    bulk_dir = _get_bulk_dir()
    if not bulk_dir.exists():
        if json_output:
            print(json.dumps({"removed": 0, "files": []}, indent=2))
        else:
            console.print("Nothing to clean.")
        return

    db_files = list(bulk_dir.glob("*.db"))
    if not db_files:
        if json_output:
            print(json.dumps({"removed": 0, "files": []}, indent=2))
        else:
            console.print("Nothing to clean.")
        return

    now = datetime.now(tz=timezone.utc)
    # Default: if only --dry-run, show all files
    cutoff_days = older_than if older_than is not None else 0
    cutoff = now - timedelta(days=cutoff_days)

    to_remove: list[Path] = []
    for f in db_files:
        mtime = datetime.fromtimestamp(f.stat().st_mtime, tz=timezone.utc)
        if mtime < cutoff:
            to_remove.append(f)

    if json_output:
        result_files = [
            {"file": str(f), "size_bytes": f.stat().st_size} for f in to_remove
        ]
        output = {
            "dry_run": dry_run,
            "removed": len(to_remove) if not dry_run else 0,
            "would_remove": len(to_remove),
            "files": result_files,
        }
        print(json.dumps(output, indent=2))
        return

    if not to_remove:
        console.print("No DB files match the criteria.")
        return

    action = "Would remove" if dry_run else "Removing"
    for f in to_remove:
        size_kb = f.stat().st_size / 1024
        console.print(f"  {action}: {f.name} ({size_kb:.1f} KB)")
        if not dry_run:
            f.unlink()

    if dry_run:
        console.print(f"\n{len(to_remove)} file(s) would be removed.")
    else:
        console.print(f"\n[green]{len(to_remove)} file(s) removed.[/green]")
