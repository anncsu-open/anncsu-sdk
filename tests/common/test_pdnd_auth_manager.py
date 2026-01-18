"""Tests for PDNDAuthManager class.

This module tests the PDNDAuthManager that manages the entire PDND authentication
lifecycle, including both client assertion and access token management with
awareness of expiration for both.
"""

from __future__ import annotations

import base64
import json
import time
from typing import TYPE_CHECKING
from unittest.mock import MagicMock, patch

import pytest

if TYPE_CHECKING:
    pass


# Helper to create JWT tokens for testing
def create_test_jwt(
    exp: int, iat: int | None = None, claims: dict | None = None
) -> str:
    """Create a test JWT token with specified expiration.

    Args:
        exp: Expiration timestamp (Unix epoch seconds)
        iat: Issued at timestamp (defaults to exp - 600)
        claims: Additional claims to include in payload

    Returns:
        JWT token string (not cryptographically signed, for testing only)
    """
    if iat is None:
        iat = exp - 600

    header = {"alg": "RS256", "typ": "JWT", "kid": "test-kid"}
    payload = {
        "iss": "test-issuer",
        "sub": "test-subject",
        "aud": "test-audience",
        "exp": exp,
        "iat": iat,
    }
    if claims:
        payload.update(claims)

    def b64_encode(data: dict) -> str:
        return base64.urlsafe_b64encode(json.dumps(data).encode()).decode().rstrip("=")

    return f"{b64_encode(header)}.{b64_encode(payload)}.fake_signature"


def create_expired_token(seconds_ago: int = 60) -> str:
    """Create a token that expired N seconds ago."""
    return create_test_jwt(exp=int(time.time()) - seconds_ago)


def create_valid_token(expires_in: int = 600) -> str:
    """Create a token that expires in N seconds."""
    return create_test_jwt(exp=int(time.time()) + expires_in)


def create_client_assertion(expires_in_days: int = 30) -> str:
    """Create a client assertion that expires in N days."""
    expires_in_seconds = expires_in_days * 24 * 60 * 60
    return create_test_jwt(
        exp=int(time.time()) + expires_in_seconds,
        claims={"purposeId": "test-purpose-id"},
    )


def create_expired_client_assertion(days_ago: int = 1) -> str:
    """Create a client assertion that expired N days ago."""
    seconds_ago = days_ago * 24 * 60 * 60
    return create_test_jwt(
        exp=int(time.time()) - seconds_ago,
        claims={"purposeId": "test-purpose-id"},
    )


