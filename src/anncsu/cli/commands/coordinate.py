# SPDX-FileCopyrightText: 2025-present Geobeyond <info@geobeyond.it>
# SPDX-License-Identifier: MIT
"""Coordinate command group for ANNCSU coordinate management."""

from __future__ import annotations

from typing import Annotated

import httpx
import typer
from rich.console import Console
from rich.table import Table

from anncsu.cli.models import (
    CoordinateStatusResult,
    CoordinateUpdateResult,
    DryRunResult,
    OriginalCoordinates,
)
from anncsu.common import PDNDAuthManager
from anncsu.common.config import APIType, ClientAssertionSettings
from anncsu.common.security import Security as PASecurity
from anncsu.common.session import get_config_dir
from anncsu.coordinate import AnncsuCoordinate
from anncsu.coordinate.models import Accesso, Coordinate, Richiesta, Security
from anncsu.pa import AnncsuConsultazione

coordinate_app = typer.Typer(
    name="coordinate",
    help="Coordinate management commands for ANNCSU.",
    no_args_is_help=True,
)

console = Console()
error_console = Console(stderr=True)

# Default token endpoint for UAT
DEFAULT_TOKEN_ENDPOINT = "https://auth.uat.interop.pagopa.it/token.oauth2"

# Default server URLs for coordinate API
# Note: Uses AgenziaEntrate-PDND path and anncsu-aggiornamento-coordinate endpoint
SERVERS = {
    "production": "https://modipa.agenziaentrate.it/govway/rest/in/AgenziaEntrate-PDND/anncsu-aggiornamento-coordinate/v1",
    "validation": "https://modipa-val.agenziaentrate.it/govway/rest/in/AgenziaEntrate-PDND/anncsu-aggiornamento-coordinate/v1",
}

# Default server URLs for consultazione API
CONSULT_SERVERS = {
    "production": "https://modipa.agenziaentrate.it/govway/rest/in/AgenziaEntrate-PDND/anncsu-consultazione/v1",
    "validation": "https://modipa-val.agenziaentrate.it/govway/rest/in/AgenziaEntrate-PDND/anncsu-consultazione/v1",
}


def _get_consult_sdk(
    token_endpoint: str,
    server_url: str | None = None,
    verify_ssl: bool = True,
) -> AnncsuConsultazione:
    """Create an authenticated consultazione SDK instance.

    Uses APIType.PA for authentication (PA Consultazione API).
    """
    try:
        settings = ClientAssertionSettings()
    except Exception as e:
        error_console.print(f"[red]Error:[/red] Configuration not found: {e}")
        raise typer.Exit(1) from None

    try:
        manager = PDNDAuthManager(
            api_type=APIType.PA,
            settings=settings,
            token_endpoint=token_endpoint,
            session_persistence=True,
            config_dir=get_config_dir(),
        )
        access_token = manager.get_access_token()
    except Exception as e:
        error_console.print(f"[red]Error:[/red] Authentication failed: {e}")
        raise typer.Exit(1) from None

    # Create security object for consultazione API
    security = PASecurity(bearer=access_token)

    # Create HTTP client with optional SSL verification
    client = httpx.Client(verify=verify_ssl)

    return AnncsuConsultazione(
        security=security,
        server_url=server_url,
        client=client,
    )


def _get_sdk(
    token_endpoint: str,
    server_url: str | None = None,
    verify_ssl: bool = True,
    modi_audience: str | None = None,
) -> tuple[AnncsuCoordinate, PDNDAuthManager]:
    """Create an authenticated SDK instance with optional ModI support.

    Uses APIType.COORDINATE for authentication (Coordinate API).

    Args:
        token_endpoint: PDND token endpoint URL.
        server_url: API server URL.
        verify_ssl: Whether to verify SSL certificates.
        modi_audience: Audience URL for ModI headers (typically the API base URL).

    Returns:
        Tuple of (SDK instance, PDNDAuthManager for ModI header generation).
    """
    try:
        settings = ClientAssertionSettings()
    except Exception as e:
        error_console.print(f"[red]Error:[/red] Configuration not found: {e}")
        raise typer.Exit(1) from None

    try:
        manager = PDNDAuthManager(
            api_type=APIType.COORDINATE,
            settings=settings,
            token_endpoint=token_endpoint,
            session_persistence=True,
            config_dir=get_config_dir(),
            modi_audience=modi_audience,
        )
        access_token = manager.get_access_token()
    except Exception as e:
        error_console.print(f"[red]Error:[/red] Authentication failed: {e}")
        raise typer.Exit(1) from None

    # Create security object for coordinate API
    security = Security(bearer_auth=access_token)

    # Create HTTP client with optional SSL verification
    client = httpx.Client(verify=verify_ssl)

    sdk = AnncsuCoordinate(
        security=security,
        server_url=server_url,
        client=client,
    )

    return sdk, manager


