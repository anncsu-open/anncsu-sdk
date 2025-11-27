"""
Client assertion generation for PDND authentication.

This module provides the core logic for generating JWT client assertions
required for PDND (Piattaforma Digitale Nazionale Dati) authentication.
It can be used both programmatically by the SDK and via the CLI.

Example usage (programmatic):
    >>> from anncsu.common.pdnd_assertion import ClientAssertionConfig, create_client_assertion
    >>> config = ClientAssertionConfig(
    ...     kid="my-key-id",
    ...     issuer="my-client-id",
    ...     subject="my-client-id",
    ...     audience="https://auth.interop.pagopa.it/token.oauth2",
    ...     purpose_id="my-purpose-id",
    ...     private_key=b"-----BEGIN RSA PRIVATE KEY-----...",
    ... )
    >>> token = create_client_assertion(config)

Example usage (with key file path):
    >>> from pathlib import Path
    >>> from anncsu.common.pdnd_assertion import ClientAssertionConfig, create_client_assertion
    >>> config = ClientAssertionConfig(
    ...     kid="my-key-id",
    ...     issuer="my-client-id",
    ...     subject="my-client-id",
    ...     audience="https://auth.interop.pagopa.it/token.oauth2",
    ...     purpose_id="my-purpose-id",
    ...     key_path=Path("./private_key.pem"),
    ... )
    >>> token = create_client_assertion(config)
"""

from __future__ import annotations

import datetime
import uuid
from pathlib import Path
from typing import Annotated

from authlib.jose import jwt
from pydantic import BaseModel, Field, field_validator, model_validator


class ClientAssertionError(Exception):
    """Base exception for client assertion errors."""

    pass


class KeyFileError(ClientAssertionError):
    """Exception raised when there's an error reading the private key file."""

    pass


class JWTGenerationError(ClientAssertionError):
    """Exception raised when JWT generation fails."""

    pass


class ClientAssertionConfig(BaseModel):
    """Configuration for JWT client assertion generation.

    This model validates all parameters required to generate a PDND client assertion.
    You must provide either `private_key` (bytes) or `key_path` (Path to key file).

    Attributes:
        kid: Key ID (kid) header parameter - identifies which key was used.
        alg: Algorithm for signing the JWT (only RS256 supported).
        typ: Token type (should be JWT).
        issuer: Issuer (iss) claim - typically your client_id from PDND.
        subject: Subject (sub) claim - typically your client_id from PDND.
        audience: Audience (aud) claim - the PDND token endpoint URL.
        purpose_id: Purpose ID for the PDND request.
        private_key: RSA private key content in PEM format (bytes).
        key_path: Path to the RSA private key file (alternative to private_key).
        validity_minutes: JWT validity period in minutes (default: 43200 = 30 days).

    Example:
        >>> config = ClientAssertionConfig(
        ...     kid="my-key-id",
        ...     issuer="my-client-id",
        ...     subject="my-client-id",
        ...     audience="https://auth.interop.pagopa.it/token.oauth2",
        ...     purpose_id="my-purpose-id",
        ...     private_key=b"-----BEGIN RSA PRIVATE KEY-----...",
        ... )
    """

    kid: Annotated[
        str,
        Field(
            description="Key ID (kid) header parameter - identifies which key was used",
            min_length=1,
        ),
    ]
    alg: Annotated[
        str,
        Field(
            description="Algorithm for signing the JWT",
            pattern="^RS256$",
        ),
    ] = "RS256"
    typ: Annotated[
        str,
        Field(
            description="Token type",
            pattern="^JWT$",
        ),
    ] = "JWT"
    issuer: Annotated[
        str,
        Field(
            description="Issuer (iss) - typically your client_id from PDND",
            min_length=1,
        ),
    ]
    subject: Annotated[
        str,
        Field(
            description="Subject (sub) - typically your client_id from PDND",
            min_length=1,
        ),
    ]
    audience: Annotated[
        str,
        Field(
            description="Audience (aud) - the PDND token endpoint URL",
            pattern="^https://.*",
        ),
    ]
    purpose_id: Annotated[
        str,
        Field(
            description="Purpose ID for the PDND request",
            min_length=1,
        ),
    ]
    private_key: Annotated[
        bytes | None,
        Field(
            default=None,
            description="RSA private key content in PEM format (bytes)",
        ),
    ] = None
    key_path: Annotated[
        Path | None,
        Field(
            default=None,
            description="Path to the RSA private key file (PEM format)",
        ),
    ] = None
    validity_minutes: Annotated[
        int,
        Field(
            description="JWT validity period in minutes",
            gt=0,
            le=43200,  # Max 30 days
        ),
    ] = 43200

    @field_validator("audience")
    @classmethod
    def validate_audience(cls, v: str) -> str:
        """Validate audience URL format."""
        if not v.startswith("https://"):
            raise ValueError("Audience must be an HTTPS URL")
        return v

    @field_validator("key_path")
    @classmethod
    def validate_key_path(cls, v: Path | None) -> Path | None:
        """Validate that the key file exists and is readable."""
        if v is None:
            return v
        if not v.exists():
            raise ValueError(f"Key file not found: {v}")
        if not v.is_file():
            raise ValueError(f"Key path is not a file: {v}")
        return v

    @model_validator(mode="after")
    def validate_key_source(self) -> "ClientAssertionConfig":
        """Validate that either private_key or key_path is provided."""
        if self.private_key is None and self.key_path is None:
            raise ValueError("Either 'private_key' or 'key_path' must be provided")
        return self

    def get_private_key(self) -> bytes:
        """Get the private key content.

        Returns the private_key if provided directly, otherwise reads from key_path.

        Returns:
            bytes: The private key content in PEM format.

        Raises:
            KeyFileError: If the key file cannot be read.
        """
        if self.private_key is not None:
            return self.private_key

        if self.key_path is not None:
            try:
                return self.key_path.read_bytes()
            except FileNotFoundError as e:
                raise KeyFileError(f"Key file not found: {self.key_path}") from e
            except PermissionError as e:
                raise KeyFileError(
                    f"Permission denied reading key file: {self.key_path}"
                ) from e
            except OSError as e:
                raise KeyFileError(
                    f"Error reading key file {self.key_path}: {e}"
                ) from e

        # This should never happen due to model validation
        raise KeyFileError("No private key source available")


