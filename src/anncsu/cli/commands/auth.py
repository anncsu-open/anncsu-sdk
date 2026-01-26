# SPDX-FileCopyrightText: 2025-present Geobeyond <info@geobeyond.it>
# SPDX-License-Identifier: MIT
"""Auth command group for authentication management."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Annotated

import typer
from rich.console import Console
from rich.table import Table

from anncsu.cli.models import AuthStatus, LoginResult, TokenStatus
from anncsu.common import PDNDAuthManager
from anncsu.common.config import APIType, ClientAssertionSettings
from anncsu.common.session import get_config_dir

# Module-level state for api_type (set by callback)
_current_api_type: APIType | None = None


def _api_type_callback(ctx: typer.Context, value: str) -> str:
    """Callback to validate and store api_type."""
    global _current_api_type
    try:
        _current_api_type = APIType(value)
    except ValueError:
        valid_values = ", ".join(api.value for api in APIType)
        raise typer.BadParameter(
            f"Invalid API type '{value}'. Must be one of: {valid_values}"
        ) from None
    return value


def _get_api_type() -> APIType:
    """Get the current api_type (must be set by callback)."""
    if _current_api_type is None:
        raise typer.BadParameter("--api option is required")
    return _current_api_type


# Build help text with valid API types
_api_help = f"API type for authentication. Valid values: {', '.join(api.value for api in APIType)}"

auth_app = typer.Typer(
    name="auth",
    help="Authentication commands.",
    no_args_is_help=True,
)

console = Console()
error_console = Console(stderr=True)

# Default token endpoint for UAT
DEFAULT_TOKEN_ENDPOINT = "https://auth.uat.interop.pagopa.it/token.oauth2"


def _ttl_to_expires_at(ttl_seconds: int | None) -> datetime | None:
    """Convert TTL in seconds to expiration datetime."""
    if ttl_seconds is None:
        return None
    return datetime.now(timezone.utc) + timedelta(seconds=ttl_seconds)


def _format_ttl(ttl_seconds: int | None) -> str:
    """Format TTL as human-readable string."""
    if ttl_seconds is None:
        return "N/A"
    if ttl_seconds <= 0:
        return "[red]EXPIRED[/red]"

    days, remainder = divmod(ttl_seconds, 86400)
    hours, remainder = divmod(remainder, 3600)
    minutes, seconds = divmod(remainder, 60)

    parts = []
    if days > 0:
        parts.append(f"{days}d")
    if hours > 0:
        parts.append(f"{hours}h")
    if minutes > 0:
        parts.append(f"{minutes}m")
    if seconds > 0 or not parts:
        parts.append(f"{seconds}s")

    return " ".join(parts)


@auth_app.command("login")
def login(
    api: Annotated[
        str,
        typer.Option(
            "--api",
            "-a",
            help=_api_help,
            callback=_api_type_callback,
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
    json_output: Annotated[
        bool,
        typer.Option("--json", help="Output as JSON."),
    ] = False,
) -> None:
    """Authenticate and obtain an access token.

    Creates a client assertion (if needed) and exchanges it for an access token.
    """
    api_type = _get_api_type()

    try:
        settings = ClientAssertionSettings()
    except Exception as e:
        error_console.print(f"[red]Error:[/red] Configuration not found: {e}")
        raise typer.Exit(1) from None

    try:
        manager = PDNDAuthManager(
            settings=settings,
            token_endpoint=token_endpoint,
            api_type=api_type,
            session_persistence=True,
            config_dir=get_config_dir(),
        )
        # Force token retrieval (will save session automatically)
        manager.get_access_token()
    except Exception as e:
        error_console.print(f"[red]Error:[/red] Login failed: {e}")
        raise typer.Exit(1) from None

    # Use TTL methods from PDNDAuthManager
    access_token_ttl = manager.access_token_ttl() or 0
    assertion_ttl = manager.client_assertion_ttl() or 0

    # Calculate expires_at from TTL for display
    access_token_expires_at = _ttl_to_expires_at(access_token_ttl)
    assertion_expires_at = _ttl_to_expires_at(assertion_ttl)

    if json_output:
        result = LoginResult(
            success=True,
            access_token_ttl=access_token_ttl,
            client_assertion_ttl=assertion_ttl,
            message="Login successful",
        )
        console.print(result.model_dump_json(indent=2))
        return

    console.print("[green]Login successful![/green]\n")

    table = Table(show_header=True, header_style="bold")
    table.add_column("Token", style="cyan")
    table.add_column("TTL")
    table.add_column("Expires At")

    table.add_row(
        "Client Assertion",
        _format_ttl(assertion_ttl),
        assertion_expires_at.isoformat() if assertion_expires_at else "N/A",
    )
    table.add_row(
        "Access Token",
        _format_ttl(access_token_ttl),
        access_token_expires_at.isoformat() if access_token_expires_at else "N/A",
    )

    console.print(table)


@auth_app.command("status")
def status(
    api: Annotated[
        str,
        typer.Option(
            "--api",
            "-a",
            help=_api_help,
            callback=_api_type_callback,
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
    json_output: Annotated[
        bool,
        typer.Option("--json", help="Output as JSON."),
    ] = False,
) -> None:
    """Show current authentication status."""
    api_type = _get_api_type()

    try:
        settings = ClientAssertionSettings()
    except Exception as e:
        error_console.print(f"[red]Error:[/red] Configuration not found: {e}")
        raise typer.Exit(1) from None

    try:
        manager = PDNDAuthManager(
            settings=settings,
            token_endpoint=token_endpoint,
            api_type=api_type,
            session_persistence=True,
            config_dir=get_config_dir(),
        )
    except Exception as e:
        error_console.print(f"[red]Error:[/red] Failed to initialize: {e}")
        raise typer.Exit(1) from None

    # Use is_*_expired() methods (inverted logic: not expired = valid)
    has_valid_assertion = not manager.is_client_assertion_expired()
    has_valid_token = not manager.is_access_token_expired()

    # Get TTL values
    assertion_ttl = manager.client_assertion_ttl()
    token_ttl = manager.access_token_ttl()

    # Calculate expires_at from TTL
    assertion_expires_at = _ttl_to_expires_at(assertion_ttl)
    token_expires_at = _ttl_to_expires_at(token_ttl)

    assertion_status = TokenStatus(
        valid=has_valid_assertion,
        expires_at=assertion_expires_at,
        ttl_seconds=assertion_ttl,
    )

    token_status = TokenStatus(
        valid=has_valid_token,
        expires_at=token_expires_at,
        ttl_seconds=token_ttl,
    )

    auth_status = AuthStatus(
        client_assertion=assertion_status,
        access_token=token_status,
        logged_in=has_valid_assertion and has_valid_token,
    )

    if json_output:
        console.print(auth_status.model_dump_json(indent=2))
        return

    if not has_valid_assertion and not has_valid_token:
        console.print(
            "[yellow]Not logged in.[/yellow] Run [cyan]anncsu auth login[/cyan] to authenticate."
        )
        return

    table = Table(title="Authentication Status", show_header=True, header_style="bold")
    table.add_column("Token", style="cyan")
    table.add_column("Status")
    table.add_column("TTL")
    table.add_column("Expires At")

    assertion_status_str = (
        "[green]Valid[/green]" if has_valid_assertion else "[red]Invalid/Expired[/red]"
    )
    token_status_str = (
        "[green]Valid[/green]" if has_valid_token else "[red]Invalid/Expired[/red]"
    )

    table.add_row(
        "Client Assertion",
        assertion_status_str,
        _format_ttl(assertion_status.ttl_seconds),
        assertion_status.expires_at.isoformat()
        if assertion_status.expires_at
        else "N/A",
    )
    table.add_row(
        "Access Token",
        token_status_str,
        _format_ttl(token_status.ttl_seconds),
        token_status.expires_at.isoformat() if token_status.expires_at else "N/A",
    )

    console.print(table)


@auth_app.command("refresh")
def refresh(
    api: Annotated[
        str,
        typer.Option(
            "--api",
            "-a",
            help=_api_help,
            callback=_api_type_callback,
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
    force_assertion: Annotated[
        bool,
        typer.Option(
            "--force-assertion",
            help="Force regeneration of client assertion.",
        ),
    ] = False,
) -> None:
    """Refresh the access token (and optionally the client assertion)."""
    api_type = _get_api_type()

    try:
        settings = ClientAssertionSettings()
    except Exception as e:
        error_console.print(f"[red]Error:[/red] Configuration not found: {e}")
        raise typer.Exit(1) from None

    try:
        manager = PDNDAuthManager(
            settings=settings,
            token_endpoint=token_endpoint,
            api_type=api_type,
            session_persistence=True,
            config_dir=get_config_dir(),
        )

        if force_assertion:
            # Clear cached client assertion to force regeneration
            manager._client_assertion = None
            console.print("[green]Client assertion refreshed.[/green]")

        # Get new access token (will save session automatically)
        manager.get_access_token()
        ttl = manager.access_token_ttl()

        console.print(f"[green]Token refreshed.[/green] TTL: {_format_ttl(ttl)}")

    except Exception as e:
        error_console.print(f"[red]Error:[/red] Refresh failed: {e}")
        raise typer.Exit(1) from None


@auth_app.command("token")
def token(
    api: Annotated[
        str,
        typer.Option(
            "--api",
            "-a",
            help=_api_help,
            callback=_api_type_callback,
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
) -> None:
    """Print the current access token (for piping to other commands).

    Example:
        curl -H "Authorization: Bearer $(anncsu auth token --api pa)" https://api.example.com
    """
    api_type = _get_api_type()

    try:
        settings = ClientAssertionSettings()
    except Exception as e:
        error_console.print(f"[red]Error:[/red] Configuration not found: {e}", err=True)
        raise typer.Exit(1) from None

    try:
        manager = PDNDAuthManager(
            settings=settings,
            token_endpoint=token_endpoint,
            api_type=api_type,
            session_persistence=True,
            config_dir=get_config_dir(),
        )
        access_token = manager.get_access_token()
        # Print only the token, no formatting
        print(access_token)
    except Exception as e:
        error_console.print(f"[red]Error:[/red] Failed to get token: {e}", err=True)
        raise typer.Exit(1) from None


@auth_app.command("logout")
def logout(
    api: Annotated[
        str,
        typer.Option(
            "--api",
            "-a",
            help=_api_help,
            callback=_api_type_callback,
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
) -> None:
    """Clear cached tokens (end session).

    Note: This clears local state only. The tokens may still be valid
    on the server until they expire.
    """
    api_type = _get_api_type()

    try:
        settings = ClientAssertionSettings()
        manager = PDNDAuthManager(
            settings=settings,
            token_endpoint=token_endpoint,
            api_type=api_type,
            session_persistence=True,
            config_dir=get_config_dir(),
        )
        manager.clear_session()
    except Exception:
        # If settings aren't available, just clear session file directly
        from anncsu.common.session import clear_session

        clear_session(api_type=api_type, config_dir=get_config_dir())

    console.print("[green]Logout successful.[/green] Session cleared.")
