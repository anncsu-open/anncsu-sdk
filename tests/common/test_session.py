# SPDX-FileCopyrightText: 2025-present Geobeyond <info@geobeyond.it>
# SPDX-License-Identifier: MIT
"""Tests for session persistence."""

from __future__ import annotations

import json
import time
from pathlib import Path
from unittest.mock import patch

from anncsu.common.session import (
    Session,
    clear_session,
    get_session_path,
    load_session,
    save_session,
)


class TestSessionModel:
    """Tests for Session Pydantic model."""

    def test_session_model_valid(self) -> None:
        """Test that Session model accepts valid data."""
        session = Session(
            client_assertion="eyJhbGciOiJSUzI1NiJ9.test.sig",
            access_token="eyJhbGciOiJSUzI1NiJ9.access.sig",
            token_endpoint="https://auth.uat.interop.pagopa.it/token.oauth2",
        )
        assert session.client_assertion == "eyJhbGciOiJSUzI1NiJ9.test.sig"
        assert session.access_token == "eyJhbGciOiJSUzI1NiJ9.access.sig"
        assert (
            session.token_endpoint == "https://auth.uat.interop.pagopa.it/token.oauth2"
        )

    def test_session_model_optional_fields(self) -> None:
        """Test that Session model handles optional fields."""
        session = Session(
            client_assertion="eyJhbGciOiJSUzI1NiJ9.test.sig",
            access_token=None,
            token_endpoint="https://auth.uat.interop.pagopa.it/token.oauth2",
        )
        assert session.client_assertion == "eyJhbGciOiJSUzI1NiJ9.test.sig"
        assert session.access_token is None

    def test_session_model_serialization(self) -> None:
        """Test that Session model serializes to JSON correctly."""
        session = Session(
            client_assertion="assertion-token",
            access_token="access-token",
            token_endpoint="https://example.com/token",
        )
        json_str = session.model_dump_json()
        data = json.loads(json_str)
        assert data["client_assertion"] == "assertion-token"
        assert data["access_token"] == "access-token"
        assert data["token_endpoint"] == "https://example.com/token"


class TestGetSessionPath:
    """Tests for get_session_path function."""

    def test_get_session_path_default(self) -> None:
        """Test that get_session_path returns correct default path."""
        path = get_session_path()
        assert path == Path.home() / ".anncsu" / "session.json"

    def test_get_session_path_custom_config_dir(self, tmp_path: Path) -> None:
        """Test that get_session_path respects custom config dir."""
        path = get_session_path(config_dir=tmp_path)
        assert path == tmp_path / "session.json"


class TestSaveSession:
    """Tests for save_session function."""

    def test_save_session_creates_file(self, tmp_path: Path) -> None:
        """Test that save_session creates the session file."""
        session = Session(
            client_assertion="test-assertion",
            access_token="test-token",
            token_endpoint="https://example.com/token",
        )
        save_session(session, config_dir=tmp_path)

        session_file = tmp_path / "session.json"
        assert session_file.exists()

    def test_save_session_creates_directory(self, tmp_path: Path) -> None:
        """Test that save_session creates the config directory if needed."""
        config_dir = tmp_path / "new_config_dir"
        session = Session(
            client_assertion="test-assertion",
            access_token="test-token",
            token_endpoint="https://example.com/token",
        )
        save_session(session, config_dir=config_dir)

        assert config_dir.exists()
        assert (config_dir / "session.json").exists()

    def test_save_session_content(self, tmp_path: Path) -> None:
        """Test that save_session writes correct content."""
        session = Session(
            client_assertion="my-assertion",
            access_token="my-token",
            token_endpoint="https://auth.example.com/token",
        )
        save_session(session, config_dir=tmp_path)

        session_file = tmp_path / "session.json"
        data = json.loads(session_file.read_text())
        assert data["client_assertion"] == "my-assertion"
        assert data["access_token"] == "my-token"
        assert data["token_endpoint"] == "https://auth.example.com/token"

    def test_save_session_overwrites_existing(self, tmp_path: Path) -> None:
        """Test that save_session overwrites existing session."""
        session1 = Session(
            client_assertion="old-assertion",
            access_token="old-token",
            token_endpoint="https://old.example.com/token",
        )
        save_session(session1, config_dir=tmp_path)

        session2 = Session(
            client_assertion="new-assertion",
            access_token="new-token",
            token_endpoint="https://new.example.com/token",
        )
        save_session(session2, config_dir=tmp_path)

        session_file = tmp_path / "session.json"
        data = json.loads(session_file.read_text())
        assert data["client_assertion"] == "new-assertion"
        assert data["access_token"] == "new-token"


