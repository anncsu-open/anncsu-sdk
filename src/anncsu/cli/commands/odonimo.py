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
from anncsu.cli.models import (
    OdonimoDryRunResult,
    OdonimoOperationResult,
    OdonimoStatusResult,
)
from anncsu.common import PDNDAuthManager
from anncsu.common.auth import extract_voucher_audience
from anncsu.common.config import APIType, ClientAssertionSettings
from anncsu.common.errors import AudienceMismatchError
from anncsu.common.hooks import SDKHooks, register_modi_hook
from anncsu.common.modi import AuditContext, ModIConfig
from anncsu.common.security import Security as PASecurity
from anncsu.common.session import get_config_dir
from anncsu.odonimi import AnncsuOdonimi
from anncsu.odonimi.models import Security
from anncsu.odonimi.models.richiestaoperazione import (
    AutPrefettura,
    Provvedimento,
    Richiesta,
)
from anncsu.odonimi.models.validated import ValidatedOdonimo
from anncsu.pa import AnncsuConsultazione

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


def _get_consult_sdk(
    token_endpoint: str,
    verify_ssl: bool = True,
) -> AnncsuConsultazione:
    """Build a read-only PA Consultazione SDK for odonimo lookups.

    Used by ``--auto-resolve`` (to resolve progr_nazionale from
    ``codcom`` + ``denom``). Auto-discovers the server URL from the
    voucher audience.
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

    server_url = extract_voucher_audience(access_token)

    def security_provider() -> PASecurity:
        return PASecurity(bearer=manager.get_access_token())

    client = httpx.Client(verify=verify_ssl)
    return AnncsuConsultazione(
        security=security_provider,
        server_url=server_url,
        client=client,
    )


def _resolve_prognaz_via_pa(
    consult_sdk: AnncsuConsultazione,
    *,
    codcom: str,
    denom: str,
) -> str:
    """Resolve ``progr_nazionale`` from ``codcom`` + ``denom`` (base64) via PA API.

    Used by ``--auto-resolve``. Errors out if zero or multiple matches are
    found, since either case is a setup error the user must address.
    """
    try:
        response = consult_sdk.queryparam.elencoodonimiprog_get_query_param(
            codcom=codcom, denom=denom
        )
    except Exception as e:
        error_console.print(f"[red]Error:[/red] PA odonimo lookup failed: {e}")
        raise typer.Exit(1) from None

    matches = list(response.data or [])
    if not matches:
        error_console.print(
            f"[red]Error:[/red] No odonimo found for codcom={codcom} "
            f"denom={denom}. Cannot auto-resolve prognaz."
        )
        raise typer.Exit(1)
    if len(matches) > 1:
        error_console.print(
            f"[red]Error:[/red] Ambiguous lookup: {len(matches)} matches for "
            f"codcom={codcom} denom={denom}. Specify --prognaz explicitly "
            f"to disambiguate."
        )
        raise typer.Exit(1)

    return str(matches[0].prognaz)


def _ensure_prognaz_resolved(
    *,
    prognaz: str | None,
    auto_resolve: bool,
    denom: str | None,
    codcom: str,
    token_endpoint: str,
    verify_ssl: bool,
) -> str:
    """Return the final ``progr_nazionale``: explicit or resolved via PA."""
    if auto_resolve:
        if not denom:
            error_console.print(
                "[red]Error:[/red] --auto-resolve requires --denom "
                "(base64-encoded odonimo denomination)."
            )
            raise typer.Exit(1)
        if prognaz:
            error_console.print(
                "[yellow]Warning:[/yellow] --prognaz is ignored when "
                "--auto-resolve is set."
            )
        consult_sdk = _get_consult_sdk(token_endpoint, verify_ssl)
        return _resolve_prognaz_via_pa(consult_sdk, codcom=codcom, denom=denom)

    if not prognaz:
        error_console.print(
            "[red]Error:[/red] --prognaz is required (or use --auto-resolve "
            "with --denom)."
        )
        raise typer.Exit(1)
    return prognaz


def _generate_fake_denom() -> str:
    """Generate a unique, recognizable fictitious denominazione delibera.

    Format: ``TEST SDK <YYYYMMDDHHMMSS>-<short-uuid>``. Safely under the
    OAS maxLength of 120 chars for ``denom_delibera``. The prefix
    ``TEST SDK`` makes the record easy to identify in audit logs for
    manual cleanup if the cycle crashes.
    """
    import datetime
    import uuid

    ts = datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%d%H%M%S")
    short_uuid = uuid.uuid4().hex[:8]
    return f"TEST SDK {ts}-{short_uuid}"


def _write_pending_log(
    *,
    tipo_operazione: str,
    payload: dict,
    note: str,
) -> str:
    """Write a pending-rollback log file before issuing the rollback call.

    If the CLI crashes between the I step and the rollback S, the user has
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
        "tipo_operazione": tipo_operazione,
        "payload": payload,
        "note": note,
        "pid": os.getpid(),
    }
    pending_path.write_text(json.dumps(record, indent=2, default=str))
    return str(pending_path)


