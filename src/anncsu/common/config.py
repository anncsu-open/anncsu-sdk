"""
Configuration settings for ANNCSU SDK.

This module provides settings classes that load configuration from environment
variables or .env files using pydantic-settings.
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Annotated

from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

if TYPE_CHECKING:
    from anncsu.common.pdnd_assertion import ClientAssertionConfig


class ClientAssertionSettings(BaseSettings):
    """Settings for loading client assertion configuration from environment variables.

    This class uses pydantic-settings to load configuration from environment
    variables or a .env file. All environment variables are prefixed with `PDND_`.

    Environment Variables:
        PDND_KID: Key ID (kid) header parameter.
        PDND_ISSUER: Issuer (iss) claim - typically your client_id.
        PDND_SUBJECT: Subject (sub) claim - typically your client_id.
        PDND_AUDIENCE: Audience (aud) claim - the PDND token endpoint URL.
        PDND_PURPOSE_ID: Purpose ID for the PDND request.
        PDND_PRIVATE_KEY: RSA private key content in PEM format (string).
        PDND_KEY_PATH: Path to the RSA private key file (alternative to PDND_PRIVATE_KEY).
        PDND_ALG: Algorithm for signing (default: RS256).
        PDND_TYP: Token type (default: JWT).
        PDND_VALIDITY_MINUTES: JWT validity in minutes (default: 43200).

    Example .env file:
        PDND_KID=my-key-id
        PDND_ISSUER=my-client-id
        PDND_SUBJECT=my-client-id
        PDND_AUDIENCE=https://auth.interop.pagopa.it/token.oauth2
        PDND_PURPOSE_ID=my-purpose-id
        PDND_KEY_PATH=./private_key.pem

    Example usage:
        >>> from anncsu.common.config import ClientAssertionSettings
        >>> from anncsu.common.pdnd_assertion import create_client_assertion
        >>> settings = ClientAssertionSettings()  # Loads from env
        >>> config = settings.to_config()
        >>> token = create_client_assertion(config)
    """

    model_config = SettingsConfigDict(
        env_prefix="PDND_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    kid: Annotated[
        str,
        Field(description="Key ID (kid) header parameter"),
    ]
    issuer: Annotated[
        str,
        Field(description="Issuer (iss) - typically your client_id from PDND"),
    ]
    subject: Annotated[
        str,
        Field(description="Subject (sub) - typically your client_id from PDND"),
    ]
    audience: Annotated[
        str,
        Field(description="Audience (aud) - the PDND token endpoint URL"),
    ]
    purpose_id: Annotated[
        str,
        Field(description="Purpose ID for the PDND request"),
    ]
    private_key: Annotated[
        str | None,
        Field(
            default=None,
            description="RSA private key content in PEM format (string)",
        ),
    ] = None
    key_path: Annotated[
        str | None,
        Field(
            default=None,
            description="Path to the RSA private key file",
        ),
    ] = None
    alg: Annotated[
        str,
        Field(description="Algorithm for signing the JWT"),
    ] = "RS256"
    typ: Annotated[
        str,
        Field(description="Token type"),
    ] = "JWT"
    validity_minutes: Annotated[
        int,
        Field(description="JWT validity period in minutes"),
    ] = 43200

    @model_validator(mode="after")
    def validate_key_source(self) -> "ClientAssertionSettings":
        """Validate that either private_key or key_path is provided."""
        if self.private_key is None and self.key_path is None:
            raise ValueError(
                "Either 'PDND_PRIVATE_KEY' or 'PDND_KEY_PATH' environment variable must be set"
            )
        return self

    def to_config(self) -> "ClientAssertionConfig":
        """Convert settings to a ClientAssertionConfig instance.

        Returns:
            ClientAssertionConfig: Configuration ready for use with create_client_assertion.

        Raises:
            ValueError: If neither private_key nor key_path is set.
        """
        # Import here to avoid circular imports
        from anncsu.common.pdnd_assertion import ClientAssertionConfig

        config_kwargs: dict = {
            "kid": self.kid,
            "issuer": self.issuer,
            "subject": self.subject,
            "audience": self.audience,
            "purpose_id": self.purpose_id,
            "alg": self.alg,
            "typ": self.typ,
            "validity_minutes": self.validity_minutes,
        }

        # Handle private key - convert string to bytes if provided
        if self.private_key is not None:
            config_kwargs["private_key"] = self.private_key.encode("utf-8")
        elif self.key_path is not None:
            config_kwargs["key_path"] = Path(self.key_path)

        return ClientAssertionConfig(**config_kwargs)


__all__ = [
    "ClientAssertionSettings",
]
