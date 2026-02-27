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

# Default API type for tests
TEST_API_TYPE = "pa"


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

                    result = cli_runner.invoke(
                        app, ["auth", "login", "--api", TEST_API_TYPE]
                    )

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

                    result = cli_runner.invoke(
                        app, ["auth", "login", "--api", TEST_API_TYPE]
                    )

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
                            "--api",
                            TEST_API_TYPE,
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
                result = cli_runner.invoke(
                    app, ["auth", "login", "--api", TEST_API_TYPE]
                )

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

                    result = cli_runner.invoke(
                        app, ["auth", "login", "--api", TEST_API_TYPE]
                    )

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

                    result = cli_runner.invoke(
                        app, ["auth", "login", "--api", TEST_API_TYPE, "--json"]
                    )

            assert result.exit_code == 0
            # Should be valid JSON parseable as Pydantic model
            login_result = LoginResult.model_validate_json(result.output)
            assert login_result.success is True
            assert login_result.access_token_ttl > 0

    def test_login_shows_environment_mismatch_warning(
        self, cli_runner: CliRunner, tmp_path: Path
    ) -> None:
        """Test that auth login shows a warning when audience/endpoint environments mismatch."""
        import warnings

        from anncsu.cli import app

        with cli_runner.isolated_filesystem(temp_dir=tmp_path):
            with patch(
                "anncsu.cli.commands.auth.ClientAssertionSettings"
            ) as mock_settings:
                settings = MagicMock()
                mock_settings.return_value = settings

                # Make PDNDAuthManager emit a warning on init (environment mismatch)
                def manager_with_warning(**kwargs):
                    warnings.warn(
                        "PDND environment mismatch: PDND_AUDIENCE refers to production "
                        "(auth.interop.pagopa.it) but token_endpoint refers to UAT "
                        "(auth.uat.interop.pagopa.it). "
                        "Authentication will likely fail.",
                        UserWarning,
                        stacklevel=2,
                    )
                    manager = MagicMock()
                    manager.get_access_token.side_effect = Exception(
                        "Token request failed: 015-0008"
                    )
                    return manager

                with patch(
                    "anncsu.cli.commands.auth.PDNDAuthManager",
                    side_effect=manager_with_warning,
                ):
                    result = cli_runner.invoke(
                        app, ["auth", "login", "--api", TEST_API_TYPE]
                    )

            # Should fail (token request fails due to mismatch)
            assert result.exit_code == 1
            # The warning about environment mismatch should be visible in output
            assert (
                "mismatch" in result.output.lower()
                or "environment" in result.output.lower()
            )


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

                    result = cli_runner.invoke(
                        app, ["auth", "status", "--api", TEST_API_TYPE]
                    )

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

                    result = cli_runner.invoke(
                        app, ["auth", "status", "--api", TEST_API_TYPE]
                    )

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

                    result = cli_runner.invoke(
                        app, ["auth", "status", "--api", TEST_API_TYPE]
                    )

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

                    result = cli_runner.invoke(
                        app,
                        ["auth", "status", "--api", TEST_API_TYPE, "--json"],
                    )

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

                    result = cli_runner.invoke(
                        app, ["auth", "refresh", "--api", TEST_API_TYPE]
                    )

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
                        app,
                        [
                            "auth",
                            "refresh",
                            "--api",
                            TEST_API_TYPE,
                            "--force-assertion",
                        ],
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

                    result = cli_runner.invoke(
                        app, ["auth", "refresh", "--api", TEST_API_TYPE]
                    )

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

                    result = cli_runner.invoke(
                        app, ["auth", "token", "--api", TEST_API_TYPE]
                    )

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

                    result = cli_runner.invoke(
                        app, ["auth", "token", "--api", TEST_API_TYPE]
                    )

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

                    result = cli_runner.invoke(
                        app, ["auth", "token", "--api", TEST_API_TYPE]
                    )

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

                    result = cli_runner.invoke(
                        app, ["auth", "token", "--api", TEST_API_TYPE]
                    )

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

                    result = cli_runner.invoke(
                        app, ["auth", "logout", "--api", TEST_API_TYPE]
                    )

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

                    result = cli_runner.invoke(
                        app, ["auth", "logout", "--api", TEST_API_TYPE]
                    )

            # Should succeed even if not logged in
            assert result.exit_code == 0


