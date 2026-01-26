# SPDX-FileCopyrightText: 2025-present Geobeyond <info@geobeyond.it>
# SPDX-License-Identifier: MIT
"""Pydantic models for CLI output serialization."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


# JWT Models
class JWTHeader(BaseModel):
    """JWT header structure."""

    alg: str = Field(description="Algorithm used for signing")
    typ: str = Field(default="JWT", description="Token type")
    kid: str | None = Field(default=None, description="Key ID")


class JWTPayload(BaseModel):
    """JWT payload for PDND client assertions."""

    iss: str = Field(description="Issuer (client_id)")
    sub: str = Field(description="Subject (client_id)")
    aud: str = Field(description="Audience (token endpoint)")
    exp: int = Field(description="Expiration timestamp")
    iat: int = Field(description="Issued at timestamp")
    jti: str | None = Field(default=None, description="JWT ID (unique identifier)")
    purposeId: str | None = Field(default=None, description="PDND Purpose ID")


class DecodedJWT(BaseModel):
    """Decoded JWT with header and payload."""

    header: JWTHeader
    payload: JWTPayload


# Auth Status Models
class TokenStatus(BaseModel):
    """Status information for a token."""

    valid: bool = Field(description="Whether the token is currently valid")
    expires_at: datetime | None = Field(
        default=None, description="Token expiration timestamp"
    )
    ttl_seconds: int | None = Field(default=None, description="Time to live in seconds")


class AuthStatus(BaseModel):
    """Authentication status response."""

    client_assertion: TokenStatus = Field(description="Client assertion status")
    access_token: TokenStatus = Field(description="Access token status")
    logged_in: bool = Field(description="Whether user is logged in with valid tokens")


class LoginResult(BaseModel):
    """Result of a login operation."""

    success: bool = Field(description="Whether login was successful")
    access_token_ttl: int = Field(description="Access token TTL in seconds")
    client_assertion_ttl: int = Field(description="Client assertion TTL in seconds")
    message: str | None = Field(default=None, description="Optional status message")


# Config Models
class ConfigInfo(BaseModel):
    """Configuration information for display."""

    kid: str = Field(description="Key ID (masked)")
    issuer: str = Field(description="Issuer/Client ID (masked)")
    subject: str = Field(description="Subject (masked)")
    audience: str = Field(description="Audience URL")
    # Multi-API purpose IDs
    purpose_id_pa: str = Field(description="Purpose ID for PA API (masked)")
    purpose_id_coordinate: str = Field(
        description="Purpose ID for Coordinate API (masked)"
    )
    purpose_id_accessi: str = Field(description="Purpose ID for Accessi API (masked)")
    purpose_id_interni: str = Field(description="Purpose ID for Interni API (masked)")
    purpose_id_odonimi: str = Field(description="Purpose ID for Odonimi API (masked)")
    key_path: str = Field(description="Path to private key")
    key_exists: bool = Field(description="Whether key file exists")
    validity_minutes: int = Field(description="Assertion validity in minutes")
    # ModI configuration
    modi_user_id: str | None = Field(default=None, description="ModI User ID")
    modi_user_location: str | None = Field(
        default=None, description="ModI User Location"
    )
    modi_loa: str | None = Field(default=None, description="ModI Level of Assurance")
    modi_configured: bool = Field(
        default=False, description="Whether ModI is fully configured"
    )


class AssertionInfo(BaseModel):
    """Client assertion configuration info."""

    kid: str = Field(description="Key ID")
    issuer: str = Field(description="Issuer (client_id)")
    subject: str = Field(description="Subject (client_id)")
    audience: str = Field(description="Audience URL")
    purpose_id: str = Field(description="Purpose ID")
    validity_minutes: int = Field(description="Validity period in minutes")
    validity_days: float = Field(description="Validity period in days")


# Coordinate Models
class CoordinateUpdateResult(BaseModel):
    """Result of a coordinate update operation."""

    success: bool = Field(description="Whether the operation was successful")
    id_richiesta: str | None = Field(
        default=None, description="Request ID assigned by the API"
    )
    esito: str | None = Field(default=None, description="Operation outcome")
    messaggio: str | None = Field(
        default=None, description="Message associated with the outcome"
    )
    dati_count: int = Field(default=0, description="Number of data records returned")


class CoordinateStatusResult(BaseModel):
    """Result of a coordinate API status check."""

    available: bool = Field(description="Whether the API is available")
    status: str = Field(description="Status message from the API")
    server_url: str = Field(description="Server URL being checked")
    environment: str = Field(description="Environment (validation or production)")


class OriginalCoordinates(BaseModel):
    """Original coordinates saved before dry-run test."""

    prognazacc: str = Field(description="Progressivo nazionale dell'accesso")
    codcom: str = Field(description="Codice comune (Belfiore)")
    civico: str | None = Field(default=None, description="Numero civico")
    coord_x: str | None = Field(default=None, description="Coordinata X (longitude)")
    coord_y: str | None = Field(default=None, description="Coordinata Y (latitude)")
    quota: str | None = Field(default=None, description="Quota (altitude)")
    metodo: str | None = Field(default=None, description="Metodo di rilevazione")


class DryRunResult(BaseModel):
    """Result of a coordinate dry-run operation."""

    success: bool = Field(description="Whether the full dry-run cycle completed")
    original_coordinates: OriginalCoordinates = Field(
        description="Original coordinates before the test"
    )
    test_update: CoordinateUpdateResult = Field(description="Result of the test update")
    restore: CoordinateUpdateResult | None = Field(
        default=None, description="Result of the restore operation"
    )
    restore_failed: bool = Field(
        default=False,
        description="Whether restore failed (requires manual intervention)",
    )
    error_message: str | None = Field(
        default=None, description="Error message if operation failed"
    )
