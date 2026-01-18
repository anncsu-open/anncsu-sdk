# SPDX-FileCopyrightText: 2025-present Geobeyond <info@geobeyond.it>
# SPDX-License-Identifier: MIT
"""Tests for auth CLI commands."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING
from unittest.mock import MagicMock, patch

# Note: datetime is still needed for Pydantic model definitions
from pydantic import BaseModel

if TYPE_CHECKING:
    from typer.testing import CliRunner


# Pydantic models for auth status output
class TokenStatus(BaseModel):
    """Token status information."""

    valid: bool
    expires_at: datetime | None = None
    ttl_seconds: int | None = None


class AuthStatus(BaseModel):
    """Authentication status response."""

    client_assertion: TokenStatus
    access_token: TokenStatus
    logged_in: bool


class LoginResult(BaseModel):
    """Login command result."""

    success: bool
    access_token_ttl: int
    client_assertion_ttl: int
    message: str | None = None


class TestAuthLogin:
    """Tests for auth login command."""

    def test_login_success(
        self, cli_runner: CliRunner, tmp_path: Path, mock_private_key: Path
    ) -> None:
        """Test that auth login succeeds with valid config."""
        from anncsu.cli import app

        with cli_runner.isolated_filesystem(temp_dir=tmp_path):
            Path("private_key.pem").write_text(mock_private_key.read_text())

            with patch(
                "anncsu.cli.commands.auth.ClientAssertionSettings"
            ) as mock_settings:
                settings = MagicMock()
                settings.kid = "test-key-id"
                settings.issuer = "test-client-id"
                mock_settings.return_value = settings

                with patch("anncsu.cli.commands.auth.PDNDAuthManager") as mock_manager:
                    manager = MagicMock()
                    manager.get_access_token.return_value = "mock-access-token"
                    # Use TTL methods instead of expires_at attributes
                    manager.access_token_ttl.return_value = 600  # 10 minutes
                    manager.client_assertion_ttl.return_value = 2592000  # 30 days
                    mock_manager.return_value = manager

                    result = cli_runner.invoke(app, ["auth", "login"])

            assert result.exit_code == 0
            output_lower = result.output.lower()
            assert (
                "success" in output_lower
                or "login" in output_lower
                or "token" in output_lower
            )

    def test_login_shows_token_info(
        self, cli_runner: CliRunner, tmp_path: Path, mock_private_key: Path
    ) -> None:
        """Test that auth login shows token expiration info."""
        from anncsu.cli import app

        with cli_runner.isolated_filesystem(temp_dir=tmp_path):
            Path("private_key.pem").write_text(mock_private_key.read_text())

            with patch(
                "anncsu.cli.commands.auth.ClientAssertionSettings"
            ) as mock_settings:
                settings = MagicMock()
                mock_settings.return_value = settings

                with patch("anncsu.cli.commands.auth.PDNDAuthManager") as mock_manager:
                    manager = MagicMock()
                    manager.get_access_token.return_value = "mock-access-token"
                    # Use TTL methods instead of expires_at attributes
                    manager.access_token_ttl.return_value = 600  # 10 minutes
                    manager.client_assertion_ttl.return_value = 2505600  # 29 days
                    mock_manager.return_value = manager

                    result = cli_runner.invoke(app, ["auth", "login"])

            assert result.exit_code == 0
            # Should show expiration/TTL info
            output_lower = result.output.lower()
            assert (
                "expire" in output_lower
                or "ttl" in output_lower
                or "second" in output_lower
                or "minute" in output_lower
                or "day" in output_lower
            )

    def test_login_custom_token_endpoint(
        self, cli_runner: CliRunner, tmp_path: Path, mock_private_key: Path
    ) -> None:
        """Test that auth login accepts custom token endpoint."""
        from anncsu.cli import app

        with cli_runner.isolated_filesystem(temp_dir=tmp_path):
            Path("private_key.pem").write_text(mock_private_key.read_text())

            with patch(
                "anncsu.cli.commands.auth.ClientAssertionSettings"
            ) as mock_settings:
                settings = MagicMock()
                mock_settings.return_value = settings

                with patch("anncsu.cli.commands.auth.PDNDAuthManager") as mock_manager:
                    manager = MagicMock()
                    manager.get_access_token.return_value = "mock-access-token"
                    # Use TTL methods instead of expires_at attributes
                    manager.access_token_ttl.return_value = 600  # 10 minutes
                    manager.client_assertion_ttl.return_value = 2592000  # 30 days
                    mock_manager.return_value = manager

                    result = cli_runner.invoke(
                        app,
                        [
                            "auth",
                            "login",
                            "--token-endpoint",
                            "https://custom.endpoint/token",
                        ],
                    )

            assert result.exit_code == 0
            # Verify the custom endpoint was passed
            mock_manager.assert_called_once()
            call_kwargs = mock_manager.call_args[1]
            assert call_kwargs.get("token_endpoint") == "https://custom.endpoint/token"

    def test_login_error_no_config(self, cli_runner: CliRunner, tmp_path: Path) -> None:
        """Test that auth login fails gracefully without config."""
        from anncsu.cli import app

        with cli_runner.isolated_filesystem(temp_dir=tmp_path):
            with patch(
                "anncsu.cli.commands.auth.ClientAssertionSettings",
                side_effect=Exception("No configuration found"),
            ):
                result = cli_runner.invoke(app, ["auth", "login"])

            assert result.exit_code == 1
            assert "error" in result.output.lower()

    def test_login_error_token_request_failed(
        self, cli_runner: CliRunner, tmp_path: Path, mock_private_key: Path
    ) -> None:
        """Test that auth login handles token request failure."""
        from anncsu.cli import app

        with cli_runner.isolated_filesystem(temp_dir=tmp_path):
            Path("private_key.pem").write_text(mock_private_key.read_text())

            with patch(
                "anncsu.cli.commands.auth.ClientAssertionSettings"
            ) as mock_settings:
                settings = MagicMock()
                mock_settings.return_value = settings

                with patch("anncsu.cli.commands.auth.PDNDAuthManager") as mock_manager:
                    manager = MagicMock()
                    manager.get_access_token.side_effect = Exception(
                        "Token request failed"
                    )
                    mock_manager.return_value = manager

                    result = cli_runner.invoke(app, ["auth", "login"])

            assert result.exit_code == 1
            assert "error" in result.output.lower() or "failed" in result.output.lower()

    def test_login_json_output(
        self, cli_runner: CliRunner, tmp_path: Path, mock_private_key: Path
    ) -> None:
        """Test that auth login can output JSON (Pydantic model)."""
        from anncsu.cli import app

        with cli_runner.isolated_filesystem(temp_dir=tmp_path):
            Path("private_key.pem").write_text(mock_private_key.read_text())

            with patch(
                "anncsu.cli.commands.auth.ClientAssertionSettings"
            ) as mock_settings:
                settings = MagicMock()
                mock_settings.return_value = settings

                with patch("anncsu.cli.commands.auth.PDNDAuthManager") as mock_manager:
                    manager = MagicMock()
                    manager.get_access_token.return_value = "mock-access-token"
                    # Use TTL methods instead of expires_at attributes
                    manager.access_token_ttl.return_value = 600  # 10 minutes
                    manager.client_assertion_ttl.return_value = 2592000  # 30 days
                    mock_manager.return_value = manager

                    result = cli_runner.invoke(app, ["auth", "login", "--json"])

            assert result.exit_code == 0
            # Should be valid JSON parseable as Pydantic model
            login_result = LoginResult.model_validate_json(result.output)
            assert login_result.success is True
            assert login_result.access_token_ttl > 0


class TestAuthStatus:
    """Tests for auth status command."""

    def test_status_shows_token_info(
        self, cli_runner: CliRunner, tmp_path: Path
    ) -> None:
        """Test that auth status shows current token status."""
        from anncsu.cli import app

        with cli_runner.isolated_filesystem(temp_dir=tmp_path):
            with patch(
                "anncsu.cli.commands.auth.ClientAssertionSettings"
            ) as mock_settings:
                settings = MagicMock()
                mock_settings.return_value = settings

                with patch("anncsu.cli.commands.auth.PDNDAuthManager") as mock_manager:
                    manager = MagicMock()
                    # Use is_*_expired() methods (False = valid)
                    manager.is_access_token_expired.return_value = False
                    manager.is_client_assertion_expired.return_value = False
                    # Use TTL methods
                    manager.access_token_ttl.return_value = 300  # 5 minutes
                    manager.client_assertion_ttl.return_value = 1296000  # 15 days
                    mock_manager.return_value = manager

                    result = cli_runner.invoke(app, ["auth", "status"])

            assert result.exit_code == 0
            output_lower = result.output.lower()
            # Should show status information
            assert (
                "token" in output_lower
                or "assertion" in output_lower
                or "valid" in output_lower
                or "expire" in output_lower
            )

    def test_status_shows_expired_token(
        self, cli_runner: CliRunner, tmp_path: Path
    ) -> None:
        """Test that auth status shows when token is expired."""
        from anncsu.cli import app

        with cli_runner.isolated_filesystem(temp_dir=tmp_path):
            with patch(
                "anncsu.cli.commands.auth.ClientAssertionSettings"
            ) as mock_settings:
                settings = MagicMock()
                mock_settings.return_value = settings

                with patch("anncsu.cli.commands.auth.PDNDAuthManager") as mock_manager:
                    manager = MagicMock()
                    # Use is_*_expired() methods (True = expired/invalid)
                    manager.is_access_token_expired.return_value = True
                    manager.is_client_assertion_expired.return_value = False
                    # Use TTL methods (negative or 0 = expired)
                    manager.access_token_ttl.return_value = 0  # expired
                    manager.client_assertion_ttl.return_value = 1296000  # 15 days
                    mock_manager.return_value = manager

                    result = cli_runner.invoke(app, ["auth", "status"])

            assert result.exit_code == 0
            output_lower = result.output.lower()
            assert (
                "expired" in output_lower
                or "invalid" in output_lower
                or "no" in output_lower
            )

    def test_status_no_token(self, cli_runner: CliRunner, tmp_path: Path) -> None:
        """Test that auth status handles no active session."""
        from anncsu.cli import app

        with cli_runner.isolated_filesystem(temp_dir=tmp_path):
            with patch(
                "anncsu.cli.commands.auth.ClientAssertionSettings"
            ) as mock_settings:
                settings = MagicMock()
                mock_settings.return_value = settings

                with patch("anncsu.cli.commands.auth.PDNDAuthManager") as mock_manager:
                    manager = MagicMock()
                    # Use is_*_expired() methods (True = no token/expired)
                    manager.is_access_token_expired.return_value = True
                    manager.is_client_assertion_expired.return_value = True
                    # Use TTL methods (None = no token cached)
                    manager.access_token_ttl.return_value = None
                    manager.client_assertion_ttl.return_value = None
                    mock_manager.return_value = manager

                    result = cli_runner.invoke(app, ["auth", "status"])

            assert result.exit_code == 0
            output_lower = result.output.lower()
            assert (
                "no" in output_lower or "not" in output_lower or "login" in output_lower
            )

    def test_status_json_output(self, cli_runner: CliRunner, tmp_path: Path) -> None:
        """Test that auth status can output JSON (Pydantic model)."""
        from anncsu.cli import app

        with cli_runner.isolated_filesystem(temp_dir=tmp_path):
            with patch(
                "anncsu.cli.commands.auth.ClientAssertionSettings"
            ) as mock_settings:
                settings = MagicMock()
                mock_settings.return_value = settings

                with patch("anncsu.cli.commands.auth.PDNDAuthManager") as mock_manager:
                    manager = MagicMock()
                    # Use is_*_expired() methods (False = valid)
                    manager.is_access_token_expired.return_value = False
                    manager.is_client_assertion_expired.return_value = False
                    # Use TTL methods
                    manager.access_token_ttl.return_value = 300  # 5 minutes
                    manager.client_assertion_ttl.return_value = 1296000  # 15 days
                    mock_manager.return_value = manager

                    result = cli_runner.invoke(app, ["auth", "status", "--json"])

            assert result.exit_code == 0
            # Should be valid JSON parseable as Pydantic model
            status = AuthStatus.model_validate_json(result.output)
            assert status.logged_in is True
            assert status.access_token.valid is True


class TestAuthRefresh:
    """Tests for auth refresh command."""

    def test_refresh_success(
        self, cli_runner: CliRunner, tmp_path: Path, mock_private_key: Path
    ) -> None:
        """Test that auth refresh obtains new token."""
        from anncsu.cli import app

        with cli_runner.isolated_filesystem(temp_dir=tmp_path):
            Path("private_key.pem").write_text(mock_private_key.read_text())

            with patch(
                "anncsu.cli.commands.auth.ClientAssertionSettings"
            ) as mock_settings:
                settings = MagicMock()
                mock_settings.return_value = settings

                with patch("anncsu.cli.commands.auth.PDNDAuthManager") as mock_manager:
                    manager = MagicMock()
                    manager.get_access_token.return_value = "new-access-token"
                    # Use TTL method instead of expires_at attribute
                    manager.access_token_ttl.return_value = 600  # 10 minutes
                    mock_manager.return_value = manager

                    result = cli_runner.invoke(app, ["auth", "refresh"])

            assert result.exit_code == 0
            output_lower = result.output.lower()
            assert (
                "refresh" in output_lower
                or "success" in output_lower
                or "token" in output_lower
            )

    def test_refresh_force_assertion(
        self, cli_runner: CliRunner, tmp_path: Path, mock_private_key: Path
    ) -> None:
        """Test that auth refresh --force-assertion regenerates assertion."""
        from anncsu.cli import app

        with cli_runner.isolated_filesystem(temp_dir=tmp_path):
            Path("private_key.pem").write_text(mock_private_key.read_text())

            with patch(
                "anncsu.cli.commands.auth.ClientAssertionSettings"
            ) as mock_settings:
                settings = MagicMock()
                mock_settings.return_value = settings

                with patch("anncsu.cli.commands.auth.PDNDAuthManager") as mock_manager:
                    manager = MagicMock()
                    manager.get_access_token.return_value = "new-access-token"
                    # Use TTL methods instead of expires_at attributes
                    manager.access_token_ttl.return_value = 600  # 10 minutes
                    manager.client_assertion_ttl.return_value = 2592000  # 30 days
                    # _client_assertion is the internal attribute to clear
                    manager._client_assertion = "old-assertion"
                    mock_manager.return_value = manager

                    result = cli_runner.invoke(
                        app, ["auth", "refresh", "--force-assertion"]
                    )

            assert result.exit_code == 0
            # Should have cleared _client_assertion to force regeneration
            assert manager._client_assertion is None

    def test_refresh_error(
        self, cli_runner: CliRunner, tmp_path: Path, mock_private_key: Path
    ) -> None:
        """Test that auth refresh handles errors gracefully."""
        from anncsu.cli import app

        with cli_runner.isolated_filesystem(temp_dir=tmp_path):
            Path("private_key.pem").write_text(mock_private_key.read_text())

            with patch(
                "anncsu.cli.commands.auth.ClientAssertionSettings"
            ) as mock_settings:
                settings = MagicMock()
                mock_settings.return_value = settings

                with patch("anncsu.cli.commands.auth.PDNDAuthManager") as mock_manager:
                    manager = MagicMock()
                    manager.get_access_token.side_effect = Exception("Refresh failed")
                    mock_manager.return_value = manager

                    result = cli_runner.invoke(app, ["auth", "refresh"])

            assert result.exit_code == 1
            assert "error" in result.output.lower() or "failed" in result.output.lower()


class TestAuthToken:
    """Tests for auth token command."""

    def test_token_outputs_only_token(
        self, cli_runner: CliRunner, tmp_path: Path, mock_private_key: Path
    ) -> None:
        """Test that auth token outputs only the token (for piping)."""
        from anncsu.cli import app

        with cli_runner.isolated_filesystem(temp_dir=tmp_path):
            Path("private_key.pem").write_text(mock_private_key.read_text())

            with patch(
                "anncsu.cli.commands.auth.ClientAssertionSettings"
            ) as mock_settings:
                settings = MagicMock()
                mock_settings.return_value = settings

                with patch("anncsu.cli.commands.auth.PDNDAuthManager") as mock_manager:
                    manager = MagicMock()
                    manager.get_access_token.return_value = (
                        "eyJhbGciOiJSUzI1NiJ9.test.signature"
                    )
                    mock_manager.return_value = manager

                    result = cli_runner.invoke(app, ["auth", "token"])

            assert result.exit_code == 0
            # Output should be just the token, no extra text
            output = result.output.strip()
            assert output == "eyJhbGciOiJSUzI1NiJ9.test.signature"
            # No extra formatting or text
            assert "success" not in output.lower()
            assert "token:" not in output.lower()

    def test_token_no_extra_output(
        self, cli_runner: CliRunner, tmp_path: Path, mock_private_key: Path
    ) -> None:
        """Test that auth token has no decorative output."""
        from anncsu.cli import app

        with cli_runner.isolated_filesystem(temp_dir=tmp_path):
            Path("private_key.pem").write_text(mock_private_key.read_text())

            with patch(
                "anncsu.cli.commands.auth.ClientAssertionSettings"
            ) as mock_settings:
                settings = MagicMock()
                mock_settings.return_value = settings

                with patch("anncsu.cli.commands.auth.PDNDAuthManager") as mock_manager:
                    manager = MagicMock()
                    manager.get_access_token.return_value = "the-token-value"
                    mock_manager.return_value = manager

                    result = cli_runner.invoke(app, ["auth", "token"])

            assert result.exit_code == 0
            # Should be exactly one line
            lines = result.output.strip().split("\n")
            assert len(lines) == 1

    def test_token_error_when_no_token(
        self, cli_runner: CliRunner, tmp_path: Path
    ) -> None:
        """Test that auth token fails when no token available."""
        from anncsu.cli import app

        with cli_runner.isolated_filesystem(temp_dir=tmp_path):
            with patch(
                "anncsu.cli.commands.auth.ClientAssertionSettings"
            ) as mock_settings:
                settings = MagicMock()
                mock_settings.return_value = settings

                with patch("anncsu.cli.commands.auth.PDNDAuthManager") as mock_manager:
                    manager = MagicMock()
                    manager.get_access_token.side_effect = Exception("No token")
                    mock_manager.return_value = manager

                    result = cli_runner.invoke(app, ["auth", "token"])

            assert result.exit_code == 1

    def test_token_for_piping(
        self, cli_runner: CliRunner, tmp_path: Path, mock_private_key: Path
    ) -> None:
        """Test that auth token output works for shell piping."""
        from anncsu.cli import app

        with cli_runner.isolated_filesystem(temp_dir=tmp_path):
            Path("private_key.pem").write_text(mock_private_key.read_text())

            with patch(
                "anncsu.cli.commands.auth.ClientAssertionSettings"
            ) as mock_settings:
                settings = MagicMock()
                mock_settings.return_value = settings

                with patch("anncsu.cli.commands.auth.PDNDAuthManager") as mock_manager:
                    manager = MagicMock()
                    expected_token = "eyJ0eXAiOiJKV1QiLCJhbGciOiJSUzI1NiJ9.payload.sig"
                    manager.get_access_token.return_value = expected_token
                    mock_manager.return_value = manager

                    result = cli_runner.invoke(app, ["auth", "token"])

            assert result.exit_code == 0
            # Token should be usable in curl -H "Authorization: Bearer $(anncsu auth token)"
            token = result.output.strip()
            assert token == expected_token
            assert " " not in token  # No spaces
            assert "\n" not in token.strip()  # Single line


class TestAuthLogout:
    """Tests for auth logout command (optional, clears cached tokens)."""

    def test_logout_clears_tokens(self, cli_runner: CliRunner, tmp_path: Path) -> None:
        """Test that auth logout clears cached tokens."""
        from anncsu.cli import app

        with cli_runner.isolated_filesystem(temp_dir=tmp_path):
            with patch(
                "anncsu.cli.commands.auth.ClientAssertionSettings"
            ) as mock_settings:
                settings = MagicMock()
                mock_settings.return_value = settings

                with patch("anncsu.cli.commands.auth.PDNDAuthManager") as mock_manager:
                    manager = MagicMock()
                    mock_manager.return_value = manager

                    result = cli_runner.invoke(app, ["auth", "logout"])

            assert result.exit_code == 0
            output_lower = result.output.lower()
            assert (
                "logout" in output_lower
                or "cleared" in output_lower
                or "success" in output_lower
            )

    def test_logout_when_not_logged_in(
        self, cli_runner: CliRunner, tmp_path: Path
    ) -> None:
        """Test that auth logout handles case when not logged in."""
        from anncsu.cli import app

        with cli_runner.isolated_filesystem(temp_dir=tmp_path):
            with patch(
                "anncsu.cli.commands.auth.ClientAssertionSettings"
            ) as mock_settings:
                settings = MagicMock()
                mock_settings.return_value = settings

                with patch("anncsu.cli.commands.auth.PDNDAuthManager") as mock_manager:
                    manager = MagicMock()
                    # Use is_*_expired() methods (True = not logged in)
                    manager.is_access_token_expired.return_value = True
                    manager.is_client_assertion_expired.return_value = True
                    mock_manager.return_value = manager

                    result = cli_runner.invoke(app, ["auth", "logout"])

            # Should succeed even if not logged in
            assert result.exit_code == 0
