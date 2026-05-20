# SPDX-FileCopyrightText: 2025-present Geobeyond <info@geobeyond.it>
# SPDX-License-Identifier: MIT
"""Auth command group for authentication management."""

from __future__ import annotations

import warnings
from datetime import datetime, timedelta, timezone
from typing import Annotated

import typer
from rich.console import Console
from rich.table import Table

from anncsu.cli.commands.constants import _resolve_token_endpoint
from anncsu.cli.models import AuthStatus, CurlOutput, LoginResult, TokenStatus
from anncsu.common import PDNDAuthManager
from anncsu.common.config import APIType, ClientAssertionSettings
from anncsu.common.session import get_config_dir

# Module-level state for api_type (set by callback)
_current_api_type: APIType | None = None


def _api_type_callback(ctx: typer.Context, value: str | None) -> str | None:
    """Callback to validate and store api_type."""
    global _current_api_type
    if value is None:
        _current_api_type = None
        return value
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


def _show_auth_warnings(caught_warnings: list) -> None:
    """Display captured warnings to the user via stderr.

    Args:
        caught_warnings: List of warnings.WarningMessage from catch_warnings.
    """
    for w in caught_warnings:
        error_console.print(f"[yellow]Warning:[/yellow] {w.message}")


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
        with warnings.catch_warnings(record=True) as caught_warnings:
            warnings.simplefilter("always")
            manager = PDNDAuthManager(
                settings=settings,
                token_endpoint=token_endpoint,
                api_type=api_type,
                session_persistence=True,
                config_dir=get_config_dir(),
            )
        _show_auth_warnings(caught_warnings)

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
        with warnings.catch_warnings(record=True) as caught_warnings:
            warnings.simplefilter("always")
            manager = PDNDAuthManager(
                settings=settings,
                token_endpoint=token_endpoint,
                api_type=api_type,
                session_persistence=True,
                config_dir=get_config_dir(),
            )
        _show_auth_warnings(caught_warnings)
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
        with warnings.catch_warnings(record=True) as caught_warnings:
            warnings.simplefilter("always")
            manager = PDNDAuthManager(
                settings=settings,
                token_endpoint=token_endpoint,
                api_type=api_type,
                session_persistence=True,
                config_dir=get_config_dir(),
            )
        _show_auth_warnings(caught_warnings)

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
        with warnings.catch_warnings(record=True) as caught_warnings:
            warnings.simplefilter("always")
            manager = PDNDAuthManager(
                settings=settings,
                token_endpoint=token_endpoint,
                api_type=api_type,
                session_persistence=True,
                config_dir=get_config_dir(),
            )
        _show_auth_warnings(caught_warnings)
        access_token = manager.get_access_token()
        # Print only the token, no formatting
        print(access_token)
    except Exception as e:
        error_console.print(f"[red]Error:[/red] Failed to get token: {e}", err=True)
        raise typer.Exit(1) from None


# Sample payloads for --api coordinate when --body is not provided
_SAMPLE_COORDINATE_PAYLOAD = {
    "richiesta": {
        "accesso": {
            "codcom": "H501",
            "progr_civico": "12345",
            "coordinate": {
                "x": "12.4922309",
                "y": "41.8902102",
                "metodo": "4",
            },
        }
    }
}

# PA consultazione endpoint definitions: path + required query param names
# Params listed in "base64_params" are auto-encoded from plain text by the CLI
_PA_ENDPOINTS: dict[str, dict] = {
    "esisteodonimo": {
        "path": "esisteodonimo",
        "params": ["codcom", "denom"],
        "base64_params": {"denom"},
        "description": "Verifica esistenza odonimo",
    },
    "esisteaccesso": {
        "path": "esisteaccesso",
        "params": ["codcom", "denom", "accesso"],
        "base64_params": {"denom"},
        "description": "Verifica esistenza accesso",
    },
    "elencoodonimi": {
        "path": "elencoodonimi",
        "params": ["codcom", "denomparz"],
        "base64_params": {"denomparz"},
        "description": "Elenco odonimi",
    },
    "elencoaccessi": {
        "path": "elencoaccessi",
        "params": ["codcom", "denom", "accparz"],
        "base64_params": {"denom"},
        "description": "Elenco accessi",
    },
    "elencoodonimiprog": {
        "path": "elencoodonimiprog",
        "params": ["codcom", "denomparz"],
        "base64_params": {"denomparz"},
        "description": "Elenco odonimi con progressivo nazionale",
    },
    "elencoaccessiprog": {
        "path": "elencoaccessiprog",
        "params": ["prognaz", "accparz"],
        "base64_params": set(),
        "description": "Elenco accessi con progressivo nazionale",
    },
    "prognazarea": {
        "path": "prognazarea",
        "params": ["prognaz"],
        "base64_params": set(),
        "description": "Dati odonimo per progressivo nazionale",
    },
    "prognazacc": {
        "path": "prognazacc",
        "params": ["prognazacc"],
        "base64_params": set(),
        "description": "Dati accesso per progressivo nazionale accesso",
    },
}