class TestPDNDAuthManagerInitialization:
    """Tests for PDNDAuthManager initialization."""

    def test_manager_can_be_initialized_with_settings(self):
        """Test that manager can be initialized with ClientAssertionSettings."""
        from anncsu.common.auth import PDNDAuthManager

        # Mock settings
        settings = MagicMock()
        settings.to_config.return_value = MagicMock()

        manager = PDNDAuthManager(settings=settings)

        assert manager is not None
        assert manager.settings == settings

    def test_manager_can_be_initialized_with_config(self):
        """Test that manager can be initialized with ClientAssertionConfig."""
        from anncsu.common.auth import PDNDAuthManager

        config = MagicMock()

        manager = PDNDAuthManager(config=config)

        assert manager is not None
        assert manager.config == config

    def test_manager_requires_settings_or_config(self):
        """Test that manager requires either settings or config."""
        from anncsu.common.auth import PDNDAuthManager

        with pytest.raises(ValueError, match="Either 'settings' or 'config'"):
            PDNDAuthManager()

    def test_manager_prefers_config_over_settings(self):
        """Test that config takes precedence over settings."""
        from anncsu.common.auth import PDNDAuthManager

        settings = MagicMock()
        config = MagicMock()

        manager = PDNDAuthManager(settings=settings, config=config)

        # Config should be used directly, settings.to_config() not called
        settings.to_config.assert_not_called()
        assert manager.config == config

    def test_manager_converts_settings_to_config(self):
        """Test that manager converts settings to config when no config provided."""
        from anncsu.common.auth import PDNDAuthManager

        settings = MagicMock()
        mock_config = MagicMock()
        settings.to_config.return_value = mock_config

        manager = PDNDAuthManager(settings=settings)

        settings.to_config.assert_called_once()
        assert manager.config == mock_config

    def test_manager_accepts_token_endpoint(self):
        """Test that manager accepts token_endpoint parameter."""
        from anncsu.common.auth import PDNDAuthManager

        config = MagicMock()
        endpoint = "https://auth.example.com/token.oauth2"

        manager = PDNDAuthManager(config=config, token_endpoint=endpoint)

        assert manager.token_endpoint == endpoint

    def test_manager_accepts_expiration_thresholds(self):
        """Test that manager accepts expiration threshold parameters."""
        from anncsu.common.auth import PDNDAuthManager

        config = MagicMock()

        manager = PDNDAuthManager(
            config=config,
            client_assertion_threshold_seconds=3600,  # 1 hour
            access_token_threshold_seconds=60,  # 1 minute
        )

        assert manager.client_assertion_threshold_seconds == 3600
        assert manager.access_token_threshold_seconds == 60

    def test_manager_default_thresholds(self):
        """Test that manager has sensible default thresholds."""
        from anncsu.common.auth import PDNDAuthManager

        config = MagicMock()

        manager = PDNDAuthManager(config=config)

        # Default client assertion threshold: 1 day (86400 seconds)
        assert manager.client_assertion_threshold_seconds == 86400
        # Default access token threshold: 60 seconds
        assert manager.access_token_threshold_seconds == 60


class TestPDNDAuthManagerClientAssertion:
    """Tests for client assertion management."""

    def test_manager_creates_client_assertion_on_first_request(self):
        """Test that manager creates client assertion when first requested."""
        from anncsu.common.auth import PDNDAuthManager

        config = MagicMock()
        mock_assertion = create_client_assertion()

        with patch(
            "anncsu.common.auth.create_client_assertion",
            return_value=mock_assertion,
        ) as mock_create:
            manager = PDNDAuthManager(config=config)
            assertion = manager.get_client_assertion()

            mock_create.assert_called_once_with(config)
            assert assertion == mock_assertion

    def test_manager_caches_client_assertion(self):
        """Test that manager caches client assertion between calls."""
        from anncsu.common.auth import PDNDAuthManager

        config = MagicMock()
        mock_assertion = create_client_assertion()

        with patch(
            "anncsu.common.auth.create_client_assertion",
            return_value=mock_assertion,
        ) as mock_create:
            manager = PDNDAuthManager(config=config)

            # Get assertion twice
            assertion1 = manager.get_client_assertion()
            assertion2 = manager.get_client_assertion()

            # Should only call create once
            mock_create.assert_called_once()
            assert assertion1 == assertion2

    def test_manager_regenerates_expired_client_assertion(self):
        """Test that manager regenerates expired client assertion."""
        from anncsu.common.auth import PDNDAuthManager

        config = MagicMock()
        expired_assertion = create_expired_client_assertion()
        new_assertion = create_client_assertion()

        with patch(
            "anncsu.common.auth.create_client_assertion",
            return_value=new_assertion,
        ) as mock_create:
            manager = PDNDAuthManager(config=config)

            # Manually set an expired assertion in the cache
            manager._client_assertion = expired_assertion

            # Get assertion - should detect expiration and regenerate
            assertion = manager.get_client_assertion()

            # Should have called create_client_assertion to regenerate
            mock_create.assert_called_once()
            assert assertion == new_assertion

    def test_manager_regenerates_client_assertion_within_threshold(self):
        """Test that manager regenerates assertion when within threshold."""
        from anncsu.common.auth import PDNDAuthManager

        config = MagicMock()

        # Assertion that expires in 12 hours (less than 1 day threshold)
        expiring_soon = create_test_jwt(
            exp=int(time.time()) + 12 * 3600,
            claims={"purposeId": "test"},
        )
        new_assertion = create_client_assertion()

        with patch(
            "anncsu.common.auth.create_client_assertion",
            return_value=new_assertion,
        ) as mock_create:
            manager = PDNDAuthManager(
                config=config,
                client_assertion_threshold_seconds=86400,  # 1 day
            )

            # Manually set cached assertion that's expiring soon
            manager._client_assertion = expiring_soon

            # Should regenerate because TTL < threshold
            assertion = manager.get_client_assertion()

            # Should have called create_client_assertion to regenerate
            mock_create.assert_called_once()
            assert assertion == new_assertion

    def test_manager_client_assertion_ttl(self):
        """Test that manager reports client assertion TTL correctly."""
        from anncsu.common.auth import PDNDAuthManager

        config = MagicMock()
        assertion = create_client_assertion(expires_in_days=30)

        with patch(
            "anncsu.common.auth.create_client_assertion", return_value=assertion
        ):
            manager = PDNDAuthManager(config=config)
            manager.get_client_assertion()

            ttl = manager.client_assertion_ttl()

            # Should be approximately 30 days in seconds
            assert ttl is not None
            assert ttl > 29 * 24 * 3600  # More than 29 days
            assert ttl <= 30 * 24 * 3600  # At most 30 days

    def test_manager_is_client_assertion_expired(self):
        """Test that manager correctly reports client assertion expiration."""
        from anncsu.common.auth import PDNDAuthManager

        config = MagicMock()

        manager = PDNDAuthManager(config=config)

        # No assertion yet
        assert manager.is_client_assertion_expired() is True

        # Set expired assertion
        manager._client_assertion = create_expired_client_assertion()
        assert manager.is_client_assertion_expired() is True

        # Set valid assertion
        manager._client_assertion = create_client_assertion()
        assert manager.is_client_assertion_expired() is False


