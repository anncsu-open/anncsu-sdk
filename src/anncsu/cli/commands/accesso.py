# SPDX-FileCopyrightText: 2025-present Geobeyond <info@geobeyond.it>
# SPDX-License-Identifier: MIT
"""``anncsu accesso`` command group — CRUD on ANNCSU accessi.

Three sub-commands map 1:1 to the ``operazione_civico`` field of the
POST ``/accessi`` endpoint:

* ``insert``  → ``operazione_civico='I'`` (insert new accesso)
* ``update``  → ``operazione_civico='R'`` (replace/update existing)
* ``delete``  → ``operazione_civico='S'`` (soppressione)

Plus ``status`` for the GET ``/status`` health check.

Validation is operation-aware via ``ValidatedAccesso``: for ``delete`` the
Typer signature does not expose ``--numero``/``--metrico``/etc., so Typer
rejects them at parse time before any API call.
"""

from __future__ import annotations

import warnings
from typing import Annotated

import httpx
import typer
from rich.console import Console
from rich.table import Table

from anncsu.accessi import AnncsuAccessi
from anncsu.accessi.models import Security
from anncsu.accessi.models.richiestaoperazione import (
    Accesso,
    Coordinate,
    Richiesta,
)
from anncsu.accessi.models.validated import ValidatedAccesso
from anncsu.cli.models import AccessoOperationResult, AccessoStatusResult
from anncsu.common import PDNDAuthManager
from anncsu.common.auth import extract_voucher_audience
from anncsu.common.config import APIType, ClientAssertionSettings
from anncsu.common.errors import AudienceMismatchError
from anncsu.common.hooks import SDKHooks, register_modi_hook
from anncsu.common.modi import AuditContext, ModIConfig
from anncsu.common.session import get_config_dir

accesso_app = typer.Typer(
    name="accesso",
    help="ANNCSU accesso CRUD (insert/update/delete) and status.",
    no_args_is_help=True,
)

console = Console()
error_console = Console(stderr=True)

# Default token endpoint for UAT (matches the pattern used in coordinate.py).
DEFAULT_TOKEN_ENDPOINT = "https://auth.uat.interop.pagopa.it/token.oauth2"

# Default server URLs for the Accessi e-service.
# The OAS spec lists path ``AgenziaEntrate/anncsuaccessi/v1`` but real
# GovWay paths often differ — voucher audience auto-discovery corrects the
# URL at runtime.
SERVERS = {
    "production": (
        "https://modipa.agenziaentrate.gov.it/govway/rest/in/"
        "AgenziaEntrate/anncsuaccessi/v1"
    ),
    "validation": (
        "https://modipa-val.agenziaentrate.it/govway/rest/in/"
        "AgenziaEntrate/anncsuaccessi/v1"
    ),
}


