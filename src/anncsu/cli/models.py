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
    purpose_id: str = Field(description="Purpose ID (masked)")
    key_path: str = Field(description="Path to private key")
    key_exists: bool = Field(description="Whether key file exists")
    validity_minutes: int = Field(description="Assertion validity in minutes")


class AssertionInfo(BaseModel):
    """Client assertion configuration info."""

    kid: str = Field(description="Key ID")
    issuer: str = Field(description="Issuer (client_id)")
    subject: str = Field(description="Subject (client_id)")
    audience: str = Field(description="Audience URL")
    purpose_id: str = Field(description="Purpose ID")
    validity_minutes: int = Field(description="Validity period in minutes")
    validity_days: float = Field(description="Validity period in days")
