"""
Create a client assertion JWT for PDND authentication.

This script provides a CLI interface to generate signed JWT client assertions
required for PDND (Piattaforma Digitale Nazionale Dati) authentication.
It uses the core module from anncsu.common.pdnd_assertion.

Usage:
    python create_client_assertion.py create \
        --kid <key_id> \
        --issuer <client_id> \
        --subject <client_id> \
        --audience <audience_url> \
        --purpose-id <purpose_id> \
        --key-path <path_to_private_key>

Requirements:
    - Python 3.12+
    - anncsu-sdk (with authlib>=1.3.0)
    - typer>=0.15.0
"""

import os
from pathlib import Path
from typing import Annotated

import typer
from rich.console import Console

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


@app.command()
def create(
    kid: Annotated[
        str,
        typer.Option(
            "--kid",
            help="Key ID (kid) header parameter - identifies which key was used",
            show_default=False,
            metavar="KEY_ID",
            rich_help_panel="Required JWT Header Parameters",
        ),
    ],
    issuer: Annotated[
        str,
        typer.Option(
            "--issuer",
            help="Issuer (iss) - typically your client_id from PDND. Example: 'a1b2c3d4-e5f6-7890-abcd-ef1234567890'",
            show_default=False,
            metavar="CLIENT_ID",
            rich_help_panel="Required JWT Claims",
        ),
    ],
    subject: Annotated[
        str,
        typer.Option(
            "--subject",
            help="Subject (sub) - typically your client_id from PDND. Example: 'a1b2c3d4-e5f6-7890-abcd-ef1234567890'",
            show_default=False,
            metavar="CLIENT_ID",
            rich_help_panel="Required JWT Claims",
        ),
    ],
    audience: Annotated[
        str,
        typer.Option(
            "--audience",
            help="Audience (aud) - the PDND token endpoint URL. Example: 'https://auth.interop.pagopa.it/token.oauth2'",
            show_default=False,
            metavar="URL",
            rich_help_panel="Required JWT Claims",
        ),
    ],
    purpose_id: Annotated[
        str,
        typer.Option(
            "--purpose-id",
            help="Purpose ID for the PDND request. Example: '12345678-90ab-cdef-1234-567890abcdef'",
            show_default=False,
            metavar="PURPOSE_ID",
            rich_help_panel="Required JWT Claims",
        ),
    ],
    key_path: Annotated[
        Path,
        typer.Option(
            "--key-path",
            help="Path to the RSA private key file (PEM format). Example: './private_key.pem'",
            exists=True,
            file_okay=True,
            dir_okay=False,
            readable=True,
            show_default=False,
            metavar="PATH",
            rich_help_panel="Required JWT Signing",
        ),
    ],
    alg: Annotated[
        str,
        typer.Option(
            "--alg",
            help="Algorithm for signing the JWT (only RS256 supported)",
            metavar="ALGORITHM",
            rich_help_panel="Optional JWT Parameters",
        ),
    ] = "RS256",
    typ: Annotated[
        str,
        typer.Option(
            "--typ",
            help="Token type (should be JWT)",
            metavar="TYPE",
            rich_help_panel="Optional JWT Parameters",
        ),
    ] = "JWT",
    validity_minutes: Annotated[
        int,
        typer.Option(
            "--validity-minutes",
            help="JWT validity period in minutes. Examples: 1440 (24 hours), 10080 (7 days), 43200 (30 days max)",
            min=1,
            max=43200,
            metavar="MINUTES",
            rich_help_panel="Optional JWT Parameters",
        ),
    ] = 43200,
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

    Example:

        python create_client_assertion.py create \\
            --kid "my-key-id" \\
            --issuer "my-client-id" \\
            --subject "my-client-id" \\
            --audience "https://auth.interop.pagopa.it/token.oauth2" \\
            --purpose-id "my-purpose-id" \\
            --key-path ./private_key.pem
    """
    try:
        # Create and validate configuration using the core module
        config = ClientAssertionConfig(
            kid=kid,
            alg=alg,
            typ=typ,
            issuer=issuer,
            subject=subject,
            audience=audience,
            purpose_id=purpose_id,
            key_path=key_path,
            validity_minutes=validity_minutes,
        )

        # Generate JWT using the core module
        token = create_client_assertion(config)

        # Clear screen if requested
        if clear_screen:
            os.system("clear")

        # Output the token
        console.print(token)

    except ClientAssertionError as e:
        console.print(f"[red]Error: {e}[/red]")
        raise typer.Exit(code=1) from None
    except ValueError as e:
        console.print(f"[red]Validation error: {e}[/red]")
        raise typer.Exit(code=1) from None
    except Exception as e:
        console.print(f"[red]Unexpected error: {e}[/red]")
        raise typer.Exit(code=1) from None


if __name__ == "__main__":
    app()