@coordinate_app.command("update")
def update(
    codcom: Annotated[
        str,
        typer.Option(
            "--codcom",
            "-c",
            help="Codice comune (Belfiore code, e.g. H501 for Roma).",
        ),
    ],
    progr_civico: Annotated[
        str,
        typer.Option(
            "--progr-civico",
            "-p",
            help="Progressivo civico (access progressive number).",
        ),
    ],
    x: Annotated[
        str | None,
        typer.Option(
            "--x",
            help="Coordinata X (longitude). Valid range for Italy: 6.0-18.0",
        ),
    ] = None,
    y: Annotated[
        str | None,
        typer.Option(
            "--y",
            help="Coordinata Y (latitude). Valid range for Italy: 36.0-47.0",
        ),
    ] = None,
    z: Annotated[
        str | None,
        typer.Option(
            "--z",
            help="Quota (altitude in meters).",
        ),
    ] = None,
    metodo: Annotated[
        str | None,
        typer.Option(
            "--metodo",
            "-m",
            help="Metodo di rilevazione (1-4).",
        ),
    ] = None,
    token_endpoint: Annotated[
        str,
        typer.Option(
            "--token-endpoint",
            "-e",
            help="PDND token endpoint URL.",
        ),
    ] = DEFAULT_TOKEN_ENDPOINT,
    server_url: Annotated[
        str | None,
        typer.Option(
            "--server-url",
            "-s",
            help="API server URL. Defaults to validation environment.",
        ),
    ] = None,
    validation_env: Annotated[
        bool,
        typer.Option(
            "--validation/--production",
            help="Use validation (UAT) or production environment.",
        ),
    ] = True,
    no_verify_ssl: Annotated[
        bool,
        typer.Option(
            "--no-verify-ssl",
            help="Disable SSL certificate verification (use with caution).",
        ),
    ] = False,
    json_output: Annotated[
        bool,
        typer.Option("--json", help="Output as JSON."),
    ] = False,
) -> None:
    """Update coordinates for an access point (civico).

    Example:
        anncsu coordinate update --codcom H501 --progr-civico 12345 --x 12.4963655 --y 41.9027835 --metodo 4
    """
    # Determine server URL
    if server_url is None:
        server_url = SERVERS["validation"] if validation_env else SERVERS["production"]

    # Create SDK with ModI support (modi_audience is the API base URL)
    sdk, auth_manager = _get_sdk(
        token_endpoint=token_endpoint,
        server_url=server_url,
        verify_ssl=not no_verify_ssl,
        modi_audience=server_url,
    )

    # Build coordinate object if any coordinate provided
    coordinate_obj = None
    if x is not None or y is not None or z is not None or metodo is not None:
        coordinate_obj = Coordinate(
            x=x,
            y=y,
            z=z,
            metodo=metodo,
        )

    # Build request
    richiesta = Richiesta(
        accesso=Accesso(
            codcom=codcom,
            progr_civico=progr_civico,
            coordinate=coordinate_obj,
        )
    )

    # Generate ModI headers if configured
    http_headers = auth_manager.get_modi_headers(
        richiesta.model_dump(by_alias=True, exclude_none=True)
    )

    try:
        response = sdk.json_post.gestionecoordinate(
            richiesta=richiesta,
            http_headers=http_headers if http_headers else None,
        )
    except Exception as e:
        error_console.print(f"[red]Error:[/red] API call failed: {e}")
        raise typer.Exit(1) from None

    # Build result
    result = CoordinateUpdateResult(
        success=response.esito == "OK" if response.esito else False,
        id_richiesta=response.id_richiesta,
        esito=response.esito,
        messaggio=response.messaggio,
        dati_count=len(response.dati) if response.dati else 0,
    )

    if json_output:
        print(result.model_dump_json(indent=2))
        return

    # Display table
    if result.success:
        console.print(
            f"[green]Operation successful![/green] ID: {result.id_richiesta}\n"
        )
    else:
        console.print(f"[red]Operation failed.[/red] ID: {result.id_richiesta}\n")

    table = Table(show_header=True, header_style="bold")
    table.add_column("Field", style="cyan")
    table.add_column("Value")

    table.add_row("ID Richiesta", result.id_richiesta or "N/A")
    table.add_row("Esito", result.esito or "N/A")
    table.add_row("Messaggio", result.messaggio or "N/A")
    table.add_row("Dati Restituiti", str(result.dati_count))

    console.print(table)


