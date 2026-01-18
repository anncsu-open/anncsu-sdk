# SPDX-FileCopyrightText: 2025-present Geobeyond <info@geobeyond.it>
# SPDX-License-Identifier: MIT
"""Config command group for managing PDND configuration."""

from __future__ import annotations

from pathlib import Path
from typing import Annotated

import typer
from rich.console import Console
from rich.table import Table

from anncsu.cli.models import ConfigInfo
from anncsu.common.config import ClientAssertionSettings

config_app = typer.Typer(
    name="config",
    help="Configuration management commands.",
    no_args_is_help=True,
)

console = Console()
error_console = Console(stderr=True)

# Default config directory name
CONFIG_DIR_NAME = ".anncsu"


def get_config_dir() -> Path:
    """Get the ANNCSU configuration directory path.

    Returns ~/.anncsu/ by default. Creates the directory if it doesn't exist.

    Returns:
        Path to the configuration directory.
    """
    config_dir = Path.home() / CONFIG_DIR_NAME
    return config_dir


def get_default_env_path() -> Path:
    """Get the default .env file path.

    Returns:
        Path to ~/.anncsu/.env
    """
    return get_config_dir() / ".env"


# .env template content
ENV_TEMPLATE = """# PDND Configuration for ANNCSU SDK
# See https://github.com/geobeyond/anncsu-sdk for documentation

# Key ID from PDND
PDND_KID=your-key-id

# Client ID (same as issuer and subject)
PDND_ISSUER=your-client-id
PDND_SUBJECT=your-client-id

# Audience - must end with /client-assertion
PDND_AUDIENCE=auth.uat.interop.pagopa.it/client-assertion

# Purpose ID from PDND
PDND_PURPOSE_ID=your-purpose-id

# Path to private key file (or use PDND_PRIVATE_KEY for content)
PDND_KEY_PATH=./private_key.pem

# Optional: Validity period in minutes (default: 43200 = 30 days)
# PDND_VALIDITY_MINUTES=43200
"""


def _mask_value(value: str, visible_chars: int = 8) -> str:
    """Mask a sensitive value, showing only first few characters."""
    if len(value) <= visible_chars:
        return value[:2] + "***"
    return value[:visible_chars] + "..."


def _read_env_file(path: Path) -> dict[str, str]:
    """Read a .env file and return as dictionary."""
    env_vars: dict[str, str] = {}
    if not path.exists():
        return env_vars

    for line in path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if "=" in line:
            key, _, value = line.partition("=")
            env_vars[key.strip()] = value.strip()

    return env_vars


def _write_env_file(path: Path, env_vars: dict[str, str]) -> None:
    """Write environment variables to a .env file."""
    lines = []
    for key, value in env_vars.items():
        lines.append(f"{key}={value}")
    path.write_text("\n".join(lines) + "\n")


@config_app.command("init")
def init(
    output: Annotated[
        Path | None,
        typer.Option(
            "--output",
            "-o",
            help="Output path for .env file. Defaults to ~/.anncsu/.env",
        ),
    ] = None,
    force: Annotated[
        bool,
        typer.Option(
            "--force",
            "-f",
            help="Overwrite existing .env file.",
        ),
    ] = False,
) -> None:
    """Generate a .env template file with PDND configuration variables.

    By default, creates the configuration in ~/.anncsu/.env
    """
    # Use default path if not specified
    if output is None:
        config_dir = get_config_dir()
        # Create config directory if it doesn't exist
        config_dir.mkdir(parents=True, exist_ok=True)
        output = config_dir / ".env"

    if output.exists() and not force:
        error_console.print(
            f"[red]Error:[/red] File '{output}' already exists. Use --force to overwrite."
        )
        raise typer.Exit(1)

    # Ensure parent directory exists for custom paths
    output.parent.mkdir(parents=True, exist_ok=True)

    output.write_text(ENV_TEMPLATE)
    console.print(f"[green]Created[/green] {output}")
    console.print("\nEdit the file with your PDND credentials, then run:")
    console.print("  [cyan]anncsu config validate[/cyan]")


@config_app.command("import")
def import_config(
    source: Annotated[
        Path | None,
        typer.Argument(
            help="Path to .env file to import. Defaults to .env in current directory.",
        ),
    ] = None,
    force: Annotated[
        bool,
        typer.Option(
            "--force",
            "-f",
            help="Overwrite existing configuration.",
        ),
    ] = False,
) -> None:
    """Import an existing .env file into ~/.anncsu/.env

    This copies your existing configuration to the ANNCSU config directory.

    Examples:
        anncsu config import              # Import .env from current directory
        anncsu config import /path/to/.env  # Import from specific path
        anncsu config import --force      # Overwrite existing config
    """
    # Default to .env in current directory
    if source is None:
        source = Path(".env")

    # Check source exists
    if not source.exists():
        error_console.print(f"[red]Error:[/red] Source file not found: {source}")
        raise typer.Exit(1)

    # Get destination
    config_dir = get_config_dir()
    dest = config_dir / ".env"

    # Check if destination exists
    if dest.exists() and not force:
        error_console.print(
            f"[red]Error:[/red] Configuration already exists at {dest}. "
            "Use --force to overwrite."
        )
        raise typer.Exit(1)

    # Create config directory if needed
    config_dir.mkdir(parents=True, exist_ok=True)

    # Copy the file
    import shutil

    shutil.copy2(source, dest)

    console.print(f"[green]Imported[/green] {source} -> {dest}")
    console.print("\nVerify with:")
    console.print("  [cyan]anncsu config show[/cyan]")
    console.print("  [cyan]anncsu config validate[/cyan]")


