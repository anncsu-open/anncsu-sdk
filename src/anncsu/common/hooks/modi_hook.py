# SPDX-FileCopyrightText: 2025-present Geobeyond <info@geobeyond.it>
# SPDX-License-Identifier: MIT
"""
ModI Pre-Request Hook for ANNCSU APIs.

This hook intercepts HTTP requests AFTER Speakeasy has serialized the body,
computes the SHA-256 digest from the actual bytes, and injects ModI headers:
- Digest: HTTP Digest header (RFC 3230)
- Agid-JWT-Signature: INTEGRITY_REST_02 pattern
- Agid-JWT-TrackingEvidence: AUDIT_REST_02 pattern (optional)

The key insight is that this hook calculates the digest from request.content
(the actual serialized bytes) rather than from a Python dictionary. This ensures
the Digest header matches exactly what the server receives.

Example usage:
    >>> from anncsu.common.hooks.modi_hook import ModIPreRequestHook, register_modi_hook
    >>> from anncsu.common.modi import ModIConfig, AuditContext
    >>>
    >>> config = ModIConfig(
    ...     private_key=key_bytes,
    ...     kid="my-key-id",
    ...     issuer="my-client-id",
    ...     audience="https://api.example.com",
    ... )
    >>> audit = AuditContext(
    ...     user_id="batch-user",
    ...     user_location="server-01",
    ...     loa="SPID_L2",
    ... )
    >>>
    >>> # Register with SDK hooks
    >>> hooks = SDKHooks()
    >>> register_modi_hook(hooks, config=config, audit_context=audit)
"""

from __future__ import annotations

import base64
import hashlib
import uuid
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Union

import httpx

from anncsu.common.hooks.types import BeforeRequestContext, BeforeRequestHook

if TYPE_CHECKING:
    from anncsu.common.hooks.sdkhooks import SDKHooks
    from anncsu.common.modi import AuditContext, ModIConfig


class ModIHookError(Exception):
    """Exception raised when ModI header generation fails.

    Attributes:
        message: Human-readable error message.
        cause: Original exception that caused this error, if any.
    """

    def __init__(self, message: str, cause: Exception | None = None):
        """Initialize ModIHookError.

        Args:
            message: Human-readable error message.
            cause: Original exception that caused this error.
        """
        super().__init__(message)
        self.message = message
        self.cause = cause

    def __str__(self) -> str:
        """Return string representation."""
        if self.cause:
            return f"{self.message}: {self.cause}"
        return self.message


