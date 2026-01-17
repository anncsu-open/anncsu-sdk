"""Tests for pre-request token validation hook.

This module tests the TokenValidationHook that validates token expiration
before each API request, preventing unnecessary HTTP calls with expired tokens.
"""

from __future__ import annotations

import base64
import json
import time
from typing import TYPE_CHECKING
from unittest.mock import MagicMock

import httpx

if TYPE_CHECKING:
    pass


# Helper to create JWT tokens for testing
def create_test_jwt(exp: int, iat: int | None = None) -> str:
    """Create a test JWT token with specified expiration.

    Args:
        exp: Expiration timestamp (Unix epoch seconds)
        iat: Issued at timestamp (defaults to exp - 600)

    Returns:
        JWT token string (not cryptographically signed, for testing only)
    """
    if iat is None:
        iat = exp - 600

    header = {"alg": "RS256", "typ": "JWT"}
    payload = {
        "iss": "test-issuer",
        "sub": "test-subject",
        "aud": "test-audience",
        "exp": exp,
        "iat": iat,
    }

    def b64_encode(data: dict) -> str:
        return base64.urlsafe_b64encode(json.dumps(data).encode()).decode().rstrip("=")

    # Create unsigned JWT (signature is just placeholder for testing)
    return f"{b64_encode(header)}.{b64_encode(payload)}.fake_signature"


def create_expired_token(seconds_ago: int = 60) -> str:
    """Create a token that expired N seconds ago."""
    return create_test_jwt(exp=int(time.time()) - seconds_ago)


def create_valid_token(expires_in: int = 600) -> str:
    """Create a token that expires in N seconds."""
    return create_test_jwt(exp=int(time.time()) + expires_in)


def create_expiring_soon_token(expires_in: int = 30) -> str:
    """Create a token that expires in N seconds (soon)."""
    return create_test_jwt(exp=int(time.time()) + expires_in)


class TestTokenValidationHook:
    """Tests for TokenValidationHook class."""

    def test_hook_implements_before_request_hook_interface(self):
        """Test that TokenValidationHook implements BeforeRequestHook."""
        from anncsu.common.hooks.token_validation import TokenValidationHook
        from anncsu.common.hooks.types import BeforeRequestHook

        hook = TokenValidationHook()
        assert isinstance(hook, BeforeRequestHook)

    def test_hook_allows_valid_token(self):
        """Test that hook allows requests with valid (non-expired) tokens."""
        from anncsu.common.hooks.token_validation import TokenValidationHook
        from anncsu.common.security import Security

        token = create_valid_token(expires_in=600)
        security = Security(bearer=token, validate_expiration=False)

        hook = TokenValidationHook()
        request = httpx.Request("GET", "https://api.example.com/test")

        # Create mock context with security
        ctx = MagicMock()
        ctx.security_source = security

        result = hook.before_request(ctx, request)

        # Should return the request unchanged
        assert result == request

    def test_hook_raises_token_expired_error_for_expired_token(self):
        """Test that hook raises TokenExpiredError for expired tokens."""
        from anncsu.common.hooks.token_validation import TokenValidationHook
        from anncsu.common.security import Security, TokenExpiredError

        token = create_expired_token(seconds_ago=60)
        security = Security(bearer=token, validate_expiration=False)

        hook = TokenValidationHook()
        request = httpx.Request("GET", "https://api.example.com/test")

        ctx = MagicMock()
        ctx.security_source = security

        result = hook.before_request(ctx, request)

        # Should return an exception
        assert isinstance(result, TokenExpiredError)

    def test_hook_allows_request_when_no_security_configured(self):
        """Test that hook allows requests when no security is configured."""
        from anncsu.common.hooks.token_validation import TokenValidationHook

        hook = TokenValidationHook()
        request = httpx.Request("GET", "https://api.example.com/test")

        ctx = MagicMock()
        ctx.security_source = None

        result = hook.before_request(ctx, request)

        # Should return the request unchanged
        assert result == request

    def test_hook_allows_request_when_bearer_is_none(self):
        """Test that hook allows requests when bearer token is None."""
        from anncsu.common.hooks.token_validation import TokenValidationHook
        from anncsu.common.security import Security

        security = Security(bearer=None)

        hook = TokenValidationHook()
        request = httpx.Request("GET", "https://api.example.com/test")

        ctx = MagicMock()
        ctx.security_source = security

        result = hook.before_request(ctx, request)

        # Should return the request unchanged
        assert result == request