def _extract_progr_nazionale_from_response(response: object) -> str | None:
    """Pull the assigned progr_nazionale from a successful I response.

    ANNCSU returns the assigned value inside ``dati[0].progr_nazionale``.
    Returns None if the response shape is unexpected.
    """
    dati = getattr(response, "dati", None) or []
    if not dati:
        return None
    item = dati[0]
    value = getattr(item, "progr_nazionale", None)
    return str(value) if value else None


def _build_result(response: object, tipo_operazione: str) -> OdonimoOperationResult:
    """Convert a raw SDK response into an OdonimoOperationResult.

    The Odonimi API has an asymmetry between I/R and S responses:

    * I and R always populate ``esito="0"`` on success
    * S omits ``esito`` entirely but populates ``data_FINE`` /
      ``data_fine_valid_amm`` on the returned ``dati`` record as the
      soppressione markers (verified empirically against UAT 2026-05-25)

    For S responses we therefore infer success from the presence of the
    soppression markers when ``esito`` is missing. If ``esito`` is set
    explicitly (any value), it takes precedence — supporting both the
    common case and any future server-side change that aligns S with I/R.
    """
    esito = getattr(response, "esito", None)
    dati = getattr(response, "dati", []) or []

    if esito is not None:
        success = esito == "0"
    elif tipo_operazione == "S" and dati:
        first = dati[0]
        # Pydantic-side ``data_fine`` is aliased to OAS ``data_FINE``.
        success = bool(
            getattr(first, "data_fine", None)
            or getattr(first, "data_fine_valid_amm", None)
        )
    else:
        success = False

    return OdonimoOperationResult(
        success=success,
        tipo_operazione=tipo_operazione,
        id_richiesta=getattr(response, "id_richiesta", None),
        esito=esito,
        messaggio=getattr(response, "messaggio", None),
        dati_count=len(dati),
    )