class TestPDNDAuthManagerAccessToken:
    """Tests for access token management."""

    def test_manager_obtains_access_token(self):
        """Test that manager obtains access token from PDND."""
        from anncsu.common.auth import PDNDAuthManager

        config = MagicMock()
        config.issuer = "test-client-id"
        mock_assertion = create_client_assertion()
        mock_token_response = MagicMock()
        mock_token_response.access_token = create_valid_token()

        with (
            patch(
                "anncsu.common.auth.create_client_assertion",
                return_value=mock_assertion,
            ),
            patch(
                "anncsu.common.auth.get_access_token",
                return_value=mock_token_response,
            ) as mock_get_token,
        ):
            manager = PDNDAuthManager(
                config=config,
                token_endpoint="https://auth.example.com/token.oauth2",
            )

            token = manager.get_access_token()

            mock_get_token.assert_called_once()
            assert token == mock_token_response.access_token

    def test_manager_caches_access_token(self):
        """Test that manager caches access token between calls."""
        from anncsu.common.auth import PDNDAuthManager

        config = MagicMock()
        config.issuer = "test-client-id"
        mock_assertion = create_client_assertion()
        mock_token_response = MagicMock()
        mock_token_response.access_token = create_valid_token()

        with (
            patch(
                "anncsu.common.auth.create_client_assertion",
                return_value=mock_assertion,
            ),
            patch(
                "anncsu.common.auth.get_access_token",
                return_value=mock_token_response,
            ) as mock_get_token,
        ):
            manager = PDNDAuthManager(
                config=config,
                token_endpoint="https://auth.example.com/token.oauth2",
            )

            # Get token twice
            token1 = manager.get_access_token()
            token2 = manager.get_access_token()

            # Should only call get_access_token once
            mock_get_token.assert_called_once()
            assert token1 == token2

    def test_manager_refreshes_expired_access_token(self):
        """Test that manager refreshes expired access token."""
        from anncsu.common.auth import PDNDAuthManager

        config = MagicMock()
        config.issuer = "test-client-id"
        mock_assertion = create_client_assertion()

        expired_token = create_expired_token()
        new_token = create_valid_token()

        mock_response = MagicMock()
        mock_response.access_token = new_token

        with (
            patch(
                "anncsu.common.auth.create_client_assertion",
                return_value=mock_assertion,
            ),
            patch(
                "anncsu.common.auth.get_access_token",
                return_value=mock_response,
            ) as mock_get_token,
        ):
            manager = PDNDAuthManager(
                config=config,
                token_endpoint="https://auth.example.com/token.oauth2",
            )

            # Set expired token in cache
            manager._access_token = expired_token

            # Should detect expiration and refresh
            token = manager.get_access_token()

            # Should have called get_access_token to refresh
            mock_get_token.assert_called_once()
            assert token == new_token

    def test_manager_refreshes_access_token_within_threshold(self):
        """Test that manager refreshes access token when within threshold."""
        from anncsu.common.auth import PDNDAuthManager

        config = MagicMock()
        config.issuer = "test-client-id"
        mock_assertion = create_client_assertion()

        # Token that expires in 30 seconds (less than 60 second threshold)
        expiring_token = create_valid_token(expires_in=30)
        new_token = create_valid_token(expires_in=600)

        mock_response = MagicMock()
        mock_response.access_token = new_token

        with (
            patch(
                "anncsu.common.auth.create_client_assertion",
                return_value=mock_assertion,
            ),
            patch(
                "anncsu.common.auth.get_access_token",
                return_value=mock_response,
            ),
        ):
            manager = PDNDAuthManager(
                config=config,
                token_endpoint="https://auth.example.com/token.oauth2",
                access_token_threshold_seconds=60,
            )

            # Set expiring token in cache
            manager._access_token = expiring_token

            # Should refresh because TTL < threshold
            token = manager.get_access_token()

            assert token == new_token

    def test_manager_access_token_ttl(self):
        """Test that manager reports access token TTL correctly."""
        from anncsu.common.auth import PDNDAuthManager

        config = MagicMock()
        config.issuer = "test-client-id"
        mock_assertion = create_client_assertion()

        access_token = create_valid_token(expires_in=600)
        mock_response = MagicMock()
        mock_response.access_token = access_token

        with (
            patch(
                "anncsu.common.auth.create_client_assertion",
                return_value=mock_assertion,
            ),
            patch(
                "anncsu.common.auth.get_access_token",
                return_value=mock_response,
            ),
        ):
            manager = PDNDAuthManager(
                config=config,
                token_endpoint="https://auth.example.com/token.oauth2",
            )
            manager.get_access_token()

            ttl = manager.access_token_ttl()

            assert ttl is not None
            assert ttl > 500  # More than 500 seconds
            assert ttl <= 600  # At most 600 seconds

    def test_manager_is_access_token_expired(self):
        """Test that manager correctly reports access token expiration."""
        from anncsu.common.auth import PDNDAuthManager

        config = MagicMock()

        manager = PDNDAuthManager(
            config=config,
            token_endpoint="https://auth.example.com/token.oauth2",
        )

        # No token yet
        assert manager.is_access_token_expired() is True

        # Set expired token
        manager._access_token = create_expired_token()
        assert manager.is_access_token_expired() is True

        # Set valid token
        manager._access_token = create_valid_token()
        assert manager.is_access_token_expired() is False