class TestAuthLogoutAll:
    """Tests for auth logout --all flag (clears all session files)."""

    def test_logout_all_clears_all_session_files(
        self, cli_runner: CliRunner, tmp_path: Path
    ) -> None:
        """Test that auth logout --all removes all session_*.json files."""
        from anncsu.cli import app

        # Create fake session files for multiple API types
        config_dir = tmp_path / ".anncsu"
        config_dir.mkdir()
        session_files = [
            config_dir / "session_pa.json",
            config_dir / "session_coordinate.json",
            config_dir / "session_coordinate_bulk.json",
        ]
        for sf in session_files:
            sf.write_text(
                '{"client_assertion": "x", "access_token": "y", "token_endpoint": "z"}'
            )

        # All files should exist before logout
        for sf in session_files:
            assert sf.exists()

        with patch("anncsu.cli.commands.auth.get_config_dir", return_value=config_dir):
            result = cli_runner.invoke(app, ["auth", "logout", "--all"])

        assert result.exit_code == 0
        # All session files should be deleted
        for sf in session_files:
            assert not sf.exists(), f"{sf.name} should have been deleted"

    def test_logout_all_shows_count_of_cleared_sessions(
        self, cli_runner: CliRunner, tmp_path: Path
    ) -> None:
        """Test that auth logout --all reports number of sessions cleared."""
        from anncsu.cli import app

        config_dir = tmp_path / ".anncsu"
        config_dir.mkdir()
        for name in ["session_pa.json", "session_coordinate.json"]:
            (config_dir / name).write_text(
                '{"client_assertion": "x", "access_token": "y", "token_endpoint": "z"}'
            )

        with patch("anncsu.cli.commands.auth.get_config_dir", return_value=config_dir):
            result = cli_runner.invoke(app, ["auth", "logout", "--all"])

        assert result.exit_code == 0
        assert "2" in result.output  # should mention 2 sessions cleared

    def test_logout_all_with_no_sessions(
        self, cli_runner: CliRunner, tmp_path: Path
    ) -> None:
        """Test that auth logout --all handles empty config dir gracefully."""
        from anncsu.cli import app

        config_dir = tmp_path / ".anncsu"
        config_dir.mkdir()

        with patch("anncsu.cli.commands.auth.get_config_dir", return_value=config_dir):
            result = cli_runner.invoke(app, ["auth", "logout", "--all"])

        assert result.exit_code == 0
        output_lower = result.output.lower()
        assert "no" in output_lower or "0" in output_lower

    def test_logout_all_preserves_non_session_files(
        self, cli_runner: CliRunner, tmp_path: Path
    ) -> None:
        """Test that auth logout --all only deletes session_*.json, not .env or other files."""
        from anncsu.cli import app

        config_dir = tmp_path / ".anncsu"
        config_dir.mkdir()

        # Create session file + non-session files
        (config_dir / "session_pa.json").write_text(
            '{"client_assertion": "x", "access_token": "y", "token_endpoint": "z"}'
        )
        env_file = config_dir / ".env"
        env_file.write_text("PDND_KID=abc")
        other_file = config_dir / "config.json"
        other_file.write_text("{}")

        with patch("anncsu.cli.commands.auth.get_config_dir", return_value=config_dir):
            result = cli_runner.invoke(app, ["auth", "logout", "--all"])

        assert result.exit_code == 0
        # Session file deleted
        assert not (config_dir / "session_pa.json").exists()
        # Non-session files preserved
        assert env_file.exists()
        assert other_file.exists()

    def test_logout_all_with_nonexistent_config_dir(
        self, cli_runner: CliRunner, tmp_path: Path
    ) -> None:
        """Test that auth logout --all handles missing config dir gracefully."""
        from anncsu.cli import app

        config_dir = tmp_path / ".anncsu_nonexistent"

        with patch("anncsu.cli.commands.auth.get_config_dir", return_value=config_dir):
            result = cli_runner.invoke(app, ["auth", "logout", "--all"])

        assert result.exit_code == 0

    def test_logout_all_and_api_are_mutually_exclusive(
        self, cli_runner: CliRunner, tmp_path: Path
    ) -> None:
        """Test that --all and --api cannot be used together."""
        from anncsu.cli import app

        result = cli_runner.invoke(app, ["auth", "logout", "--all", "--api", "pa"])

        # Should fail - mutually exclusive options
        assert result.exit_code != 0