def create_client_assertion(
    config: ClientAssertionConfig,
    *,
    issued_at: datetime.datetime | None = None,
    jti: str | None = None,
) -> str:
    """
    Generate a JWT client assertion with the given configuration.

    This function creates a signed JWT token that can be used for PDND
    (Piattaforma Digitale Nazionale Dati) authentication.

    Args:
        config: Configuration for the client assertion (validated by Pydantic).
        issued_at: Optional issued-at timestamp. Defaults to current UTC time.
        jti: Optional JWT ID. Defaults to a new UUID4.

    Returns:
        str: The generated JWT token.

    Raises:
        KeyFileError: If there's an error reading the private key file.
        JWTGenerationError: If JWT generation fails.

    Example:
        >>> config = ClientAssertionConfig(
        ...     kid="my-key-id",
        ...     issuer="my-client-id",
        ...     subject="my-client-id",
        ...     audience="https://auth.interop.pagopa.it/token.oauth2",
        ...     purpose_id="my-purpose-id",
        ...     private_key=b"-----BEGIN RSA PRIVATE KEY-----...",
        ... )
        >>> token = create_client_assertion(config)
    """
    # Generate timestamps
    if issued_at is None:
        issued_at = datetime.datetime.now(datetime.UTC)
    delta = datetime.timedelta(minutes=config.validity_minutes)
    expire_at = issued_at + delta

    # Generate JTI if not provided
    if jti is None:
        jti = str(uuid.uuid4())

    # JWT header
    header = {
        "kid": config.kid,
        "alg": config.alg,
        "typ": config.typ,
    }

    # JWT payload
    payload = {
        "iss": config.issuer,
        "sub": config.subject,
        "aud": config.audience,
        "purposeId": config.purpose_id,
        "jti": jti,
        "iat": int(issued_at.timestamp()),
        "exp": int(expire_at.timestamp()),
    }

    # Get the private key
    rsa_key = config.get_private_key()

    try:
        # Encode the JWT using authlib
        client_assertion = jwt.encode(header, payload, rsa_key)

        # authlib returns bytes, decode to string
        if isinstance(client_assertion, bytes):
            client_assertion = client_assertion.decode("utf-8")

        return client_assertion
    except Exception as e:
        raise JWTGenerationError(f"Failed to generate JWT: {e}") from e


__all__ = [
    "ClientAssertionConfig",
    "ClientAssertionError",
    "KeyFileError",
    "JWTGenerationError",
    "create_client_assertion",
]