def _get_sdk(
    token_endpoint: str,
    server_url: str | None = None,
    verify_ssl: bool = True,
    modi_audience: str | None = None,
) -> tuple[AnncsuAccessi, PDNDAuthManager]:
    """Create an authenticated AnncsuAccessi SDK with ModI hook support.

    1. Loads settings + token via PDNDAuthManager(api_type=ACCESSI)
    2. Auto-corrects ``server_url`` from voucher audience
    3. Wires a security provider callable for automatic token refresh
    4. Registers the ModI pre-request hook for AUDIT_REST_02 +
       INTEGRITY_REST_02 headers required by the Accessi e-service
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
                api_type=APIType.ACCESSI,
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

    # Auto-correct server URL from voucher audience if different.
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

    # security_provider: callable that returns a fresh Security on each
    # request — the SDK invokes it before every call, enabling automatic
    # token refresh when the cached token expires.
    def security_provider() -> Security:
        return Security(bearer_auth=manager.get_access_token())

    client = httpx.Client(verify=verify_ssl)

    # ModI pre-request hook (AUDIT_REST_02 + INTEGRITY_REST_02 per OAS spec).
    hooks = SDKHooks()

    if modi_audience:
        try:
            if settings.has_e_service_key:
                modi_kid = settings.modi_kid
                modi_private_key: bytes | None = None
                if settings.modi_private_key:
                    modi_private_key = settings.modi_private_key.encode("utf-8")
                elif settings.modi_key_path:
                    with open(settings.modi_key_path, "rb") as f:
                        modi_private_key = f.read()
            else:
                if not getattr(settings, "modi_kid", None):
                    error_console.print(
                        "[yellow]Warning:[/yellow] PDND_MODI_KID not configured. "
                        "Using voucher key for ModI signing. Set PDND_MODI_KID "
                        "and PDND_MODI_PRIVATE_KEY for a dedicated ModI signing "
                        "key (required by GovWay in production)."
                    )
                modi_kid = settings.kid
                modi_private_key = None
                if settings.private_key:
                    modi_private_key = settings.private_key.encode("utf-8")
                elif settings.key_path:
                    with open(settings.key_path, "rb") as f:
                        modi_private_key = f.read()

            if modi_private_key:
                modi_config = ModIConfig(
                    private_key=modi_private_key,
                    kid=modi_kid,
                    issuer=settings.issuer,
                    audience=modi_audience,
                )
                audit_context: AuditContext | None = None
                if settings.has_modi_audit_context:
                    audit_context = settings.get_modi_audit_context()
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

    sdk = AnncsuAccessi(
        security=security_provider,
        server_url=server_url,
        client=client,
        hooks=hooks,
    )
    return sdk, manager


def _resolve_server_url(server_url: str | None, validation_env: bool) -> str:
    """Pick validation/production default if ``server_url`` not supplied."""
    if server_url is not None:
        return server_url
    return SERVERS["validation"] if validation_env else SERVERS["production"]


def _print_raw(response: object, label: str = "Raw API response") -> None:
    """Print raw API response to stderr as formatted JSON."""
    import json

    error_console.print(
        f"[dim]{label}:[/dim]\n"
        f"{json.dumps(response.model_dump(), indent=2, default=str)}"
    )


def _execute_operation(
    *,
    operazione_civico: str,
    codcom: str,
    progr_nazionale: str,
    accesso: Accesso,
    token_endpoint: str,
    server_url: str,
    verify_ssl: bool,
    raw_output: bool,
    json_output: bool,
) -> None:
    """Common send-and-render flow for I / R / S operations.

    Validates the ``Accesso`` via ``ValidatedAccesso`` BEFORE the API call,
    then issues the POST and renders the response either as JSON
    (``--json``) or as a rich table.
    """
    # Pre-validate with business rules (raises ValidationError / typer.Exit on
    # invalid input).
    try:
        ValidatedAccesso.model_validate(accesso.model_dump(exclude_unset=True))
    except Exception as e:
        error_console.print(f"[red]Validation error:[/red] {e}")
        raise typer.Exit(1) from None

    sdk, _ = _get_sdk(
        token_endpoint=token_endpoint,
        server_url=server_url,
        verify_ssl=verify_ssl,
        modi_audience=server_url,
    )

    richiesta = Richiesta(
        codcom=codcom,
        progr_nazionale=progr_nazionale,
        accesso=accesso,
    )

    try:
        response = sdk.anncsu.gestione_anncsu_pdnd(richiesta=richiesta)
    except Exception as e:
        error_console.print(f"[red]Error:[/red] API call failed: {e}")
        raise typer.Exit(1) from None

    if raw_output:
        _print_raw(response)

    esito = getattr(response, "esito", None)
    success = esito == "0"

    result = AccessoOperationResult(
        success=success,
        operazione_civico=operazione_civico,
        id_richiesta=getattr(response, "id_richiesta", None),
        esito=esito,
        messaggio=getattr(response, "messaggio", None),
        dati_count=len(getattr(response, "dati", []) or []),
    )

    if json_output:
        print(result.model_dump_json(indent=2))
        if not success:
            raise typer.Exit(1)
        return

    if success:
        console.print(
            f"[green]Operation '{operazione_civico}' successful![/green] "
            f"ID: {result.id_richiesta}\n"
        )
    else:
        console.print(
            f"[red]Operation '{operazione_civico}' failed.[/red] "
            f"ID: {result.id_richiesta}\n"
        )

    table = Table(show_header=True, header_style="bold")
    table.add_column("Field", style="cyan")
    table.add_column("Value")
    table.add_row("Operation", operazione_civico)
    table.add_row("Request ID", result.id_richiesta or "—")
    table.add_row("Esito", result.esito or "—")
    table.add_row("Messaggio", result.messaggio or "—")
    table.add_row("Dati count", str(result.dati_count))
    console.print(table)

    if not success:
        raise typer.Exit(1)


# ---------------------------------------------------------------------------
# Subcommand: insert (operazione_civico='I')
# ---------------------------------------------------------------------------


@accesso_app.command("insert")
def insert(
    codcom: Annotated[
        str,
        typer.Option(
            "--codcom",
            "-c",
            help="Codice comune (Belfiore code, e.g. A062).",
        ),
    ],
    prognaz: Annotated[
        str,
        typer.Option(
            "--prognaz",
            "-p",
            help="Progressivo nazionale dell'odonimo.",
        ),
    ],
    numero: Annotated[
        str | None,
        typer.Option(
            "--numero",
            "-n",
            help="Numero civico (mutually exclusive with --metrico).",
        ),
    ] = None,
    metrico: Annotated[
        str | None,
        typer.Option(
            "--metrico",
            "-M",
            help="Metrico (mutually exclusive with --numero).",
        ),
    ] = None,
    esponente: Annotated[
        str | None,
        typer.Option("--esponente", help="Esponente (e.g. 'A', 'BIS')."),
    ] = None,
    specificita: Annotated[
        str | None,
        typer.Option("--specificita", help="Specificita (e.g. 'ROSSO')."),
    ] = None,
    sezione_censimento: Annotated[
        str | None,
        typer.Option("--sezione-censimento", help="Sezione di censimento."),
    ] = None,
    isolato: Annotated[
        str | None,
        typer.Option("--isolato", help="Codice isolato (facoltativo)."),
    ] = None,
    codice_civico_comunale: Annotated[
        str | None,
        typer.Option(
            "--codice-civico-comunale", help="Codifica comunale dell'accesso."
        ),
    ] = None,
    coord_x: Annotated[
        str | None,
        typer.Option("--coord-x", help="Coordinata X (longitudine, 6-18)."),
    ] = None,
    coord_y: Annotated[
        str | None,
        typer.Option("--coord-y", help="Coordinata Y (latitudine, 36-47)."),
    ] = None,
    coord_z: Annotated[
        str | None,
        typer.Option("--coord-z", help="Quota."),
    ] = None,
    metodo: Annotated[
        str | None,
        typer.Option("--metodo", "-m", help="Metodo di rilevazione (1-4)."),
    ] = None,
    data_valid_amm: Annotated[
        str | None,
        typer.Option(
            "--data-valid-amm",
            help="Data inizio validita' amministrativa (dd/MM/yyyy).",
        ),
    ] = None,
    token_endpoint: Annotated[
        str,
        typer.Option("--token-endpoint", "-e", help="PDND token endpoint URL."),
    ] = DEFAULT_TOKEN_ENDPOINT,
    server_url: Annotated[
        str | None,
        typer.Option(
            "--server-url",
            "-s",
            help="API server URL (auto-discovered from voucher if omitted).",
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
        bool, typer.Option("--json", help="Output as JSON.")
    ] = False,
    raw_output: Annotated[
        bool, typer.Option("--raw", help="Print raw API response to stderr.")
    ] = False,
) -> None:
    """Insert a new accesso (``operazione_civico='I'``).

    Exactly one of ``--numero`` or ``--metrico`` is required.

    Example:
        anncsu accesso insert --codcom A062 --prognaz 2000449 --numero 12
    """
    coordinate_obj: Coordinate | None = None
    if any(v is not None for v in (coord_x, coord_y, coord_z, metodo)):
        coordinate_obj = Coordinate(x=coord_x, y=coord_y, z=coord_z, metodo=metodo)

    accesso = Accesso(
        operazione_civico="I",
        numero=numero,
        metrico=metrico,
        esponente=esponente,
        specificita=specificita,
        sezione_censimento=sezione_censimento,
        isolato=isolato,
        codice_civico_comunale=codice_civico_comunale,
        coordinate=coordinate_obj,
        data_valid_amm=data_valid_amm,
    )

    _execute_operation(
        operazione_civico="I",
        codcom=codcom,
        progr_nazionale=prognaz,
        accesso=accesso,
        token_endpoint=token_endpoint,
        server_url=_resolve_server_url(server_url, validation_env),
        verify_ssl=not no_verify_ssl,
        raw_output=raw_output,
        json_output=json_output,
    )


# ---------------------------------------------------------------------------
# Subcommand: update (operazione_civico='R')
# ---------------------------------------------------------------------------


@accesso_app.command("update")
def update(
    codcom: Annotated[str, typer.Option("--codcom", "-c", help="Codice comune.")],
    prognaz: Annotated[
        str,
        typer.Option("--prognaz", "-p", help="Progressivo nazionale dell'odonimo."),
    ],
    progr_civico: Annotated[
        str,
        typer.Option(
            "--progr-civico",
            "-P",
            help="Progressivo civico (identifier of the accesso).",
        ),
    ],
    numero: Annotated[
        str | None,
        typer.Option(
            "--numero",
            "-n",
            help="Numero civico (mutually exclusive with --metrico).",
        ),
    ] = None,
    metrico: Annotated[
        str | None,
        typer.Option(
            "--metrico",
            "-M",
            help="Metrico (mutually exclusive with --numero).",
        ),
    ] = None,
    esponente: Annotated[
        str | None, typer.Option("--esponente", help="Esponente.")
    ] = None,
    specificita: Annotated[
        str | None, typer.Option("--specificita", help="Specificita.")
    ] = None,
    sezione_censimento: Annotated[
        str | None,
        typer.Option("--sezione-censimento", help="Sezione di censimento."),
    ] = None,
    isolato: Annotated[
        str | None, typer.Option("--isolato", help="Codice isolato.")
    ] = None,
    codice_civico_comunale: Annotated[
        str | None,
        typer.Option(
            "--codice-civico-comunale", help="Codifica comunale dell'accesso."
        ),
    ] = None,
    coord_x: Annotated[
        str | None, typer.Option("--coord-x", help="Coordinata X.")
    ] = None,
    coord_y: Annotated[
        str | None, typer.Option("--coord-y", help="Coordinata Y.")
    ] = None,
    coord_z: Annotated[str | None, typer.Option("--coord-z", help="Quota.")] = None,
    metodo: Annotated[
        str | None,
        typer.Option("--metodo", "-m", help="Metodo di rilevazione (1-4)."),
    ] = None,
    data_valid_amm: Annotated[
        str | None,
        typer.Option(
            "--data-valid-amm",
            help="Data inizio validita' amministrativa (dd/MM/yyyy).",
        ),
    ] = None,
    token_endpoint: Annotated[
        str,
        typer.Option("--token-endpoint", "-e", help="PDND token endpoint URL."),
    ] = DEFAULT_TOKEN_ENDPOINT,
    server_url: Annotated[
        str | None,
        typer.Option("--server-url", "-s", help="API server URL."),
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
        typer.Option("--no-verify-ssl", help="Disable SSL verification."),
    ] = False,
    json_output: Annotated[
        bool, typer.Option("--json", help="Output as JSON.")
    ] = False,
    raw_output: Annotated[
        bool, typer.Option("--raw", help="Print raw API response to stderr.")
    ] = False,
) -> None:
    """Update/replace an existing accesso (``operazione_civico='R'``).

    Example:
        anncsu accesso update --codcom A062 --prognaz 2000449 \\
            --progr-civico 1370588 --numero 12
    """
    coordinate_obj: Coordinate | None = None
    if any(v is not None for v in (coord_x, coord_y, coord_z, metodo)):
        coordinate_obj = Coordinate(x=coord_x, y=coord_y, z=coord_z, metodo=metodo)

    accesso = Accesso(
        operazione_civico="R",
        progr_civico=progr_civico,
        numero=numero,
        metrico=metrico,
        esponente=esponente,
        specificita=specificita,
        sezione_censimento=sezione_censimento,
        isolato=isolato,
        codice_civico_comunale=codice_civico_comunale,
        coordinate=coordinate_obj,
        data_valid_amm=data_valid_amm,
    )

    _execute_operation(
        operazione_civico="R",
        codcom=codcom,
        progr_nazionale=prognaz,
        accesso=accesso,
        token_endpoint=token_endpoint,
        server_url=_resolve_server_url(server_url, validation_env),
        verify_ssl=not no_verify_ssl,
        raw_output=raw_output,
        json_output=json_output,
    )


# ---------------------------------------------------------------------------
# Subcommand: delete (operazione_civico='S')
# ---------------------------------------------------------------------------


@accesso_app.command("delete")
def delete(
    codcom: Annotated[str, typer.Option("--codcom", "-c", help="Codice comune.")],
    prognaz: Annotated[
        str,
        typer.Option("--prognaz", "-p", help="Progressivo nazionale dell'odonimo."),
    ],
    progr_civico: Annotated[
        str,
        typer.Option(
            "--progr-civico",
            "-P",
            help="Progressivo civico of the accesso to delete.",
        ),
    ],
    data_valid_amm: Annotated[
        str | None,
        typer.Option(
            "--data-valid-amm",
            help=(
                "Data FINE validita' amministrativa (dd/MM/yyyy). "
                "For delete, this represents the end date (not start)."
            ),
        ),
    ] = None,
    token_endpoint: Annotated[
        str,
        typer.Option("--token-endpoint", "-e", help="PDND token endpoint URL."),
    ] = DEFAULT_TOKEN_ENDPOINT,
    server_url: Annotated[
        str | None,
        typer.Option("--server-url", "-s", help="API server URL."),
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
        typer.Option("--no-verify-ssl", help="Disable SSL verification."),
    ] = False,
    json_output: Annotated[
        bool, typer.Option("--json", help="Output as JSON.")
    ] = False,
    raw_output: Annotated[
        bool, typer.Option("--raw", help="Print raw API response to stderr.")
    ] = False,
) -> None:
    """Delete (soppressione) an accesso (``operazione_civico='S'``).

    This command does NOT accept ``--numero``, ``--metrico``,
    ``--esponente``, ``--specificita``, ``--sezione-censimento``,
    ``--isolato``, ``--coord-*``, or ``--metodo`` — Typer rejects them at
    parse time as unknown options because they have no meaning for a
    deletion.

    Example:
        anncsu accesso delete --codcom A062 --prognaz 2000449 \\
            --progr-civico 1370588
    """
    accesso = Accesso(
        operazione_civico="S",
        progr_civico=progr_civico,
        data_valid_amm=data_valid_amm,
    )

    _execute_operation(
        operazione_civico="S",
        codcom=codcom,
        progr_nazionale=prognaz,
        accesso=accesso,
        token_endpoint=token_endpoint,
        server_url=_resolve_server_url(server_url, validation_env),
        verify_ssl=not no_verify_ssl,
        raw_output=raw_output,
        json_output=json_output,
    )


# ---------------------------------------------------------------------------
# Subcommand: status
# ---------------------------------------------------------------------------


@accesso_app.command("status")
def status(
    token_endpoint: Annotated[
        str,
        typer.Option("--token-endpoint", "-e", help="PDND token endpoint URL."),
    ] = DEFAULT_TOKEN_ENDPOINT,
    server_url: Annotated[
        str | None,
        typer.Option("--server-url", "-s", help="API server URL."),
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
        typer.Option("--no-verify-ssl", help="Disable SSL verification."),
    ] = False,
    json_output: Annotated[
        bool, typer.Option("--json", help="Output as JSON.")
    ] = False,
    raw_output: Annotated[
        bool, typer.Option("--raw", help="Print raw API response to stderr.")
    ] = False,
) -> None:
    """Check the Accessi API health (GET ``/status``)."""
    resolved_url = _resolve_server_url(server_url, validation_env)
    # status is a GET, no ModI signature needed → omit modi_audience.
    sdk, _ = _get_sdk(
        token_endpoint=token_endpoint,
        server_url=resolved_url,
        verify_ssl=not no_verify_ssl,
        modi_audience=None,
    )

    try:
        response = sdk.status.show_status()
        if raw_output:
            _print_raw(response)
        api_status = getattr(response, "status", None) or "unknown"
        available = api_status.lower() in {"ok", "running"}
    except Exception as e:
        api_status = f"Error: {e}"
        available = False

    result = AccessoStatusResult(
        available=available,
        status=api_status,
        server_url=resolved_url,
        environment="validation" if validation_env else "production",
    )

    if json_output:
        print(result.model_dump_json(indent=2))
        return

    env_label = "Validation (UAT)" if validation_env else "Production"
    icon = "[green]OK[/green]" if available else "[red]UNAVAILABLE[/red]"
    console.print(f"\n[bold]Accessi API Status — {env_label}[/bold]\n")
    table = Table(show_header=True, header_style="bold")
    table.add_column("Field", style="cyan")
    table.add_column("Value")
    table.add_row("Status", f"{icon} ({api_status})")
    table.add_row("Environment", result.environment)
    table.add_row("Server URL", result.server_url)
    console.print(table)


__all__ = ["accesso_app"]
