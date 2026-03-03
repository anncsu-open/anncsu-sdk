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


def _print_raw(response: object, label: str = "Raw API response") -> None:
    """Print raw API response to stderr as formatted JSON."""
    import json

    error_console.print(
        f"[dim]{label}:[/dim]\n"
        f"{json.dumps(response.model_dump(), indent=2, default=str)}"
    )


@pa_app.command("odonimo")
def odonimo(
    codcom: Annotated[
        str | None,
        typer.Option(
            "--codcom",
            "-c",
            help="Codice Belfiore del comune (e.g. I501 for Scanno).",
        ),
    ] = None,
    denom: Annotated[
        str | None,
        typer.Option(
            "--denom",
            "-d",
            help="Denominazione anche parziale dell'odonimo - base64 encoded.",
        ),
    ] = None,
    prognaz: Annotated[
        str | None,
        typer.Option(
            "--prognaz",
            "-p",
            help="Progressivo nazionale dell'odonimo (direct lookup).",
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
    """Search streets (odonimi) in a municipality or lookup by national code.

    Use --codcom + --denom to search by municipality and partial name.
    Use --prognaz for direct lookup by national progressive code.

    Example:
        anncsu pa odonimo --codcom I501 --denom "VklBIFJPTUE="
        anncsu pa odonimo --prognaz 907000 --production
    """
    # Validate mutually exclusive options
    if prognaz and (codcom or denom):
        error_console.print(
            "[red]Error:[/red] --prognaz is mutually exclusive with --codcom/--denom"
        )
        raise typer.Exit(1) from None
    if not prognaz and not (codcom and denom):
        error_console.print(
            "[red]Error:[/red] Provide either --prognaz or both --codcom and --denom"
        )
        raise typer.Exit(1) from None

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

    if prognaz:
        # Direct lookup by national progressive code
        try:
            response = sdk.queryparam.prognazarea_get_query_param(
                prognaz=prognaz,
            )
        except Exception as e:
            error_console.print(f"[red]Error:[/red] Odonimo lookup failed: {e}")
            raise typer.Exit(1) from None

        if raw_output:
            _print_raw(response)

        if not response.data:
            error_console.print(
                f"[red]No results:[/red] No odonimo found for prognaz={prognaz}"
            )
            raise typer.Exit(1) from None

        title = f"Odonimo - prognaz={prognaz}"
    else:
        # Search by municipality + partial name
        try:
            response = sdk.queryparam.elencoodonimiprog_get_query_param(
                codcom=codcom,
                denomparz=denom,
            )
        except Exception as e:
            error_console.print(f"[red]Error:[/red] Odonimo search failed: {e}")
            raise typer.Exit(1) from None

        if raw_output:
            _print_raw(response)

        if not response.data:
            error_console.print(
                f"[red]No results:[/red] No odonimo found for codcom={codcom}, denom={denom}"
            )
            raise typer.Exit(1) from None

        title = f"Odonimi - Comune {codcom}"

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
        title=title,
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
    raw_output: Annotated[
        bool,
        typer.Option("--raw", help="Print raw API response to stderr."),
    ] = False,
) -> None:
    """Lookup access point by national progressive (with coordinates).

    Returns the complete detail: street info, civic number, coordinates,
    and survey method.

    Example:
        anncsu pa accesso --prognazacc 28586543
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

    if raw_output:
        _print_raw(response)

    if not response.data:
        error_console.print(
            f"[red]No results:[/red] No access point found for prognazacc={prognazacc}"
        )
        raise typer.Exit(1) from None

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
    raw_output: Annotated[
        bool,
        typer.Option("--raw", help="Print raw API response to stderr."),
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

    if raw_output:
        _print_raw(odonimo_response, "Raw odonimo response")

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

    if raw_output:
        _print_raw(accessi_response, "Raw accessi response")

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