_PA_ENDPOINT_NAMES = list(_PA_ENDPOINTS.keys())
_PA_ENDPOINT_HELP = (
    "PA endpoint to query. "
    f"Valid values: {', '.join(_PA_ENDPOINT_NAMES)}. "
    "Default: esisteodonimo"
)


def _build_pa_query_string(
    endpoint_def: dict,
    user_params: dict[str, str | None],
) -> tuple[str, list[str]]:
    """Build query string for a PA endpoint from user-provided params.

    For params in base64_params, the user's plain text value is base64-encoded.
    Returns (query_string, warnings_list).
    """
    import base64
    from urllib.parse import quote

    query_parts: list[str] = []
    query_warnings: list[str] = []
    required_params: list[str] = endpoint_def["params"]
    b64_params: set[str] = endpoint_def["base64_params"]
    missing: list[str] = []

    for param_name in required_params:
        value = user_params.get(param_name)
        if value is None:
            missing.append(param_name)
            continue
        if param_name in b64_params:
            encoded = base64.b64encode(value.encode("utf-8")).decode("utf-8")
            query_parts.append(f"{param_name}={quote(encoded, safe='')}")
            query_warnings.append(f'{param_name}: "{value}" -> base64: {encoded}')
        else:
            query_parts.append(f"{param_name}={quote(value, safe='')}")

    if missing:
        query_warnings.insert(
            0,
            f"Missing params: {', '.join(missing)}. "
            f"Pass them with {' '.join('--' + m for m in missing)}",
        )

    # Warn about params provided but not used by this endpoint
    ignored = [
        p for p, v in user_params.items() if v is not None and p not in required_params
    ]
    if ignored:
        query_warnings.append(
            f"Ignored params (not used by this endpoint): {', '.join('--' + p for p in ignored)}"
        )

    return "&".join(query_parts), query_warnings


