# SPDX-FileCopyrightText: 2025-present Geobeyond <info@geobeyond.it>
# SPDX-License-Identifier: MIT
"""``anncsu odonimo`` command group — CRUD on ANNCSU odonimi.

Three sub-commands map 1:1 to the ``tipo_operazione`` field of the
POST ``/odonimi`` endpoint:

* ``insert``  → ``tipo_operazione='I'`` (insert new odonimo)
* ``update``  → ``tipo_operazione='R'`` (replace/update existing)
* ``delete``  → ``tipo_operazione='S'`` (soppressione)

Plus ``status`` for the GET ``/status`` health check.

Validation is operation-aware via ``ValidatedOdonimo``: for ``delete`` the
Typer signature does not expose ``--dug``/``--denom-*``/etc., so Typer
rejects them at parse time before any API call.
"""

from __future__ import annotations

import warnings
from typing import Annotated

import httpx
import typer
from rich.console import Console
from rich.table import Table

from anncsu.cli.commands.constants import _resolve_token_endpoint
from anncsu.cli.models import OdonimoOperationResult, OdonimoStatusResult
from anncsu.common import PDNDAuthManager
from anncsu.common.auth import extract_voucher_audience
from anncsu.common.config import APIType, ClientAssertionSettings
from anncsu.common.errors import AudienceMismatchError
from anncsu.common.hooks import SDKHooks, register_modi_hook
from anncsu.common.modi import AuditContext, ModIConfig
from anncsu.common.session import get_config_dir
from anncsu.odonimi import AnncsuOdonimi
from anncsu.odonimi.models import Security
from anncsu.odonimi.models.richiestaoperazione import (
    AutPrefettura,
    Provvedimento,
    Richiesta,
)
from anncsu.odonimi.models.validated import ValidatedOdonimo

odonimo_app = typer.Typer(
    name="odonimo",
    help="ANNCSU odonimo CRUD (insert/update/delete) and status.",
    no_args_is_help=True,
)

console = Console()
error_console = Console(stderr=True)

# Default server URLs for the Odonimi e-service.
SERVERS = {
    "production": (
        "https://modipa.agenziaentrate.it/govway/rest/in/"
        "AgenziaEntrate-PDND/anncsu-aggiornamento-odonimi/v1"
    ),
    "validation": (
        "https://modipa-val.agenziaentrate.it/govway/rest/in/"
        "AgenziaEntrate-PDND/anncsu-aggiornamento-odonimi/v1"
    ),
}