class TestPDNDAuthManagerRefreshCallback:
    """Tests for using PDNDAuthManager as refresh callback for TokenValidationHook."""

    def test_manager_provides_refresh_callback(self):
        """Test that manager provides a callable refresh callback."""
        from anncsu.common.auth import PDNDAuthManager

        config = MagicMock()

        manager = PDNDAuthManager(
            config=config,
            token_endpoint="https://auth.example.com/token.oauth2",
        )

        callback = manager.get_refresh_callback()

        assert callable(callback)

    def test_refresh_callback_returns_new_token(self):
        """Test that refresh callback returns new access token."""
        from anncsu.common.auth import PDNDAuthManager

        config = MagicMock()
        config.issuer = "test-client-id"
        mock_assertion = create_client_assertion()
        new_token = create_valid_token()

        mock_response = MagicMock()
        mock_response.access_token = new_token

        with (
            patch(
                "anncsu.common.auth.create_client_assertion",
                return_value=mock_assertion,
            ),
            patch(
                "anncsu.common.auth.get_access_token",
                return_value=mock_response,
            ),
        ):
            manager = PDNDAuthManager(
                config=config,
                token_endpoint="https://auth.example.com/token.oauth2",
            )

            callback = manager.get_refresh_callback()
            token = callback()

            assert token == new_token

    def test_refresh_callback_forces_refresh(self):
        """Test that refresh callback forces token refresh even if not expired."""
        from anncsu.common.auth import PDNDAuthManager

        config = MagicMock()
        config.issuer = "test-client-id"
        mock_assertion = create_client_assertion()

        old_token = create_valid_token(expires_in=600)
        new_token = create_valid_token(expires_in=600)

        mock_response = MagicMock()
        mock_response.access_token = new_token

        with (
            patch(
                "anncsu.common.auth.create_client_assertion",
                return_value=mock_assertion,
            ),
            patch(
                "anncsu.common.auth.get_access_token",
                return_value=mock_response,
            ) as mock_get_token,
        ):
            manager = PDNDAuthManager(
                config=config,
                token_endpoint="https://auth.example.com/token.oauth2",
            )

            # Set a valid token in cache
            manager._access_token = old_token

            # Callback should force refresh
            callback = manager.get_refresh_callback()
            token = callback()

            # get_access_token should have been called
            mock_get_token.assert_called_once()
            assert token == new_token

    def test_manager_integrates_with_token_validation_hook(self):
        """Test that manager integrates with TokenValidationHook."""
        from anncsu.common.auth import PDNDAuthManager
        from anncsu.common.hooks.sdkhooks import SDKHooks
        from anncsu.common.hooks.token_validation import (
            register_token_validation_hook,
        )

        config = MagicMock()
        config.issuer = "test-client-id"

        manager = PDNDAuthManager(
            config=config,
            token_endpoint="https://auth.example.com/token.oauth2",
        )

        hooks = SDKHooks()

        # Should not raise
        hook = register_token_validation_hook(
            hooks,
            expiration_threshold_seconds=60,
            refresh_callback=manager.get_refresh_callback(),
        )

        assert hook.refresh_callback is not None