@coordinate_app.command("dry-run")
def dry_run(
    codcom: Annotated[
        str,
        typer.Option(
            "--codcom",
            "-c",
            help="Codice comune (Belfiore code, e.g. H501 for Roma).",
        ),
    ],
    denom: Annotated[
        str,
        typer.Option(
            "--denom",
            "-d",
            help="Denominazione esatta dell'odonimo - base64 encoded.",
        ),
    ],
    accparz: Annotated[
        str | None,
        typer.Option(
            "--accparz",
            "-a",
            help="Valore anche parziale del civico. If not provided, uses first available.",
        ),
    ] = None,
    token_endpoint: Annotated[
        str,
        typer.Option(
            "--token-endpoint",
            "-e",
            help="PDND token endpoint URL.",
        ),
    ] = DEFAULT_TOKEN_ENDPOINT,
    server_url: Annotated[
        str | None,
        typer.Option(
            "--server-url",
            "-s",
            help="API server URL. Defaults to validation environment.",
        ),
    ] = None,
    validation_env: Annotated[
        bool,
        typer.Option(
            "--validation/--production",
            help="Use validation (UAT) or production environment.",
        ),
    ] = True,
    no_verify_ssl: Annotated[
        bool,
        typer.Option(
            "--no-verify-ssl",
            help="Disable SSL certificate verification (use with caution).",
        ),
    ] = False,
    json_output: Annotated[
        bool,
        typer.Option("--json", help="Output as JSON."),
    ] = False,
) -> None:
    """Dry-run coordinate update: search, test update, then restore original values.

    This command performs a complete test cycle:
    1. Search for an access point (civico) using codcom and denom
    2. Save the original coordinates
    3. Perform a test update (with same or slightly modified coordinates)
    4. Immediately restore the original coordinates

    If restore fails, a warning is shown with the original values for manual restoration.

    Example:
        anncsu coordinate dry-run --codcom H501 --denom VklBIFJPTUE=
        anncsu coordinate dry-run --codcom H501 --denom VklBIFJPTUE= --accparz 10
    """
    # Determine server URLs
    coord_server = server_url or (
        SERVERS["validation"] if validation_env else SERVERS["production"]
    )
    consult_server = (
        CONSULT_SERVERS["validation"]
        if validation_env
        else CONSULT_SERVERS["production"]
    )

    # Step 1: Search for the odonimo to get prognaz (progressivo nazionale)
    if not json_output:
        console.print(
            "[bold]Step 1:[/bold] Searching for odonimo and access point...\n"
        )

    consult_sdk = _get_consult_sdk(
        token_endpoint=token_endpoint,
        server_url=consult_server,
        verify_ssl=not no_verify_ssl,
    )

    # Step 1a: Get progressivo nazionale dell'odonimo
    try:
        odonimo_response = consult_sdk.queryparam.elencoodonimiprog_get_query_param(
            codcom=codcom,
            denomparz=denom,
        )
    except Exception as e:
        error_console.print(f"[red]Error:[/red] Odonimo search failed: {e}")
        raise typer.Exit(1) from None

    if not odonimo_response.data or len(odonimo_response.data) == 0:
        error_console.print(
            f"[red]Error:[/red] No odonimo found for codcom={codcom}, denom={denom}"
        )
        raise typer.Exit(1) from None

    # Use the first odonimo result
    odonimo_data = odonimo_response.data[0]
    prognaz = odonimo_data.prognaz

    if not prognaz:
        error_console.print(
            "[red]Error:[/red] Odonimo found but no prognaz (progressivo nazionale) available"
        )
        raise typer.Exit(1) from None

    if not json_output:
        console.print(f"  Found odonimo: {odonimo_data.dug} {odonimo_data.denomuff}")
        console.print(f"  Progressivo nazionale: {prognaz}\n")

    # Step 1b: Get accessi for this odonimo
    try:
        # Use accparz if provided, otherwise use "1" to get at least one result
        search_accparz = accparz if accparz else "1"
        search_response = consult_sdk.queryparam.elencoaccessiprog_get_query_param(
            prognaz=prognaz,
            accparz=search_accparz,
        )
    except Exception as e:
        error_console.print(f"[red]Error:[/red] Access search failed: {e}")
        raise typer.Exit(1) from None

    if not search_response.data or len(search_response.data) == 0:
        error_console.print(
            f"[red]Error:[/red] No access point found for prognaz={prognaz}"
        )
        raise typer.Exit(1) from None

    # Use the first result
    accesso_data = search_response.data[0]
    prognazacc = accesso_data.prognazacc

    if not prognazacc:
        error_console.print(
            "[red]Error:[/red] Access point found but no prognazacc available"
        )
        raise typer.Exit(1) from None

    # Save original coordinates
    original = OriginalCoordinates(
        prognazacc=prognazacc,
        codcom=codcom,
        civico=accesso_data.civico,
        coord_x=accesso_data.coord_x,
        coord_y=accesso_data.coord_y,
        quota=accesso_data.quota,
        metodo=accesso_data.metodo,
    )

    if not json_output:
        console.print(f"[green]Found access point:[/green] prognazacc={prognazacc}")
        console.print(f"  Civico: {original.civico or 'N/A'}")
        console.print(f"  Coord X: {original.coord_x or 'N/A'}")
        console.print(f"  Coord Y: {original.coord_y or 'N/A'}")
        console.print(f"  Quota: {original.quota or 'N/A'}")
        console.print(f"  Metodo: {original.metodo or 'N/A'}\n")

    # Step 2: Perform test update
    if not json_output:
        console.print("[bold]Step 2:[/bold] Performing test update...\n")

    coord_sdk, auth_manager = _get_sdk(
        token_endpoint=token_endpoint,
        server_url=coord_server,
        verify_ssl=not no_verify_ssl,
        modi_audience=coord_server,
    )

    # Build test coordinate (use same values)
    test_coordinate = Coordinate(
        x=original.coord_x,
        y=original.coord_y,
        z=original.quota,
        metodo=original.metodo,
    )

    test_richiesta = Richiesta(
        accesso=Accesso(
            codcom=codcom,
            progr_civico=prognazacc,
            coordinate=test_coordinate,
        )
    )

    # Generate ModI headers for test update
    test_http_headers = auth_manager.get_modi_headers(
        test_richiesta.model_dump(by_alias=True, exclude_none=True)
    )

    test_update_result: CoordinateUpdateResult
    try:
        test_response = coord_sdk.json_post.gestionecoordinate(
            richiesta=test_richiesta,
            http_headers=test_http_headers if test_http_headers else None,
        )
        test_update_result = CoordinateUpdateResult(
            success=test_response.esito == "OK" if test_response.esito else False,
            id_richiesta=test_response.id_richiesta,
            esito=test_response.esito,
            messaggio=test_response.messaggio,
            dati_count=len(test_response.dati) if test_response.dati else 0,
        )
        if not json_output:
            console.print(
                f"[green]Test update completed:[/green] esito={test_update_result.esito}\n"
            )
    except Exception as e:
        error_console.print(f"[red]Error:[/red] Test update failed: {e}")
        raise typer.Exit(1) from None

    # Step 3: Restore original coordinates
    if not json_output:
        console.print("[bold]Step 3:[/bold] Restoring original coordinates...\n")

    restore_coordinate = Coordinate(
        x=original.coord_x,
        y=original.coord_y,
        z=original.quota,
        metodo=original.metodo,
    )

    restore_richiesta = Richiesta(
        accesso=Accesso(
            codcom=codcom,
            progr_civico=prognazacc,
            coordinate=restore_coordinate,
        )
    )

    # Generate ModI headers for restore (fresh headers for new request)
    restore_http_headers = auth_manager.get_modi_headers(
        restore_richiesta.model_dump(by_alias=True, exclude_none=True)
    )

    restore_result: CoordinateUpdateResult | None = None
    restore_failed = False
    error_message: str | None = None

    try:
        restore_response = coord_sdk.json_post.gestionecoordinate(
            richiesta=restore_richiesta,
            http_headers=restore_http_headers if restore_http_headers else None,
        )
        restore_result = CoordinateUpdateResult(
            success=restore_response.esito == "OK" if restore_response.esito else False,
            id_richiesta=restore_response.id_richiesta,
            esito=restore_response.esito,
            messaggio=restore_response.messaggio,
            dati_count=len(restore_response.dati) if restore_response.dati else 0,
        )
        if not json_output:
            console.print(
                f"[green]Restore completed:[/green] esito={restore_result.esito}\n"
            )
    except Exception as e:
        restore_failed = True
        error_message = str(e)
        error_console.print(f"\n[yellow]WARNING:[/yellow] Restore failed: {e}\n")
        error_console.print(
            "[yellow]Original coordinates to restore manually:[/yellow]"
        )
        error_console.print(f"  prognazacc: {original.prognazacc}")
        error_console.print(f"  codcom: {original.codcom}")
        error_console.print(f"  coord_x: {original.coord_x}")
        error_console.print(f"  coord_y: {original.coord_y}")
        error_console.print(f"  quota: {original.quota}")
        error_console.print(f"  metodo: {original.metodo}\n")

    # Build final result
    result = DryRunResult(
        success=not restore_failed and test_update_result.success,
        original_coordinates=original,
        test_update=test_update_result,
        restore=restore_result,
        restore_failed=restore_failed,
        error_message=error_message,
    )

    if json_output:
        print(result.model_dump_json(indent=2))
        if restore_failed:
            raise typer.Exit(1)
        return

    # Display summary
    console.print("[bold]Dry-run Summary:[/bold]\n")

    table = Table(show_header=True, header_style="bold")
    table.add_column("Step", style="cyan")
    table.add_column("Status")
    table.add_column("Details")

    table.add_row(
        "Search",
        "[green]OK[/green]",
        f"Found prognazacc={prognazacc}",
    )
    table.add_row(
        "Test Update",
        "[green]OK[/green]" if test_update_result.success else "[red]FAILED[/red]",
        test_update_result.messaggio or test_update_result.esito or "N/A",
    )
    if restore_result:
        table.add_row(
            "Restore",
            "[green]OK[/green]" if restore_result.success else "[red]FAILED[/red]",
            restore_result.messaggio or restore_result.esito or "N/A",
        )
    else:
        table.add_row(
            "Restore",
            "[red]FAILED[/red]",
            error_message or "Unknown error",
        )

    console.print(table)

    if restore_failed:
        raise typer.Exit(1)