def _emit_dry_run_result(result: OdonimoDryRunResult, *, json_output: bool) -> None:
    """Render a dry-run result as JSON or a Rich summary table."""
    if json_output:
        print(result.model_dump_json(indent=2))
        if not result.success:
            raise typer.Exit(1)
        return

    if result.success:
        console.print(
            f"[green]Dry-run '{result.tipo_operazione}' succeeded[/green] — "
            "all steps completed cleanly.\n"
        )
    else:
        console.print(
            f"[red]Dry-run '{result.tipo_operazione}' failed[/red]"
            + (f": {result.error_message}\n" if result.error_message else "\n")
        )

    table = Table(show_header=True, header_style="bold")
    table.add_column("Step", style="cyan")
    table.add_column("Outcome")
    table.add_column("Request ID")
    table.add_row(
        "I (fake odonimo)",
        "[green]OK[/green]" if result.test_op.success else "[red]FAIL[/red]",
        result.test_op.id_richiesta or "—",
    )
    if result.update_op is not None:
        table.add_row(
            "R (apply user data)",
            "[green]OK[/green]" if result.update_op.success else "[red]FAIL[/red]",
            result.update_op.id_richiesta or "—",
        )
    if result.rollback is not None:
        rollback_label = (
            "[green]OK[/green]" if result.rollback.success else "[red]FAIL[/red]"
        )
        if result.rollback_failed:
            rollback_label += " — [yellow]MANUAL CLEANUP NEEDED[/yellow]"
        table.add_row(
            "S (cleanup)",
            rollback_label,
            result.rollback.id_richiesta or "—",
        )
    console.print(table)

    if result.fake_prognaz:
        console.print(f"\n[dim]Fake odonimo prognaz:[/dim] {result.fake_prognaz}")
    if result.fake_denom:
        console.print(f"[dim]Fake denomination:[/dim] {result.fake_denom}")
    if result.pending_log_path:
        console.print(f"[dim]Pending log:[/dim] {result.pending_log_path}")

    if not result.success:
        raise typer.Exit(1)


def _run_insert_dry_run(
    *,
    richiesta: Richiesta,
    token_endpoint: str,
    server_url: str,
    verify_ssl: bool,
    raw_output: bool,
    json_output: bool,
) -> None:
    """I (user data) → S (rollback) on the newly created odonimo."""
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

    # Step I (insert)
    try:
        insert_response = sdk.anncsu.gestione_anncsu_odonimi_pdnd(richiesta=richiesta)
    except Exception as e:
        error_console.print(f"[red]Error:[/red] Insert API call failed: {e}")
        raise typer.Exit(1) from None

    if raw_output:
        _print_raw(insert_response, "Raw insert response")

    test_op = _build_result(insert_response, "I")
    fake_prognaz = _extract_progr_nazionale_from_response(insert_response)

    if not test_op.success or not fake_prognaz:
        error_console.print("[red]Insert step failed; no rollback executed.[/red]")
        result = OdonimoDryRunResult(
            success=False,
            tipo_operazione="I",
            fake_denom=str(richiesta.denom_delibera or ""),
            fake_prognaz=None,
            test_op=test_op,
            error_message=(
                "Insert did not return a progr_nazionale — cannot roll back."
                if test_op.success
                else (test_op.messaggio or "Insert failed")
            ),
        )
        _emit_dry_run_result(result, json_output=json_output)
        return

    # Pending log before rollback for crash safety
    pending_log_path = _write_pending_log(
        tipo_operazione="I_then_S",
        payload={
            "codcom": richiesta.codcom,
            "fake_prognaz": fake_prognaz,
            "fake_denom": str(richiesta.denom_delibera or ""),
        },
        note=(
            "Created an odonimo via I; about to delete it via S to roll back. "
            "If the CLI crashed before deletion, run 'anncsu odonimo delete' "
            "manually with the fake_prognaz to clean up."
        ),
    )
    if not json_output:
        console.print(f"[dim]Pending log written to {pending_log_path}[/dim]")

    # Step S (rollback)
    rollback_richiesta = Richiesta(
        codcom=richiesta.codcom,
        tipo_operazione="S",
        progr_nazionale=fake_prognaz,
    )
    rollback_failed = False
    try:
        rollback_response = sdk.anncsu.gestione_anncsu_odonimi_pdnd(
            richiesta=rollback_richiesta
        )
        if raw_output:
            _print_raw(rollback_response, "Raw rollback (S) response")
        rollback = _build_result(rollback_response, "S")
        if not rollback.success:
            rollback_failed = True
    except Exception as e:
        rollback_failed = True
        rollback = OdonimoOperationResult(
            success=False,
            tipo_operazione="S",
            esito=None,
            messaggio=f"Rollback exception: {e}",
        )

    result = OdonimoDryRunResult(
        success=test_op.success and not rollback_failed,
        tipo_operazione="I",
        fake_denom=str(richiesta.denom_delibera or ""),
        fake_prognaz=fake_prognaz,
        test_op=test_op,
        rollback=rollback,
        rollback_failed=rollback_failed,
        pending_log_path=pending_log_path,
    )
    _emit_dry_run_result(result, json_output=json_output)