class TestPDNDAuthManagerSecurity:
    """Tests for Security object creation."""

    def test_manager_creates_security_object(self):
        """Test that manager creates Security object with access token."""
        from anncsu.common.auth import PDNDAuthManager
        from anncsu.common.security import Security

        config = MagicMock()
        config.issuer = "test-client-id"
        mock_assertion = create_client_assertion()
        access_token = create_valid_token()

        mock_response = MagicMock()
        mock_response.access_token = access_token

        with (
            patch(
                "anncsu.common.auth.create_client_assertion",
                return_value=mock_assertion,
            ),
            patch(
                "anncsu.common.auth.get_access_token",
                return_value=mock_response,
            ),
        ):
            manager = PDNDAuthManager(
                config=config,
                token_endpoint="https://auth.example.com/token.oauth2",
            )

            security = manager.get_security()

            assert isinstance(security, Security)
            assert security.bearer == access_token

    def test_manager_security_uses_cached_token(self):
        """Test that get_security uses cached access token."""
        from anncsu.common.auth import PDNDAuthManager

        config = MagicMock()
        config.issuer = "test-client-id"
        mock_assertion = create_client_assertion()
        access_token = create_valid_token()

        mock_response = MagicMock()
        mock_response.access_token = access_token

        with (
            patch(
                "anncsu.common.auth.create_client_assertion",
                return_value=mock_assertion,
            ),
            patch(
                "anncsu.common.auth.get_access_token",
                return_value=mock_response,
            ) as mock_get_token,
        ):
            manager = PDNDAuthManager(
                config=config,
                token_endpoint="https://auth.example.com/token.oauth2",
            )

            # Get security twice
            security1 = manager.get_security()
            security2 = manager.get_security()

            # get_access_token should only be called once
            mock_get_token.assert_called_once()
            assert security1.bearer == security2.bearer