@config_app.command("show")
def show(
    json_output: Annotated[
        bool,
        typer.Option(
            "--json",
            help="Output as JSON.",
        ),
    ] = False,
) -> None:
    """Show current PDND configuration (with masked secrets)."""
    try:
        settings = ClientAssertionSettings()
    except Exception as e:
        error_console.print(
            f"[red]Error:[/red] Configuration not found or invalid: {e}"
        )
        raise typer.Exit(1) from None

    key_exists = settings.key_path.exists() if settings.key_path else False

    config_info = ConfigInfo(
        kid=_mask_value(settings.kid),
        issuer=_mask_value(settings.issuer),
        subject=_mask_value(settings.subject),
        audience=settings.audience,
        purpose_id=_mask_value(settings.purpose_id),
        key_path=str(settings.key_path) if settings.key_path else "Not set",
        key_exists=key_exists,
        validity_minutes=settings.validity_minutes,
    )

    if json_output:
        console.print(config_info.model_dump_json(indent=2))
        return

    table = Table(title="PDND Configuration", show_header=False)
    table.add_column("Setting", style="cyan")
    table.add_column("Value")

    table.add_row("KID", config_info.kid)
    table.add_row("Issuer", config_info.issuer)
    table.add_row("Subject", config_info.subject)
    table.add_row("Audience", config_info.audience)
    table.add_row("Purpose ID", config_info.purpose_id)
    table.add_row(
        "Key Path",
        f"{config_info.key_path} {'[green]OK[/green]' if key_exists else '[red]NOT FOUND[/red]'}",
    )
    table.add_row(
        "Validity",
        f"{config_info.validity_minutes} minutes ({config_info.validity_minutes // 1440} days)",
    )

    console.print(table)


@config_app.command("validate")
def validate() -> None:
    """Validate the current PDND configuration."""
    errors: list[str] = []
    warnings: list[str] = []

    try:
        settings = ClientAssertionSettings()
    except Exception as e:
        error_console.print(f"[red]Error:[/red] Failed to load configuration: {e}")
        raise typer.Exit(1) from None

    # Check key file exists
    if settings.key_path:
        if not settings.key_path.exists():
            errors.append(f"Private key file not found: {settings.key_path}")
        else:
            # Try to read the key
            try:
                key_content = settings.key_path.read_text()
                if "PRIVATE KEY" not in key_content:
                    errors.append("Key file does not appear to be a valid private key")
            except Exception as e:
                errors.append(f"Cannot read key file: {e}")
    elif not settings.private_key:
        errors.append("No private key configured (PDND_KEY_PATH or PDND_PRIVATE_KEY)")

    # Check audience format
    if not settings.audience.endswith("/client-assertion"):
        warnings.append(
            f"Audience should end with '/client-assertion', got: {settings.audience}"
        )

    # Check required fields are not placeholder values
    if settings.kid == "your-key-id":
        errors.append("PDND_KID has placeholder value - please set your actual key ID")
    if settings.issuer == "your-client-id":
        errors.append(
            "PDND_ISSUER has placeholder value - please set your actual client ID"
        )

    # Report results
    if errors:
        error_console.print("[red]Validation failed:[/red]\n")
        for error in errors:
            error_console.print(f"  [red]x[/red] {error}")
        if warnings:
            console.print("\n[yellow]Warnings:[/yellow]")
            for warning in warnings:
                console.print(f"  [yellow]![/yellow] {warning}")
        raise typer.Exit(1)

    if warnings:
        console.print("[yellow]Warnings:[/yellow]")
        for warning in warnings:
            console.print(f"  [yellow]![/yellow] {warning}")
        console.print()

    console.print("[green]Configuration is valid![/green]")


@config_app.command("set")
def set_config(
    kid: Annotated[
        str | None,
        typer.Option("--kid", help="Set PDND_KID value."),
    ] = None,
    issuer: Annotated[
        str | None,
        typer.Option("--issuer", help="Set PDND_ISSUER value."),
    ] = None,
    subject: Annotated[
        str | None,
        typer.Option("--subject", help="Set PDND_SUBJECT value."),
    ] = None,
    audience: Annotated[
        str | None,
        typer.Option("--audience", help="Set PDND_AUDIENCE value."),
    ] = None,
    purpose_id: Annotated[
        str | None,
        typer.Option("--purpose-id", help="Set PDND_PURPOSE_ID value."),
    ] = None,
    key_path: Annotated[
        str | None,
        typer.Option("--key-path", help="Set PDND_KEY_PATH value."),
    ] = None,
    env_file: Annotated[
        Path | None,
        typer.Option(
            "--env-file", help="Path to .env file. Defaults to ~/.anncsu/.env"
        ),
    ] = None,
) -> None:
    """Set configuration values in the .env file.

    By default, updates ~/.anncsu/.env
    """
    # Use default path if not specified
    if env_file is None:
        config_dir = get_config_dir()
        # Create config directory if it doesn't exist
        config_dir.mkdir(parents=True, exist_ok=True)
        env_file = config_dir / ".env"

    # Read existing values or create empty dict
    env_vars = _read_env_file(env_file)

    # Update with provided values
    updates = {
        "PDND_KID": kid,
        "PDND_ISSUER": issuer,
        "PDND_SUBJECT": subject,
        "PDND_AUDIENCE": audience,
        "PDND_PURPOSE_ID": purpose_id,
        "PDND_KEY_PATH": key_path,
    }

    updated_count = 0
    for key, value in updates.items():
        if value is not None:
            env_vars[key] = value
            updated_count += 1

    if updated_count == 0:
        error_console.print("[yellow]No values provided to set.[/yellow]")
        raise typer.Exit(1)

    _write_env_file(env_file, env_vars)
    console.print(f"[green]Updated {updated_count} value(s) in {env_file}[/green]")