class ModIPreRequestHook(BeforeRequestHook):
    """Pre-request hook that injects ModI headers.

    This hook:
    1. Reads the actual serialized body from the request
    2. Computes SHA-256 digest from those exact bytes
    3. Generates Agid-JWT-Signature with the digest in signed_headers claim
    4. Optionally generates Agid-JWT-TrackingEvidence for audit
    5. Returns a new request with all ModI headers added

    The hook only processes POST/PUT/PATCH requests with a body.
    GET/DELETE requests and requests without a body are passed through unchanged.
    """

    def __init__(
        self,
        config: "ModIConfig",
        audit_context: "AuditContext | None" = None,
    ):
        """Initialize the ModI pre-request hook.

        Args:
            config: ModI configuration with private key and audience.
            audit_context: Optional audit context for tracking header.
                If None, only Digest and Signature headers are generated.
        """
        self._config = config
        self._audit_context = audit_context

    def before_request(
        self,
        hook_ctx: BeforeRequestContext,
        request: httpx.Request,
    ) -> Union[httpx.Request, Exception]:
        """Process request and add ModI headers.

        Args:
            hook_ctx: Hook context (not used, but required by interface).
            request: The HTTP request to process.

        Returns:
            Modified request with ModI headers, or original request if skipped,
            or ModIHookError if header generation fails.
        """
        # Skip if not a method that has a body
        if request.method.upper() in ("GET", "DELETE", "HEAD", "OPTIONS"):
            return request

        # Skip if no body
        body = request.content
        if not body:
            return request

        try:
            # Compute digest from actual body bytes
            digest_value = self._compute_digest(body)

            # Get content type from request headers
            content_type = request.headers.get("Content-Type", "application/json")

            # Generate ModI headers
            headers = dict(request.headers)
            headers["Digest"] = digest_value
            headers["Agid-JWT-Signature"] = self._generate_signature(
                digest_value, content_type
            )

            if self._audit_context:
                headers["Agid-JWT-TrackingEvidence"] = self._generate_tracking()

            # Create new request with updated headers
            return httpx.Request(
                method=request.method,
                url=request.url,
                headers=headers,
                content=body,
            )

        except Exception as e:
            return ModIHookError("Failed to generate ModI headers", cause=e)

    def _compute_digest(self, body: bytes) -> str:
        """Compute SHA-256 digest from body bytes.

        Uses standard base64 encoding with padding as per RFC 3230.

        Args:
            body: Raw request body bytes.

        Returns:
            Digest value in format "SHA-256=<base64-encoded-hash>"
        """
        digest = hashlib.sha256(body).digest()
        digest_b64 = base64.b64encode(digest).decode("utf-8")
        return f"SHA-256={digest_b64}"

    def _generate_signature(
        self,
        digest_value: str,
        content_type: str,
    ) -> str:
        """Generate Agid-JWT-Signature header (INTEGRITY_REST_02).

        Args:
            digest_value: Pre-computed digest value.
            content_type: Content-Type header value.

        Returns:
            Signed JWT string.
        """
        # Import here to avoid circular imports
        from authlib.jose import jwt

        now = datetime.now(timezone.utc)
        iat = int(now.timestamp())

        claims = {
            "iss": self._config.issuer,
            "aud": self._config.audience,
            "iat": iat,
            "nbf": iat,
            "exp": iat + self._config.validity_seconds,
            "jti": str(uuid.uuid4()),
            "signed_headers": [
                {"digest": digest_value},
                {"content-type": content_type},
            ],
        }

        header = {
            "alg": self._config.alg,
            "typ": "JWT",
            "kid": self._config.kid,
        }

        token = jwt.encode(header, claims, self._config.private_key)
        if isinstance(token, bytes):
            token = token.decode("utf-8")

        return token

    def _generate_tracking(self) -> str:
        """Generate Agid-JWT-TrackingEvidence header (AUDIT_REST_02).

        Returns:
            Signed JWT string.

        Raises:
            ValueError: If audit context is not configured.
        """
        if not self._audit_context:
            raise ValueError("Audit context is required for tracking header")

        # Import here to avoid circular imports
        from authlib.jose import jwt

        now = datetime.now(timezone.utc)
        iat = int(now.timestamp())

        claims = {
            "iss": self._config.issuer,
            "aud": self._config.audience,
            "iat": iat,
            "nbf": iat,
            "exp": iat + self._config.validity_seconds,
            "jti": str(uuid.uuid4()),
            "userID": self._audit_context.user_id,
            "userLocation": self._audit_context.user_location,
            "LoA": self._audit_context.loa,
        }

        header = {
            "alg": self._config.alg,
            "typ": "JWT",
            "kid": self._config.kid,
        }

        token = jwt.encode(header, claims, self._config.private_key)
        if isinstance(token, bytes):
            token = token.decode("utf-8")

        return token


def register_modi_hook(
    hooks: "SDKHooks",
    config: "ModIConfig",
    audit_context: "AuditContext | None" = None,
) -> ModIPreRequestHook:
    """Register ModI pre-request hook with SDK hooks system.

    Helper function to create and register a ModIPreRequestHook.

    Args:
        hooks: SDKHooks instance to register with.
        config: ModI configuration.
        audit_context: Optional audit context for tracking header.

    Returns:
        The created ModIPreRequestHook instance.

    Example:
        >>> from anncsu.common.hooks.sdkhooks import SDKHooks
        >>> from anncsu.common.hooks.modi_hook import register_modi_hook
        >>> from anncsu.common.modi import ModIConfig, AuditContext
        >>>
        >>> hooks = SDKHooks()
        >>> config = ModIConfig(...)
        >>> audit = AuditContext(...)
        >>> hook = register_modi_hook(hooks, config=config, audit_context=audit)
    """
    hook = ModIPreRequestHook(config=config, audit_context=audit_context)
    hooks.register_before_request_hook(hook)
    return hook


__all__ = [
    "ModIHookError",
    "ModIPreRequestHook",
    "register_modi_hook",
]