class TestLoadSession:
    """Tests for load_session function."""

    def test_load_session_returns_none_if_no_file(self, tmp_path: Path) -> None:
        """Test that load_session returns None if no session file exists."""
        session = load_session(config_dir=tmp_path)
        assert session is None

    def test_load_session_returns_session(self, tmp_path: Path) -> None:
        """Test that load_session returns saved session."""
        # Save a session first
        original = Session(
            client_assertion="saved-assertion",
            access_token="saved-token",
            token_endpoint="https://saved.example.com/token",
        )
        save_session(original, config_dir=tmp_path)

        # Load it back
        loaded = load_session(config_dir=tmp_path)
        assert loaded is not None
        assert loaded.client_assertion == "saved-assertion"
        assert loaded.access_token == "saved-token"
        assert loaded.token_endpoint == "https://saved.example.com/token"

    def test_load_session_handles_invalid_json(self, tmp_path: Path) -> None:
        """Test that load_session returns None for invalid JSON."""
        session_file = tmp_path / "session.json"
        session_file.write_text("not valid json {{{")

        session = load_session(config_dir=tmp_path)
        assert session is None

    def test_load_session_handles_missing_fields(self, tmp_path: Path) -> None:
        """Test that load_session returns None for incomplete data."""
        session_file = tmp_path / "session.json"
        session_file.write_text('{"client_assertion": "only-this"}')

        session = load_session(config_dir=tmp_path)
        assert session is None


class TestClearSession:
    """Tests for clear_session function."""

    def test_clear_session_removes_file(self, tmp_path: Path) -> None:
        """Test that clear_session removes the session file."""
        session = Session(
            client_assertion="to-delete",
            access_token="to-delete",
            token_endpoint="https://example.com/token",
        )
        save_session(session, config_dir=tmp_path)

        session_file = tmp_path / "session.json"
        assert session_file.exists()

        clear_session(config_dir=tmp_path)
        assert not session_file.exists()

    def test_clear_session_no_error_if_no_file(self, tmp_path: Path) -> None:
        """Test that clear_session doesn't error if no file exists."""
        # Should not raise
        clear_session(config_dir=tmp_path)