@auth_app.command("curl")
def curl_command(
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
    validation_env: Annotated[
        bool,
        typer.Option(
            "--validation/--production",
            help="Use validation (UAT) or production environment.",
        ),
    ] = True,
    body: Annotated[
        str | None,
        typer.Option(
            "--body",
            "-b",
            help="JSON body for POST requests (coordinate API). If omitted, uses a sample payload.",
        ),
    ] = None,
    endpoint: Annotated[
        str | None,
        typer.Option(
            "--endpoint",
            "-p",
            help=_PA_ENDPOINT_HELP,
        ),
    ] = None,
    codcom: Annotated[
        str | None,
        typer.Option("--codcom", help="Codice Belfiore del comune (es. H501)."),
    ] = None,
    denom: Annotated[
        str | None,
        typer.Option(
            "--denom", help="Denominazione esatta dell'odonimo (testo, auto base64)."
        ),
    ] = None,
    denomparz: Annotated[
        str | None,
        typer.Option(
            "--denomparz",
            help="Denominazione parziale dell'odonimo (testo, auto base64).",
        ),
    ] = None,
    accesso: Annotated[
        str | None,
        typer.Option(
            "--accesso", help="Valore civico (+esponente/specificita) o metrico."
        ),
    ] = None,
    accparz: Annotated[
        str | None,
        typer.Option("--accparz", help="Valore parziale del civico o metrico."),
    ] = None,
    prognaz: Annotated[
        str | None,
        typer.Option("--prognaz", help="Progressivo nazionale dell'odonimo."),
    ] = None,
    prognazacc_param: Annotated[
        str | None,
        typer.Option("--prognazacc", help="Progressivo nazionale dell'accesso."),
    ] = None,
    headers_only: Annotated[
        bool,
        typer.Option(
            "--headers-only",
            help="Output only -H flags without the full cURL command.",
        ),
    ] = False,
    json_output: Annotated[
        bool,
        typer.Option("--json", help="Output as structured JSON."),
    ] = False,
) -> None:
    """Generate a complete cURL command with authentication headers.

    For PA (GET) APIs, generates a cURL with Bearer token.
    Use --endpoint to select which PA endpoint (default: esisteodonimo).
    Pass query parameters directly (--codcom, --denom, etc.) to build
    a ready-to-use cURL. Text values for denom/denomparz are auto base64-encoded.

    For Coordinate (POST) APIs, generates a cURL with Bearer token plus
    all ModI headers (Digest, Agid-JWT-Signature, Agid-JWT-TrackingEvidence).

    Examples:
        anncsu auth curl --api pa --codcom H501 --denom "VIA ROMA"
        anncsu auth curl --api pa --endpoint prognazacc --prognazacc 0001234500001
        anncsu auth curl --api pa --endpoint elencoodonimi --codcom H501 --denomparz VIA
        anncsu auth curl --api coordinate
        anncsu auth curl --api coordinate --body '{"richiesta":{...}}'
        anncsu auth curl --api pa --production --codcom I702 --denom "VIA NAPOLI"
    """
    import json

    from anncsu.cli.commands.coordinate import CONSULT_SERVERS, SERVERS

    api_type = _get_api_type()
    env_name = "validation" if validation_env else "production"
    token_endpoint = _resolve_token_endpoint(token_endpoint, validation_env)
    curl_warnings: list[str] = []

    if endpoint is not None and api_type != APIType.PA:
        error_console.print(
            "[yellow]Warning:[/yellow] --endpoint is only used with --api pa, ignoring."
        )

    # 1. Authenticate
    try:
        settings = ClientAssertionSettings()
    except Exception as e:
        error_console.print(f"[red]Error:[/red] Configuration not found: {e}")
        raise typer.Exit(1) from None

    try:
        with warnings.catch_warnings(record=True) as caught_warnings:
            warnings.simplefilter("always")
            manager = PDNDAuthManager(
                settings=settings,
                token_endpoint=token_endpoint,
                api_type=api_type,
                session_persistence=True,
                config_dir=get_config_dir(),
            )
        _show_auth_warnings(caught_warnings)
        access_token = manager.get_access_token()
    except Exception as e:
        error_console.print(f"[red]Error:[/red] Failed to get token: {e}")
        raise typer.Exit(1) from None

    token_ttl = manager.access_token_ttl()

    # 2. Determine server URL, HTTP method, and endpoint path
    if api_type == APIType.PA:
        server_url = CONSULT_SERVERS[env_name]
        http_method = "GET"

        # Select PA endpoint
        pa_endpoint_name = endpoint or "esisteodonimo"
        if pa_endpoint_name not in _PA_ENDPOINTS:
            valid = ", ".join(_PA_ENDPOINT_NAMES)
            error_console.print(
                f"[red]Error:[/red] Unknown PA endpoint '{pa_endpoint_name}'. "
                f"Valid values: {valid}"
            )
            raise typer.Exit(1)

        pa_ep = _PA_ENDPOINTS[pa_endpoint_name]

        # Collect user-provided query params
        user_params: dict[str, str | None] = {
            "codcom": codcom,
            "denom": denom,
            "denomparz": denomparz,
            "accesso": accesso,
            "accparz": accparz,
            "prognaz": prognaz,
            "prognazacc": prognazacc_param,
        }

        query_string, query_warnings = _build_pa_query_string(pa_ep, user_params)
        curl_warnings.extend(query_warnings)

        if query_string:
            endpoint_path = f"{pa_ep['path']}?{query_string}"
        else:
            endpoint_path = pa_ep["path"]
            curl_warnings.append(
                f"No query params provided for {pa_endpoint_name}. "
                f"Required: {', '.join('--' + p for p in pa_ep['params'])}"
            )
        request_body = None
    else:
        # coordinate (and other POST-based APIs)
        server_url = SERVERS[env_name]
        http_method = "POST"
        endpoint_path = "gestionecoordinate"

        if body is not None:
            try:
                # Validate JSON
                parsed_body = json.loads(body)
                request_body = json.dumps(
                    parsed_body, separators=(",", ":"), sort_keys=True
                )
            except json.JSONDecodeError as e:
                error_console.print(f"[red]Error:[/red] Invalid JSON body: {e}")
                raise typer.Exit(1) from None
        else:
            request_body = json.dumps(
                _SAMPLE_COORDINATE_PAYLOAD, separators=(",", ":"), sort_keys=True
            )
            curl_warnings.append(
                "Using sample payload. ModI headers (Digest, Signature) are computed from this body "
                "and will be invalid if the body is changed."
            )

    full_url = f"{server_url}/{endpoint_path}"

    # 3. Build headers
    headers: dict[str, str] = {"Authorization": f"Bearer {access_token}"}

    if api_type != APIType.PA and request_body is not None:
        # Generate ModI headers for POST APIs
        headers["Content-Type"] = "application/json"

        try:
            from anncsu.common.modi import (
                ModIHeaderGenerator,
                create_modi_config_from_settings,
            )

            modi_config = create_modi_config_from_settings(settings, server_url)
            audit_context = (
                settings.get_modi_audit_context()
                if settings.has_modi_audit_context
                else None
            )

            if audit_context is None:
                curl_warnings.append(
                    "ModI audit context not configured (PDND_MODI_USER_ID, PDND_MODI_USER_LOCATION, PDND_MODI_LOA). "
                    "Agid-JWT-TrackingEvidence header will be missing."
                )

            generator = ModIHeaderGenerator(modi_config, audit_context)
            payload_dict = json.loads(request_body)
            modi_headers = generator.generate_headers(payload_dict)
            headers.update(modi_headers)

            curl_warnings.append(
                "ModI headers (Agid-JWT-Signature) valid for ~5 minutes from generation."
            )
        except Exception as e:
            error_console.print(
                f"[yellow]Warning:[/yellow] Could not generate ModI headers: {e}"
            )
            curl_warnings.append(f"ModI header generation failed: {e}")

    # 4. Build output
    header_lines = [f'-H "{k}: {v}"' for k, v in headers.items()]

    if headers_only:
        # Output only -H flags, one per line
        if json_output:
            output = CurlOutput(
                curl_command="\n".join(header_lines),
                headers=headers,
                server_url=full_url,
                method=http_method,
                body=request_body,
                api_type=api_type.value,
                environment=env_name,
                token_ttl=token_ttl,
                warnings=curl_warnings,
            )
            print(output.model_dump_json(indent=2))
        else:
            for w in curl_warnings:
                error_console.print(f"[yellow]Warning:[/yellow] {w}")
            print("\n".join(header_lines))
        return

    # Full cURL command
    parts = [f"curl -X {http_method}"]
    parts.append(f'  "{full_url}"')
    for hl in header_lines:
        parts.append(f"  {hl}")
    if request_body is not None:
        # Escape single quotes in body for shell safety
        escaped_body = request_body.replace("'", "'\\''")
        parts.append(f"  -d '{escaped_body}'")

    curl_cmd = " \\\n".join(parts)

    if json_output:
        output = CurlOutput(
            curl_command=curl_cmd,
            headers=headers,
            server_url=full_url,
            method=http_method,
            body=request_body,
            api_type=api_type.value,
            environment=env_name,
            token_ttl=token_ttl,
            warnings=curl_warnings,
        )
        print(output.model_dump_json(indent=2))
    else:
        for w in curl_warnings:
            error_console.print(f"[yellow]Warning:[/yellow] {w}")
        if token_ttl is not None:
            error_console.print(f"[dim]Token TTL: {_format_ttl(token_ttl)}[/dim]")
        print(curl_cmd)