def _run_update_dry_run(
    *,
    codcom: str,
    user_richiesta: Richiesta,
    token_endpoint: str,
    server_url: str,
    verify_ssl: bool,
    raw_output: bool,
    json_output: bool,
) -> None:
    """I (fake denom) → R (user data on fake) → S (cleanup).

    The user's ``Richiesta`` contains the R payload (what they want to test).
    We construct a fictitious I first, then re-apply the user's R on the
    fake odonimo, then delete it.
    """
    sdk, _ = _get_sdk(
        token_endpoint=token_endpoint,
        server_url=server_url,
        verify_ssl=verify_ssl,
        modi_audience=server_url,
    )

    # Step I: insert a fake odonimo with a generated denom_delibera.
    fake_denom = _generate_fake_denom()
    insert_richiesta = Richiesta(
        codcom=codcom,
        tipo_operazione="I",
        dug="VIA",
        denom_delibera=fake_denom,
    )
    try:
        ValidatedOdonimo.model_validate(insert_richiesta.model_dump(exclude_unset=True))
    except Exception as e:
        error_console.print(f"[red]Validation error (fake I):[/red] {e}")
        raise typer.Exit(1) from None

    try:
        insert_response = sdk.anncsu.gestione_anncsu_odonimi_pdnd(
            richiesta=insert_richiesta
        )
    except Exception as e:
        error_console.print(f"[red]Error:[/red] Fake insert API call failed: {e}")
        raise typer.Exit(1) from None

    if raw_output:
        _print_raw(insert_response, "Raw insert response")

    test_op = _build_result(insert_response, "I")
    fake_prognaz = _extract_progr_nazionale_from_response(insert_response)

    if not test_op.success or not fake_prognaz:
        result = OdonimoDryRunResult(
            success=False,
            tipo_operazione="R",
            fake_denom=fake_denom,
            test_op=test_op,
            error_message=(
                "Fake insert did not return a progr_nazionale — cannot proceed."
                if test_op.success
                else (test_op.messaggio or "Fake insert failed")
            ),
        )
        _emit_dry_run_result(result, json_output=json_output)
        return

    # Step R: apply user's payload on the fake odonimo.
    user_dump = user_richiesta.model_dump(exclude_unset=True)
    user_dump["codcom"] = codcom
    user_dump["tipo_operazione"] = "R"
    user_dump["progr_nazionale"] = fake_prognaz
    update_richiesta = Richiesta.model_validate(user_dump)

    try:
        ValidatedOdonimo.model_validate(update_richiesta.model_dump(exclude_unset=True))
    except Exception as e:
        error_console.print(f"[red]Validation error (user R):[/red] {e}")
        # Still try to roll back the fake odonimo we just created.
        _emergency_cleanup(sdk, codcom=codcom, fake_prognaz=fake_prognaz)
        raise typer.Exit(1) from None

    pending_log_path = _write_pending_log(
        tipo_operazione="I_then_R_then_S",
        payload={
            "codcom": codcom,
            "fake_prognaz": fake_prognaz,
            "fake_denom": fake_denom,
        },
        note=(
            "Created a fake odonimo via I; will run R then S. If the CLI "
            "crashed before deletion, delete fake_prognaz manually."
        ),
    )
    if not json_output:
        console.print(f"[dim]Pending log written to {pending_log_path}[/dim]")

    update_op: OdonimoOperationResult
    try:
        update_response = sdk.anncsu.gestione_anncsu_odonimi_pdnd(
            richiesta=update_richiesta
        )
        if raw_output:
            _print_raw(update_response, "Raw update (R) response")
        update_op = _build_result(update_response, "R")
    except Exception as e:
        update_op = OdonimoOperationResult(
            success=False,
            tipo_operazione="R",
            esito=None,
            messaggio=f"Update exception: {e}",
        )

    # Step S: cleanup the fake odonimo (always attempted).
    rollback_failed = False
    rollback_richiesta = Richiesta(
        codcom=codcom,
        tipo_operazione="S",
        progr_nazionale=fake_prognaz,
    )
    try:
        rollback_response = sdk.anncsu.gestione_anncsu_odonimi_pdnd(
            richiesta=rollback_richiesta
        )
        if raw_output:
            _print_raw(rollback_response, "Raw rollback (S) response")
        rollback = _build_result(rollback_response, "S")
        if not rollback.success:
            rollback_failed = True
    except Exception as e:
        rollback_failed = True
        rollback = OdonimoOperationResult(
            success=False,
            tipo_operazione="S",
            esito=None,
            messaggio=f"Rollback exception: {e}",
        )

    result = OdonimoDryRunResult(
        success=(test_op.success and update_op.success and not rollback_failed),
        tipo_operazione="R",
        fake_denom=fake_denom,
        fake_prognaz=fake_prognaz,
        test_op=test_op,
        update_op=update_op,
        rollback=rollback,
        rollback_failed=rollback_failed,
        pending_log_path=pending_log_path,
    )
    _emit_dry_run_result(result, json_output=json_output)