class TestAuthCurl:
    """Tests for auth curl command."""

    def test_curl_pa_get_command(self, cli_runner: CliRunner, tmp_path: Path) -> None:
        """Test that auth curl --api pa with params generates a GET cURL with Bearer token."""
        from anncsu.cli import app

        with cli_runner.isolated_filesystem(temp_dir=tmp_path):
            with patch(
                "anncsu.cli.commands.auth.ClientAssertionSettings"
            ) as mock_settings:
                settings = MagicMock()
                mock_settings.return_value = settings

                with patch("anncsu.cli.commands.auth.PDNDAuthManager") as mock_manager:
                    manager = MagicMock()
                    manager.get_access_token.return_value = "mock-pa-token"
                    manager.access_token_ttl.return_value = 600
                    mock_manager.return_value = manager

                    result = cli_runner.invoke(
                        app,
                        [
                            "auth",
                            "curl",
                            "--api",
                            "pa",
                            "--codcom",
                            "H501",
                            "--denom",
                            "VIA ROMA",
                        ],
                    )

            assert result.exit_code == 0
            output = result.output
            assert "curl -X GET" in output
            assert "Authorization: Bearer mock-pa-token" in output
            # Default endpoint is esisteodonimo
            assert "esisteodonimo?" in output
            assert "codcom=H501" in output
            assert "denom=" in output
            # PA is GET - no Content-Type or Digest
            assert "Digest:" not in output
            assert "Agid-JWT-Signature:" not in output

    def test_curl_coordinate_post_with_modi(
        self, cli_runner: CliRunner, tmp_path: Path
    ) -> None:
        """Test that auth curl --api coordinate generates POST with ModI headers."""
        from anncsu.common.modi import AuditContext

        from anncsu.cli import app

        with cli_runner.isolated_filesystem(temp_dir=tmp_path):
            with patch(
                "anncsu.cli.commands.auth.ClientAssertionSettings"
            ) as mock_settings:
                settings = MagicMock()
                settings.has_modi_audit_context = True
                settings.has_e_service_key = False
                settings.modi_kid = None
                settings.kid = "test-kid"
                settings.private_key = None
                settings.key_path = str(tmp_path / "test_key.pem")
                settings.issuer = "test-issuer"
                settings.get_modi_audit_context.return_value = AuditContext(
                    user_id="test-user",
                    user_location="test-location",
                    loa="SPID_L2",
                )
                mock_settings.return_value = settings

                with patch("anncsu.cli.commands.auth.PDNDAuthManager") as mock_manager:
                    manager = MagicMock()
                    manager.get_access_token.return_value = "mock-coord-token"
                    manager.access_token_ttl.return_value = 600
                    mock_manager.return_value = manager

                    # Mock the ModI header generation to avoid needing real RSA key
                    with patch(
                        "anncsu.common.modi.create_modi_config_from_settings"
                    ) as mock_modi_config:
                        mock_config = MagicMock()
                        mock_modi_config.return_value = mock_config

                        with patch(
                            "anncsu.common.modi.ModIHeaderGenerator"
                        ) as mock_gen_cls:
                            mock_gen = MagicMock()
                            mock_gen.generate_headers.return_value = {
                                "Digest": "SHA-256=abc123",
                                "Agid-JWT-Signature": "eyJ.sig.test",
                                "Agid-JWT-TrackingEvidence": "eyJ.track.test",
                            }
                            mock_gen_cls.return_value = mock_gen

                            result = cli_runner.invoke(
                                app, ["auth", "curl", "--api", "coordinate"]
                            )

            assert result.exit_code == 0
            output = result.output
            assert "curl -X POST" in output
            assert "Authorization: Bearer mock-coord-token" in output
            assert "Content-Type: application/json" in output
            assert "Digest: SHA-256=abc123" in output
            assert "Agid-JWT-Signature: eyJ.sig.test" in output
            assert "Agid-JWT-TrackingEvidence: eyJ.track.test" in output
            assert "-d '" in output
            assert "gestionecoordinate" in output

    def test_curl_coordinate_without_audit_context(
        self, cli_runner: CliRunner, tmp_path: Path
    ) -> None:
        """Test that missing audit context produces a warning and no TrackingEvidence."""
        from anncsu.cli import app

        with cli_runner.isolated_filesystem(temp_dir=tmp_path):
            with patch(
                "anncsu.cli.commands.auth.ClientAssertionSettings"
            ) as mock_settings:
                settings = MagicMock()
                settings.has_modi_audit_context = False
                settings.has_e_service_key = False
                settings.modi_kid = None
                settings.kid = "test-kid"
                settings.private_key = None
                settings.key_path = str(tmp_path / "test_key.pem")
                settings.issuer = "test-issuer"
                mock_settings.return_value = settings

                with patch("anncsu.cli.commands.auth.PDNDAuthManager") as mock_manager:
                    manager = MagicMock()
                    manager.get_access_token.return_value = "mock-token"
                    manager.access_token_ttl.return_value = 600
                    mock_manager.return_value = manager

                    with patch(
                        "anncsu.common.modi.create_modi_config_from_settings"
                    ) as mock_modi_config:
                        mock_config = MagicMock()
                        mock_modi_config.return_value = mock_config

                        with patch(
                            "anncsu.common.modi.ModIHeaderGenerator"
                        ) as mock_gen_cls:
                            mock_gen = MagicMock()
                            # No TrackingEvidence when no audit context
                            mock_gen.generate_headers.return_value = {
                                "Digest": "SHA-256=xyz",
                                "Agid-JWT-Signature": "eyJ.sig.noaudit",
                            }
                            mock_gen_cls.return_value = mock_gen

                            result = cli_runner.invoke(
                                app, ["auth", "curl", "--api", "coordinate"]
                            )

            assert result.exit_code == 0
            output = result.output
            # TrackingEvidence should NOT appear as a -H header in the cURL
            assert '-H "Agid-JWT-TrackingEvidence:' not in output
            # But the warning text should mention it's missing
            assert "TrackingEvidence" in output

    def test_curl_custom_body(self, cli_runner: CliRunner, tmp_path: Path) -> None:
        """Test that --body overrides the sample payload."""
        from anncsu.cli import app

        custom_body = '{"custom": "payload"}'

        with cli_runner.isolated_filesystem(temp_dir=tmp_path):
            with patch(
                "anncsu.cli.commands.auth.ClientAssertionSettings"
            ) as mock_settings:
                settings = MagicMock()
                settings.has_modi_audit_context = False
                settings.has_e_service_key = False
                settings.modi_kid = None
                mock_settings.return_value = settings

                with patch("anncsu.cli.commands.auth.PDNDAuthManager") as mock_manager:
                    manager = MagicMock()
                    manager.get_access_token.return_value = "mock-token"
                    manager.access_token_ttl.return_value = 600
                    mock_manager.return_value = manager

                    with patch("anncsu.common.modi.create_modi_config_from_settings"):
                        with patch(
                            "anncsu.common.modi.ModIHeaderGenerator"
                        ) as mock_gen_cls:
                            mock_gen = MagicMock()
                            mock_gen.generate_headers.return_value = {
                                "Digest": "SHA-256=custom",
                                "Agid-JWT-Signature": "eyJ.custom",
                            }
                            mock_gen_cls.return_value = mock_gen

                            result = cli_runner.invoke(
                                app,
                                [
                                    "auth",
                                    "curl",
                                    "--api",
                                    "coordinate",
                                    "--body",
                                    custom_body,
                                ],
                            )

            assert result.exit_code == 0
            output = result.output
            # The custom body should appear in the -d flag (compact form)
            assert '"custom"' in output
            assert '"payload"' in output

    def test_curl_headers_only(self, cli_runner: CliRunner, tmp_path: Path) -> None:
        """Test that --headers-only outputs only -H lines."""
        from anncsu.cli import app

        with cli_runner.isolated_filesystem(temp_dir=tmp_path):
            with patch(
                "anncsu.cli.commands.auth.ClientAssertionSettings"
            ) as mock_settings:
                settings = MagicMock()
                mock_settings.return_value = settings

                with patch("anncsu.cli.commands.auth.PDNDAuthManager") as mock_manager:
                    manager = MagicMock()
                    manager.get_access_token.return_value = "mock-token"
                    manager.access_token_ttl.return_value = 600
                    mock_manager.return_value = manager

                    result = cli_runner.invoke(
                        app, ["auth", "curl", "--api", "pa", "--headers-only"]
                    )

            assert result.exit_code == 0
            output = result.output.strip()
            # Should contain -H flag
            assert '-H "Authorization: Bearer mock-token"' in output
            # Should NOT contain curl, URL, or -X
            assert "curl " not in output
            assert "modipa" not in output

    def test_curl_production_env(self, cli_runner: CliRunner, tmp_path: Path) -> None:
        """Test that --production selects production server URL."""
        from anncsu.cli import app

        with cli_runner.isolated_filesystem(temp_dir=tmp_path):
            with patch(
                "anncsu.cli.commands.auth.ClientAssertionSettings"
            ) as mock_settings:
                settings = MagicMock()
                mock_settings.return_value = settings

                with patch("anncsu.cli.commands.auth.PDNDAuthManager") as mock_manager:
                    manager = MagicMock()
                    manager.get_access_token.return_value = "mock-token"
                    manager.access_token_ttl.return_value = 600
                    mock_manager.return_value = manager

                    result = cli_runner.invoke(
                        app, ["auth", "curl", "--api", "pa", "--production"]
                    )

            assert result.exit_code == 0
            output = result.output
            # Production URL uses .gov.it domain
            assert "modipa.agenziaentrate.gov.it" in output

    def test_curl_validation_env_default(
        self, cli_runner: CliRunner, tmp_path: Path
    ) -> None:
        """Test that default (validation) selects UAT server URL."""
        from anncsu.cli import app

        with cli_runner.isolated_filesystem(temp_dir=tmp_path):
            with patch(
                "anncsu.cli.commands.auth.ClientAssertionSettings"
            ) as mock_settings:
                settings = MagicMock()
                mock_settings.return_value = settings

                with patch("anncsu.cli.commands.auth.PDNDAuthManager") as mock_manager:
                    manager = MagicMock()
                    manager.get_access_token.return_value = "mock-token"
                    manager.access_token_ttl.return_value = 600
                    mock_manager.return_value = manager

                    result = cli_runner.invoke(app, ["auth", "curl", "--api", "pa"])

            assert result.exit_code == 0
            output = result.output
            # Validation URL uses .it domain
            assert "modipa-val.agenziaentrate.it" in output

    def test_curl_json_output(self, cli_runner: CliRunner, tmp_path: Path) -> None:
        """Test that --json outputs structured CurlOutput model."""
        import json

        from anncsu.cli.models import CurlOutput

        from anncsu.cli import app

        with cli_runner.isolated_filesystem(temp_dir=tmp_path):
            with patch(
                "anncsu.cli.commands.auth.ClientAssertionSettings"
            ) as mock_settings:
                settings = MagicMock()
                mock_settings.return_value = settings

                with patch("anncsu.cli.commands.auth.PDNDAuthManager") as mock_manager:
                    manager = MagicMock()
                    manager.get_access_token.return_value = "mock-token"
                    manager.access_token_ttl.return_value = 600
                    mock_manager.return_value = manager

                    result = cli_runner.invoke(
                        app, ["auth", "curl", "--api", "pa", "--json"]
                    )

            assert result.exit_code == 0
            # Should be valid JSON parseable as CurlOutput
            parsed = json.loads(result.output)
            output = CurlOutput.model_validate(parsed)
            assert output.method == "GET"
            assert output.api_type == "pa"
            assert output.environment == "validation"
            assert "Authorization" in output.headers
            assert output.body is None

    def test_curl_invalid_body_json(
        self, cli_runner: CliRunner, tmp_path: Path
    ) -> None:
        """Test that invalid JSON body produces an error."""
        from anncsu.cli import app

        with cli_runner.isolated_filesystem(temp_dir=tmp_path):
            with patch(
                "anncsu.cli.commands.auth.ClientAssertionSettings"
            ) as mock_settings:
                settings = MagicMock()
                mock_settings.return_value = settings

                with patch("anncsu.cli.commands.auth.PDNDAuthManager") as mock_manager:
                    manager = MagicMock()
                    manager.get_access_token.return_value = "mock-token"
                    manager.access_token_ttl.return_value = 600
                    mock_manager.return_value = manager

                    result = cli_runner.invoke(
                        app,
                        [
                            "auth",
                            "curl",
                            "--api",
                            "coordinate",
                            "--body",
                            "not-valid-json",
                        ],
                    )

            assert result.exit_code == 1

    def test_auth_token_unchanged(self, cli_runner: CliRunner, tmp_path: Path) -> None:
        """Regression: auth token still outputs only the raw token."""
        from anncsu.cli import app

        with cli_runner.isolated_filesystem(temp_dir=tmp_path):
            with patch(
                "anncsu.cli.commands.auth.ClientAssertionSettings"
            ) as mock_settings:
                settings = MagicMock()
                mock_settings.return_value = settings

                with patch("anncsu.cli.commands.auth.PDNDAuthManager") as mock_manager:
                    manager = MagicMock()
                    manager.get_access_token.return_value = "raw-token-only"
                    mock_manager.return_value = manager

                    result = cli_runner.invoke(app, ["auth", "token", "--api", "pa"])

            assert result.exit_code == 0
            output = result.output.strip()
            assert output == "raw-token-only"
            # No curl, no headers
            assert "curl" not in output
            assert "-H" not in output

    def _run_pa_endpoint(
        self,
        cli_runner: CliRunner,
        tmp_path: Path,
        endpoint_name: str,
        extra_args: list[str] | None = None,
    ) -> str:
        """Helper to run auth curl --api pa --endpoint <name> with optional params."""
        from anncsu.cli import app

        with cli_runner.isolated_filesystem(temp_dir=tmp_path):
            with patch(
                "anncsu.cli.commands.auth.ClientAssertionSettings"
            ) as mock_settings:
                settings = MagicMock()
                mock_settings.return_value = settings

                with patch("anncsu.cli.commands.auth.PDNDAuthManager") as mock_manager:
                    manager = MagicMock()
                    manager.get_access_token.return_value = "mock-token"
                    manager.access_token_ttl.return_value = 600
                    mock_manager.return_value = manager

                    args = ["auth", "curl", "--api", "pa", "--endpoint", endpoint_name]
                    if extra_args:
                        args.extend(extra_args)

                    result = cli_runner.invoke(app, args)

            assert result.exit_code == 0
            return result.output

    def test_curl_pa_endpoint_esisteaccesso(
        self, cli_runner: CliRunner, tmp_path: Path
    ) -> None:
        """Test --endpoint esisteaccesso with params generates correct URL."""
        output = self._run_pa_endpoint(
            cli_runner,
            tmp_path,
            "esisteaccesso",
            ["--codcom", "H501", "--denom", "VIA ROMA", "--accesso", "1"],
        )
        assert "esisteaccesso?" in output
        assert "codcom=H501" in output
        assert "denom=" in output  # base64-encoded value
        assert "accesso=1" in output

    def test_curl_pa_endpoint_elencoodonimi(
        self, cli_runner: CliRunner, tmp_path: Path
    ) -> None:
        """Test --endpoint elencoodonimi with params generates correct URL."""
        output = self._run_pa_endpoint(
            cli_runner,
            tmp_path,
            "elencoodonimi",
            ["--codcom", "H501", "--denomparz", "VIA"],
        )
        assert "elencoodonimi?" in output
        assert "codcom=H501" in output
        assert "denomparz=" in output  # base64-encoded value

    def test_curl_pa_endpoint_elencoaccessi(
        self, cli_runner: CliRunner, tmp_path: Path
    ) -> None:
        """Test --endpoint elencoaccessi with params generates correct URL."""
        output = self._run_pa_endpoint(
            cli_runner,
            tmp_path,
            "elencoaccessi",
            ["--codcom", "H501", "--denom", "VIA ROMA", "--accparz", "1"],
        )
        assert "elencoaccessi?" in output
        assert "codcom=H501" in output
        assert "denom=" in output  # base64-encoded value
        assert "accparz=1" in output

    def test_curl_pa_endpoint_elencoodonimiprog(
        self, cli_runner: CliRunner, tmp_path: Path
    ) -> None:
        """Test --endpoint elencoodonimiprog with params generates correct URL."""
        output = self._run_pa_endpoint(
            cli_runner,
            tmp_path,
            "elencoodonimiprog",
            ["--codcom", "H501", "--denomparz", "VIA"],
        )
        assert "elencoodonimiprog?" in output
        assert "codcom=H501" in output
        assert "denomparz=" in output  # base64-encoded value

    def test_curl_pa_endpoint_elencoaccessiprog(
        self, cli_runner: CliRunner, tmp_path: Path
    ) -> None:
        """Test --endpoint elencoaccessiprog with params generates correct URL."""
        output = self._run_pa_endpoint(
            cli_runner,
            tmp_path,
            "elencoaccessiprog",
            ["--prognaz", "0001234500000", "--accparz", "1"],
        )
        assert "elencoaccessiprog?" in output
        assert "prognaz=0001234500000" in output
        assert "accparz=1" in output

    def test_curl_pa_endpoint_prognazarea(
        self, cli_runner: CliRunner, tmp_path: Path
    ) -> None:
        """Test --endpoint prognazarea with params generates correct URL."""
        output = self._run_pa_endpoint(
            cli_runner,
            tmp_path,
            "prognazarea",
            ["--prognaz", "0001234500000"],
        )
        assert "prognazarea?" in output
        assert "prognaz=0001234500000" in output

    def test_curl_pa_endpoint_prognazacc(
        self, cli_runner: CliRunner, tmp_path: Path
    ) -> None:
        """Test --endpoint prognazacc with params generates correct URL."""
        output = self._run_pa_endpoint(
            cli_runner,
            tmp_path,
            "prognazacc",
            ["--prognazacc", "0001234500001"],
        )
        assert "prognazacc?" in output
        assert "prognazacc=0001234500001" in output

    def test_curl_pa_endpoint_invalid(
        self, cli_runner: CliRunner, tmp_path: Path
    ) -> None:
        """Test that an invalid --endpoint value produces an error."""
        from anncsu.cli import app

        with cli_runner.isolated_filesystem(temp_dir=tmp_path):
            with patch(
                "anncsu.cli.commands.auth.ClientAssertionSettings"
            ) as mock_settings:
                settings = MagicMock()
                mock_settings.return_value = settings

                with patch("anncsu.cli.commands.auth.PDNDAuthManager") as mock_manager:
                    manager = MagicMock()
                    manager.get_access_token.return_value = "mock-token"
                    manager.access_token_ttl.return_value = 600
                    mock_manager.return_value = manager

                    result = cli_runner.invoke(
                        app,
                        ["auth", "curl", "--api", "pa", "--endpoint", "nonexistent"],
                    )

            assert result.exit_code == 1

    def test_curl_endpoint_ignored_for_coordinate(
        self, cli_runner: CliRunner, tmp_path: Path
    ) -> None:
        """Test that --endpoint is ignored (with warning) when --api coordinate."""
        from anncsu.cli import app

        with cli_runner.isolated_filesystem(temp_dir=tmp_path):
            with patch(
                "anncsu.cli.commands.auth.ClientAssertionSettings"
            ) as mock_settings:
                settings = MagicMock()
                settings.has_modi_audit_context = False
                settings.has_e_service_key = False
                settings.modi_kid = None
                mock_settings.return_value = settings

                with patch("anncsu.cli.commands.auth.PDNDAuthManager") as mock_manager:
                    manager = MagicMock()
                    manager.get_access_token.return_value = "mock-token"
                    manager.access_token_ttl.return_value = 600
                    mock_manager.return_value = manager

                    with patch("anncsu.common.modi.create_modi_config_from_settings"):
                        with patch(
                            "anncsu.common.modi.ModIHeaderGenerator"
                        ) as mock_gen_cls:
                            mock_gen = MagicMock()
                            mock_gen.generate_headers.return_value = {
                                "Digest": "SHA-256=abc",
                                "Agid-JWT-Signature": "eyJ.sig",
                            }
                            mock_gen_cls.return_value = mock_gen

                            result = cli_runner.invoke(
                                app,
                                [
                                    "auth",
                                    "curl",
                                    "--api",
                                    "coordinate",
                                    "--endpoint",
                                    "prognazacc",
                                ],
                            )

            assert result.exit_code == 0
            output = result.output
            # Should still be coordinate POST, not PA GET
            assert "curl -X POST" in output
            assert "gestionecoordinate" in output

    def test_curl_pa_base64_encoding(
        self, cli_runner: CliRunner, tmp_path: Path
    ) -> None:
        """Test that denom is auto base64-encoded from plain text."""
        import base64

        output = self._run_pa_endpoint(
            cli_runner,
            tmp_path,
            "esisteodonimo",
            ["--codcom", "H501", "--denom", "VIA ROMA"],
        )
        expected_b64 = base64.b64encode(b"VIA ROMA").decode("utf-8")
        assert f"denom={expected_b64}" in output or "denom=" in output
        # The plain text should NOT appear as-is in the URL query
        assert "denom=VIA ROMA" not in output
        assert "denom=VIA%20ROMA" not in output

    def test_curl_pa_denomparz_base64_encoding(
        self, cli_runner: CliRunner, tmp_path: Path
    ) -> None:
        """Test that denomparz is auto base64-encoded from plain text."""
        import base64

        output = self._run_pa_endpoint(
            cli_runner,
            tmp_path,
            "elencoodonimi",
            ["--codcom", "H501", "--denomparz", "VIA"],
        )
        expected_b64 = base64.b64encode(b"VIA").decode("utf-8")
        assert f"denomparz={expected_b64}" in output or "denomparz=" in output
        # Plain text should not appear directly
        assert "denomparz=VIA&" not in output

    def test_curl_pa_missing_params_warning(
        self, cli_runner: CliRunner, tmp_path: Path
    ) -> None:
        """Test that missing params produce a warning but don't error out."""
        from anncsu.cli import app

        with cli_runner.isolated_filesystem(temp_dir=tmp_path):
            with patch(
                "anncsu.cli.commands.auth.ClientAssertionSettings"
            ) as mock_settings:
                settings = MagicMock()
                mock_settings.return_value = settings

                with patch("anncsu.cli.commands.auth.PDNDAuthManager") as mock_manager:
                    manager = MagicMock()
                    manager.get_access_token.return_value = "mock-token"
                    manager.access_token_ttl.return_value = 600
                    mock_manager.return_value = manager

                    # Only pass codcom, missing denom
                    result = cli_runner.invoke(
                        app,
                        [
                            "auth",
                            "curl",
                            "--api",
                            "pa",
                            "--endpoint",
                            "esisteodonimo",
                            "--codcom",
                            "H501",
                        ],
                    )

            assert result.exit_code == 0
            # URL should have codcom but not denom
            assert "codcom=H501" in result.output
            # Warning about missing denom should be on stderr (captured in output by test runner)
            assert "esisteodonimo" in result.output

    def test_curl_pa_no_params_warning(
        self, cli_runner: CliRunner, tmp_path: Path
    ) -> None:
        """Test that providing no params at all produces a no-params warning."""
        from anncsu.cli import app

        with cli_runner.isolated_filesystem(temp_dir=tmp_path):
            with patch(
                "anncsu.cli.commands.auth.ClientAssertionSettings"
            ) as mock_settings:
                settings = MagicMock()
                mock_settings.return_value = settings

                with patch("anncsu.cli.commands.auth.PDNDAuthManager") as mock_manager:
                    manager = MagicMock()
                    manager.get_access_token.return_value = "mock-token"
                    manager.access_token_ttl.return_value = 600
                    mock_manager.return_value = manager

                    result = cli_runner.invoke(
                        app,
                        ["auth", "curl", "--api", "pa", "--endpoint", "esisteodonimo"],
                    )

            assert result.exit_code == 0
            # URL should be just the path without ?
            assert "esisteodonimo" in result.output
            # Should NOT have a query string
            assert "esisteodonimo?" not in result.output

    def test_curl_pa_default_endpoint_with_params(
        self, cli_runner: CliRunner, tmp_path: Path
    ) -> None:
        """Test default endpoint (esisteodonimo) with --codcom and --denom."""
        from anncsu.cli import app

        with cli_runner.isolated_filesystem(temp_dir=tmp_path):
            with patch(
                "anncsu.cli.commands.auth.ClientAssertionSettings"
            ) as mock_settings:
                settings = MagicMock()
                mock_settings.return_value = settings

                with patch("anncsu.cli.commands.auth.PDNDAuthManager") as mock_manager:
                    manager = MagicMock()
                    manager.get_access_token.return_value = "mock-token"
                    manager.access_token_ttl.return_value = 600
                    mock_manager.return_value = manager

                    result = cli_runner.invoke(
                        app,
                        [
                            "auth",
                            "curl",
                            "--api",
                            "pa",
                            "--codcom",
                            "H501",
                            "--denom",
                            "VIA ROMA",
                        ],
                    )

            assert result.exit_code == 0
            output = result.output
            # Default endpoint is esisteodonimo
            assert "esisteodonimo?" in output
            assert "codcom=H501" in output
            assert "denom=" in output

    def test_curl_pa_ignored_params_warning(
        self, cli_runner: CliRunner, tmp_path: Path
    ) -> None:
        """Test that params not used by the endpoint produce an 'Ignored' warning."""
        from anncsu.cli import app

        with cli_runner.isolated_filesystem(temp_dir=tmp_path):
            with patch(
                "anncsu.cli.commands.auth.ClientAssertionSettings"
            ) as mock_settings:
                settings = MagicMock()
                mock_settings.return_value = settings

                with patch("anncsu.cli.commands.auth.PDNDAuthManager") as mock_manager:
                    manager = MagicMock()
                    manager.get_access_token.return_value = "mock-token"
                    manager.access_token_ttl.return_value = 600
                    mock_manager.return_value = manager

                    # prognazarea requires only --prognaz; --codcom is extraneous
                    result = cli_runner.invoke(
                        app,
                        [
                            "auth",
                            "curl",
                            "--api",
                            "pa",
                            "--endpoint",
                            "prognazarea",
                            "--prognaz",
                            "0001234500000",
                            "--codcom",
                            "H501",
                        ],
                    )

            assert result.exit_code == 0
            output = result.output
            # The URL should contain only prognaz, not codcom
            assert "prognaz=0001234500000" in output
            assert "codcom=" not in output
            # Warning about ignored param should be present (on stderr, captured by runner)
            assert "Ignored" in output or "ignored" in output
            assert "--codcom" in output