@auth_app.command("logout")
def logout(
    api: Annotated[
        str | None,
        typer.Option(
            "--api",
            "-a",
            help=_api_help,
            callback=_api_type_callback,
        ),
    ] = None,
    all_sessions: Annotated[
        bool,
        typer.Option(
            "--all",
            help="Clear all session files for every API type.",
        ),
    ] = False,
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

    Use --api to clear a specific API session, or --all to clear all sessions.

    Note: This clears local state only. The tokens may still be valid
    on the server until they expire.
    """
    if all_sessions and api is not None:
        error_console.print("[red]Error:[/red] --all and --api are mutually exclusive.")
        raise typer.Exit(1)

    if not all_sessions and api is None:
        error_console.print("[red]Error:[/red] Either --api or --all is required.")
        raise typer.Exit(1)

    if all_sessions:
        config_dir = get_config_dir()
        if not config_dir.exists():
            console.print("[yellow]No sessions found.[/yellow]")
            return

        session_files = list(config_dir.glob("session_*.json"))
        for sf in session_files:
            sf.unlink()

        count = len(session_files)
        if count == 0:
            console.print("[yellow]No sessions found.[/yellow]")
        else:
            console.print(
                f"[green]Logout successful.[/green] Cleared {count} session(s)."
            )
        return

    api_type = _get_api_type()

    try:
        settings = ClientAssertionSettings()
        with warnings.catch_warnings(record=True) as caught_warnings:
            warnings.simplefilter("always")
            manager = PDNDAuthManager(
                settings=settings,
                token_endpoint=token_endpoint,
                api_type=api_type,
                session_persistence=True,
                config_dir=get_config_dir(),
            )
        _show_auth_warnings(caught_warnings)
        manager.clear_session()
    except Exception:
        # If settings aren't available, just clear session file directly
        from anncsu.common.session import clear_session

        clear_session(api_type=api_type, config_dir=get_config_dir())

    console.print("[green]Logout successful.[/green] Session cleared.")
