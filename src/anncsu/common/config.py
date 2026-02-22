"""
Configuration settings for ANNCSU SDK.

This module provides settings classes that load configuration from environment
variables or .env files using pydantic-settings.

It also defines the APIType enum which is the single source of truth for:
- Environment variable names: PDND_PURPOSE_ID_{api_type.value.upper()}
- CLI subcommand names: anncsu {api_type.cli_command} ...
- API descriptions for help and error messages
"""

from __future__ import annotations

from enum import Enum
from pathlib import Path
from typing import TYPE_CHECKING, Annotated

from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

if TYPE_CHECKING:
    from anncsu.common.modi import AuditContext
    from anncsu.common.pdnd_assertion import ClientAssertionConfig


class MissingPurposeIDError(Exception):
    """Exception raised when required PDND_PURPOSE_ID_* variables are missing from .env."""

    pass


class EmptyPurposeIDError(Exception):
    """Exception raised when attempting to use an API with an empty purpose_id."""

    pass


class APIType(str, Enum):
    """
    Supported ANNCSU API types.

    Each enum value is the single source of truth for:
    - Environment variable: PDND_PURPOSE_ID_{value.upper()}
    - CLI subcommand: anncsu {cli_command} ...
    - API description

    Example:
        APIType.PA -> PDND_PURPOSE_ID_PA, CLI: anncsu pa ...
        APIType.COORDINATE -> PDND_PURPOSE_ID_COORDINATE, CLI: anncsu coordinate ...
    """

    PA = "pa"  # Consultazione PA
    COORDINATE = "coordinate"  # Gestione coordinate accessi
    COORDINATE_BULK = "coordinate_bulk"  # Gestione coordinate massivo (grandi comuni)
    ACCESSI = "accessi"  # Aggiornamento accessi
    INTERNI = "interni"  # Aggiornamento interni
    ODONIMI = "odonimi"  # Aggiornamento odonimi

    @property
    def env_var_name(self) -> str:
        """Return the environment variable name for this API type."""
        return f"PDND_PURPOSE_ID_{self.value.upper()}"

    @property
    def cli_command(self) -> str:
        """Return the CLI subcommand name for this API type.

        Note: COORDINATE_BULK uses 'coordinate bulk' as subcommand (handled by Typer).
        """
        if self == APIType.COORDINATE_BULK:
            return "coordinate bulk"
        return self.value

    @property
    def description(self) -> str:
        """Return the full description of this API."""
        descriptions = {
            APIType.PA: "ANNCSU Consultazione per le PA",
            APIType.COORDINATE: "ANNCSU Aggiornamento Coordinate",
            APIType.COORDINATE_BULK: "ANNCSU Aggiornamento Coordinate Massivo",
            APIType.ACCESSI: "ANNCSU Aggiornamento Accessi",
            APIType.INTERNI: "ANNCSU Aggiornamento Interni",
            APIType.ODONIMI: "ANNCSU Aggiornamento Odonimi",
        }
        return descriptions[self]

    @classmethod
    def from_cli_command(cls, command: str) -> "APIType":
        """Return the APIType from a CLI subcommand name.

        Args:
            command: The CLI subcommand name (e.g., "pa", "coordinate")

        Returns:
            The corresponding APIType

        Raises:
            ValueError: If the command doesn't match any APIType
        """
        for api_type in cls:
            if api_type.cli_command == command:
                return api_type
        raise ValueError(f"Unknown CLI command: {command}")


