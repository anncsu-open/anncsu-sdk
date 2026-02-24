# SPDX-FileCopyrightText: 2025-present Geobeyond <info@geobeyond.it>
# SPDX-License-Identifier: MIT
"""PA consultazione command group for ANNCSU read-only queries."""

from __future__ import annotations

from typing import Annotated

import typer
from rich.console import Console
from rich.table import Table

from anncsu.cli.commands.coordinate import (
    CONSULT_SERVERS,
    DEFAULT_TOKEN_ENDPOINT,
    _get_consult_sdk,
)

pa_app = typer.Typer(
    name="pa",
    help="PA consultazione commands (read-only queries).",
    no_args_is_help=True,
)

console = Console()
error_console = Console(stderr=True)


@pa_app.command("odonimo")
def odonimo(
    codcom: Annotated[
        str,
        typer.Option(
            "--codcom",
            "-c",
            help="Codice Belfiore del comune (e.g. I501 for Scanno).",
        ),
    ],
    denom: Annotated[
        str,
        typer.Option(
            "--denom",
            "-d",
            help="Denominazione anche parziale dell'odonimo - base64 encoded.",
        ),
    ],
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
    """Search streets (odonimi) in a municipality.

    Returns a list of streets matching the partial name, with their
    national progressive code (prognaz), DUG, and official denomination.

    Example:
        anncsu pa odonimo --codcom I501 --denom "VklBIFJPTUE="
        anncsu pa odonimo --codcom I501 --denom "VklBIFJPTUE=" --production
    """
    if server_url is None:
        server_url = (
            CONSULT_SERVERS["validation"]
            if validation_env
            else CONSULT_SERVERS["production"]
        )

    sdk = _get_consult_sdk(
        token_endpoint=token_endpoint,
        server_url=server_url,
        verify_ssl=not no_verify_ssl,
    )

    try:
        response = sdk.queryparam.elencoodonimiprog_get_query_param(
            codcom=codcom,
            denomparz=denom,
        )
    except Exception as e:
        error_console.print(f"[red]Error:[/red] Odonimo search failed: {e}")
        raise typer.Exit(1) from None

    if not response.data:
        error_console.print(
            f"[red]No results:[/red] No odonimo found for codcom={codcom}, denom={denom}"
        )
        raise typer.Exit(1) from None

    if json_output:
        import json

        print(
            json.dumps(
                [item.model_dump() for item in response.data],
                indent=2,
                ensure_ascii=False,
            )
        )
        return

    table = Table(
        title=f"Odonimi - Comune {codcom}",
        show_header=True,
        header_style="bold",
    )
    table.add_column("Prog. Naz.", style="cyan")
    table.add_column("DUG")
    table.add_column("Denominazione Ufficiale")
    table.add_column("Denominazione Locale")
    table.add_column("Lingua 1")
    table.add_column("Lingua 2")

    for item in response.data:
        table.add_row(
            item.prognaz or "",
            item.dug or "",
            item.denomuff or "",
            item.denomloc or "",
            item.denomlingua1 or "",
            item.denomlingua2 or "",
        )

    console.print(table)
    console.print(f"\n[dim]{len(response.data)} result(s) found.[/dim]")


@pa_app.command("accesso")
def accesso(
    prognazacc: Annotated[
        str,
        typer.Option(
            "--prognazacc",
            "-p",
            help="Progressivo nazionale dell'accesso.",
        ),
    ],
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
    enrich: Annotated[
        bool,
        typer.Option(
            "--enrich/--no-enrich",
            help="Enrich with street denomination via additional API call.",
        ),
    ] = False,
) -> None:
    """Lookup access point by national progressive (with coordinates).

    Returns the complete detail: street info, civic number, coordinates,
    and survey method. Use --enrich to fetch the street denomination
    (denomuff) via an additional prognazarea lookup.

    Example:
        anncsu pa accesso --prognazacc 28586543
        anncsu pa accesso --prognazacc 28586543 --enrich
        anncsu pa accesso --prognazacc 28586543 --production --json
    """
    if server_url is None:
        server_url = (
            CONSULT_SERVERS["validation"]
            if validation_env
            else CONSULT_SERVERS["production"]
        )

    sdk = _get_consult_sdk(
        token_endpoint=token_endpoint,
        server_url=server_url,
        verify_ssl=not no_verify_ssl,
    )

    try:
        response = sdk.queryparam.prognazacc_get_query_param(
            prognazacc=prognazacc,
        )
    except Exception as e:
        error_console.print(f"[red]Error:[/red] Access point lookup failed: {e}")
        raise typer.Exit(1) from None

    if not response.data:
        error_console.print(
            f"[red]No results:[/red] No access point found for prognazacc={prognazacc}"
        )
        raise typer.Exit(1) from None

    # Enrich: prognazacc API doesn't return denomuff, fetch it via prognazarea
    if enrich:
        for item in response.data:
            if not item.denomuff and item.prognaz:
                try:
                    area_resp = sdk.queryparam.prognazarea_get_query_param(
                        prognaz=item.prognaz,
                    )
                    if area_resp.data:
                        area = area_resp.data[0]
                        if area.denomuff:
                            item.denomuff = area.denomuff
                        if area.denomloc and not item.denomloc:
                            item.denomloc = area.denomloc
                        if area.denomlingua1 and not item.denomlingua1:
                            item.denomlingua1 = area.denomlingua1
                        if area.denomlingua2 and not item.denomlingua2:
                            item.denomlingua2 = area.denomlingua2
                except Exception as e:
                    error_console.print(
                        f"[yellow]Warning:[/yellow] Enrichment failed for prognaz={item.prognaz}: {e}"
                    )

    if json_output:
        import json

        print(
            json.dumps(
                [item.model_dump(by_alias=True) for item in response.data],
                indent=2,
                ensure_ascii=False,
            )
        )
        return

    for item in response.data:
        console.print(f"\n[bold]Access Point - prognazacc={prognazacc}[/bold]\n")

        table = Table(show_header=True, header_style="bold")
        table.add_column("Field", style="cyan")
        table.add_column("Value")

        table.add_row("Prog. Naz. Odonimo", item.prognaz or "N/A")
        table.add_row("DUG", item.dug or "N/A")
        table.add_row("Denominazione Ufficiale", item.denomuff or "N/A")
        table.add_row("Denominazione Locale", item.denomloc or "N/A")
        table.add_row("Lingua 1", item.denomlingua1 or "N/A")
        table.add_row("Lingua 2", item.denomlingua2 or "N/A")
        table.add_row("Prog. Naz. Accesso", item.prognazacc or "N/A")
        table.add_row("Civico", item.civico or "N/A")
        table.add_row("Esponente", item.esp or "N/A")
        table.add_row("Specificita", item.specif or "N/A")
        table.add_row("Metrico", item.metrico or "N/A")
        table.add_row("Coord X", item.coord_x or "N/A")
        table.add_row("Coord Y", item.coord_y or "N/A")
        table.add_row("Quota", item.quota or "N/A")
        table.add_row("Metodo", item.metodo or "N/A")

        console.print(table)


@pa_app.command("accessi")
def accessi(
    codcom: Annotated[
        str,
        typer.Option(
            "--codcom",
            "-c",
            help="Codice Belfiore del comune (e.g. I501 for Scanno).",
        ),
    ],
    denom: Annotated[
        str,
        typer.Option(
            "--denom",
            "-d",
            help="Denominazione anche parziale dell'odonimo - base64 encoded.",
        ),
    ],
    accparz: Annotated[
        str | None,
        typer.Option(
            "--accparz",
            "-a",
            help="Valore anche parziale del civico (e.g. '1').",
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
    """List access points for a street.

    First searches for the street (odonimo) by municipality code and name,
    then lists all access points (civici) for that street.

    Example:
        anncsu pa accessi --codcom I501 --denom "VklBIFJPTUE="
        anncsu pa accessi --codcom I501 --denom "VklBIFJPTUE=" --accparz "1"
    """
    if server_url is None:
        server_url = (
            CONSULT_SERVERS["validation"]
            if validation_env
            else CONSULT_SERVERS["production"]
        )

    sdk = _get_consult_sdk(
        token_endpoint=token_endpoint,
        server_url=server_url,
        verify_ssl=not no_verify_ssl,
    )

    # Step 1: Find odonimo prognaz
    try:
        odonimo_response = sdk.queryparam.elencoodonimiprog_get_query_param(
            codcom=codcom,
            denomparz=denom,
        )
    except Exception as e:
        error_console.print(f"[red]Error:[/red] Odonimo search failed: {e}")
        raise typer.Exit(1) from None

    if not odonimo_response.data:
        error_console.print(
            f"[red]No results:[/red] No odonimo found for codcom={codcom}, denom={denom}"
        )
        raise typer.Exit(1) from None

    odonimo_data = odonimo_response.data[0]
    prognaz = odonimo_data.prognaz

    if not prognaz:
        error_console.print("[red]Error:[/red] Odonimo found but no prognaz available")
        raise typer.Exit(1) from None

    if not json_output:
        console.print(
            f"[bold]Street:[/bold] {odonimo_data.dug} {odonimo_data.denomuff} "
            f"(prognaz={prognaz})\n"
        )

    # Step 2: List accessi for this odonimo
    search_accparz = accparz if accparz else "1"
    try:
        accessi_response = sdk.queryparam.elencoaccessiprog_get_query_param(
            prognaz=prognaz,
            accparz=search_accparz,
        )
    except Exception as e:
        error_console.print(f"[red]Error:[/red] Access search failed: {e}")
        raise typer.Exit(1) from None

    if not accessi_response.data:
        error_console.print(
            f"[red]No results:[/red] No access points found for prognaz={prognaz}"
        )
        raise typer.Exit(1) from None

    if json_output:
        import json

        print(
            json.dumps(
                {
                    "odonimo": odonimo_data.model_dump(),
                    "accessi": [
                        item.model_dump(by_alias=True) for item in accessi_response.data
                    ],
                },
                indent=2,
                ensure_ascii=False,
            )
        )
        return

    table = Table(
        title=f"Accessi - {odonimo_data.dug} {odonimo_data.denomuff}",
        show_header=True,
        header_style="bold",
    )
    table.add_column("Prog. Naz. Acc.", style="cyan")
    table.add_column("Civico")
    table.add_column("Esp.")
    table.add_column("Specif.")
    table.add_column("Metrico")
    table.add_column("Coord X")
    table.add_column("Coord Y")
    table.add_column("Quota")
    table.add_column("Metodo")

    for item in accessi_response.data:
        table.add_row(
            item.prognazacc or "",
            item.civico or "",
            item.esp or "",
            item.specif or "",
            item.metrico or "",
            item.coord_x or "",
            item.coord_y or "",
            item.quota or "",
            item.metodo or "",
        )

    console.print(table)
    console.print(f"\n[dim]{len(accessi_response.data)} access point(s) found.[/dim]")