class TestTokenValidationHookWithThreshold:
    """Tests for TokenValidationHook with expiration threshold."""

    def test_hook_with_threshold_raises_for_expiring_soon_token(self):
        """Test that hook raises error when token expires within threshold."""
        from anncsu.common.hooks.token_validation import TokenValidationHook
        from anncsu.common.security import Security, TokenExpiredError

        # Token expires in 30 seconds, threshold is 60 seconds
        token = create_expiring_soon_token(expires_in=30)
        security = Security(bearer=token, validate_expiration=False)

        hook = TokenValidationHook(expiration_threshold_seconds=60)
        request = httpx.Request("GET", "https://api.example.com/test")

        ctx = MagicMock()
        ctx.security_source = security

        result = hook.before_request(ctx, request)

        # Should return an exception because token expires within threshold
        assert isinstance(result, TokenExpiredError)

    def test_hook_with_threshold_allows_token_outside_threshold(self):
        """Test that hook allows token when expiration is outside threshold."""
        from anncsu.common.hooks.token_validation import TokenValidationHook
        from anncsu.common.security import Security

        # Token expires in 120 seconds, threshold is 60 seconds
        token = create_valid_token(expires_in=120)
        security = Security(bearer=token, validate_expiration=False)

        hook = TokenValidationHook(expiration_threshold_seconds=60)
        request = httpx.Request("GET", "https://api.example.com/test")

        ctx = MagicMock()
        ctx.security_source = security

        result = hook.before_request(ctx, request)

        # Should return the request unchanged
        assert result == request

    def test_hook_default_threshold_is_zero(self):
        """Test that default expiration threshold is 0 (no early expiration)."""
        from anncsu.common.hooks.token_validation import TokenValidationHook

        hook = TokenValidationHook()
        assert hook.expiration_threshold_seconds == 0

    def test_hook_custom_threshold_is_stored(self):
        """Test that custom expiration threshold is stored correctly."""
        from anncsu.common.hooks.token_validation import TokenValidationHook

        hook = TokenValidationHook(expiration_threshold_seconds=120)
        assert hook.expiration_threshold_seconds == 120


class TestTokenValidationHookWithAutoRefresh:
    """Tests for TokenValidationHook with auto-refresh capability."""

    def test_hook_with_refresh_callback_refreshes_expired_token(self):
        """Test that hook calls refresh callback when token is expired."""
        from anncsu.common.hooks.token_validation import TokenValidationHook
        from anncsu.common.security import Security

        expired_token = create_expired_token(seconds_ago=60)
        new_token = create_valid_token(expires_in=600)

        # Mock refresh callback
        refresh_callback = MagicMock(return_value=new_token)

        security = Security(bearer=expired_token, validate_expiration=False)

        hook = TokenValidationHook(refresh_callback=refresh_callback)
        request = httpx.Request("GET", "https://api.example.com/test")

        ctx = MagicMock()
        ctx.security_source = security

        result = hook.before_request(ctx, request)

        # Refresh callback should have been called
        refresh_callback.assert_called_once()

        # Should return the request (allowing it to proceed with new token)
        assert result == request

    def test_hook_with_refresh_callback_updates_security_bearer(self):
        """Test that hook updates security.bearer with new token after refresh."""
        from anncsu.common.hooks.token_validation import TokenValidationHook
        from anncsu.common.security import Security

        expired_token = create_expired_token(seconds_ago=60)
        new_token = create_valid_token(expires_in=600)

        refresh_callback = MagicMock(return_value=new_token)

        security = Security(bearer=expired_token, validate_expiration=False)

        hook = TokenValidationHook(refresh_callback=refresh_callback)
        request = httpx.Request("GET", "https://api.example.com/test")

        ctx = MagicMock()
        ctx.security_source = security

        hook.before_request(ctx, request)

        # Security bearer should be updated with new token
        assert security.bearer == new_token

    def test_hook_raises_if_refresh_callback_fails(self):
        """Test that hook raises error if refresh callback raises exception."""
        from anncsu.common.hooks.token_validation import (
            TokenRefreshError,
            TokenValidationHook,
        )
        from anncsu.common.security import Security

        expired_token = create_expired_token(seconds_ago=60)

        # Mock refresh callback that raises an exception
        refresh_callback = MagicMock(side_effect=Exception("Refresh failed"))

        security = Security(bearer=expired_token, validate_expiration=False)

        hook = TokenValidationHook(refresh_callback=refresh_callback)
        request = httpx.Request("GET", "https://api.example.com/test")

        ctx = MagicMock()
        ctx.security_source = security

        result = hook.before_request(ctx, request)

        # Should return a TokenRefreshError
        assert isinstance(result, TokenRefreshError)

    def test_hook_raises_if_refresh_callback_returns_none(self):
        """Test that hook raises error if refresh callback returns None."""
        from anncsu.common.hooks.token_validation import (
            TokenRefreshError,
            TokenValidationHook,
        )
        from anncsu.common.security import Security

        expired_token = create_expired_token(seconds_ago=60)

        refresh_callback = MagicMock(return_value=None)

        security = Security(bearer=expired_token, validate_expiration=False)

        hook = TokenValidationHook(refresh_callback=refresh_callback)
        request = httpx.Request("GET", "https://api.example.com/test")

        ctx = MagicMock()
        ctx.security_source = security

        result = hook.before_request(ctx, request)

        # Should return a TokenRefreshError
        assert isinstance(result, TokenRefreshError)

    def test_hook_raises_if_refresh_callback_returns_expired_token(self):
        """Test that hook raises error if refresh returns another expired token."""
        from anncsu.common.hooks.token_validation import (
            TokenRefreshError,
            TokenValidationHook,
        )
        from anncsu.common.security import Security

        expired_token = create_expired_token(seconds_ago=60)
        still_expired_token = create_expired_token(seconds_ago=30)

        refresh_callback = MagicMock(return_value=still_expired_token)

        security = Security(bearer=expired_token, validate_expiration=False)

        hook = TokenValidationHook(refresh_callback=refresh_callback)
        request = httpx.Request("GET", "https://api.example.com/test")

        ctx = MagicMock()
        ctx.security_source = security

        result = hook.before_request(ctx, request)

        # Should return a TokenRefreshError
        assert isinstance(result, TokenRefreshError)

    def test_hook_without_refresh_callback_raises_token_expired(self):
        """Test that hook raises TokenExpiredError when no refresh callback."""
        from anncsu.common.hooks.token_validation import TokenValidationHook
        from anncsu.common.security import Security, TokenExpiredError

        expired_token = create_expired_token(seconds_ago=60)
        security = Security(bearer=expired_token, validate_expiration=False)

        # No refresh callback provided
        hook = TokenValidationHook(refresh_callback=None)
        request = httpx.Request("GET", "https://api.example.com/test")

        ctx = MagicMock()
        ctx.security_source = security

        result = hook.before_request(ctx, request)

        # Should return TokenExpiredError, not TokenRefreshError
        assert isinstance(result, TokenExpiredError)


