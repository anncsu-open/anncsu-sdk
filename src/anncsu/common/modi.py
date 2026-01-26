# SPDX-FileCopyrightText: 2025-present Geobeyond <info@geobeyond.it>
# SPDX-License-Identifier: MIT
"""
ModI Header Generator for ANNCSU APIs.

This module generates the ModI security headers required by certain ANNCSU APIs:
- Agid-JWT-Signature (INTEGRITY_REST_02): Ensures payload integrity
- Agid-JWT-TrackingEvidence (AUDIT_REST_02): Audit trail for requests

IMPORTANT: These JWTs are generated PER-REQUEST, not cached!
- Signature JWT contains a digest of the request payload
- Tracking JWT contains a unique jti (JWT ID) per request

The same RSA private key used for PDND authentication is used for ModI headers.

Example usage:
    >>> from anncsu.common.modi import ModIConfig, AuditContext, ModIHeaderGenerator
    >>>
    >>> config = ModIConfig(
    ...     private_key=key_bytes,
    ...     kid="my-key-id",
    ...     issuer="my-client-id",
    ...     audience="https://modipa-val.anpr.interno.it",
    ... )
    >>> audit = AuditContext(
    ...     user_id="batch-user",
    ...     user_location="server-01",
    ...     loa="SPID_L2",
    ... )
    >>> generator = ModIHeaderGenerator(config, audit)
    >>>
    >>> # For each request:
    >>> payload = {"codcom": "H501", "operazione": "M"}
    >>> headers = generator.generate_headers(payload)
    >>> # headers = {
    >>> #     "Agid-JWT-Signature": "eyJ...",
    >>> #     "Agid-JWT-TrackingEvidence": "eyJ...",
    >>> # }
"""

from __future__ import annotations

import base64
import hashlib
import json
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import TYPE_CHECKING, Any

from authlib.jose import jwt

if TYPE_CHECKING:
    from anncsu.common.config import ClientAssertionSettings


@dataclass
class AuditContext:
    """Audit context for AUDIT_REST_02 pattern.

    These values identify the user/system making the request for audit purposes.
    Required by the Agid-JWT-TrackingEvidence header.

    Attributes:
        user_id: Unique identifier of the user in the consumer's domain.
            Example: "batch-user-001", "operator@example.com"
        user_location: Identifier of the workstation/system initiating the request.
            Example: "server-batch-01", "192.168.1.100"
        loa: Level of Assurance in the authentication process.
            Example: "SPID_L2", "CIE_L3", "INTERNAL_AUTH"
    """

    user_id: str
    user_location: str
    loa: str


@dataclass
class ModIConfig:
    """Configuration for ModI header generation.

    Uses the same RSA key pair as PDND authentication.

    Attributes:
        private_key: RSA private key bytes (PEM format).
        kid: Key ID (same as PDND_KID).
        issuer: Client ID (same as PDND_ISSUER).
        audience: API base URL (NOT the token endpoint).
            Example: "https://modipa-val.anpr.interno.it"
        alg: JWT algorithm (default RS256).
        validity_seconds: JWT validity in seconds (default 300 = 5 minutes).
    """

    private_key: bytes
    kid: str
    issuer: str
    audience: str
    alg: str = "RS256"
    validity_seconds: int = 300


