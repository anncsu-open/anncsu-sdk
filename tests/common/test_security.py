"""
Tests for the Security class with token expiration validation.
"""

from __future__ import annotations

import time

import pytest
from authlib.jose import jwt

from anncsu.common.security import Security, TokenExpiredError


def create_test_token(exp_offset: int = 600, include_exp: bool = True) -> str:
    """Create a test JWT token with specified expiration offset.

    Args:
        exp_offset: Seconds from now until expiration (negative for expired).
        include_exp: Whether to include the exp claim.

    Returns:
        A JWT token string.
    """
    header = {"alg": "HS256", "typ": "JWT"}
    payload = {
        "sub": "test-subject",
        "iss": "test-issuer",
        "iat": int(time.time()),
    }

    if include_exp:
        payload["exp"] = int(time.time()) + exp_offset

    # Create a simple token (we're not verifying signatures)
    return jwt.encode(header, payload, "test-secret").decode("utf-8")


class TestSecurityTokenExpiration:
    """Tests for token expiration validation in Security class."""

    def test_valid_token_accepted(self):
        """Test that a valid (non-expired) token is accepted."""
        token = create_test_token(exp_offset=600)  # Expires in 10 minutes
        security = Security(bearer=token)
        assert security.bearer == token

    def test_expired_token_raises_error(self):
        """Test that an expired token raises TokenExpiredError."""
        token = create_test_token(exp_offset=-60)  # Expired 1 minute ago

        with pytest.raises(TokenExpiredError) as exc_info:
            Security(bearer=token)

        assert "expired" in str(exc_info.value).lower()
        assert exc_info.value.expired_at is not None
        assert exc_info.value.current_time is not None
        assert exc_info.value.current_time >= exc_info.value.expired_at

    def test_expired_token_with_validation_disabled(self):
        """Test that expired token is accepted when validation is disabled."""
        token = create_test_token(exp_offset=-60)  # Expired 1 minute ago

        # Should not raise with validation disabled
        security = Security(bearer=token, validate_expiration=False)
        assert security.bearer == token

    def test_token_without_exp_claim(self):
        """Test that a token without exp claim is accepted."""
        token = create_test_token(include_exp=False)
        security = Security(bearer=token)
        assert security.bearer == token

    def test_none_bearer_accepted(self):
        """Test that None bearer is accepted (no validation needed)."""
        security = Security(bearer=None)
        assert security.bearer is None

    def test_invalid_token_format_skips_validation(self):
        """Test that invalid token format skips validation gracefully."""
        # Invalid JWT format - should not raise, let API handle it
        security = Security(bearer="not-a-valid-jwt")
        assert security.bearer == "not-a-valid-jwt"


class TestSecurityIsExpired:
    """Tests for the is_expired() method."""

    def test_is_expired_false_for_valid_token(self):
        """Test is_expired returns False for valid token."""
        token = create_test_token(exp_offset=600)
        security = Security(bearer=token)
        assert security.is_expired() is False

    def test_is_expired_true_for_expired_token(self):
        """Test is_expired returns True for expired token."""
        token = create_test_token(exp_offset=-60)
        security = Security(bearer=token, validate_expiration=False)
        assert security.is_expired() is True

    def test_is_expired_true_for_none_bearer(self):
        """Test is_expired returns True when bearer is None."""
        security = Security(bearer=None)
        assert security.is_expired() is True

    def test_is_expired_false_for_token_without_exp(self):
        """Test is_expired returns False when token has no exp claim."""
        token = create_test_token(include_exp=False)
        security = Security(bearer=token)
        assert security.is_expired() is False

    def test_is_expired_true_for_invalid_token(self):
        """Test is_expired returns True for invalid token format."""
        security = Security(bearer="invalid-token", validate_expiration=False)
        assert security.is_expired() is True


class TestSecurityTimeUntilExpiration:
    """Tests for the time_until_expiration() method."""

    def test_time_until_expiration_positive_for_valid_token(self):
        """Test time_until_expiration returns positive value for valid token."""
        token = create_test_token(exp_offset=600)
        security = Security(bearer=token)
        ttl = security.time_until_expiration()

        assert ttl is not None
        assert 595 <= ttl <= 600  # Allow small timing variance

    def test_time_until_expiration_negative_for_expired_token(self):
        """Test time_until_expiration returns negative value for expired token."""
        token = create_test_token(exp_offset=-60)
        security = Security(bearer=token, validate_expiration=False)
        ttl = security.time_until_expiration()

        assert ttl is not None
        assert ttl < 0

    def test_time_until_expiration_none_for_none_bearer(self):
        """Test time_until_expiration returns None when bearer is None."""
        security = Security(bearer=None)
        assert security.time_until_expiration() is None

    def test_time_until_expiration_none_for_token_without_exp(self):
        """Test time_until_expiration returns None when token has no exp claim."""
        token = create_test_token(include_exp=False)
        security = Security(bearer=token)
        assert security.time_until_expiration() is None

    def test_time_until_expiration_none_for_invalid_token(self):
        """Test time_until_expiration returns None for invalid token format."""
        security = Security(bearer="invalid-token", validate_expiration=False)
        assert security.time_until_expiration() is None


class TestTokenExpiredErrorAttributes:
    """Tests for TokenExpiredError exception attributes."""

    def test_error_attributes(self):
        """Test that TokenExpiredError has correct attributes."""
        token = create_test_token(exp_offset=-60)

        with pytest.raises(TokenExpiredError) as exc_info:
            Security(bearer=token)

        error = exc_info.value
        assert error.expired_at is not None
        assert error.current_time is not None
        assert isinstance(error.expired_at, int)
        assert isinstance(error.current_time, int)

    def test_error_message_contains_timestamps(self):
        """Test that error message contains timestamp information."""
        token = create_test_token(exp_offset=-60)

        with pytest.raises(TokenExpiredError) as exc_info:
            Security(bearer=token)

        message = str(exc_info.value)
        assert "expired" in message.lower()
        assert "get_access_token" in message


class TestSecuritySerialization:
    """Tests for Security serialization behavior."""

    def test_validate_expiration_excluded_from_serialization(self):
        """Test that validate_expiration field is excluded from model_dump."""
        token = create_test_token(exp_offset=600)
        security = Security(bearer=token, validate_expiration=True)

        dumped = security.model_dump()
        assert "validate_expiration" not in dumped
        assert "bearer" in dumped

    def test_validate_expiration_excluded_from_json(self):
        """Test that validate_expiration field is excluded from JSON."""
        token = create_test_token(exp_offset=600)
        security = Security(bearer=token, validate_expiration=True)

        json_str = security.model_dump_json()
        assert "validate_expiration" not in json_str
        assert "bearer" in json_str
