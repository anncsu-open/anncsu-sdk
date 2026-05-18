# SPDX-FileCopyrightText: 2025-present Geobeyond <info@geobeyond.it>
# SPDX-License-Identifier: MIT
"""Coordinate command group for ANNCSU coordinate management."""

from __future__ import annotations

import warnings
from typing import Annotated

import duckdb
import httpx
import typer
from rich.console import Console
from rich.progress import (
    BarColumn,
    SpinnerColumn,
    TaskProgressColumn,
    TextColumn,
)
from rich.table import Table

from anncsu.cli.commands.bulk import bulk_app
from anncsu.cli.commands.constants import DEFAULT_TOKEN_ENDPOINT, SERVERS
from anncsu.cli.models import (
    CoordinateStatusResult,
    CoordinateUpdateResult,
    DryRunResult,
    OriginalCoordinates,
)
from anncsu.common import PDNDAuthManager
from anncsu.common.auth import extract_voucher_audience
from anncsu.common.config import APIType, ClientAssertionSettings
from anncsu.common.errors import AudienceMismatchError
from anncsu.common.hooks import SDKHooks, register_modi_hook
from anncsu.common.modi import AuditContext, ModIConfig
from anncsu.common.security import Security as PASecurity
from anncsu.common.session import get_config_dir
from anncsu.coordinate import AnncsuCoordinate
from anncsu.coordinate.models import Accesso, Coordinate, Richiesta, Security
from anncsu.coordinate.models.validated import ValidatedRispostaOperazione
from anncsu.pa import AnncsuConsultazione

coordinate_app = typer.Typer(
    name="coordinate",
    help="Coordinate management commands for ANNCSU.",
    no_args_is_help=True,
)

coordinate_app.add_typer(
    bulk_app,
    name="bulk",
    help="Bulk coordinate operations with CSV input.",
)

console = Console()
error_console = Console(stderr=True)


def _create_results_table(db_path: str) -> None:
    """Create results table in DuckDB if it doesn't exist."""
    conn = duckdb.connect(db_path)
    try:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS batch_update_results (
                run_id VARCHAR,
                timestamp VARCHAR,
                progressivo_accesso INTEGER,
                civico INTEGER,
                http_status INTEGER,
                esito VARCHAR,
                messaggio VARCHAR,
                id_richiesta VARCHAR,
                error_detail VARCHAR,
                elapsed_ms DOUBLE
            )
        """)
        conn.close()
    except Exception as e:
        error_console.print(f"[red]Error creating results table:[/red] {e}")
        raise


def _insert_result(
    db_path: str,
    run_id: str,
    timestamp: str,
    progressivo_accesso: int,
    civico: int,
    http_status: int | None,
    esito: str | None,
    messaggio: str | None,
    id_richiesta: str | None,
    error_detail: str | None,
    elapsed_ms: float,
) -> None:
    """Insert update result into DuckDB."""
    conn = duckdb.connect(db_path)
    try:
        conn.execute(
            """
            INSERT INTO batch_update_results VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            [
                run_id,
                timestamp,
                progressivo_accesso,
                civico,
                http_status,
                esito,
                messaggio,
                id_richiesta,
                error_detail,
                elapsed_ms,
            ],
        )
        conn.close()
    except Exception as e:
        error_console.print(f"[red]Error inserting result:[/red] {e}")


def _print_raw(response: object, label: str = "Raw API response") -> None:
    """Print raw API response to stderr as formatted JSON."""
    import json

    error_console.print(
        f"[dim]{label}:[/dim]\n"
        f"{json.dumps(response.model_dump(), indent=2, default=str)}"
    )


