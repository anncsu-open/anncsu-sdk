# SPDX-FileCopyrightText: 2025-present Geobeyond <info@geobeyond.it>
# SPDX-License-Identifier: MIT
"""Tests for the ``_resolve_token_endpoint`` helper.

Maps the ``--validation/--production`` flag to the corresponding PDND token
endpoint when the user does not pass ``--token-endpoint`` explicitly, and
validates the match (exit 1 on mismatch) when both are provided.
"""

from __future__ import annotations

import pytest
import typer


UAT = "https://auth.uat.interop.pagopa.it/token.oauth2"
PROD = "https://auth.interop.pagopa.it/token.oauth2"


class TestResolveTokenEndpointDefaults:
    """When ``token_endpoint is None``, pick the default per environment."""

    def test_validation_default_returns_uat(self) -> None:
        from anncsu.cli.commands.constants import _resolve_token_endpoint

        assert _resolve_token_endpoint(None, validation_env=True) == UAT

    def test_production_default_returns_prod(self) -> None:
        from anncsu.cli.commands.constants import _resolve_token_endpoint

        assert _resolve_token_endpoint(None, validation_env=False) == PROD


class TestResolveTokenEndpointExplicitMatch:
    """When the explicit endpoint matches the environment flag, accept it."""

    def test_validation_with_explicit_uat_endpoint_ok(self) -> None:
        from anncsu.cli.commands.constants import _resolve_token_endpoint

        assert _resolve_token_endpoint(UAT, validation_env=True) == UAT

    def test_production_with_explicit_prod_endpoint_ok(self) -> None:
        from anncsu.cli.commands.constants import _resolve_token_endpoint

        assert _resolve_token_endpoint(PROD, validation_env=False) == PROD


class TestResolveTokenEndpointExplicitMismatch:
    """When the explicit endpoint conflicts with the environment flag, exit 1."""

    def test_validation_with_explicit_prod_endpoint_errors(self, capsys) -> None:
        from anncsu.cli.commands.constants import _resolve_token_endpoint

        with pytest.raises(typer.Exit) as exc_info:
            _resolve_token_endpoint(PROD, validation_env=True)
        assert exc_info.value.exit_code == 1
        # Error message must mention both --validation and the production
        # endpoint, so the user can fix the invocation without guessing.
        captured = capsys.readouterr()
        combined = (captured.out + captured.err).lower()
        assert "mismatch" in combined or "conflict" in combined
        assert "--validation" in combined or "validation" in combined

    def test_production_with_explicit_uat_endpoint_errors(self, capsys) -> None:
        from anncsu.cli.commands.constants import _resolve_token_endpoint

        with pytest.raises(typer.Exit) as exc_info:
            _resolve_token_endpoint(UAT, validation_env=False)
        assert exc_info.value.exit_code == 1
        captured = capsys.readouterr()
        combined = (captured.out + captured.err).lower()
        assert "mismatch" in combined or "conflict" in combined
        assert "--production" in combined or "production" in combined
