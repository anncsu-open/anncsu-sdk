# SPDX-FileCopyrightText: 2025-present Geobeyond <info@geobeyond.it>
# SPDX-License-Identifier: MIT
"""Shared constants for CLI commands."""

# Default token endpoint for UAT
DEFAULT_TOKEN_ENDPOINT = "https://auth.uat.interop.pagopa.it/token.oauth2"

# Default server URLs for coordinate API
# Note: Uses AgenziaEntrate-PDND path and anncsu-aggiornamento-coordinate endpoint
SERVERS = {
    "production": "https://modipa.agenziaentrate.gov.it/govway/rest/in/AgenziaEntrate-PDND/anncsu-aggiornamento-coordinate/v1",
    "validation": "https://modipa-val.agenziaentrate.it/govway/rest/in/AgenziaEntrate-PDND/anncsu-aggiornamento-coordinate/v1",
}