def _run_delete_dry_run(
    *,
    codcom: str,
    token_endpoint: str,
    server_url: str,
    verify_ssl: bool,
    raw_output: bool,
    json_output: bool,
) -> None:
    """I (fake denom) → S (immediate). Smoke-test of the S flow."""
    sdk, _ = _get_sdk(
        token_endpoint=token_endpoint,
        server_url=server_url,
        verify_ssl=verify_ssl,
        modi_audience=server_url,
    )

    fake_denom = _generate_fake_denom()
    insert_richiesta = Richiesta(
        codcom=codcom,
        tipo_operazione="I",
        dug="VIA",
        denom_delibera=fake_denom,
    )
    try:
        ValidatedOdonimo.model_validate(insert_richiesta.model_dump(exclude_unset=True))
    except Exception as e:
        error_console.print(f"[red]Validation error (fake I):[/red] {e}")
        raise typer.Exit(1) from None

    try:
        insert_response = sdk.anncsu.gestione_anncsu_odonimi_pdnd(
            richiesta=insert_richiesta
        )
    except Exception as e:
        error_console.print(f"[red]Error:[/red] Fake insert API call failed: {e}")
        raise typer.Exit(1) from None

    if raw_output:
        _print_raw(insert_response, "Raw insert response")

    test_op = _build_result(insert_response, "I")
    fake_prognaz = _extract_progr_nazionale_from_response(insert_response)

    if not test_op.success or not fake_prognaz:
        result = OdonimoDryRunResult(
            success=False,
            tipo_operazione="S",
            fake_denom=fake_denom,
            test_op=test_op,
            error_message=(
                "Fake insert did not return a progr_nazionale — cannot proceed."
                if test_op.success
                else (test_op.messaggio or "Fake insert failed")
            ),
        )
        _emit_dry_run_result(result, json_output=json_output)
        return

    pending_log_path = _write_pending_log(
        tipo_operazione="I_then_S",
        payload={
            "codcom": codcom,
            "fake_prognaz": fake_prognaz,
            "fake_denom": fake_denom,
        },
        note=(
            "Created a fake odonimo via I; about to delete via S. If the "
            "CLI crashed before deletion, delete fake_prognaz manually."
        ),
    )
    if not json_output:
        console.print(f"[dim]Pending log written to {pending_log_path}[/dim]")

    rollback_richiesta = Richiesta(
        codcom=codcom,
        tipo_operazione="S",
        progr_nazionale=fake_prognaz,
    )
    rollback_failed = False
    try:
        rollback_response = sdk.anncsu.gestione_anncsu_odonimi_pdnd(
            richiesta=rollback_richiesta
        )
        if raw_output:
            _print_raw(rollback_response, "Raw rollback (S) response")
        rollback = _build_result(rollback_response, "S")
        if not rollback.success:
            rollback_failed = True
    except Exception as e:
        rollback_failed = True
        rollback = OdonimoOperationResult(
            success=False,
            tipo_operazione="S",
            esito=None,
            messaggio=f"Delete exception: {e}",
        )

    result = OdonimoDryRunResult(
        success=test_op.success and not rollback_failed,
        tipo_operazione="S",
        fake_denom=fake_denom,
        fake_prognaz=fake_prognaz,
        test_op=test_op,
        rollback=rollback,
        rollback_failed=rollback_failed,
        pending_log_path=pending_log_path,
    )
    _emit_dry_run_result(result, json_output=json_output)