class ClientAssertionSettings(BaseSettings):
    """Settings for loading client assertion configuration from environment variables.

    This class uses pydantic-settings to load configuration from environment
    variables or a .env file. All environment variables are prefixed with `PDND_`.

    IMPORTANT: ALL PDND_PURPOSE_ID_* variables must be present in .env (can be empty).
    The validation happens at initialization time.

    Environment Variables:
        PDND_KID: Key ID (kid) header parameter.
        PDND_ISSUER: Issuer (iss) claim - typically your client_id.
        PDND_SUBJECT: Subject (sub) claim - typically your client_id.
        PDND_AUDIENCE: Audience (aud) claim - the PDND token endpoint URL.
        PDND_PURPOSE_ID_PA: Purpose ID for PA Consultazione API.
        PDND_PURPOSE_ID_COORDINATE: Purpose ID for Coordinate API.
        PDND_PURPOSE_ID_COORDINATE_BULK: Purpose ID for Coordinate Bulk API (grandi comuni, 50k calls/day).
        PDND_PURPOSE_ID_ACCESSI: Purpose ID for Accessi API.
        PDND_PURPOSE_ID_INTERNI: Purpose ID for Interni API.
        PDND_PURPOSE_ID_ODONIMI: Purpose ID for Odonimi API.
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
        PDND_PURPOSE_ID_PA=pa-purpose-id
        PDND_PURPOSE_ID_COORDINATE=coordinate-purpose-id
        PDND_PURPOSE_ID_COORDINATE_BULK=bulk-purpose-id
        PDND_PURPOSE_ID_ACCESSI=
        PDND_PURPOSE_ID_INTERNI=
        PDND_PURPOSE_ID_ODONIMI=
        PDND_KEY_PATH=./private_key.pem

    Example usage:
        >>> from anncsu.common.config import ClientAssertionSettings, APIType
        >>> from anncsu.common.pdnd_assertion import create_client_assertion
        >>> settings = ClientAssertionSettings()  # Loads from env
        >>> config = settings.to_config(APIType.PA)  # API-specific config
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

    # Purpose ID per API - None means not defined, "" means defined but empty
    purpose_id_pa: Annotated[
        str | None,
        Field(default=None, description="Purpose ID for PA Consultazione API"),
    ] = None
    purpose_id_coordinate: Annotated[
        str | None,
        Field(default=None, description="Purpose ID for Coordinate API"),
    ] = None
    purpose_id_coordinate_bulk: Annotated[
        str | None,
        Field(
            default=None,
            description="Purpose ID for Coordinate Bulk API (grandi comuni, 50k calls/day)",
        ),
    ] = None
    purpose_id_accessi: Annotated[
        str | None,
        Field(default=None, description="Purpose ID for Accessi API"),
    ] = None
    purpose_id_interni: Annotated[
        str | None,
        Field(default=None, description="Purpose ID for Interni API"),
    ] = None
    purpose_id_odonimi: Annotated[
        str | None,
        Field(default=None, description="Purpose ID for Odonimi API"),
    ] = None

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

    # ModI Audit Context fields (optional, for APIs requiring AUDIT_REST_02)
    modi_user_id: Annotated[
        str | None,
        Field(
            default=None,
            description="ModI audit: User identifier in the consumer's domain",
        ),
    ] = None
    modi_user_location: Annotated[
        str | None,
        Field(
            default=None,
            description="ModI audit: Workstation/system identifier",
        ),
    ] = None
    modi_loa: Annotated[
        str | None,
        Field(
            default=None,
            description="ModI audit: Level of Assurance (e.g., SPID_L2, CIE_L3)",
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

    @model_validator(mode="after")
    def validate_all_purpose_ids_present(self) -> "ClientAssertionSettings":
        """Validate that ALL PDND_PURPOSE_ID_* variables are present in .env or environment.

        The variables can have empty values (""), but they must be defined (not None).
        None means the variable was never set, "" means it was set but empty.

        Raises:
            MissingPurposeIDError: If any required variable is not defined
        """
        missing_vars = []
        for api_type in APIType:
            field_name = f"purpose_id_{api_type.value}"
            value = getattr(self, field_name, None)
            # None means not defined at all, "" is valid (defined but empty)
            if value is None:
                missing_vars.append(f"{api_type.env_var_name} ({api_type.description})")

        if missing_vars:
            raise MissingPurposeIDError(
                "Missing required environment variables in .env:\n"
                + "\n".join(f"  - {var}" for var in missing_vars)
                + "\n\nAll PDND_PURPOSE_ID_* variables must be present (can be empty)."
            )

        return self

    def get_purpose_id(self, api_type: APIType) -> str:
        """Return the purpose_id for the specified API.

        Args:
            api_type: The API type to get the purpose_id for

        Returns:
            The configured purpose_id

        Raises:
            EmptyPurposeIDError: If the purpose_id is empty/not configured
        """
        # Dynamic mapping based on enum
        field_name = f"purpose_id_{api_type.value}"
        purpose_id = getattr(self, field_name, None)

        if purpose_id is None or purpose_id.strip() == "":
            raise EmptyPurposeIDError(
                f"Purpose ID for {api_type.description} ({api_type.env_var_name}) "
                f"is empty. Cannot generate client assertion."
            )

        return purpose_id

    @property
    def has_modi_audit_context(self) -> bool:
        """Check if all ModI audit context fields are configured.

        Returns:
            True if all three audit fields (user_id, user_location, loa) are set.
        """
        return (
            self.modi_user_id is not None
            and self.modi_user_location is not None
            and self.modi_loa is not None
        )

    def get_modi_audit_context(self) -> "AuditContext | None":
        """Get the ModI audit context if all fields are configured.

        Returns:
            AuditContext instance if all audit fields are set, None otherwise.
        """
        if not self.has_modi_audit_context:
            return None

        # Import here to avoid circular imports
        from anncsu.common.modi import AuditContext

        return AuditContext(
            user_id=self.modi_user_id,  # type: ignore[arg-type]
            user_location=self.modi_user_location,  # type: ignore[arg-type]
            loa=self.modi_loa,  # type: ignore[arg-type]
        )

    def to_config(self, api_type: APIType) -> "ClientAssertionConfig":
        """Convert settings to a ClientAssertionConfig instance for a specific API.

        Args:
            api_type: The API type (REQUIRED) to generate config for

        Returns:
            ClientAssertionConfig: Configuration ready for use with create_client_assertion.

        Raises:
            EmptyPurposeIDError: If the purpose_id for the API is empty
            ValueError: If neither private_key nor key_path is set.
        """
        # Import here to avoid circular imports
        from anncsu.common.pdnd_assertion import ClientAssertionConfig

        purpose_id = self.get_purpose_id(api_type)

        config_kwargs: dict = {
            "kid": self.kid,
            "issuer": self.issuer,
            "subject": self.subject,
            "audience": self.audience,
            "purpose_id": purpose_id,
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
    "APIType",
    "ClientAssertionSettings",
    "EmptyPurposeIDError",
    "MissingPurposeIDError",
]
