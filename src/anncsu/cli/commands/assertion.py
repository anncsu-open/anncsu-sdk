# SPDX-FileCopyrightText: 2025-present Geobeyond <info@geobeyond.it>
# SPDX-License-Identifier: MIT
"""Assertion command group for client assertion utilities."""

from __future__ import annotations

import base64
import json
import sys
from datetime import datetime, timezone
from typing import Annotated

import typer
from rich.console import Console
from rich.table import Table

from anncsu.cli.models import AssertionInfo, DecodedJWT, JWTHeader, JWTPayload
from anncsu.common import create_client_assertion
from anncsu.common.config import ClientAssertionSettings

assertion_app = typer.Typer(
    name="assertion",
    help="Client assertion utilities.",
    no_args_is_help=True,
)

console = Console()
error_console = Console(stderr=True)


def decode_jwt(token: str) -> DecodedJWT:
    """Decode a JWT token without verification.

    Args:
        token: The JWT string to decode.

    Returns:
        DecodedJWT with header and payload.

    Raises:
        ValueError: If the token is not a valid JWT format.
    """
    parts = token.strip().split(".")
    if len(parts) != 3:
        raise ValueError(f"Invalid JWT format: expected 3 parts, got {len(parts)}")

    def decode_part(part: str) -> dict:
        # Add padding if needed
        padding = 4 - len(part) % 4
        if padding != 4:
            part += "=" * padding
        try:
            decoded = base64.urlsafe_b64decode(part)
            return json.loads(decoded)
        except Exception as e:
            raise ValueError(f"Failed to decode JWT part: {e}") from e

    header_data = decode_part(parts[0])
    payload_data = decode_part(parts[1])

    # Validate with Pydantic models
    header = JWTHeader.model_validate(header_data)
    payload = JWTPayload.model_validate(payload_data)

    return DecodedJWT(header=header, payload=payload)


@assertion_app.command("create")
def create() -> None:
    """Create a new client assertion JWT.

    The assertion is printed to stdout for easy piping to other commands.
    """
    try:
        settings = ClientAssertionSettings()
        config = settings.to_config()
        assertion = create_client_assertion(config)
        console.print(assertion)
    except Exception as e:
        error_console.print(f"[red]Error:[/red] Failed to create assertion: {e}")
        raise typer.Exit(1) from None


@assertion_app.command("info")
def info(
    json_output: Annotated[
        bool,
        typer.Option("--json", help="Output as JSON."),
    ] = False,
) -> None:
    """Show information about current assertion configuration."""
    try:
        settings = ClientAssertionSettings()
    except Exception as e:
        error_console.print(f"[red]Error:[/red] Configuration not found: {e}")
        raise typer.Exit(1) from None

    assertion_info = AssertionInfo(
        kid=settings.kid,
        issuer=settings.issuer,
        subject=settings.subject,
        audience=settings.audience,
        purpose_id=settings.purpose_id,
        validity_minutes=settings.validity_minutes,
        validity_days=settings.validity_minutes / 1440,
    )

    if json_output:
        console.print(assertion_info.model_dump_json(indent=2))
        return

    table = Table(title="Client Assertion Configuration", show_header=False)
    table.add_column("Field", style="cyan")
    table.add_column("Value")

    table.add_row("KID", assertion_info.kid)
    table.add_row("Issuer (iss)", assertion_info.issuer)
    table.add_row("Subject (sub)", assertion_info.subject)
    table.add_row("Audience (aud)", assertion_info.audience)
    table.add_row("Purpose ID", assertion_info.purpose_id)
    table.add_row(
        "Validity",
        f"{assertion_info.validity_minutes} minutes ({assertion_info.validity_days:.1f} days)",
    )

    console.print(table)


@assertion_app.command("decode")
def decode(
    token: Annotated[
        str | None,
        typer.Argument(help="JWT token to decode. If not provided, reads from stdin."),
    ] = None,
    json_output: Annotated[
        bool,
        typer.Option("--json", help="Output as JSON."),
    ] = False,
) -> None:
    """Decode and display a JWT token (without signature verification)."""
    # Get token from argument or stdin
    if token is None:
        if sys.stdin.isatty():
            error_console.print(
                "[red]Error:[/red] No token provided. Pass as argument or pipe to stdin."
            )
            raise typer.Exit(1)
        token = sys.stdin.read().strip()

    if not token:
        error_console.print("[red]Error:[/red] Empty token provided.")
        raise typer.Exit(1)

    try:
        decoded = decode_jwt(token)
    except ValueError as e:
        error_console.print(f"[red]Error:[/red] Invalid JWT: {e}")
        raise typer.Exit(1) from None

    if json_output:
        console.print(decoded.model_dump_json(indent=2))
        return

    # Display header
    header_table = Table(title="JWT Header", show_header=False)
    header_table.add_column("Field", style="cyan")
    header_table.add_column("Value")

    header_table.add_row("Algorithm (alg)", decoded.header.alg)
    header_table.add_row("Type (typ)", decoded.header.typ)
    if decoded.header.kid:
        header_table.add_row("Key ID (kid)", decoded.header.kid)

    console.print(header_table)
    console.print()

    # Display payload
    payload_table = Table(title="JWT Payload", show_header=False)
    payload_table.add_column("Field", style="cyan")
    payload_table.add_column("Value")

    payload_table.add_row("Issuer (iss)", decoded.payload.iss)
    payload_table.add_row("Subject (sub)", decoded.payload.sub)
    payload_table.add_row("Audience (aud)", decoded.payload.aud)

    # Format timestamps
    iat_dt = datetime.fromtimestamp(decoded.payload.iat, tz=timezone.utc)
    exp_dt = datetime.fromtimestamp(decoded.payload.exp, tz=timezone.utc)

    payload_table.add_row(
        "Issued At (iat)", f"{iat_dt.isoformat()} ({decoded.payload.iat})"
    )
    payload_table.add_row(
        "Expires (exp)", f"{exp_dt.isoformat()} ({decoded.payload.exp})"
    )

    if decoded.payload.jti:
        payload_table.add_row("JWT ID (jti)", decoded.payload.jti)
    if decoded.payload.purposeId:
        payload_table.add_row("Purpose ID", decoded.payload.purposeId)

    # Calculate TTL
    now = datetime.now(timezone.utc)
    ttl_seconds = int((exp_dt - now).total_seconds())
    if ttl_seconds > 0:
        days, remainder = divmod(ttl_seconds, 86400)
        hours, remainder = divmod(remainder, 3600)
        minutes, seconds = divmod(remainder, 60)
        ttl_str = f"{days}d {hours}h {minutes}m {seconds}s"
        payload_table.add_row("TTL", f"[green]{ttl_str}[/green]")
    else:
        payload_table.add_row("TTL", f"[red]EXPIRED ({abs(ttl_seconds)}s ago)[/red]")

    console.print(payload_table)
