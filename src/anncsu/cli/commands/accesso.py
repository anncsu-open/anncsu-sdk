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
from anncsu.cli.commands.constants import _resolve_token_endpoint
from anncsu.cli.models import (
    AccessoDryRunResult,
    AccessoOperationResult,
    AccessoStatusResult,
)
from anncsu.common import PDNDAuthManager
from anncsu.common.auth import extract_voucher_audience
from anncsu.common.config import APIType, ClientAssertionSettings
from anncsu.common.errors import AudienceMismatchError
from anncsu.common.hooks import SDKHooks, register_modi_hook
from anncsu.common.modi import AuditContext, ModIConfig
from anncsu.common.security import Security as PASecurity
from anncsu.common.session import get_config_dir
from anncsu.pa import AnncsuConsultazione

accesso_app = typer.Typer(
    name="accesso",
    help="ANNCSU accesso CRUD (insert/update/delete) and status.",
    no_args_is_help=True,
)

console = Console()
error_console = Console(stderr=True)

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


# Fields that must be valued in the original accesso for a R rollback to be
# safe. If any of these is null/missing on the originals (legacy ANNCSU
# data), update --dry-run aborts before any write to avoid an irreversible
# update.
DRY_RUN_REQUIRED_ORIGINAL_FIELDS: tuple[str, ...] = (
    "metodo",
    # sezione_censimento is optional in the OAS but commonly null on legacy
    # data — we only require the strict ones to keep dry-run usable.
)


