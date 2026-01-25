# SPDX-FileCopyrightText: 2025-present Geobeyond <info@geobeyond.it>
# SPDX-License-Identifier: MIT
"""Main CLI application."""

from __future__ import annotations

from importlib.metadata import version
from typing import Annotated

import typer
from rich.console import Console

from anncsu.cli.commands import (
    assertion_app,
    auth_app,
    config_app,
    coordinate_app,
)

# Create main app
app = typer.Typer(
    name="anncsu",
    help="ANNCSU SDK Command Line Interface for PDND authentication management.",
    no_args_is_help=True,
    rich_markup_mode="rich",
)

# Register command groups
app.add_typer(
    auth_app, name="auth", help="Authentication commands (login, status, token)"
)
app.add_typer(config_app, name="config", help="Configuration management")
app.add_typer(assertion_app, name="assertion", help="Client assertion utilities")
app.add_typer(
    coordinate_app,
    name="coordinate",
    help="Coordinate management (update access points)",
)

console = Console()


def get_version() -> str:
    """Get the package version."""
    try:
        return version("anncsu")
    except Exception:
        return "0.0.0-dev"


def version_callback(value: bool) -> None:
    """Show version and exit."""
    if value:
        console.print(f"anncsu version {get_version()}")
        raise typer.Exit()


@app.callback()
def main(
    version: Annotated[
        bool | None,
        typer.Option(
            "--version",
            "-v",
            help="Show version and exit.",
            callback=version_callback,
            is_eager=True,
        ),
    ] = None,
) -> None:
    """ANNCSU SDK - Command Line Interface for PDND authentication.

    Manage PDND credentials, generate client assertions, and obtain access tokens
    for ANNCSU API consumption.

    [bold]Quick Start:[/bold]

        $ anncsu config init      # Create .env template
        $ anncsu auth login       # Authenticate and get token
        $ anncsu auth status      # Check authentication status

    [bold]Documentation:[/bold]

        See https://github.com/geobeyond/anncsu-sdk for full documentation.
    """
    pass


if __name__ == "__main__":
    app()