class TestPDNDAuthManagerErrors:
    """Tests for error handling."""

    def test_manager_raises_on_client_assertion_failure(self):
        """Test that manager raises error when client assertion fails."""
        from anncsu.common.auth import PDNDAuthManager
        from anncsu.common.pdnd_assertion import JWTGenerationError

        config = MagicMock()

        with patch(
            "anncsu.common.auth.create_client_assertion",
            side_effect=JWTGenerationError("Key error"),
        ):
            manager = PDNDAuthManager(config=config)

            with pytest.raises(JWTGenerationError):
                manager.get_client_assertion()

    def test_manager_raises_on_token_request_failure(self):
        """Test that manager raises error when token request fails."""
        from anncsu.common.auth import PDNDAuthManager
        from anncsu.common.pdnd_token import TokenRequestError

        config = MagicMock()
        config.issuer = "test-client-id"
        mock_assertion = create_client_assertion()

        with (
            patch(
                "anncsu.common.auth.create_client_assertion",
                return_value=mock_assertion,
            ),
            patch(
                "anncsu.common.auth.get_access_token",
                side_effect=TokenRequestError("Network error"),
            ),
        ):
            manager = PDNDAuthManager(
                config=config,
                token_endpoint="https://auth.example.com/token.oauth2",
            )

            with pytest.raises(TokenRequestError):
                manager.get_access_token()

    def test_manager_regenerates_client_assertion_on_token_error(self):
        """Test manager regenerates client assertion if token request fails due to assertion."""
        from anncsu.common.auth import PDNDAuthManager
        from anncsu.common.pdnd_token import TokenResponseError

        config = MagicMock()
        config.issuer = "test-client-id"
        old_assertion = create_client_assertion()
        new_assertion = create_client_assertion()
        valid_token = create_valid_token()

        mock_response = MagicMock()
        mock_response.access_token = valid_token

        # First call fails with assertion error, second succeeds
        call_count = 0

        def mock_get_token(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise TokenResponseError(
                    "Invalid assertion",
                    error="invalid_client",
                    error_description="Client assertion expired",
                )
            return mock_response

        with (
            patch(
                "anncsu.common.auth.create_client_assertion",
                side_effect=[old_assertion, new_assertion],
            ),
            patch(
                "anncsu.common.auth.get_access_token",
                side_effect=mock_get_token,
            ),
        ):
            manager = PDNDAuthManager(
                config=config,
                token_endpoint="https://auth.example.com/token.oauth2",
            )

            # First attempt should fail and retry with new assertion
            token = manager.get_access_token()

            assert token == valid_token


class TestPDNDAuthManagerExports:
    """Tests for module exports."""

    def test_pdnd_auth_manager_exported_from_auth_module(self):
        """Test that PDNDAuthManager is exported from auth module."""
        from anncsu.common.auth import PDNDAuthManager

        assert PDNDAuthManager is not None

    def test_pdnd_auth_manager_exported_from_common_module(self):
        """Test that PDNDAuthManager is exported from common module."""
        from anncsu.common import PDNDAuthManager

        assert PDNDAuthManager is not None