class ModIHeaderGenerator:
    """Generator for ModI security headers.

    Generates fresh JWTs for each request - these are NOT cached.

    The generator creates two types of JWT headers:
    1. Agid-JWT-Signature: Contains a digest of the request payload (INTEGRITY_REST_02)
    2. Agid-JWT-TrackingEvidence: Contains audit information (AUDIT_REST_02)

    Example:
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
        >>> generator = ModIHeaderGenerator(config, audit)
        >>>
        >>> # For each request:
        >>> payload = {"codcom": "H501", "operazione": "M"}
        >>> headers = generator.generate_headers(payload)
    """

    def __init__(
        self,
        config: ModIConfig,
        audit_context: AuditContext | None = None,
    ):
        """Initialize the ModI header generator.

        Args:
            config: ModI configuration with key and audience.
            audit_context: Optional audit context for tracking header.
                If None, only Signature header is generated.
        """
        self._config = config
        self._audit_context = audit_context

    @property
    def has_audit_context(self) -> bool:
        """Check if audit context is configured."""
        return self._audit_context is not None

    def generate_headers(
        self,
        payload: dict[str, Any],
        content_type: str = "application/json",
    ) -> dict[str, str]:
        """Generate all ModI headers for a request.

        This method generates fresh JWTs for each call. Do NOT cache the results.

        Args:
            payload: The request body as a dictionary.
            content_type: Content-Type header value.

        Returns:
            Dictionary with ModI headers:
            - "Digest": HTTP Digest header (RFC 3230) - always present
            - "Agid-JWT-Signature": Always present
            - "Agid-JWT-TrackingEvidence": Present if audit_context configured
        """
        headers = {}

        # Compute digest once (used in both HTTP header and JWT)
        digest_value = self._compute_digest(payload)

        # HTTP Digest header (RFC 3230) - required by ModI INTEGRITY_REST_02
        headers["Digest"] = digest_value

        # Always generate signature header
        headers["Agid-JWT-Signature"] = self._generate_signature(
            digest_value, content_type
        )

        # Generate tracking header if audit context is configured
        if self._audit_context:
            headers["Agid-JWT-TrackingEvidence"] = self._generate_tracking()

        return headers

    def _compute_digest(self, payload: dict[str, Any]) -> str:
        """Compute SHA-256 digest of payload for HTTP Digest header.

        Uses standard base64 encoding with padding as per RFC 3230.

        Args:
            payload: Request body to compute digest from.

        Returns:
            Digest value in format "SHA-256=<base64-encoded-hash>"
        """
        # Use compact JSON serialization with sorted keys for determinism
        payload_bytes = json.dumps(
            payload, separators=(",", ":"), sort_keys=True
        ).encode("utf-8")
        digest = hashlib.sha256(payload_bytes).digest()
        # Use standard base64 with padding (NOT urlsafe, NOT without padding)
        digest_b64 = base64.b64encode(digest).decode("utf-8")
        return f"SHA-256={digest_b64}"

    def _generate_signature(
        self,
        digest_value: str,
        content_type: str,
    ) -> str:
        """Generate Agid-JWT-Signature header (INTEGRITY_REST_02).

        The JWT contains:
        - iss: Issuer (client ID)
        - aud: Audience (API URL)
        - iat: Issued at timestamp
        - nbf: Not before timestamp (same as iat)
        - exp: Expiration timestamp
        - jti: Unique JWT ID
        - signed_headers: Array with digest and content-type

        Args:
            digest_value: Pre-computed digest value (format: "SHA-256=<base64>").
            content_type: Content-Type header value.

        Returns:
            Signed JWT string.
        """
        now = datetime.now(timezone.utc)
        iat = int(now.timestamp())
        claims = {
            "iss": self._config.issuer,
            "aud": self._config.audience,
            "iat": iat,
            "nbf": iat,  # Token valid from issue time
            "exp": iat + self._config.validity_seconds,
            "jti": str(uuid.uuid4()),  # Unique ID for each signature
            "signed_headers": [
                {"digest": digest_value},
                {"content-type": content_type},
            ],
        }

        return self._sign_jwt(claims)

    def _generate_tracking(self) -> str:
        """Generate Agid-JWT-TrackingEvidence header (AUDIT_REST_02).

        The JWT contains:
        - iss: Issuer (client ID)
        - aud: Audience (API URL)
        - iat: Issued at timestamp
        - exp: Expiration timestamp
        - jti: Unique JWT ID (UUID)
        - userID: User identifier from audit context
        - userLocation: Location from audit context
        - LoA: Level of Assurance from audit context

        Returns:
            Signed JWT string.

        Raises:
            ValueError: If audit context is not configured.
        """
        if not self._audit_context:
            raise ValueError("Audit context is required for tracking header")

        now = datetime.now(timezone.utc)
        iat = int(now.timestamp())
        claims = {
            "iss": self._config.issuer,
            "aud": self._config.audience,
            "iat": iat,
            "nbf": iat,  # Token valid from issue time
            "exp": iat + self._config.validity_seconds,
            "jti": str(uuid.uuid4()),
            "userID": self._audit_context.user_id,
            "userLocation": self._audit_context.user_location,
            "LoA": self._audit_context.loa,
        }

        return self._sign_jwt(claims)

    def _sign_jwt(self, claims: dict[str, Any]) -> str:
        """Sign claims as a JWT using RS256.

        Args:
            claims: JWT claims dictionary.

        Returns:
            Signed JWT string.
        """
        header = {
            "alg": self._config.alg,
            "typ": "JWT",
            "kid": self._config.kid,
        }

        token = jwt.encode(header, claims, self._config.private_key)

        # authlib returns bytes, decode to string
        if isinstance(token, bytes):
            token = token.decode("utf-8")

        return token


def create_modi_config_from_settings(
    settings: "ClientAssertionSettings",
    api_audience: str,
) -> ModIConfig:
    """Create ModIConfig from ClientAssertionSettings.

    Reuses the same RSA key and identifiers from PDND config.

    Args:
        settings: PDND client assertion settings.
        api_audience: The API base URL (audience for ModI JWTs).

    Returns:
        ModIConfig ready for header generation.

    Raises:
        ValueError: If no private key is configured.
    """
    # Import here to avoid circular imports
    from anncsu.common.config import ClientAssertionSettings as CAS

    if not isinstance(settings, CAS):
        raise TypeError("settings must be a ClientAssertionSettings instance")

    # Load private key
    if settings.private_key:
        private_key = settings.private_key.encode("utf-8")
    elif settings.key_path:
        private_key = Path(settings.key_path).read_bytes()
    else:
        raise ValueError("No private key configured in settings")

    return ModIConfig(
        private_key=private_key,
        kid=settings.kid,
        issuer=settings.issuer,
        audience=api_audience,
    )


__all__ = [
    "AuditContext",
    "ModIConfig",
    "ModIHeaderGenerator",
    "create_modi_config_from_settings",
]