class TestSessionIntegrationWithAuthManager:
    """Tests for session integration with PDNDAuthManager."""

    def _create_valid_token(self, exp_seconds: int = 3600) -> str:
        """Create a valid JWT-like token with future expiration."""
        import base64

        future_exp = int(time.time()) + exp_seconds
        payload = (
            base64.urlsafe_b64encode(json.dumps({"exp": future_exp}).encode())
            .decode()
            .rstrip("=")
        )
        return f"eyJhbGciOiJSUzI1NiJ9.{payload}.signature"

    def test_auth_manager_loads_session_on_init(self, tmp_path: Path) -> None:
        """Test that PDNDAuthManager loads session on initialization."""
        from unittest.mock import MagicMock

        from anncsu.common.auth import PDNDAuthManager

        valid_token = self._create_valid_token()

        # Save a session
        session = Session(
            client_assertion=valid_token,
            access_token=valid_token,
            token_endpoint="https://auth.example.com/token",
        )
        save_session(session, config_dir=tmp_path)

        # Create auth manager with session loading
        settings = MagicMock()
        settings.to_config.return_value = MagicMock()

        manager = PDNDAuthManager(
            settings=settings,
            token_endpoint="https://auth.example.com/token",
            session_persistence=True,
            config_dir=tmp_path,
        )

        # Tokens should be loaded from session
        assert manager._client_assertion == valid_token
        assert manager._access_token == valid_token

    def test_auth_manager_does_not_load_expired_tokens(self, tmp_path: Path) -> None:
        """Test that PDNDAuthManager does not load expired tokens."""
        from unittest.mock import MagicMock

        from anncsu.common.auth import PDNDAuthManager

        # Create an expired token
        expired_token = self._create_valid_token(exp_seconds=-100)

        # Save a session with expired tokens
        session = Session(
            client_assertion=expired_token,
            access_token=expired_token,
            token_endpoint="https://auth.example.com/token",
        )
        save_session(session, config_dir=tmp_path)

        # Create auth manager
        settings = MagicMock()
        settings.to_config.return_value = MagicMock()

        manager = PDNDAuthManager(
            settings=settings,
            token_endpoint="https://auth.example.com/token",
            session_persistence=True,
            config_dir=tmp_path,
        )

        # Expired tokens should NOT be loaded
        assert manager._client_assertion is None
        assert manager._access_token is None

    def test_auth_manager_does_not_load_mismatched_endpoint(
        self, tmp_path: Path
    ) -> None:
        """Test that PDNDAuthManager doesn't load session for different endpoint."""
        from unittest.mock import MagicMock

        from anncsu.common.auth import PDNDAuthManager

        valid_token = self._create_valid_token()

        # Save a session for UAT endpoint
        session = Session(
            client_assertion=valid_token,
            access_token=valid_token,
            token_endpoint="https://auth.uat.interop.pagopa.it/token.oauth2",
        )
        save_session(session, config_dir=tmp_path)

        # Create auth manager for PROD endpoint
        settings = MagicMock()
        settings.to_config.return_value = MagicMock()

        manager = PDNDAuthManager(
            settings=settings,
            token_endpoint="https://auth.interop.pagopa.it/token.oauth2",
            session_persistence=True,
            config_dir=tmp_path,
        )

        # Tokens should NOT be loaded (different endpoint)
        assert manager._client_assertion is None
        assert manager._access_token is None

    def test_auth_manager_saves_session_after_login(self, tmp_path: Path) -> None:
        """Test that PDNDAuthManager saves session after getting tokens."""
        from unittest.mock import MagicMock

        from anncsu.common.auth import PDNDAuthManager

        valid_token = self._create_valid_token()

        settings = MagicMock()
        config = MagicMock()
        config.issuer = "test-client"
        settings.to_config.return_value = config

        with patch(
            "anncsu.common.auth.create_client_assertion",
            return_value=valid_token,
        ):
            with patch("anncsu.common.auth.get_access_token") as mock_get_token:
                mock_response = MagicMock()
                mock_response.access_token = valid_token
                mock_get_token.return_value = mock_response

                manager = PDNDAuthManager(
                    settings=settings,
                    token_endpoint="https://auth.example.com/token",
                    session_persistence=True,
                    config_dir=tmp_path,
                )

                # Get access token (triggers save)
                manager.get_access_token()

                # Session should be saved
                session_file = tmp_path / "session.json"
                assert session_file.exists()

                data = json.loads(session_file.read_text())
                assert data["client_assertion"] == valid_token
                assert data["access_token"] == valid_token

    def test_auth_manager_clear_session(self, tmp_path: Path) -> None:
        """Test that PDNDAuthManager.clear_session removes tokens and file."""
        from unittest.mock import MagicMock

        from anncsu.common.auth import PDNDAuthManager

        valid_token = self._create_valid_token()

        # Save a session
        session = Session(
            client_assertion=valid_token,
            access_token=valid_token,
            token_endpoint="https://auth.example.com/token",
        )
        save_session(session, config_dir=tmp_path)

        # Create auth manager
        settings = MagicMock()
        settings.to_config.return_value = MagicMock()

        manager = PDNDAuthManager(
            settings=settings,
            token_endpoint="https://auth.example.com/token",
            session_persistence=True,
            config_dir=tmp_path,
        )

        # Verify tokens are loaded
        assert manager._client_assertion == valid_token
        assert manager._access_token == valid_token

        # Clear session
        manager.clear_session()

        # Tokens should be cleared
        assert manager._client_assertion is None
        assert manager._access_token is None

        # Session file should be deleted
        session_file = tmp_path / "session.json"
        assert not session_file.exists()