def _get_sdk(
    token_endpoint: str,
    server_url: str | None = None,
    verify_ssl: bool = True,
    modi_audience: str | None = None,
) -> tuple[AnncsuOdonimi, PDNDAuthManager]:
    """Create an authenticated AnncsuOdonimi SDK with ModI hook support.

    Mirrors the pattern from ``cli/commands/accesso.py::_get_sdk`` —
    1. Loads settings + token via PDNDAuthManager(api_type=ODONIMI)
    2. Auto-corrects ``server_url`` from voucher audience
    3. Wires a security provider callable for automatic token refresh
    4. Registers the ModI pre-request hook for AUDIT_REST_02 +
       INTEGRITY_REST_02 headers required by the Odonimi e-service
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
                api_type=APIType.ODONIMI,
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

    def security_provider() -> Security:
        return Security(bearer_auth=manager.get_access_token())

    client = httpx.Client(verify=verify_ssl)

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

    sdk = AnncsuOdonimi(
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


def _build_richiesta(
    *,
    codcom: str,
    tipo_operazione: str,
    progr_nazionale: str | None,
    codice_comunale: str | None,
    dug: str | None,
    denom_delibera: str | None,
    denom_in_lingua_1: str | None,
    denom_in_lingua_2: str | None,
    denom_localita: str | None,
    provv_data: str | None,
    provv_protocollo: str | None,
    provv_flag_delibera: str | None,
    prefettura_data: str | None,
    prefettura_protocollo: str | None,
    data_valid_amm: str | None,
) -> Richiesta:
    """Assemble a ``Richiesta`` from CLI flags, skipping unset fields."""
    provvedimento: Provvedimento | None = None
    if any(v is not None for v in (provv_data, provv_protocollo, provv_flag_delibera)):
        provvedimento = Provvedimento(
            data=provv_data,
            protocollo=provv_protocollo,
            flag_delibera=provv_flag_delibera,
        )

    aut_prefettura: AutPrefettura | None = None
    if any(v is not None for v in (prefettura_data, prefettura_protocollo)):
        aut_prefettura = AutPrefettura(
            data_pref=prefettura_data,
            protocollo_pref=prefettura_protocollo,
        )

    return Richiesta(
        codcom=codcom,
        tipo_operazione=tipo_operazione,
        progr_nazionale=progr_nazionale,
        codice_comunale=codice_comunale,
        dug=dug,
        denom_delibera=denom_delibera,
        denom_in_lingua_1=denom_in_lingua_1,
        denom_in_lingua_2=denom_in_lingua_2,
        denom_localita=denom_localita,
        provvedimento=provvedimento,
        aut_prefettura=aut_prefettura,
        data_valid_amm=data_valid_amm,
    )


def _execute_operation(
    *,
    tipo_operazione: str,
    richiesta: Richiesta,
    token_endpoint: str,
    server_url: str,
    verify_ssl: bool,
    raw_output: bool,
    json_output: bool,
) -> None:
    """Common send-and-render flow for I / R / S operations.

    Validates the ``Richiesta`` via ``ValidatedOdonimo`` BEFORE the API call,
    then issues the POST and renders the response either as JSON
    (``--json``) or as a rich table.
    """
    try:
        ValidatedOdonimo.model_validate(richiesta.model_dump(exclude_unset=True))
    except Exception as e:
        error_console.print(f"[red]Validation error:[/red] {e}")
        raise typer.Exit(1) from None

    sdk, _ = _get_sdk(
        token_endpoint=token_endpoint,
        server_url=server_url,
        verify_ssl=verify_ssl,
        modi_audience=server_url,
    )

    try:
        response = sdk.anncsu.gestione_anncsu_odonimi_pdnd(richiesta=richiesta)
    except Exception as e:
        error_console.print(f"[red]Error:[/red] API call failed: {e}")
        raise typer.Exit(1) from None

    if raw_output:
        _print_raw(response)

    esito = getattr(response, "esito", None)
    success = esito == "0"

    result = OdonimoOperationResult(
        success=success,
        tipo_operazione=tipo_operazione,
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
            f"[green]Operation '{tipo_operazione}' successful![/green] "
            f"ID: {result.id_richiesta}\n"
        )
    else:
        console.print(
            f"[red]Operation '{tipo_operazione}' failed.[/red] "
            f"ID: {result.id_richiesta}\n"
        )

    table = Table(show_header=True, header_style="bold")
    table.add_column("Field", style="cyan")
    table.add_column("Value")
    table.add_row("Operation", tipo_operazione)
    table.add_row("Request ID", result.id_richiesta or "—")
    table.add_row("Esito", result.esito or "—")
    table.add_row("Messaggio", result.messaggio or "—")
    table.add_row("Dati count", str(result.dati_count))
    console.print(table)

    if not success:
        raise typer.Exit(1)


# ---------------------------------------------------------------------------
# Subcommand: insert (tipo_operazione='I')
# ---------------------------------------------------------------------------


@odonimo_app.command("insert")
def insert(
    codcom: Annotated[
        str,
        typer.Option(
            "--codcom",
            "-c",
            help="Codice comune (Belfiore code, e.g. A062).",
        ),
    ],
    dug: Annotated[
        str,
        typer.Option(
            "--dug",
            help="DUG (e.g. 'VIA', 'PIAZZA'). Required for I/R, not allowed for S.",
        ),
    ],
    denom_delibera: Annotated[
        str | None,
        typer.Option(
            "--denom-delibera",
            help="Denominazione delibera (uppercase applied).",
        ),
    ] = None,
    denom_in_lingua_1: Annotated[
        str | None,
        typer.Option(
            "--denom-in-lingua-1",
            help="Odonimo in lingua 1 (comprensivo della dug, per comuni bi/tri-lingua).",
        ),
    ] = None,
    denom_in_lingua_2: Annotated[
        str | None,
        typer.Option(
            "--denom-in-lingua-2",
            help="Odonimo in lingua 2 (per comuni tri-lingua).",
        ),
    ] = None,
    denom_localita: Annotated[
        str | None,
        typer.Option(
            "--denom-localita",
            help="Denominazione località (uppercase applied).",
        ),
    ] = None,
    codice_comunale: Annotated[
        str | None,
        typer.Option(
            "--codice-comunale",
            help="Codifica comunale dell'odonimo (no uppercase).",
        ),
    ] = None,
    provv_data: Annotated[
        str | None,
        typer.Option("--provv-data", help="Data del provvedimento (dd/MM/yyyy)."),
    ] = None,
    provv_protocollo: Annotated[
        str | None,
        typer.Option(
            "--provv-protocollo",
            help="Protocollo del provvedimento (max 70 char, no uppercase).",
        ),
    ] = None,
    provv_flag_delibera: Annotated[
        str | None,
        typer.Option(
            "--provv-flag-delibera",
            help=(
                "Flag delibera (0-4). I valori 0 e 1 rendono obbligatori "
                "--provv-data e --provv-protocollo."
            ),
        ),
    ] = None,
    prefettura_data: Annotated[
        str | None,
        typer.Option(
            "--prefettura-data",
            help="Data prefettura. Obbligatoria se --prefettura-protocollo è valorizzato.",
        ),
    ] = None,
    prefettura_protocollo: Annotated[
        str | None,
        typer.Option(
            "--prefettura-protocollo",
            help="Protocollo prefettura. Obbligatorio se --prefettura-data è valorizzato.",
        ),
    ] = None,
    data_valid_amm: Annotated[
        str | None,
        typer.Option(
            "--data-valid-amm",
            help="Data di validità amministrativa (dd/MM/yyyy).",
        ),
    ] = None,
    token_endpoint: Annotated[
        str | None,
        typer.Option(
            "--token-endpoint",
            "-e",
            help=(
                "PDND token endpoint URL. If omitted, defaults to UAT or "
                "production based on --validation/--production."
            ),
        ),
    ] = None,
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
    """Insert a new odonimo (``tipo_operazione='I'``)."""
    token_endpoint = _resolve_token_endpoint(token_endpoint, validation_env)
    resolved_url = _resolve_server_url(server_url, validation_env)

    richiesta = _build_richiesta(
        codcom=codcom,
        tipo_operazione="I",
        progr_nazionale=None,
        codice_comunale=codice_comunale,
        dug=dug,
        denom_delibera=denom_delibera,
        denom_in_lingua_1=denom_in_lingua_1,
        denom_in_lingua_2=denom_in_lingua_2,
        denom_localita=denom_localita,
        provv_data=provv_data,
        provv_protocollo=provv_protocollo,
        provv_flag_delibera=provv_flag_delibera,
        prefettura_data=prefettura_data,
        prefettura_protocollo=prefettura_protocollo,
        data_valid_amm=data_valid_amm,
    )

    _execute_operation(
        tipo_operazione="I",
        richiesta=richiesta,
        token_endpoint=token_endpoint,
        server_url=resolved_url,
        verify_ssl=not no_verify_ssl,
        raw_output=raw_output,
        json_output=json_output,
    )


# ---------------------------------------------------------------------------
# Subcommand: update (tipo_operazione='R')
# ---------------------------------------------------------------------------


@odonimo_app.command("update")
def update(
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
            help="Progressivo nazionale dell'odonimo (required for update).",
        ),
    ],
    dug: Annotated[
        str,
        typer.Option(
            "--dug",
            help="DUG (e.g. 'VIA', 'PIAZZA'). Required for I/R.",
        ),
    ],
    denom_delibera: Annotated[
        str | None,
        typer.Option(
            "--denom-delibera", help="Denominazione delibera (uppercase applied)."
        ),
    ] = None,
    denom_in_lingua_1: Annotated[
        str | None,
        typer.Option(
            "--denom-in-lingua-1", help="Odonimo in lingua 1 (comuni bi/tri-lingua)."
        ),
    ] = None,
    denom_in_lingua_2: Annotated[
        str | None,
        typer.Option(
            "--denom-in-lingua-2", help="Odonimo in lingua 2 (comuni tri-lingua)."
        ),
    ] = None,
    denom_localita: Annotated[
        str | None,
        typer.Option("--denom-localita", help="Denominazione località."),
    ] = None,
    codice_comunale: Annotated[
        str | None,
        typer.Option(
            "--codice-comunale", help="Codifica comunale dell'odonimo (no uppercase)."
        ),
    ] = None,
    provv_data: Annotated[
        str | None,
        typer.Option("--provv-data", help="Data del provvedimento (dd/MM/yyyy)."),
    ] = None,
    provv_protocollo: Annotated[
        str | None,
        typer.Option(
            "--provv-protocollo",
            help="Protocollo del provvedimento (max 70 char).",
        ),
    ] = None,
    provv_flag_delibera: Annotated[
        str | None,
        typer.Option(
            "--provv-flag-delibera",
            help=(
                "Flag delibera (0-4). I valori 0 e 1 rendono obbligatori "
                "--provv-data e --provv-protocollo."
            ),
        ),
    ] = None,
    prefettura_data: Annotated[
        str | None,
        typer.Option(
            "--prefettura-data",
            help="Data prefettura. Obbligatoria se --prefettura-protocollo è valorizzato.",
        ),
    ] = None,
    prefettura_protocollo: Annotated[
        str | None,
        typer.Option(
            "--prefettura-protocollo",
            help="Protocollo prefettura. Obbligatorio se --prefettura-data è valorizzato.",
        ),
    ] = None,
    data_valid_amm: Annotated[
        str | None,
        typer.Option(
            "--data-valid-amm",
            help="Data di validità amministrativa (dd/MM/yyyy).",
        ),
    ] = None,
    token_endpoint: Annotated[
        str | None,
        typer.Option(
            "--token-endpoint",
            "-e",
            help=(
                "PDND token endpoint URL. If omitted, defaults to UAT or "
                "production based on --validation/--production."
            ),
        ),
    ] = None,
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
    """Update/replace an existing odonimo (``tipo_operazione='R'``)."""
    token_endpoint = _resolve_token_endpoint(token_endpoint, validation_env)
    resolved_url = _resolve_server_url(server_url, validation_env)

    richiesta = _build_richiesta(
        codcom=codcom,
        tipo_operazione="R",
        progr_nazionale=prognaz,
        codice_comunale=codice_comunale,
        dug=dug,
        denom_delibera=denom_delibera,
        denom_in_lingua_1=denom_in_lingua_1,
        denom_in_lingua_2=denom_in_lingua_2,
        denom_localita=denom_localita,
        provv_data=provv_data,
        provv_protocollo=provv_protocollo,
        provv_flag_delibera=provv_flag_delibera,
        prefettura_data=prefettura_data,
        prefettura_protocollo=prefettura_protocollo,
        data_valid_amm=data_valid_amm,
    )

    _execute_operation(
        tipo_operazione="R",
        richiesta=richiesta,
        token_endpoint=token_endpoint,
        server_url=resolved_url,
        verify_ssl=not no_verify_ssl,
        raw_output=raw_output,
        json_output=json_output,
    )


# ---------------------------------------------------------------------------
# Subcommand: delete (tipo_operazione='S')
# ---------------------------------------------------------------------------


@odonimo_app.command("delete")
def delete(
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
            help="Progressivo nazionale dell'odonimo (required for delete).",
        ),
    ],
    data_valid_amm: Annotated[
        str | None,
        typer.Option(
            "--data-valid-amm",
            help="Data di fine validità (dd/MM/yyyy). Default: data corrente.",
        ),
    ] = None,
    token_endpoint: Annotated[
        str | None,
        typer.Option(
            "--token-endpoint",
            "-e",
            help=(
                "PDND token endpoint URL. If omitted, defaults to UAT or "
                "production based on --validation/--production."
            ),
        ),
    ] = None,
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
    """Delete (soppressione) an odonimo (``tipo_operazione='S'``).

    Only the identifying fields and ``--data-valid-amm`` are accepted —
    Typer rejects any other CLI flag at parse time, mirroring the OAS
    constraint that ``dug``/``denom-*``/etc. are forbidden for S.
    """
    token_endpoint = _resolve_token_endpoint(token_endpoint, validation_env)
    resolved_url = _resolve_server_url(server_url, validation_env)

    richiesta = _build_richiesta(
        codcom=codcom,
        tipo_operazione="S",
        progr_nazionale=prognaz,
        codice_comunale=None,
        dug=None,
        denom_delibera=None,
        denom_in_lingua_1=None,
        denom_in_lingua_2=None,
        denom_localita=None,
        provv_data=None,
        provv_protocollo=None,
        provv_flag_delibera=None,
        prefettura_data=None,
        prefettura_protocollo=None,
        data_valid_amm=data_valid_amm,
    )

    _execute_operation(
        tipo_operazione="S",
        richiesta=richiesta,
        token_endpoint=token_endpoint,
        server_url=resolved_url,
        verify_ssl=not no_verify_ssl,
        raw_output=raw_output,
        json_output=json_output,
    )


# ---------------------------------------------------------------------------
# Subcommand: status (GET /status)
# ---------------------------------------------------------------------------


@odonimo_app.command("status")
def status(
    token_endpoint: Annotated[
        str | None,
        typer.Option(
            "--token-endpoint",
            "-e",
            help=(
                "PDND token endpoint URL. If omitted, defaults to UAT or "
                "production based on --validation/--production."
            ),
        ),
    ] = None,
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
    """Check the Odonimi API health (GET ``/status``)."""
    token_endpoint = _resolve_token_endpoint(token_endpoint, validation_env)
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

    result = OdonimoStatusResult(
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
    console.print(f"\n[bold]Odonimi API Status — {env_label}[/bold]\n")
    table = Table(show_header=True, header_style="bold")
    table.add_column("Field", style="cyan")
    table.add_column("Value")
    table.add_row("Status", f"{icon} ({api_status})")
    table.add_row("Environment", result.environment)
    table.add_row("Server URL", result.server_url)
    console.print(table)


__all__ = ["odonimo_app"]
