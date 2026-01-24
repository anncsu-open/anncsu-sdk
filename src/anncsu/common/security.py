"""Security configuration for ANNCSU APIs.

This module provides the Security class that handles authentication
across all ANNCSU API specifications using PDND Voucher tokens.
"""

from __future__ import annotations

import base64
import json
import time
from typing import Annotated

from authlib.jose import JWTClaims
from authlib.jose.errors import ExpiredTokenError as AuthlibExpiredTokenError
from pydantic import Field, model_validator

from anncsu.common.sdk.types import BaseModel
from anncsu.common.sdk.utils import FieldMetadata, SecurityMetadata


def _decode_jwt_claims(token: str) -> JWTClaims | None:
    """Decode JWT and return claims without signature verification.

    This function decodes the JWT payload and creates a JWTClaims object
    that can be used for expiration validation.

    Args:
        token: JWT token string.

    Returns:
        JWTClaims object, or None if decoding fails.
    """
    try:
        parts = token.split(".")
        if len(parts) != 3:
            return None

        # Decode header
        header_b64 = parts[0] + "=" * (4 - len(parts[0]) % 4)
        header = json.loads(base64.urlsafe_b64decode(header_b64))

        # Decode payload
        payload_b64 = parts[1] + "=" * (4 - len(parts[1]) % 4)
        payload = json.loads(base64.urlsafe_b64decode(payload_b64))

        return JWTClaims(payload, header)
    except Exception:
        return None


class TokenExpiredError(Exception):
    """Exception raised when the access token has expired.

    Attributes:
        message: Error message describing the expiration.
        expired_at: Unix timestamp when the token expired.
        current_time: Current Unix timestamp.
    """

    def __init__(
        self,
        message: str,
        expired_at: int | None = None,
        current_time: int | None = None,
    ):
        super().__init__(message)
        self.expired_at = expired_at
        self.current_time = current_time


class Security(BaseModel):
    """Security configuration for ANNCSU API authentication.

    All ANNCSU APIs use PDND (Piattaforma Digitale Nazionale Dati) voucher-based
    authentication with HTTP Bearer tokens.

    Attributes:
        bearer: PDND voucher token for Bearer authentication.
                This token is included in the Authorization header as "Bearer <token>".
        validate_expiration: If True (default), validates that the token is not expired
                            when the Security object is created.

    Raises:
        TokenExpiredError: If validate_expiration is True and the token has expired.

    Example:
        >>> security = Security(bearer="your-pdnd-voucher-token")
        >>> # Token will be used in Authorization: Bearer your-pdnd-voucher-token

        >>> # To skip expiration validation (not recommended):
        >>> security = Security(bearer="your-token", validate_expiration=False)
    """

    bearer: Annotated[
        str | None,
        Field(default=None),
        FieldMetadata(
            security=SecurityMetadata(
                scheme=True,
                scheme_type="http",
                sub_type="bearer",
                field_name="Authorization",
            )
        ),
    ] = None

    validate_expiration: Annotated[
        bool,
        Field(
            default=True,
            description="Whether to validate token expiration on initialization",
            exclude=True,  # Don't include in serialization
        ),
    ] = True

    @model_validator(mode="after")
    def check_token_expiration(self) -> "Security":
        """Validate that the bearer token is not expired."""
        if not self.validate_expiration or self.bearer is None:
            return self

        claims = _decode_jwt_claims(self.bearer)
        if claims is None:
            # Can't decode token, skip validation (let API return actual error)
            return self

        try:
            # Use authlib's built-in expiration validation
            claims.validate_exp(time.time(), 0)
        except AuthlibExpiredTokenError:
            exp = claims.get("exp")
            current_time = int(time.time())
            raise TokenExpiredError(
                f"Access token has expired. Token expired at {exp}, "
                f"current time is {current_time}. "
                "Please obtain a new access token using get_access_token().",
                expired_at=exp,
                current_time=current_time,
            ) from None

        return self

    def is_expired(self) -> bool:
        """Check if the bearer token is expired.

        Returns:
            True if the token is expired, False otherwise.
            Returns True if bearer is None or cannot be decoded.
            Returns False if token has no exp claim (assume valid).
        """
        if self.bearer is None:
            return True

        claims = _decode_jwt_claims(self.bearer)
        if claims is None:
            return True  # Can't decode, assume expired

        try:
            claims.validate_exp(time.time(), 0)
            return False
        except AuthlibExpiredTokenError:
            return True

    def time_until_expiration(self) -> int | None:
        """Get the number of seconds until the token expires.

        Returns:
            Number of seconds until expiration, or None if token is None,
            has no exp claim, or cannot be decoded. Returns negative value
            if already expired.
        """
        if self.bearer is None:
            return None

        claims = _decode_jwt_claims(self.bearer)
        if claims is None:
            return None

        exp = claims.get("exp")
        if exp is None:
            return None

        return exp - int(time.time())
