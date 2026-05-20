# SPDX-FileCopyrightText: 2025-present Geobeyond <info@geobeyond.it>
# SPDX-License-Identifier: MIT
"""Shared constants and helpers for CLI commands."""

from __future__ import annotations

import typer
from rich.console import Console

# PDND token endpoints
UAT_TOKEN_ENDPOINT = "https://auth.uat.interop.pagopa.it/token.oauth2"
PROD_TOKEN_ENDPOINT = "https://auth.interop.pagopa.it/token.oauth2"

# Backward-compatible alias used by callers that imported the old name.
DEFAULT_TOKEN_ENDPOINT = UAT_TOKEN_ENDPOINT

# Default server URLs for coordinate API
# Note: Uses AgenziaEntrate-PDND path and anncsu-aggiornamento-coordinate endpoint
SERVERS = {
    "production": "https://modipa.agenziaentrate.gov.it/govway/rest/in/AgenziaEntrate-PDND/anncsu-aggiornamento-coordinate/v1",
    "validation": "https://modipa-val.agenziaentrate.it/govway/rest/in/AgenziaEntrate-PDND/anncsu-aggiornamento-coordinate/v1",
}


_error_console = Console(stderr=True)


def _is_uat_endpoint(token_endpoint: str) -> bool:
    """True if the endpoint URL points to the UAT PDND environment.

    The UAT host contains the ``.uat.`` segment; production does not.
    """
    return ".uat." in token_endpoint


def _resolve_token_endpoint(token_endpoint: str | None, validation_env: bool) -> str:
    """Resolve the PDND token endpoint based on the environment flag.

    Behavior:

    * If ``token_endpoint`` is ``None`` (user did not pass ``--token-endpoint``),
      return the default for ``validation_env``: UAT when True, production when
      False.
    * If ``token_endpoint`` is set, validate that its environment matches
      ``validation_env``. On mismatch, print an error and raise ``typer.Exit(1)``
      so the user gets an explicit parameter validation error instead of an
      opaque 015-0008 from PDND at runtime.
    """
    if token_endpoint is None:
        return UAT_TOKEN_ENDPOINT if validation_env else PROD_TOKEN_ENDPOINT

    endpoint_is_uat = _is_uat_endpoint(token_endpoint)

    if validation_env and not endpoint_is_uat:
        _error_console.print(
            "[red]Error:[/red] environment mismatch — "
            "--validation was selected but --token-endpoint points to "
            f"a non-UAT host ({token_endpoint}). "
            "Pass --production for the production endpoint, or omit "
            "--token-endpoint to use the UAT default."
        )
        raise typer.Exit(1)

    if not validation_env and endpoint_is_uat:
        _error_console.print(
            "[red]Error:[/red] environment mismatch — "
            "--production was selected but --token-endpoint points to "
            f"the UAT host ({token_endpoint}). "
            "Pass --validation for the UAT endpoint, or omit "
            "--token-endpoint to use the production default."
        )
        raise typer.Exit(1)

    return token_endpoint