@coordinate_app.command("status")
def status(
    token_endpoint: Annotated[
        str,
        typer.Option(
            "--token-endpoint",
            "-e",
            help="PDND token endpoint URL.",
        ),
    ] = DEFAULT_TOKEN_ENDPOINT,
    server_url: Annotated[
        str | None,
        typer.Option(
            "--server-url",
            "-s",
            help="API server URL. Defaults to validation environment.",
        ),
    ] = None,
    validation_env: Annotated[
        bool,
        typer.Option(
            "--validation/--production",
            help="Use validation (UAT) or production environment.",
        ),
    ] = True,
    no_verify_ssl: Annotated[
        bool,
        typer.Option(
            "--no-verify-ssl",
            help="Disable SSL certificate verification (use with caution).",
        ),
    ] = False,
    json_output: Annotated[
        bool,
        typer.Option("--json", help="Output as JSON."),
    ] = False,
) -> None:
    """Check the status of the Coordinate API service.

    Example:
        anncsu coordinate status
        anncsu coordinate status --production
    """
    # Determine server URL
    if server_url is None:
        server_url = SERVERS["validation"] if validation_env else SERVERS["production"]

    # Create SDK (no ModI needed for status - GET request)
    sdk, _ = _get_sdk(
        token_endpoint=token_endpoint,
        server_url=server_url,
        verify_ssl=not no_verify_ssl,
    )

    try:
        response = sdk.status.show_status()
        api_status = response.status or "unknown"
        is_available = api_status.lower() == "ok" or api_status.lower() == "running"
    except Exception as e:
        api_status = f"Error: {e}"
        is_available = False

    result = CoordinateStatusResult(
        available=is_available,
        status=api_status,
        server_url=server_url,
        environment="validation" if validation_env else "production",
    )

    if json_output:
        print(result.model_dump_json(indent=2))
        return

    # Display result
    env_label = "Validation (UAT)" if validation_env else "Production"
    status_icon = "[green]OK[/green]" if is_available else "[red]UNAVAILABLE[/red]"

    console.print(f"\n[bold]Coordinate API Status - {env_label}[/bold]\n")

    table = Table(show_header=True, header_style="bold")
    table.add_column("Property", style="cyan")
    table.add_column("Value")

    table.add_row("Status", status_icon)
    table.add_row("Server", server_url)
    table.add_row("Response", api_status)

    console.print(table)
