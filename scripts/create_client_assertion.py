"""
Create a client assertion JWT for PDND authentication.

This script provides a CLI interface to generate signed JWT client assertions
required for PDND (Piattaforma Digitale Nazionale Dati) authentication.
It uses the core module from anncsu.common.pdnd_assertion.

The CLI supports loading default values from environment variables (PDND_* prefix)
or a .env file. CLI parameters override environment variable values.

Usage:
    # With all parameters from CLI:
    python create_client_assertion.py create \
        --kid <key_id> \
        --issuer <client_id> \
        --subject <client_id> \
        --audience <audience_url> \
        --purpose-id <purpose_id> \
        --key-path <path_to_private_key>

    # With defaults from .env file (CLI params override):
    python create_client_assertion.py create --purpose-id <new_purpose_id>

    # Using only environment variables:
    python create_client_assertion.py create --from-env

Environment Variables (prefix: PDND_):
    PDND_KID            - Key ID (kid) header parameter
    PDND_ISSUER         - Issuer (iss) claim
    PDND_SUBJECT        - Subject (sub) claim
    PDND_AUDIENCE       - Audience (aud) claim
    PDND_PURPOSE_ID     - Purpose ID for the request
    PDND_KEY_PATH       - Path to private key file
    PDND_PRIVATE_KEY    - Private key content (alternative to PDND_KEY_PATH)
    PDND_ALG            - Algorithm (default: RS256)
    PDND_TYP            - Token type (default: JWT)
    PDND_VALIDITY_MINUTES - Validity in minutes (default: 43200)

Requirements:
    - Python 3.12+
    - anncsu-sdk (with authlib>=1.3.0)
    - typer>=0.15.0
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Annotated

import typer
from pydantic import ValidationError
from rich.console import Console

from anncsu.common.config import ClientAssertionSettings
from anncsu.common.pdnd_assertion import (
    ClientAssertionConfig,
    ClientAssertionError,
    create_client_assertion,
)

# Initialize Typer app and Rich console
app = typer.Typer(
    help="Generate client assertion JWTs for PDND authentication",
    no_args_is_help=True,
)
console = Console()


def _load_env_settings() -> ClientAssertionSettings | None:
    """Try to load settings from environment variables.

    Returns:
        ClientAssertionSettings if all required environment variables are set, None otherwise.
    """
    try:
        return ClientAssertionSettings()
    except ValidationError:
        return None


def _get_env_var(name: str) -> str | None:
    """Get an individual environment variable with PDND_ prefix.

    Args:
        name: Variable name without prefix (e.g., 'KID' for PDND_KID).

    Returns:
        The value if set, None otherwise.
    """
    return os.environ.get(f"PDND_{name}")


@app.command()
def create(
    kid: Annotated[
        str | None,
        typer.Option(
            "--kid",
            help="Key ID (kid) header parameter - identifies which key was used. Overrides PDND_KID env var.",
            show_default=False,
            metavar="KEY_ID",
            rich_help_panel="JWT Header Parameters",
        ),
    ] = None,
    issuer: Annotated[
        str | None,
        typer.Option(
            "--issuer",
            help="Issuer (iss) - typically your client_id from PDND. Overrides PDND_ISSUER env var.",
            show_default=False,
            metavar="CLIENT_ID",
            rich_help_panel="JWT Claims",
        ),
    ] = None,
    subject: Annotated[
        str | None,
        typer.Option(
            "--subject",
            help="Subject (sub) - typically your client_id from PDND. Overrides PDND_SUBJECT env var.",
            show_default=False,
            metavar="CLIENT_ID",
            rich_help_panel="JWT Claims",
        ),
    ] = None,
    audience: Annotated[
        str | None,
        typer.Option(
            "--audience",
            help="Audience (aud) - the PDND token endpoint URL. Overrides PDND_AUDIENCE env var.",
            show_default=False,
            metavar="URL",
            rich_help_panel="JWT Claims",
        ),
    ] = None,
    purpose_id: Annotated[
        str | None,
        typer.Option(
            "--purpose-id",
            help="Purpose ID for the PDND request. Overrides PDND_PURPOSE_ID env var.",
            show_default=False,
            metavar="PURPOSE_ID",
            rich_help_panel="JWT Claims",
        ),
    ] = None,
    key_path: Annotated[
        Path | None,
        typer.Option(
            "--key-path",
            help="Path to the RSA private key file (PEM format). Overrides PDND_KEY_PATH env var.",
            exists=True,
            file_okay=True,
            dir_okay=False,
            readable=True,
            show_default=False,
            metavar="PATH",
            rich_help_panel="JWT Signing",
        ),
    ] = None,
    alg: Annotated[
        str | None,
        typer.Option(
            "--alg",
            help="Algorithm for signing the JWT (only RS256 supported). Overrides PDND_ALG env var.",
            metavar="ALGORITHM",
            rich_help_panel="Optional JWT Parameters",
        ),
    ] = None,
    typ: Annotated[
        str | None,
        typer.Option(
            "--typ",
            help="Token type (should be JWT). Overrides PDND_TYP env var.",
            metavar="TYPE",
            rich_help_panel="Optional JWT Parameters",
        ),
    ] = None,
    validity_minutes: Annotated[
        int | None,
        typer.Option(
            "--validity-minutes",
            help="JWT validity period in minutes (max 43200). Overrides PDND_VALIDITY_MINUTES env var.",
            min=1,
            max=43200,
            metavar="MINUTES",
            rich_help_panel="Optional JWT Parameters",
        ),
    ] = None,
    from_env: Annotated[
        bool,
        typer.Option(
            "--from-env",
            help="Use only environment variables (no CLI overrides required)",
            rich_help_panel="Environment Options",
        ),
    ] = False,
    clear_screen: Annotated[
        bool,
        typer.Option(
            "--clear/--no-clear",
            help="Clear the terminal screen before output",
            rich_help_panel="Display Options",
        ),
    ] = True,
) -> None:
    """
    Generate a client assertion JWT for PDND authentication.

    This command creates a signed JWT token that can be used for PDND
    (Piattaforma Digitale Nazionale Dati) authentication.

    Values can be provided via CLI options or environment variables (PDND_* prefix).
    CLI options always override environment variable values.

    Examples:

        # All parameters from CLI:
        python create_client_assertion.py create \\
            --kid "my-key-id" \\
            --issuer "my-client-id" \\
            --subject "my-client-id" \\
            --audience "https://auth.interop.pagopa.it/token.oauth2" \\
            --purpose-id "my-purpose-id" \\
            --key-path ./private_key.pem

        # Using .env file with CLI override for purpose_id:
        python create_client_assertion.py create --purpose-id "new-purpose-id"

        # Using only environment variables:
        python create_client_assertion.py create --from-env
    """
    try:
        # Try to load settings from environment
        env_settings = _load_env_settings()

        # If --from-env is used, require env settings to be available
        if from_env:
            if env_settings is None:
                console.print(
                    "[red]Error: --from-env specified but required environment "
                    "variables are not set.[/red]"
                )
                console.print(
                    "[yellow]Required: PDND_KID, PDND_ISSUER, PDND_SUBJECT, "
                    "PDND_AUDIENCE, PDND_PURPOSE_ID, and either PDND_KEY_PATH "
                    "or PDND_PRIVATE_KEY[/yellow]"
                )
                raise typer.Exit(code=1)
            config = env_settings.to_config()
        else:
            # Merge CLI options with environment defaults
            # CLI options override environment values

            # Determine final values (CLI > env_settings > individual env vars > None)
            # This allows partial env var configuration with CLI completion
            final_kid = (
                kid
                if kid is not None
                else (env_settings.kid if env_settings else _get_env_var("KID"))
            )
            final_issuer = (
                issuer
                if issuer is not None
                else (env_settings.issuer if env_settings else _get_env_var("ISSUER"))
            )
            final_subject = (
                subject
                if subject is not None
                else (env_settings.subject if env_settings else _get_env_var("SUBJECT"))
            )
            final_audience = (
                audience
                if audience is not None
                else (
                    env_settings.audience if env_settings else _get_env_var("AUDIENCE")
                )
            )
            final_purpose_id = (
                purpose_id
                if purpose_id is not None
                else (
                    env_settings.purpose_id
                    if env_settings
                    else _get_env_var("PURPOSE_ID")
                )
            )
            final_alg = (
                alg
                if alg is not None
                else (
                    env_settings.alg
                    if env_settings
                    else (_get_env_var("ALG") or "RS256")
                )
            )
            final_typ = (
                typ
                if typ is not None
                else (
                    env_settings.typ if env_settings else (_get_env_var("TYP") or "JWT")
                )
            )
            env_validity = _get_env_var("VALIDITY_MINUTES")
            final_validity = (
                validity_minutes
                if validity_minutes is not None
                else (
                    env_settings.validity_minutes
                    if env_settings
                    else (int(env_validity) if env_validity else 43200)
                )
            )

            # Handle key_path / private_key
            final_key_path = key_path
            final_private_key: bytes | None = None

            if key_path is None:
                if env_settings:
                    if env_settings.key_path:
                        final_key_path = Path(env_settings.key_path)
                    elif env_settings.private_key:
                        final_private_key = env_settings.private_key.encode("utf-8")
                else:
                    # Try individual env vars
                    env_key_path = _get_env_var("KEY_PATH")
                    env_private_key = _get_env_var("PRIVATE_KEY")
                    if env_key_path:
                        final_key_path = Path(env_key_path)
                    elif env_private_key:
                        final_private_key = env_private_key.encode("utf-8")

            # Validate required fields
            missing_fields = []
            if not final_kid:
                missing_fields.append("--kid or PDND_KID")
            if not final_issuer:
                missing_fields.append("--issuer or PDND_ISSUER")
            if not final_subject:
                missing_fields.append("--subject or PDND_SUBJECT")
            if not final_audience:
                missing_fields.append("--audience or PDND_AUDIENCE")
            if not final_purpose_id:
                missing_fields.append("--purpose-id or PDND_PURPOSE_ID")
            if not final_key_path and not final_private_key:
                missing_fields.append("--key-path or PDND_KEY_PATH/PDND_PRIVATE_KEY")

            if missing_fields:
                console.print("[red]Error: Missing required parameters:[/red]")
                for field in missing_fields:
                    console.print(f"  [yellow]- {field}[/yellow]")
                raise typer.Exit(code=1)

            # Create configuration
            config_kwargs: dict = {
                "kid": final_kid,
                "alg": final_alg,
                "typ": final_typ,
                "issuer": final_issuer,
                "subject": final_subject,
                "audience": final_audience,
                "purpose_id": final_purpose_id,
                "validity_minutes": final_validity,
            }

            if final_key_path:
                config_kwargs["key_path"] = final_key_path
            else:
                config_kwargs["private_key"] = final_private_key

            config = ClientAssertionConfig(**config_kwargs)

        # Generate JWT using the core module
        token = create_client_assertion(config)

        # Clear screen if requested
        if clear_screen:
            os.system("clear")

        # Output the token (use print instead of console.print to avoid word-wrapping)
        print(token)

    except ClientAssertionError as e:
        console.print(f"[red]Error: {e}[/red]")
        raise typer.Exit(code=1) from None
    except ValidationError as e:
        console.print(f"[red]Validation error: {e}[/red]")
        raise typer.Exit(code=1) from None
    except Exception as e:
        console.print(f"[red]Unexpected error: {e}[/red]")
        raise typer.Exit(code=1) from None


if __name__ == "__main__":
    app()