def _emergency_cleanup(sdk: AnncsuOdonimi, *, codcom: str, fake_prognaz: str) -> None:
    """Best-effort cleanup of a fake odonimo when later steps fail.

    Errors are swallowed — this is the last-ditch attempt before raising
    to the user; the pending log already contains all data needed for
    manual cleanup.
    """
    try:
        cleanup_richiesta = Richiesta(
            codcom=codcom,
            tipo_operazione="S",
            progr_nazionale=fake_prognaz,
        )
        sdk.anncsu.gestione_anncsu_odonimi_pdnd(richiesta=cleanup_richiesta)
    except Exception:
        pass


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

    # UAT odonimi endpoint is slow — raise httpx timeout to 30s (default is 5s)
    # so the client doesn't disconnect before the server finishes the I/R/S
    # operation.
    client = httpx.Client(verify=verify_ssl, timeout=httpx.Timeout(30.0))

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

    # UAT odonimi endpoint is slow — raise SDK timeout to 30s to avoid
    # client-side timeouts that leave orphaned dry-run records (server
    # commits but client never sees the response).
    sdk = AnncsuOdonimi(
        security=security_provider,
        server_url=server_url,
        client=client,
        hooks=hooks,
        timeout_ms=30000,
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
    dry_run: Annotated[
        bool,
        typer.Option(
            "--dry-run",
            help=(
                "Insert then immediately delete the new odonimo (S rollback). "
                "A pending log is written to ~/.anncsu/dryrun_pending.json "
                "before the rollback so a crash leaves a manual-recovery trail."
            ),
        ),
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

    if dry_run:
        _run_insert_dry_run(
            richiesta=richiesta,
            token_endpoint=token_endpoint,
            server_url=resolved_url,
            verify_ssl=not no_verify_ssl,
            raw_output=raw_output,
            json_output=json_output,
        )
        return

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
    dug: Annotated[
        str,
        typer.Option(
            "--dug",
            help="DUG (e.g. 'VIA', 'PIAZZA'). Required for I/R.",
        ),
    ],
    prognaz: Annotated[
        str | None,
        typer.Option(
            "--prognaz",
            "-p",
            help=(
                "Progressivo nazionale dell'odonimo. Required unless "
                "--auto-resolve + --denom are used."
            ),
        ),
    ] = None,
    auto_resolve: Annotated[
        bool,
        typer.Option(
            "--auto-resolve",
            help=(
                "Resolve --prognaz via PA consultation from --codcom + "
                "--denom. Errors out if zero or multiple matches."
            ),
        ),
    ] = False,
    denom: Annotated[
        str | None,
        typer.Option(
            "--denom",
            help=(
                "Base64-encoded odonimo denomination (used by "
                "--auto-resolve to resolve prognaz)."
            ),
        ),
    ] = None,
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
    dry_run: Annotated[
        bool,
        typer.Option(
            "--dry-run",
            help=(
                "Run the R against a fictitious odonimo: I (fake denom) → R "
                "(user data on fake) → S (cleanup). ``--prognaz`` and "
                "``--auto-resolve`` are ignored in dry-run mode."
            ),
        ),
    ] = False,
) -> None:
    """Update/replace an existing odonimo (``tipo_operazione='R'``)."""
    token_endpoint = _resolve_token_endpoint(token_endpoint, validation_env)
    resolved_url = _resolve_server_url(server_url, validation_env)

    if dry_run:
        if prognaz or auto_resolve:
            error_console.print(
                "[yellow]Warning:[/yellow] --prognaz/--auto-resolve are "
                "ignored in --dry-run mode (a fictitious odonimo is generated)."
            )
        user_richiesta = _build_richiesta(
            codcom=codcom,
            tipo_operazione="R",
            progr_nazionale=None,  # populated by dry-run helper after fake I
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
        _run_update_dry_run(
            codcom=codcom,
            user_richiesta=user_richiesta,
            token_endpoint=token_endpoint,
            server_url=resolved_url,
            verify_ssl=not no_verify_ssl,
            raw_output=raw_output,
            json_output=json_output,
        )
        return

    prognaz_final = _ensure_prognaz_resolved(
        prognaz=prognaz,
        auto_resolve=auto_resolve,
        denom=denom,
        codcom=codcom,
        token_endpoint=token_endpoint,
        verify_ssl=not no_verify_ssl,
    )

    richiesta = _build_richiesta(
        codcom=codcom,
        tipo_operazione="R",
        progr_nazionale=prognaz_final,
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
        str | None,
        typer.Option(
            "--prognaz",
            "-p",
            help=(
                "Progressivo nazionale dell'odonimo. Required unless "
                "--auto-resolve + --denom are used."
            ),
        ),
    ] = None,
    auto_resolve: Annotated[
        bool,
        typer.Option(
            "--auto-resolve",
            help=(
                "Resolve --prognaz via PA consultation from --codcom + "
                "--denom. Errors out if zero or multiple matches."
            ),
        ),
    ] = False,
    denom: Annotated[
        str | None,
        typer.Option(
            "--denom",
            help=(
                "Base64-encoded odonimo denomination (used by "
                "--auto-resolve to resolve prognaz)."
            ),
        ),
    ] = None,
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
    dry_run: Annotated[
        bool,
        typer.Option(
            "--dry-run",
            help=(
                "Smoke-test the S flow: I (fake denom) → S (immediate). "
                "``--prognaz`` and ``--auto-resolve`` are ignored in dry-run."
            ),
        ),
    ] = False,
) -> None:
    """Delete (soppressione) an odonimo (``tipo_operazione='S'``).

    Only the identifying fields and ``--data-valid-amm`` are accepted —
    Typer rejects any other CLI flag at parse time, mirroring the OAS
    constraint that ``dug``/``denom-*``/etc. are forbidden for S.
    """
    token_endpoint = _resolve_token_endpoint(token_endpoint, validation_env)
    resolved_url = _resolve_server_url(server_url, validation_env)

    if dry_run:
        if prognaz or auto_resolve:
            error_console.print(
                "[yellow]Warning:[/yellow] --prognaz/--auto-resolve are "
                "ignored in --dry-run mode (a fictitious odonimo is generated "
                "and deleted)."
            )
        _run_delete_dry_run(
            codcom=codcom,
            token_endpoint=token_endpoint,
            server_url=resolved_url,
            verify_ssl=not no_verify_ssl,
            raw_output=raw_output,
            json_output=json_output,
        )
        return

    prognaz_final = _ensure_prognaz_resolved(
        prognaz=prognaz,
        auto_resolve=auto_resolve,
        denom=denom,
        codcom=codcom,
        token_endpoint=token_endpoint,
        verify_ssl=not no_verify_ssl,
    )

    richiesta = _build_richiesta(
        codcom=codcom,
        tipo_operazione="S",
        progr_nazionale=prognaz_final,
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