# Default server URLs for consultazione API
CONSULT_SERVERS = {
    "production": "https://modipa.agenziaentrate.gov.it/govway/rest/in/AgenziaEntrate-PDND/anncsu-consultazione-comune/v1",
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
        with warnings.catch_warnings(record=True) as caught_warnings:
            warnings.simplefilter("always")
            manager = PDNDAuthManager(
                api_type=APIType.PA,
                settings=settings,
                token_endpoint=token_endpoint,
                session_persistence=True,
                config_dir=get_config_dir(),
            )
        for w in caught_warnings:
            error_console.print(f"[yellow]Warning:[/yellow] {w.message}")
        access_token = manager.get_access_token()
    except Exception as e:
        error_console.print(f"[red]Error:[/red] Authentication failed: {e}")
        raise typer.Exit(1) from None

    # Auto-correct server URL from voucher audience if different
    voucher_aud = extract_voucher_audience(access_token)
    if voucher_aud and server_url and voucher_aud.rstrip("/") != server_url.rstrip("/"):
        error_console.print(
            f"[yellow]URL auto-corrected:[/yellow] "
            f"Hardcoded URL differs from PDND voucher audience.\n"
            f"  Configured: {server_url}\n"
            f"  Voucher aud: {voucher_aud}\n"
            f"  Using voucher audience as server URL."
        )
        server_url = voucher_aud

    # Create security callable — auto-refreshes token when expired.
    def security_provider() -> PASecurity:
        return PASecurity(bearer=manager.get_access_token())

    # Create HTTP client with optional SSL verification
    client = httpx.Client(verify=verify_ssl)

    return AnncsuConsultazione(
        security=security_provider,
        server_url=server_url,
        client=client,
    )


def _get_sdk(
    token_endpoint: str,
    server_url: str | None = None,
    verify_ssl: bool = True,
    modi_audience: str | None = None,
    api_type: APIType = APIType.COORDINATE,
) -> tuple[AnncsuCoordinate, PDNDAuthManager]:
    """Create an authenticated SDK instance with ModI hook support.

    Uses the specified APIType for authentication (default: COORDINATE).
    The ModI hook is automatically registered and will add required headers
    (Digest, Agid-JWT-Signature, Agid-JWT-TrackingEvidence) to all POST requests.

    Args:
        token_endpoint: PDND token endpoint URL.
        server_url: API server URL.
        verify_ssl: Whether to verify SSL certificates.
        modi_audience: Audience URL for ModI headers (typically the API base URL).
        api_type: The APIType for authentication (default: COORDINATE).

    Returns:
        Tuple of (SDK instance, PDNDAuthManager) for token refresh support.
    """
    try:
        settings = ClientAssertionSettings()
    except Exception as e:
        error_console.print(f"[red]Error:[/red] Configuration not found: {e}")
        raise typer.Exit(1) from None

    try:
        with warnings.catch_warnings(record=True) as caught_warnings:
            warnings.simplefilter("always")
            manager = PDNDAuthManager(
                api_type=api_type,
                settings=settings,
                token_endpoint=token_endpoint,
                session_persistence=True,
                config_dir=get_config_dir(),
            )
        for w in caught_warnings:
            error_console.print(f"[yellow]Warning:[/yellow] {w.message}")
        access_token = manager.get_access_token()
    except AudienceMismatchError as e:
        error_console.print(f"[red]Configuration Error:[/red]\n{e}")
        raise typer.Exit(1) from None
    except Exception as e:
        error_console.print(f"[red]Error:[/red] Authentication failed: {e}")
        raise typer.Exit(1) from None

    # Auto-correct server URL from voucher audience if different
    voucher_aud = extract_voucher_audience(access_token)
    if voucher_aud and server_url and voucher_aud.rstrip("/") != server_url.rstrip("/"):
        error_console.print(
            f"[yellow]URL auto-corrected:[/yellow] "
            f"Hardcoded URL differs from PDND voucher audience.\n"
            f"  Configured: {server_url}\n"
            f"  Voucher aud: {voucher_aud}\n"
            f"  Using voucher audience as server URL."
        )
        server_url = voucher_aud
        if modi_audience:
            modi_audience = voucher_aud

    # Create security callable — the SDK calls this before each request,
    # so it always gets a fresh token from the auth manager (cached if valid,
    # refreshed automatically when expired).
    def security_provider() -> Security:
        return Security(bearer_auth=manager.get_access_token())

    # Create HTTP client with optional SSL verification
    client = httpx.Client(verify=verify_ssl)

    # Create hooks with ModI pre-request hook
    hooks = SDKHooks()

    # Configure ModI if audience is provided
    if modi_audience:
        try:
            # Determine which key to use for ModI JWT signing
            # Prefer dedicated ModI signing key (modi_kid + modi_private_key) when available
            if settings.has_e_service_key:
                # Use dedicated ModI signing key (separate from voucher key)
                modi_kid = settings.modi_kid
                modi_private_key: bytes | None = None
                if settings.modi_private_key:
                    modi_private_key = settings.modi_private_key.encode("utf-8")
                elif settings.modi_key_path:
                    with open(settings.modi_key_path, "rb") as f:
                        modi_private_key = f.read()
            else:
                # Fallback to voucher key (backward compatibility)
                if not getattr(settings, "modi_kid", None):
                    error_console.print(
                        "[yellow]Warning:[/yellow] PDND_MODI_KID not configured. "
                        "Using voucher key for ModI signing. "
                        "Set PDND_MODI_KID and PDND_MODI_PRIVATE_KEY for a "
                        "dedicated ModI signing key (required by GovWay in production)."
                    )
                modi_kid = settings.kid
                modi_private_key = None
                if settings.private_key:
                    modi_private_key = settings.private_key.encode("utf-8")
                elif settings.key_path:
                    with open(settings.key_path, "rb") as f:
                        modi_private_key = f.read()

            if modi_private_key:
                # Create ModI config
                modi_config = ModIConfig(
                    private_key=modi_private_key,
                    kid=modi_kid,
                    issuer=settings.issuer,
                    audience=modi_audience,
                )

                # Create audit context if configured
                audit_context: AuditContext | None = None
                if settings.has_modi_audit_context:
                    audit_context = settings.get_modi_audit_context()

                # Register ModI hook
                register_modi_hook(
                    hooks,
                    config=modi_config,
                    audit_context=audit_context,
                )
        except Exception as e:
            error_console.print(
                f"[yellow]Warning:[/yellow] ModI hook setup failed: {e}"
            )
            error_console.print("Continuing without ModI headers (API calls may fail).")

    # Create SDK with hooks via dependency injection.
    # security_provider is a callable — Speakeasy invokes it before each
    # request (basesdk.py:178), so token refresh is automatic.
    sdk = AnncsuCoordinate(
        security=security_provider,
        server_url=server_url,
        client=client,
        hooks=hooks,  # Dependency injection
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
    raw_output: Annotated[
        bool,
        typer.Option("--raw", help="Print raw API response to stderr."),
    ] = False,
) -> None:
    """Update coordinates for an access point (civico).

    Example:
        anncsu coordinate update --codcom H501 --progr-civico 12345 --x 12.4963655 --y 41.9027835 --metodo 4
    """
    # Determine server URL
    if server_url is None:
        server_url = SERVERS["validation"] if validation_env else SERVERS["production"]

    # Create SDK with ModI hook (modi_audience is the API base URL)
    # The hook automatically adds Digest, Agid-JWT-Signature, and
    # Agid-JWT-TrackingEvidence headers to POST requests
    sdk, _ = _get_sdk(
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

    # ModI headers are automatically added by the pre-request hook
    try:
        response = sdk.json_post.gestionecoordinate(
            richiesta=richiesta,
        )
    except Exception as e:
        error_console.print(f"[red]Error:[/red] API call failed: {e}")
        raise typer.Exit(1) from None

    if raw_output:
        _print_raw(response)

    # Validate response using the validated model
    validated_response = ValidatedRispostaOperazione.model_validate(
        response.model_dump()
    )

    # Build result (esito="0" means success per ANNCSU API convention)
    result = CoordinateUpdateResult(
        success=validated_response.is_success,
        id_richiesta=validated_response.id_richiesta,
        esito=validated_response.esito,
        messaggio=validated_response.messaggio,
        dati_count=len(validated_response.dati) if validated_response.dati else 0,
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
        str | None,
        typer.Option(
            "--codcom",
            "-c",
            help="Codice comune (Belfiore code, e.g. H501 for Roma). Required with --denom.",
        ),
    ] = None,
    denom: Annotated[
        str | None,
        typer.Option(
            "--denom",
            "-d",
            help="Denominazione esatta dell'odonimo - base64 encoded. Required with --codcom.",
        ),
    ] = None,
    accparz: Annotated[
        str | None,
        typer.Option(
            "--accparz",
            "-a",
            help="Valore anche parziale del civico. Used with --codcom/--denom.",
        ),
    ] = None,
    prognazacc_arg: Annotated[
        str | None,
        typer.Option(
            "--prognazacc",
            "-p",
            help="Progressivo nazionale accesso. Alternative to --codcom/--denom.",
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
    raw_output: Annotated[
        bool,
        typer.Option("--raw", help="Print raw API responses to stderr."),
    ] = False,
) -> None:
    """Dry-run coordinate update: search, test update, then restore original values.

    This command performs a complete test cycle:
    1. Search for an access point (using --prognazacc OR --codcom/--denom)
    2. Save the original coordinates
    3. Perform a test update (with same or slightly modified coordinates)
    4. Immediately restore the original coordinates

    If restore fails, a warning is shown with the original values for manual restoration.

    Two Modes of Operation:
    -----------------------
    1. Direct mode (--prognazacc): Use the progressivo nazionale accesso directly.
       Skips the odonimo search step - faster if you already know the prognazacc.

    2. Search mode (--codcom/--denom): Search for odonimo then access point.
       Use this when you only know the municipality code and street name.

    Handling Access Points Without Coordinates:
    -------------------------------------------
    When an access point has no existing coordinates (X, Y, and metodo are empty),
    the dry-run uses temporary test coordinates for the update test:

    - Test coordinates: Roma Colosseo area (X=12.4922309, Y=41.8902102)
    - Test metodo: 4 (Altro - other method)

    After the test update, the command restores the original empty state by
    sending a restore request with the original (empty) values. This ensures
    the access point returns to its original state without coordinates.

    Note: The restore operation for empty coordinates may fail if the API
    requires valid coordinates. In this case, manual intervention may be needed.

    Example:
        # Direct mode - use prognazacc directly
        anncsu coordinate dry-run --prognazacc 5256880

        # Search mode - search by municipality and street
        anncsu coordinate dry-run --codcom H501 --denom VklBIFJPTUE=
        anncsu coordinate dry-run --codcom H501 --denom VklBIFJPTUE= --accparz 10
    """
    # Validate input parameters
    # Either --prognazacc OR (--codcom AND --denom) must be provided
    if prognazacc_arg:
        # Direct mode: use prognazacc directly
        use_direct_mode = True
        if codcom or denom:
            # Warn that --codcom/--denom are ignored when --prognazacc is provided
            if not json_output:
                console.print(
                    "[yellow]Note:[/yellow] --prognazacc provided, ignoring --codcom/--denom\n"
                )
    elif codcom and denom:
        # Search mode: use codcom + denom
        use_direct_mode = False
    elif codcom and not denom:
        # codcom without denom
        error_console.print(
            "[red]Error:[/red] --codcom requires --denom. "
            "Provide both or use --prognazacc instead."
        )
        raise typer.Exit(1) from None
    elif denom and not codcom:
        # denom without codcom
        error_console.print(
            "[red]Error:[/red] --denom requires --codcom. "
            "Provide both or use --prognazacc instead."
        )
        raise typer.Exit(1) from None
    else:
        # No parameters provided
        error_console.print(
            "[red]Error:[/red] Missing required parameters. "
            "Provide --prognazacc OR (--codcom AND --denom)."
        )
        raise typer.Exit(1) from None

    # Determine server URLs
    coord_server = server_url or (
        SERVERS["validation"] if validation_env else SERVERS["production"]
    )
    consult_server = (
        CONSULT_SERVERS["validation"]
        if validation_env
        else CONSULT_SERVERS["production"]
    )

    consult_sdk = _get_consult_sdk(
        token_endpoint=token_endpoint,
        server_url=consult_server,
        verify_ssl=not no_verify_ssl,
    )

    # Step 1: Get access point data
    # Two modes: direct (--prognazacc) or search (--codcom/--denom)

    if use_direct_mode:
        # Direct mode: lookup access point by prognazacc
        if not json_output:
            console.print(
                f"[bold]Step 1:[/bold] Looking up access point prognazacc={prognazacc_arg}...\n"
            )

        try:
            prognazacc_response = consult_sdk.queryparam.prognazacc_get_query_param(
                prognazacc=prognazacc_arg
            )
        except Exception as e:
            error_console.print(f"[red]Error:[/red] Access point lookup failed: {e}")
            raise typer.Exit(1) from None

        if raw_output:
            _print_raw(prognazacc_response, "Raw lookup response")

        # data is a List[PrognazaccGetQueryParamData]
        data_list = prognazacc_response.data
        if not data_list:
            error_console.print(
                f"[red]Error:[/red] No access point found for prognazacc={prognazacc_arg}"
            )
            raise typer.Exit(1) from None

        accesso_data = data_list[0]
        prognazacc = accesso_data.prognazacc or prognazacc_arg

        # For direct mode, we don't have codcom from the search
        # Use the one from the response if available, otherwise None
        effective_codcom = codcom  # May be None in direct mode

        if not json_output:
            console.print(f"  Found: {accesso_data.dug} {accesso_data.denomuff}")
            if accesso_data.prognaz:
                console.print(
                    f"  Progressivo nazionale odonimo: {accesso_data.prognaz}\n"
                )

    else:
        # Search mode: search by codcom + denom
        if not json_output:
            console.print(
                "[bold]Step 1:[/bold] Searching for odonimo and access point...\n"
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

        if raw_output:
            _print_raw(odonimo_response, "Raw odonimo response")

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
            console.print(
                f"  Found odonimo: {odonimo_data.dug} {odonimo_data.denomuff}"
            )
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

        if raw_output:
            _print_raw(search_response, "Raw accessi response")

        if not search_response.data or len(search_response.data) == 0:
            error_console.print(
                f"[red]Error:[/red] No access point found for prognaz={prognaz}"
            )
            raise typer.Exit(1) from None

        # Use the first result
        accesso_data = search_response.data[0]
        prognazacc = accesso_data.prognazacc
        effective_codcom = codcom

        if not prognazacc:
            error_console.print(
                "[red]Error:[/red] Access point found but no prognazacc available"
            )
            raise typer.Exit(1) from None

    # Save original coordinates
    original = OriginalCoordinates(
        prognazacc=prognazacc,
        codcom=effective_codcom,
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

    # Create SDK with ModI hook - headers added automatically to POST requests
    coord_sdk, _ = _get_sdk(
        token_endpoint=token_endpoint,
        server_url=coord_server,
        verify_ssl=not no_verify_ssl,
        modi_audience=coord_server,
    )

    # Check if access has existing coordinates
    has_coordinates = original.coord_x and original.coord_y and original.metodo

    if has_coordinates:
        # Use existing coordinates for test
        test_coordinate = Coordinate(
            x=original.coord_x,
            y=original.coord_y,
            z=original.quota,
            metodo=original.metodo,
        )
    else:
        # Access has no coordinates - use test values (Roma Colosseo area)
        # These will be restored to empty after the test
        if not json_output:
            console.print(
                "[yellow]Note:[/yellow] Access has no coordinates. "
                "Using test coordinates (will be cleared after test).\n"
            )
        test_coordinate = Coordinate(
            x="12.4922309",  # Roma - Colosseo longitude
            y="41.8902102",  # Roma - Colosseo latitude
            z=None,
            metodo="4",  # Metodo 4 = Altro
        )

    test_richiesta = Richiesta(
        accesso=Accesso(
            codcom=effective_codcom,
            progr_civico=prognazacc,
            coordinate=test_coordinate,
        )
    )

    # ModI headers are automatically added by the pre-request hook
    test_update_result: CoordinateUpdateResult
    try:
        test_response = coord_sdk.json_post.gestionecoordinate(
            richiesta=test_richiesta,
        )
        if raw_output:
            _print_raw(test_response, "Raw test update response")

        # Validate response (esito="0" means success per ANNCSU API convention)
        validated_test = ValidatedRispostaOperazione.model_validate(
            test_response.model_dump()
        )
        test_update_result = CoordinateUpdateResult(
            success=validated_test.is_success,
            id_richiesta=validated_test.id_richiesta,
            esito=validated_test.esito,
            messaggio=validated_test.messaggio,
            dati_count=len(validated_test.dati) if validated_test.dati else 0,
        )
        if not json_output:
            status = (
                "[green]OK[/green]"
                if validated_test.is_success
                else "[red]FAILED[/red]"
            )
            console.print(
                f"Test update completed: {status} (esito={test_update_result.esito})\n"
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
            codcom=effective_codcom,
            progr_civico=prognazacc,
            coordinate=restore_coordinate,
        )
    )

    # ModI headers are automatically added by the pre-request hook
    restore_result: CoordinateUpdateResult | None = None
    restore_failed = False
    error_message: str | None = None

    try:
        restore_response = coord_sdk.json_post.gestionecoordinate(
            richiesta=restore_richiesta,
        )
        if raw_output:
            _print_raw(restore_response, "Raw restore response")

        # Validate response (esito="0" means success per ANNCSU API convention)
        validated_restore = ValidatedRispostaOperazione.model_validate(
            restore_response.model_dump()
        )
        restore_result = CoordinateUpdateResult(
            success=validated_restore.is_success,
            id_richiesta=validated_restore.id_richiesta,
            esito=validated_restore.esito,
            messaggio=validated_restore.messaggio,
            dati_count=len(validated_restore.dati) if validated_restore.dati else 0,
        )
        if not json_output:
            status = (
                "[green]OK[/green]"
                if validated_restore.is_success
                else "[red]FAILED[/red]"
            )
            console.print(
                f"Restore completed: {status} (esito={restore_result.esito})\n"
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


@coordinate_app.command()
def duckdb_batch_update(
    db_path: Annotated[
        str,
        typer.Option(
            "--db",
            "-d",
            help="Path to DuckDB file",
        ),
    ],
    source_table: Annotated[
        str,
        typer.Option(
            "--source-table",
            "-t",
            help="Source table name containing coordinates",
        ),
    ] = "deoverlapped_geocoded_anncsu",
    codcom: Annotated[
        str,
        typer.Option(
            "--codcom",
            "-c",
            help="Codice comune (Belfiore code)",
        ),
    ] = None,
    max_records: Annotated[
        int,
        typer.Option(
            "--max-records",
            "-m",
            help="Maximum number of records to process (0 = all)",
        ),
    ] = 0,
    token_endpoint: Annotated[
        str,
        typer.Option(
            "--token-endpoint",
            "-e",
            help="PDND token endpoint URL",
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
            help="Disable SSL certificate verification.",
        ),
    ] = False,
    json_output: Annotated[
        bool,
        typer.Option("--json", help="Output as JSON"),
    ] = False,
    resume_run_id: Annotated[
        str | None,
        typer.Option(
            "--resume",
            help="Resume a previous run by its Run ID. Skips already succeeded records.",
        ),
    ] = None,
) -> None:
    """Batch update coordinates from DuckDB table.

    Reads from source table and updates each record via ANNCSU API,
    storing results in batch_update_results table.

    Use --max-records 4000 to respect the daily limit per comune,
    then --resume RUN_ID the next day to continue.

    Example:
        anncsu coordinate duckdb-batch-update --db data.duckdb --codcom A269 --production --max-records 4000
        anncsu coordinate duckdb-batch-update --db data.duckdb --codcom A269 --production --max-records 4000 --resume 20260319_140554
    """
    import time
    from datetime import datetime
    from pathlib import Path

    # Validate DB path
    db_file = Path(db_path)
    if not db_file.exists():
        error_console.print(f"[red]Error:[/red] Database file not found: {db_path}")
        raise typer.Exit(1)

    # Load settings from environment — fail fast on missing PDND env vars
    # before touching DuckDB or making any network call via _get_sdk().
    try:
        ClientAssertionSettings()
    except Exception as e:
        error_console.print(f"[red]Error loading settings:[/red] {e}")
        raise typer.Exit(1) from e

    # Determine server URL
    if server_url is None:
        server_url = SERVERS["validation"] if validation_env else SERVERS["production"]

    # Create results table
    _create_results_table(db_path)

    # Generate or reuse run ID
    if resume_run_id:
        run_id = resume_run_id
    else:
        run_id = datetime.now().strftime("%Y%m%d_%H%M%S")
    timestamp = datetime.now().isoformat()

    # Connect to DuckDB
    conn = duckdb.connect(db_path)

    # Validate coordinate lengths before processing
    try:
        validation_query = f"""
            SELECT COUNT(*) as invalid_count,
                MAX(LENGTH(CAST(COORD_X_COMUNE AS VARCHAR))) as max_len_x,
                MAX(LENGTH(CAST(COORD_Y_COMUNE AS VARCHAR))) as max_len_y,
                MAX(LENGTH(CAST(QUOTA AS VARCHAR))) as max_len_z
            FROM {source_table}
            WHERE CODICE_COMUNE = '{codcom}'
            AND PROGRESSIVO_ACCESSO IS NOT NULL
            AND COORD_X_COMUNE IS NOT NULL
            AND COORD_Y_COMUNE IS NOT NULL
            AND (
                LENGTH(CAST(COORD_X_COMUNE AS VARCHAR)) > 12
                OR LENGTH(CAST(COORD_Y_COMUNE AS VARCHAR)) > 12
                OR (QUOTA IS NOT NULL AND LENGTH(CAST(QUOTA AS VARCHAR)) > 7)
            )
        """
        validation = conn.execute(validation_query).fetchone()
        invalid_count, max_len_x, max_len_y, max_len_z = validation

        if invalid_count > 0:
            error_console.print(
                f"[red]Source table '{source_table}' is not valid:[/red] "
                f"{invalid_count} records have coordinates exceeding maxLength limits"
            )
            error_console.print(
                f"  max len(x)={max_len_x} (limit 12), "
                f"max len(y)={max_len_y} (limit 12), "
                f"max len(z)={max_len_z} (limit 7)"
            )
            error_console.print(
                "[yellow]Use a '_prepared' table with VARCHAR coordinates "
                "truncated to the correct lengths.[/yellow]"
            )
            conn.close()
            raise typer.Exit(1)
    except typer.Exit:
        raise
    except Exception as e:
        error_console.print(f"[red]Error validating source table:[/red] {e}")
        conn.close()
        raise typer.Exit(1) from e

    # Read source data — cast to VARCHAR in SQL to avoid Python float expansion
    try:
        # When resuming, exclude records already succeeded (esito='0') for this run_id
        if resume_run_id:
            already_done = conn.execute(
                """
                SELECT COUNT(*) FROM batch_update_results
                WHERE run_id = ? AND esito = '0'
                """,
                [resume_run_id],
            ).fetchone()[0]
            console.print(
                f"[cyan]Resuming run {resume_run_id}: "
                f"{already_done} records already succeeded, skipping them[/cyan]"
            )
            exclude_clause = f"""
                AND PROGRESSIVO_ACCESSO NOT IN (
                    SELECT progressivo_accesso FROM batch_update_results
                    WHERE run_id = '{resume_run_id}' AND esito = '0'
                )
            """
        else:
            exclude_clause = ""

        query = f"""
            SELECT
                PROGRESSIVO_ACCESSO,
                CIVICO,
                CAST(COORD_X_COMUNE AS VARCHAR) as x,
                CAST(COORD_Y_COMUNE AS VARCHAR) as y,
                CAST(QUOTA AS VARCHAR) as z,
                CAST(METODO AS VARCHAR) as metodo
            FROM {source_table}
            WHERE CODICE_COMUNE = '{codcom}'
            AND PROGRESSIVO_ACCESSO IS NOT NULL
            AND COORD_X_COMUNE IS NOT NULL
            AND COORD_Y_COMUNE IS NOT NULL
            {exclude_clause}
        """
        if max_records > 0:
            query += f" LIMIT {max_records}"

        results = conn.execute(query).fetchall()
        columns = [desc[0].lower() for desc in conn.description]

        if not results:
            if resume_run_id:
                console.print(
                    f"[green]All records already completed for run {resume_run_id}[/green]"
                )
            else:
                error_console.print(
                    f"[red]No records found in {source_table} for comune {codcom}"
                )
            conn.close()
            raise typer.Exit(0 if resume_run_id else 1)

        console.print(f"[cyan]Found {len(results)} records to process[/cyan]")

    except typer.Exit:
        raise
    except Exception as e:
        error_console.print(f"[red]Error reading source table:[/red] {e}")
        conn.close()
        raise typer.Exit(1) from e

    # Get SDK
    try:
        sdk, _ = _get_sdk(
            token_endpoint=token_endpoint,
            server_url=server_url,
            verify_ssl=not no_verify_ssl,
            modi_audience=server_url,
        )
    except Exception as e:
        error_console.print(f"[red]Error initializing SDK:[/red] {e}")
        conn.close()
        raise typer.Exit(1) from e

    # Process each record
    stats = {
        "total": len(results),
        "success": 0,
        "failed": 0,
        "errors": [],
    }

    from rich.progress import (
        Progress,
    )

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TaskProgressColumn(),
        console=console,
    ) as progress:
        task = progress.add_task(
            "Processing: 0/{} (ok=0 err=0)".format(len(results)),
            total=len(results),
        )

        processed = 0
        for row in results:
            row_dict = dict(zip(columns, row, strict=True))
            progressivo_accesso = row_dict.get("progressivo_accesso")
            civico = row_dict.get("civico")
            x = row_dict.get("x")
            y = row_dict.get("y")
            z = row_dict.get("z")
            metodo = row_dict.get("metodo")

            http_status = None
            esito = None
            messaggio = None
            id_richiesta = None
            error_detail = None
            elapsed_ms = 0.0

            try:
                # Build request
                coordinate_obj = Coordinate(
                    x=str(x) if x else None,
                    y=str(y) if y else None,
                    z=str(z) if z else None,
                    metodo=str(metodo) if metodo else None,
                )

                richiesta = Richiesta(
                    accesso=Accesso(
                        codcom=codcom,
                        progr_civico=str(progressivo_accesso),
                        coordinate=coordinate_obj,
                    )
                )

                # Make API call
                start_time = time.time()
                response = sdk.json_post.gestionecoordinate(richiesta=richiesta)
                elapsed_ms = (time.time() - start_time) * 1000

                # Extract response details
                validated_response = ValidatedRispostaOperazione.model_validate(
                    response.model_dump()
                )
                http_status = 200
                esito = validated_response.esito
                messaggio = validated_response.messaggio
                id_richiesta = validated_response.id_richiesta

                if validated_response.is_success:
                    stats["success"] += 1
                else:
                    stats["failed"] += 1
                    error_detail = f"API returned esito={esito}: {messaggio}"
                    stats["errors"].append(
                        {
                            "progr_accesso": progressivo_accesso,
                            "error": error_detail,
                        }
                    )

            except Exception as e:
                stats["failed"] += 1
                error_detail = str(e)
                stats["errors"].append(
                    {
                        "progr_accesso": progressivo_accesso,
                        "error": error_detail,
                    }
                )

            # Insert result
            _insert_result(
                db_path,
                run_id,
                timestamp,
                progressivo_accesso,
                civico,
                http_status,
                esito,
                messaggio,
                id_richiesta,
                error_detail,
                elapsed_ms,
            )

            processed += 1
            progress.update(
                task,
                completed=processed,
                description=f"Processing: {processed}/{stats['total']} (ok={stats['success']} err={stats['failed']})",
            )

    # Print summary
    if json_output:
        import json

        output = {
            "run_id": run_id,
            "timestamp": timestamp,
            "total": stats["total"],
            "success": stats["success"],
            "failed": stats["failed"],
            "errors": stats["errors"],
        }
        print(json.dumps(output, indent=2))
    else:
        console.print("\n[bold]Batch Update Summary[/bold]")
        table = Table(show_header=True, header_style="bold")
        table.add_column("Metric", style="cyan")
        table.add_column("Value")
        table.add_row("Run ID", run_id)
        table.add_row("Total Records", str(stats["total"]))
        success_pct = (
            (stats["success"] / stats["total"] * 100) if stats["total"] > 0 else 0
        )
        table.add_row(
            "Success", f"[green]{stats['success']}[/green] ({success_pct:.1f}%)"
        )
        table.add_row("Failed", f"[red]{stats['failed']}[/red]")

        console.print(table)

        if stats["errors"]:
            console.print(f"\n[red]Errors ({len(stats['errors'])}):[/red]")
            for err in stats["errors"][:10]:  # Show first 10
                console.print(f"  - Progr: {err['progr_accesso']} - {err['error']}")
            if len(stats["errors"]) > 10:
                console.print(f"  ... and {len(stats['errors']) - 10} more")

    # Close connection
    conn.close()

    console.print("\n[cyan]Results saved to batch_update_results table[/cyan]")
    console.print(f"[cyan]Run ID: {run_id}[/cyan]")


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
    raw_output: Annotated[
        bool,
        typer.Option("--raw", help="Print raw API response to stderr."),
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

    # Create SDK (no ModI needed for status - GET request, hook will skip it)
    sdk, _ = _get_sdk(
        token_endpoint=token_endpoint,
        server_url=server_url,
        verify_ssl=not no_verify_ssl,
    )

    try:
        response = sdk.status.show_status()
        if raw_output:
            _print_raw(response)
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
