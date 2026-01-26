# SPDX-FileCopyrightText: 2025-present Geobeyond <info@geobeyond.it>
# SPDX-License-Identifier: MIT
"""Audience mismatch error for ModI configuration."""

from urllib.parse import urlparse


class AudienceMismatchError(Exception):
    """Error raised when ModI audience doesn't match the API server URL.

    This is a configuration error that will cause 400 InteroperabilityInvalidRequest
    errors from the API. The audience (aud) claim in ModI JWTs MUST match the
    API server URL per INTEGRITY_REST_02 pattern requirements.

    Attributes:
        modi_audience: The audience that was configured.
        server_url: The actual API server URL.
        message: Human-readable error message.

    Example:
        >>> raise AudienceMismatchError(
        ...     modi_audience="https://wrong-domain.example.com",
        ...     server_url="https://correct-domain.example.com/api/v1",
        ... )
        AudienceMismatchError: ModI audience mismatch detected.
        ...
    """

    def __init__(self, modi_audience: str, server_url: str) -> None:
        """Initialize the error with audience and server URL.

        Args:
            modi_audience: The configured ModI audience (aud claim value).
            server_url: The actual API server URL being called.
        """
        self.modi_audience = modi_audience
        self.server_url = server_url

        # Parse domains for clearer error message
        audience_domain = urlparse(modi_audience).netloc
        server_domain = urlparse(server_url).netloc

        self.message = (
            f"ModI audience mismatch detected.\n\n"
            f"The ModI JWT audience (aud) claim must match the API server URL.\n"
            f"This mismatch will cause '400 InteroperabilityInvalidRequest' errors.\n\n"
            f"  Configured audience: {modi_audience}\n"
            f"    (domain: {audience_domain})\n\n"
            f"  Actual server URL:   {server_url}\n"
            f"    (domain: {server_domain})\n\n"
            f"Solution: Ensure modi_audience equals the server_url parameter,\n"
            f"or let the system use server_url as the audience automatically."
        )

        super().__init__(self.message)

    def __str__(self) -> str:
        """Return the error message."""
        return self.message

    def __repr__(self) -> str:
        """Return a detailed representation."""
        return (
            f"AudienceMismatchError("
            f"modi_audience={self.modi_audience!r}, "
            f"server_url={self.server_url!r})"
        )