class TestTokenRefreshError:
    """Tests for TokenRefreshError exception."""

    def test_token_refresh_error_is_exception(self):
        """Test that TokenRefreshError is an Exception."""
        from anncsu.common.hooks.token_validation import TokenRefreshError

        error = TokenRefreshError("Refresh failed")
        assert isinstance(error, Exception)

    def test_token_refresh_error_with_cause(self):
        """Test TokenRefreshError with original cause."""
        from anncsu.common.hooks.token_validation import TokenRefreshError

        original = ValueError("Original error")
        error = TokenRefreshError("Refresh failed", cause=original)

        assert error.cause == original
        assert "Refresh failed" in str(error)


class TestTokenValidationHookRegistration:
    """Tests for registering TokenValidationHook with SDK hooks system."""

    def test_hook_can_be_registered_with_hooks_system(self):
        """Test that hook can be registered with Speakeasy hooks system."""
        from anncsu.common.hooks.sdkhooks import SDKHooks
        from anncsu.common.hooks.token_validation import TokenValidationHook

        hooks = SDKHooks()
        hook = TokenValidationHook()

        # Should not raise
        hooks.register_before_request_hook(hook)

    def test_register_token_validation_helper_function(self):
        """Test helper function to register token validation hook."""
        from anncsu.common.hooks.sdkhooks import SDKHooks
        from anncsu.common.hooks.token_validation import register_token_validation_hook

        hooks = SDKHooks()

        # Helper function should register the hook
        hook = register_token_validation_hook(hooks)

        # Should return the created hook instance
        from anncsu.common.hooks.token_validation import TokenValidationHook

        assert isinstance(hook, TokenValidationHook)

    def test_register_token_validation_with_options(self):
        """Test registering hook with custom options."""
        from anncsu.common.hooks.sdkhooks import SDKHooks
        from anncsu.common.hooks.token_validation import register_token_validation_hook

        hooks = SDKHooks()

        refresh_callback = MagicMock()
        hook = register_token_validation_hook(
            hooks,
            expiration_threshold_seconds=60,
            refresh_callback=refresh_callback,
        )

        assert hook.expiration_threshold_seconds == 60
        assert hook.refresh_callback == refresh_callback


class TestTokenValidationHookExports:
    """Tests for module exports."""

    def test_hook_exported_from_hooks_module(self):
        """Test that TokenValidationHook is exported from hooks module."""
        from anncsu.common.hooks import TokenValidationHook

        assert TokenValidationHook is not None

    def test_token_refresh_error_exported_from_hooks_module(self):
        """Test that TokenRefreshError is exported from hooks module."""
        from anncsu.common.hooks import TokenRefreshError

        assert TokenRefreshError is not None

    def test_register_function_exported_from_hooks_module(self):
        """Test that register_token_validation_hook is exported."""
        from anncsu.common.hooks import register_token_validation_hook

        assert register_token_validation_hook is not None

    def test_exports_from_common_module(self):
        """Test that key classes are exported from anncsu.common."""
        from anncsu.common import TokenExpiredError

        # TokenRefreshError should also be exported from common
        from anncsu.common import TokenRefreshError

        assert TokenExpiredError is not None
        assert TokenRefreshError is not None