def _get_consult_sdk(
    token_endpoint: str,
    verify_ssl: bool = True,
) -> AnncsuConsultazione:
    """Build a read-only PA Consultazione SDK for accesso lookups.

    Used by ``--dry-run`` (to fetch the original values before rollback)
    and by ``--auto-resolve`` (to resolve progr_civico from prognaz+civico).
    Auto-discovers the server URL from the voucher audience.
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
        error_console.print(
            f"[red]Error:[/red] PA Consultazione authentication failed: {e}"
        )
        raise typer.Exit(1) from None

    # Auto-discover PA server URL from voucher.
    server_url = extract_voucher_audience(access_token)

    def security_provider() -> PASecurity:
        return PASecurity(bearer=manager.get_access_token())

    client = httpx.Client(verify=verify_ssl)
    return AnncsuConsultazione(
        security=security_provider,
        server_url=server_url,
        client=client,
    )


def _resolve_progr_civico_via_pa(
    consult_sdk: AnncsuConsultazione,
    *,
    prognaz: str,
    civico: str,
) -> str:
    """Resolve ``progr_civico`` from ``prognaz`` + ``civico`` via PA API.

    Used by ``--auto-resolve``. Errors out if zero or multiple matches are
    found, since either case is a setup error the user must address.
    """
    try:
        response = consult_sdk.queryparam.elencoaccessiprog_get_query_param(
            prognaz=prognaz, accparz=civico
        )
    except Exception as e:
        error_console.print(f"[red]Error:[/red] PA lookup failed: {e}")
        raise typer.Exit(1) from None

    matches = list(response.data or [])
    if not matches:
        error_console.print(
            f"[red]Error:[/red] No accesso found for prognaz={prognaz} "
            f"civico={civico}. Cannot auto-resolve progr_civico."
        )
        raise typer.Exit(1)
    if len(matches) > 1:
        error_console.print(
            f"[red]Error:[/red] Ambiguous lookup: {len(matches)} matches for "
            f"prognaz={prognaz} civico={civico}. Specify --progr-civico "
            f"explicitly to disambiguate."
        )
        raise typer.Exit(1)

    return str(matches[0].prognazacc)


def _lookup_accesso_originali(
    consult_sdk: AnncsuConsultazione,
    progr_civico: str,
) -> dict[str, str | None]:
    """Fetch the original field values of an accesso by ``progr_civico``.

    Returns a dict of the fields needed to construct a rollback payload.
    Raises typer.Exit(1) if the accesso is not found.
    """
    try:
        response = consult_sdk.queryparam.prognazacc_get_query_param(
            prognazacc=progr_civico
        )
    except Exception as e:
        error_console.print(f"[red]Error:[/red] Original accesso lookup failed: {e}")
        raise typer.Exit(1) from None

    data_list = response.data or []
    if not data_list:
        error_console.print(
            f"[red]Error:[/red] No accesso found for progr_civico={progr_civico}."
        )
        raise typer.Exit(1)

    item = data_list[0]
    return {
        "civico": getattr(item, "civico", None),
        "metrico": getattr(item, "metrico", None),
        "esponente": getattr(item, "esp", None),
        "specificita": getattr(item, "specif", None),
        "coord_x": getattr(item, "coord_x", None),
        "coord_y": getattr(item, "coord_y", None),
        "quota": getattr(item, "quota", None),
        "metodo": getattr(item, "metodo", None),
    }


def _write_pending_log(
    *,
    operazione: str,
    payload: dict,
    note: str,
) -> str:
    """Write a pending-rollback log file before issuing the rollback call.

    If the CLI crashes between the test op and the rollback, the user has
    a JSON file with every detail needed to clean up manually.

    Returns the absolute path to the file written.
    """
    import datetime
    import json
    import os

    config_dir = get_config_dir()
    config_dir.mkdir(parents=True, exist_ok=True)
    pending_path = config_dir / "dryrun_pending.json"
    record = {
        "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "operazione": operazione,
        "payload": payload,
        "note": note,
        "pid": os.getpid(),
    }
    pending_path.write_text(json.dumps(record, indent=2, default=str))
    return str(pending_path)


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


def _build_result_from_response(
    response: object, operazione_civico: str
) -> AccessoOperationResult:
    """Convert a raw SDK response into an AccessoOperationResult."""
    esito = getattr(response, "esito", None)
    return AccessoOperationResult(
        success=esito == "0",
        operazione_civico=operazione_civico,
        id_richiesta=getattr(response, "id_richiesta", None),
        esito=esito,
        messaggio=getattr(response, "messaggio", None),
        dati_count=len(getattr(response, "dati", []) or []),
    )


def _run_insert_dry_run(
    *,
    codcom: str,
    progr_nazionale: str,
    accesso: Accesso,
    token_endpoint: str,
    server_url: str,
    verify_ssl: bool,
    raw_output: bool,
    json_output: bool,
) -> None:
    """Insert + immediate S rollback. Writes a pending log between the two
    API calls so the user has a recovery trail if the process crashes."""
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

    # Step 1: I (insert)
    richiesta = Richiesta(
        codcom=codcom, progr_nazionale=progr_nazionale, accesso=accesso
    )
    try:
        insert_response = sdk.anncsu.gestione_anncsu_pdnd(richiesta=richiesta)
    except Exception as e:
        error_console.print(f"[red]Error:[/red] Insert API call failed: {e}")
        raise typer.Exit(1) from None

    if raw_output:
        _print_raw(insert_response, "Raw insert response")

    test_op_result = _build_result_from_response(insert_response, "I")

    # Extract the progr_civico assigned by the API (needed for rollback S).
    dati = getattr(insert_response, "dati", None) or []
    assigned_progr_civico: str | None = None
    if dati:
        assigned_progr_civico = getattr(dati[0], "progr_civico", None)

    if not test_op_result.success or not assigned_progr_civico:
        # Insert itself failed → nothing to roll back.
        error_console.print("[red]Insert failed; no rollback executed.[/red]")
        dry_run_result = AccessoDryRunResult(
            success=False,
            operazione_civico="I",
            test_op=test_op_result,
            rollback=None,
            rollback_failed=False,
            error_message=(
                "Insert did not return a progr_civico — cannot roll back."
                if test_op_result.success
                else (test_op_result.messaggio or "Insert failed")
            ),
        )
        if json_output:
            print(dry_run_result.model_dump_json(indent=2))
        else:
            console.print(f"[red]Dry-run aborted:[/red] {dry_run_result.error_message}")
        raise typer.Exit(1)

    # Step 2: persist pending log BEFORE issuing the rollback. If the
    # process dies between here and the next API call, the user finds the
    # log file and can clean up manually.
    rollback_accesso = Accesso(
        operazione_civico="S",
        progr_civico=assigned_progr_civico,
    )
    pending_path = _write_pending_log(
        operazione="S",
        payload={
            "codcom": codcom,
            "progr_nazionale": progr_nazionale,
            "progr_civico": assigned_progr_civico,
            "originating_test_op": "I",
        },
        note=(
            "Insert dry-run pending rollback. If you see this file, the CLI "
            "crashed between insert and delete — manually run "
            f"`anncsu accesso delete --codcom {codcom} --prognaz "
            f"{progr_nazionale} --progr-civico {assigned_progr_civico}`."
        ),
    )
    if not json_output:
        console.print(f"[dim]Pending log written to:[/dim] {pending_path}")

    # Step 3: S (rollback)
    rollback_richiesta = Richiesta(
        codcom=codcom, progr_nazionale=progr_nazionale, accesso=rollback_accesso
    )
    rollback_failed = False
    rollback_error: str | None = None
    try:
        rollback_response = sdk.anncsu.gestione_anncsu_pdnd(
            richiesta=rollback_richiesta
        )
        if raw_output:
            _print_raw(rollback_response, "Raw rollback response")
        rollback_result = _build_result_from_response(rollback_response, "S")
        if not rollback_result.success:
            rollback_failed = True
            rollback_error = rollback_result.messaggio
    except Exception as e:
        rollback_failed = True
        rollback_error = str(e)
        rollback_result = AccessoOperationResult(
            success=False,
            operazione_civico="S",
            messaggio=str(e),
        )

    dry_run_result = AccessoDryRunResult(
        success=test_op_result.success and not rollback_failed,
        operazione_civico="I",
        test_op=test_op_result,
        rollback=rollback_result,
        rollback_failed=rollback_failed,
        pending_log_path=pending_path,
        error_message=rollback_error if rollback_failed else None,
    )

    if json_output:
        print(dry_run_result.model_dump_json(indent=2))
        if not dry_run_result.success:
            raise typer.Exit(1)
        return

    if dry_run_result.success:
        console.print("[green]Dry-run cycle successful (insert + rollback).[/green]")
    else:
        console.print(
            f"[red]Dry-run failed at rollback step.[/red] "
            f"Manual cleanup may be needed: {pending_path}"
        )

    table = Table(show_header=True, header_style="bold")
    table.add_column("Step", style="cyan")
    table.add_column("Result")
    table.add_column("Details")
    table.add_row(
        "Insert (test_op)",
        "[green]OK[/green]" if test_op_result.success else "[red]FAILED[/red]",
        test_op_result.messaggio or "—",
    )
    table.add_row(
        "Delete (rollback)",
        "[green]OK[/green]" if rollback_result.success else "[red]FAILED[/red]",
        rollback_result.messaggio or "—",
    )
    console.print(table)

    if not dry_run_result.success:
        raise typer.Exit(1)


def _run_update_dry_run(
    *,
    codcom: str,
    progr_nazionale: str,
    new_accesso: Accesso,
    token_endpoint: str,
    server_url: str,
    verify_ssl: bool,
    raw_output: bool,
    json_output: bool,
) -> None:
    """Update + immediate R rollback to original values.

    Pre-checks that every field required for a clean rollback (currently
    ``metodo``) is populated on the originals. If any is null/missing on
    ANNCSU side (legacy data), the dry-run aborts BEFORE the first R is
    sent — guaranteeing no irreversible write.
    """
    progr_civico = new_accesso.progr_civico
    if not progr_civico:
        error_console.print(
            "[red]Error:[/red] update --dry-run requires --progr-civico."
        )
        raise typer.Exit(1)

    consult_sdk = _get_consult_sdk(token_endpoint=token_endpoint, verify_ssl=verify_ssl)
    originali = _lookup_accesso_originali(consult_sdk, progr_civico)

    # Pre-check: rollback would fail on legacy data with null required fields.
    missing_required = [
        f for f in DRY_RUN_REQUIRED_ORIGINAL_FIELDS if not originali.get(f)
    ]
    if missing_required:
        msg = (
            f"[red]Dry-run aborted:[/red] the original accesso has null/missing "
            f"fields needed to rebuild the rollback payload: "
            f"{', '.join(missing_required)}. This is typical for legacy ANNCSU "
            f"data — proceeding would result in an irreversible update."
        )
        if json_output:
            print(
                AccessoDryRunResult(
                    success=False,
                    operazione_civico="R",
                    test_op=AccessoOperationResult(
                        success=False, operazione_civico="R"
                    ),
                    error_message=(
                        f"legacy originali con campi null: "
                        f"{', '.join(missing_required)}"
                    ),
                ).model_dump_json(indent=2)
            )
        else:
            console.print(msg)
        raise typer.Exit(1)

    sdk, _ = _get_sdk(
        token_endpoint=token_endpoint,
        server_url=server_url,
        verify_ssl=verify_ssl,
        modi_audience=server_url,
    )

    # Step 1: R with new values
    try:
        new_response = sdk.anncsu.gestione_anncsu_pdnd(
            richiesta=Richiesta(
                codcom=codcom,
                progr_nazionale=progr_nazionale,
                accesso=new_accesso,
            )
        )
    except Exception as e:
        error_console.print(f"[red]Error:[/red] Update API call failed: {e}")
        raise typer.Exit(1) from None

    if raw_output:
        _print_raw(new_response, "Raw update response")
    test_op_result = _build_result_from_response(new_response, "R")

    if not test_op_result.success:
        dry_run_result = AccessoDryRunResult(
            success=False,
            operazione_civico="R",
            test_op=test_op_result,
            error_message=test_op_result.messaggio or "Update failed",
        )
        if json_output:
            print(dry_run_result.model_dump_json(indent=2))
        else:
            console.print(
                f"[red]Dry-run aborted at update step.[/red] "
                f"{test_op_result.messaggio or ''}"
            )
        raise typer.Exit(1)

    # Persist pending log before rollback (R original).
    pending_path = _write_pending_log(
        operazione="R",
        payload={
            "codcom": codcom,
            "progr_nazionale": progr_nazionale,
            "progr_civico": progr_civico,
            "originals": originali,
            "originating_test_op": "R",
        },
        note=(
            f"Update dry-run pending rollback. The accesso "
            f"progr_civico={progr_civico} has been updated with new values; "
            f"if you see this file, manually run `anncsu accesso update ...` "
            f"with the originals above to restore."
        ),
    )
    if not json_output:
        console.print(f"[dim]Pending log written to:[/dim] {pending_path}")

    # Step 2: R with original values (rollback)
    rollback_coordinate: Coordinate | None = None
    if originali.get("coord_x") or originali.get("coord_y"):
        rollback_coordinate = Coordinate(
            x=originali.get("coord_x"),
            y=originali.get("coord_y"),
            z=originali.get("quota"),
            metodo=originali.get("metodo"),
        )
    rollback_accesso = Accesso(
        operazione_civico="R",
        progr_civico=progr_civico,
        numero=originali.get("civico"),
        metrico=originali.get("metrico"),
        esponente=originali.get("esponente"),
        specificita=originali.get("specificita"),
        coordinate=rollback_coordinate,
    )

    rollback_failed = False
    rollback_error: str | None = None
    try:
        rollback_response = sdk.anncsu.gestione_anncsu_pdnd(
            richiesta=Richiesta(
                codcom=codcom,
                progr_nazionale=progr_nazionale,
                accesso=rollback_accesso,
            )
        )
        if raw_output:
            _print_raw(rollback_response, "Raw rollback response")
        rollback_result = _build_result_from_response(rollback_response, "R")
        if not rollback_result.success:
            rollback_failed = True
            rollback_error = rollback_result.messaggio
    except Exception as e:
        rollback_failed = True
        rollback_error = str(e)
        rollback_result = AccessoOperationResult(
            success=False, operazione_civico="R", messaggio=str(e)
        )

    dry_run_result = AccessoDryRunResult(
        success=test_op_result.success and not rollback_failed,
        operazione_civico="R",
        test_op=test_op_result,
        rollback=rollback_result,
        rollback_failed=rollback_failed,
        pending_log_path=pending_path,
        error_message=rollback_error if rollback_failed else None,
    )

    if json_output:
        print(dry_run_result.model_dump_json(indent=2))
        if not dry_run_result.success:
            raise typer.Exit(1)
        return

    if dry_run_result.success:
        console.print(
            "[green]Dry-run cycle successful (update + restore originals).[/green]"
        )
    else:
        console.print(
            f"[red]Dry-run failed at rollback step.[/red] "
            f"Manual cleanup may be needed: {pending_path}"
        )

    table = Table(show_header=True, header_style="bold")
    table.add_column("Step", style="cyan")
    table.add_column("Result")
    table.add_column("Details")
    table.add_row(
        "Update new (test_op)",
        "[green]OK[/green]" if test_op_result.success else "[red]FAILED[/red]",
        test_op_result.messaggio or "—",
    )
    table.add_row(
        "Restore original (rollback)",
        "[green]OK[/green]" if rollback_result.success else "[red]FAILED[/red]",
        rollback_result.messaggio or "—",
    )
    console.print(table)

    if not dry_run_result.success:
        raise typer.Exit(1)


def _run_delete_dry_run(
    *,
    codcom: str,
    progr_nazionale: str,
    progr_civico: str,
    data_valid_amm: str | None,
    token_endpoint: str,
    server_url: str,
    verify_ssl: bool,
    raw_output: bool,
    json_output: bool,
) -> None:
    """Delete + immediate re-insert rollback.

    Flow: PA lookup of original fields → S → I (rebuilt from originals).
    The re-inserted accesso gets a new ``progr_civico`` assigned by ANNCSU
    (the spec doesn't let us force the old one), so the rollback result
    flags ``rollback_progr_civico_changed=True``.
    """
    consult_sdk = _get_consult_sdk(token_endpoint=token_endpoint, verify_ssl=verify_ssl)
    originali = _lookup_accesso_originali(consult_sdk, progr_civico)

    sdk, _ = _get_sdk(
        token_endpoint=token_endpoint,
        server_url=server_url,
        verify_ssl=verify_ssl,
        modi_audience=server_url,
    )

    # Step 1: S (delete under test)
    delete_accesso = Accesso(
        operazione_civico="S",
        progr_civico=progr_civico,
        data_valid_amm=data_valid_amm,
    )
    try:
        delete_response = sdk.anncsu.gestione_anncsu_pdnd(
            richiesta=Richiesta(
                codcom=codcom,
                progr_nazionale=progr_nazionale,
                accesso=delete_accesso,
            )
        )
    except Exception as e:
        error_console.print(f"[red]Error:[/red] Delete API call failed: {e}")
        raise typer.Exit(1) from None

    if raw_output:
        _print_raw(delete_response, "Raw delete response")
    test_op_result = _build_result_from_response(delete_response, "S")

    if not test_op_result.success:
        dry_run_result = AccessoDryRunResult(
            success=False,
            operazione_civico="S",
            test_op=test_op_result,
            error_message=test_op_result.messaggio or "Delete failed",
        )
        if json_output:
            print(dry_run_result.model_dump_json(indent=2))
        else:
            console.print(
                f"[red]Dry-run aborted at delete step.[/red] "
                f"{test_op_result.messaggio or ''}"
            )
        raise typer.Exit(1)

    # Persist pending log before rollback (I).
    pending_path = _write_pending_log(
        operazione="I",
        payload={
            "codcom": codcom,
            "progr_nazionale": progr_nazionale,
            "deleted_progr_civico": progr_civico,
            "originals": originali,
            "originating_test_op": "S",
        },
        note=(
            f"Delete dry-run pending rollback. The accesso "
            f"progr_civico={progr_civico} has been soppressed; if you see "
            f"this file, the CLI crashed before the re-insert. Manually run "
            f"`anncsu accesso insert ...` with the data above to restore it."
        ),
    )
    if not json_output:
        console.print(f"[dim]Pending log written to:[/dim] {pending_path}")

    # Step 2: I (rollback) using original values.
    rollback_coordinate: Coordinate | None = None
    if originali.get("coord_x") or originali.get("coord_y"):
        rollback_coordinate = Coordinate(
            x=originali.get("coord_x"),
            y=originali.get("coord_y"),
            z=originali.get("quota"),
            metodo=originali.get("metodo"),
        )
    rollback_accesso = Accesso(
        operazione_civico="I",
        numero=originali.get("civico"),
        metrico=originali.get("metrico"),
        esponente=originali.get("esponente"),
        specificita=originali.get("specificita"),
        coordinate=rollback_coordinate,
    )

    rollback_failed = False
    rollback_error: str | None = None
    progr_civico_changed = False
    try:
        rollback_response = sdk.anncsu.gestione_anncsu_pdnd(
            richiesta=Richiesta(
                codcom=codcom,
                progr_nazionale=progr_nazionale,
                accesso=rollback_accesso,
            )
        )
        if raw_output:
            _print_raw(rollback_response, "Raw rollback response")
        rollback_result = _build_result_from_response(rollback_response, "I")
        if rollback_result.success:
            # ANNCSU assigns a new progr_civico — we cannot preserve the old.
            new_dati = getattr(rollback_response, "dati", None) or []
            if new_dati:
                new_progr = getattr(new_dati[0], "progr_civico", None)
                if new_progr and str(new_progr) != progr_civico:
                    progr_civico_changed = True
        else:
            rollback_failed = True
            rollback_error = rollback_result.messaggio
    except Exception as e:
        rollback_failed = True
        rollback_error = str(e)
        rollback_result = AccessoOperationResult(
            success=False, operazione_civico="I", messaggio=str(e)
        )

    dry_run_result = AccessoDryRunResult(
        success=test_op_result.success and not rollback_failed,
        operazione_civico="S",
        test_op=test_op_result,
        rollback=rollback_result,
        rollback_failed=rollback_failed,
        rollback_progr_civico_changed=progr_civico_changed,
        pending_log_path=pending_path,
        error_message=rollback_error if rollback_failed else None,
    )

    if json_output:
        print(dry_run_result.model_dump_json(indent=2))
        if not dry_run_result.success:
            raise typer.Exit(1)
        return

    if dry_run_result.success:
        msg = "[green]Dry-run cycle successful (delete + re-insert).[/green]"
        if progr_civico_changed:
            msg += (
                " [yellow]Note:[/yellow] the re-inserted accesso has a NEW "
                "progr_civico (ANNCSU assigns it autonomously)."
            )
        console.print(msg)
    else:
        console.print(
            f"[red]Dry-run failed at rollback step.[/red] "
            f"Manual cleanup may be needed: {pending_path}"
        )

    table = Table(show_header=True, header_style="bold")
    table.add_column("Step", style="cyan")
    table.add_column("Result")
    table.add_column("Details")
    table.add_row(
        "Delete (test_op)",
        "[green]OK[/green]" if test_op_result.success else "[red]FAILED[/red]",
        test_op_result.messaggio or "—",
    )
    table.add_row(
        "Re-insert (rollback)",
        "[green]OK[/green]" if rollback_result.success else "[red]FAILED[/red]",
        rollback_result.messaggio or "—",
    )
    console.print(table)

    if not dry_run_result.success:
        raise typer.Exit(1)


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
    dry_run: Annotated[
        bool,
        typer.Option(
            "--dry-run",
            help=(
                "Run insert and immediately delete the new accesso (S rollback). "
                "A pending log is written to ~/.anncsu/dryrun_pending.json "
                "before the rollback so a crash leaves a manual-recovery trail."
            ),
        ),
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

    token_endpoint = _resolve_token_endpoint(token_endpoint, validation_env)
    resolved_server = _resolve_server_url(server_url, validation_env)

    if dry_run:
        _run_insert_dry_run(
            codcom=codcom,
            progr_nazionale=prognaz,
            accesso=accesso,
            token_endpoint=token_endpoint,
            server_url=resolved_server,
            verify_ssl=not no_verify_ssl,
            raw_output=raw_output,
            json_output=json_output,
        )
        return

    _execute_operation(
        operazione_civico="I",
        codcom=codcom,
        progr_nazionale=prognaz,
        accesso=accesso,
        token_endpoint=token_endpoint,
        server_url=resolved_server,
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
        str | None,
        typer.Option(
            "--progr-civico",
            "-P",
            help=(
                "Progressivo civico (identifier of the accesso). Required "
                "unless --auto-resolve is used."
            ),
        ),
    ] = None,
    civico: Annotated[
        str | None,
        typer.Option(
            "--civico",
            help="Numero civico — used with --auto-resolve to look up progr_civico.",
        ),
    ] = None,
    auto_resolve: Annotated[
        bool,
        typer.Option(
            "--auto-resolve",
            help=(
                "Resolve progr_civico automatically via PA accesso lookup "
                "(requires --civico). Errors if 0 or >1 matches are found."
            ),
        ),
    ] = False,
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
    dry_run: Annotated[
        bool,
        typer.Option(
            "--dry-run",
            help=(
                "Run update + immediate restore of originals (R + R). Pre-checks "
                "that the originals have all required fields (e.g. metodo) "
                "populated — aborts before any write if legacy data with nulls "
                "is detected."
            ),
        ),
    ] = False,
) -> None:
    """Update/replace an existing accesso (``operazione_civico='R'``).

    Example:
        anncsu accesso update --codcom A062 --prognaz 2000449 \\
            --progr-civico 1370588 --numero 12
    """
    # Resolve progr_civico either explicitly or via PA lookup.
    # Resolve token endpoint up-front: --auto-resolve below also uses it
    # (via PA consultation SDK), so it must be the right environment.
    token_endpoint = _resolve_token_endpoint(token_endpoint, validation_env)

    if auto_resolve:
        if not civico:
            error_console.print(
                "[red]Error:[/red] --auto-resolve requires --civico to look up "
                "the progr_civico via PA API."
            )
            raise typer.Exit(1)
        consult_sdk = _get_consult_sdk(
            token_endpoint=token_endpoint, verify_ssl=not no_verify_ssl
        )
        progr_civico = _resolve_progr_civico_via_pa(
            consult_sdk, prognaz=prognaz, civico=civico
        )
    elif not progr_civico:
        error_console.print(
            "[red]Error:[/red] --progr-civico is required (or pass --auto-resolve "
            "with --civico)."
        )
        raise typer.Exit(1)

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

    resolved_server = _resolve_server_url(server_url, validation_env)

    if dry_run:
        _run_update_dry_run(
            codcom=codcom,
            progr_nazionale=prognaz,
            new_accesso=accesso,
            token_endpoint=token_endpoint,
            server_url=resolved_server,
            verify_ssl=not no_verify_ssl,
            raw_output=raw_output,
            json_output=json_output,
        )
        return

    _execute_operation(
        operazione_civico="R",
        codcom=codcom,
        progr_nazionale=prognaz,
        accesso=accesso,
        token_endpoint=token_endpoint,
        server_url=resolved_server,
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
        str | None,
        typer.Option(
            "--progr-civico",
            "-P",
            help=(
                "Progressivo civico of the accesso to delete. Required unless "
                "--auto-resolve is used."
            ),
        ),
    ] = None,
    civico: Annotated[
        str | None,
        typer.Option(
            "--civico",
            help="Numero civico — used with --auto-resolve to look up progr_civico.",
        ),
    ] = None,
    auto_resolve: Annotated[
        bool,
        typer.Option(
            "--auto-resolve",
            help=(
                "Resolve progr_civico automatically via PA accesso lookup "
                "(requires --civico). Errors if 0 or >1 matches are found."
            ),
        ),
    ] = False,
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
    dry_run: Annotated[
        bool,
        typer.Option(
            "--dry-run",
            help=(
                "Run delete and immediately re-insert the accesso with its "
                "original data. The re-inserted accesso gets a NEW progr_civico "
                "(ANNCSU assigns it autonomously)."
            ),
        ),
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
    # Resolve token endpoint up-front: --auto-resolve below also uses it
    # (via PA consultation SDK), so it must be the right environment.
    token_endpoint = _resolve_token_endpoint(token_endpoint, validation_env)

    # Resolve progr_civico either explicitly or via PA lookup.
    if auto_resolve:
        if not civico:
            error_console.print(
                "[red]Error:[/red] --auto-resolve requires --civico to look up "
                "the progr_civico via PA API."
            )
            raise typer.Exit(1)
        consult_sdk = _get_consult_sdk(
            token_endpoint=token_endpoint, verify_ssl=not no_verify_ssl
        )
        progr_civico = _resolve_progr_civico_via_pa(
            consult_sdk, prognaz=prognaz, civico=civico
        )
    elif not progr_civico:
        error_console.print(
            "[red]Error:[/red] --progr-civico is required (or pass --auto-resolve "
            "with --civico)."
        )
        raise typer.Exit(1)

    resolved_server = _resolve_server_url(server_url, validation_env)

    if dry_run:
        _run_delete_dry_run(
            codcom=codcom,
            progr_nazionale=prognaz,
            progr_civico=progr_civico,
            data_valid_amm=data_valid_amm,
            token_endpoint=token_endpoint,
            server_url=resolved_server,
            verify_ssl=not no_verify_ssl,
            raw_output=raw_output,
            json_output=json_output,
        )
        return

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
        server_url=resolved_server,
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
    """Check the Accessi API health (GET ``/status``)."""
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
