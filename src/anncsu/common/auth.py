"""
PDND Authentication Manager.

This module provides the PDNDAuthManager class that manages the entire PDND
authentication lifecycle, including:
- Client assertion generation and renewal
- Access token acquisition and refresh
- Expiration tracking for both client assertions and access tokens
- Integration with TokenValidationHook for automatic token refresh

The manager uses dependency injection for configuration and can be used
as the central authentication component for the SDK.

Example usage (basic):
    >>> from anncsu.common.auth import PDNDAuthManager
    >>> from anncsu.common.config import ClientAssertionSettings
    >>>
    >>> # Load settings from .env
    >>> settings = ClientAssertionSettings()
    >>>
    >>> # Create auth manager
    >>> auth = PDNDAuthManager(
    ...     settings=settings,
    ...     token_endpoint="https://auth.uat.interop.pagopa.it/token.oauth2",
    ... )
    >>>
    >>> # Get access token
    >>> token = auth.get_access_token()
    >>> # Or get Security object for SDK
    >>> security = auth.get_security()

Example usage (with TokenValidationHook):
    >>> from anncsu.common.auth import PDNDAuthManager
    >>> from anncsu.common.hooks import register_token_validation_hook
    >>> from anncsu.common.hooks.sdkhooks import SDKHooks
    >>>
    >>> auth = PDNDAuthManager(settings=settings, token_endpoint=endpoint)
    >>> hooks = SDKHooks()
    >>>
    >>> # Register hook with auth manager's refresh callback
    >>> register_token_validation_hook(
    ...     hooks,
    ...     expiration_threshold_seconds=60,
    ...     refresh_callback=auth.get_refresh_callback(),
    ... )
"""

from __future__ import annotations

import base64
import json
import time
from typing import TYPE_CHECKING, Callable

from anncsu.common.pdnd_assertion import (
    ClientAssertionConfig,
    create_client_assertion,
)
from anncsu.common.pdnd_token import (
    TokenConfig,
    TokenResponseError,
    get_access_token,
)
from anncsu.common.security import Security

if TYPE_CHECKING:
    from anncsu.common.config import ClientAssertionSettings


# Default thresholds
DEFAULT_CLIENT_ASSERTION_THRESHOLD = 86400  # 1 day in seconds
DEFAULT_ACCESS_TOKEN_THRESHOLD = 60  # 60 seconds


def _get_jwt_exp(token: str) -> int | None:
    """Extract expiration timestamp from a JWT token.

    Args:
        token: JWT token string.

    Returns:
        Expiration timestamp (Unix epoch) or None if cannot be extracted.
    """
    try:
        parts = token.split(".")
        if len(parts) != 3:
            return None

        # Decode payload
        payload_b64 = parts[1] + "=" * (4 - len(parts[1]) % 4)
        payload = json.loads(base64.urlsafe_b64decode(payload_b64))

        return payload.get("exp")
    except Exception:
        return None


def _get_jwt_ttl(token: str) -> int | None:
    """Get time until JWT token expires.

    Args:
        token: JWT token string.

    Returns:
        Seconds until expiration, or None if cannot be determined.
        Returns negative value if already expired.
    """
    exp = _get_jwt_exp(token)
    if exp is None:
        return None
    return exp - int(time.time())


class PDNDAuthManager:
    """Manages PDND authentication lifecycle.

    This class handles the entire PDND authentication flow:
    - Generates and caches client assertions
    - Obtains and caches access tokens
    - Automatically regenerates tokens when expired or expiring soon
    - Provides a refresh callback for TokenValidationHook integration

    Attributes:
        settings: Optional ClientAssertionSettings (converted to config).
        config: ClientAssertionConfig for generating client assertions.
        token_endpoint: PDND token endpoint URL.
        client_assertion_threshold_seconds: Regenerate assertion this many seconds
            before expiration (default: 86400 = 1 day).
        access_token_threshold_seconds: Refresh token this many seconds before
            expiration (default: 60).

    Example:
        >>> auth = PDNDAuthManager(
        ...     settings=ClientAssertionSettings(),
        ...     token_endpoint="https://auth.uat.interop.pagopa.it/token.oauth2",
        ... )
        >>> security = auth.get_security()
    """

    def __init__(
        self,
        *,
        settings: "ClientAssertionSettings | None" = None,
        config: ClientAssertionConfig | None = None,
        token_endpoint: str | None = None,
        client_assertion_threshold_seconds: int = DEFAULT_CLIENT_ASSERTION_THRESHOLD,
        access_token_threshold_seconds: int = DEFAULT_ACCESS_TOKEN_THRESHOLD,
    ):
        """Initialize the PDND Auth Manager.

        Args:
            settings: ClientAssertionSettings to load configuration from.
                Will be converted to ClientAssertionConfig.
            config: ClientAssertionConfig for generating client assertions.
                Takes precedence over settings if both provided.
            token_endpoint: PDND token endpoint URL for obtaining access tokens.
            client_assertion_threshold_seconds: Regenerate client assertion
                this many seconds before it expires. Default is 86400 (1 day).
            access_token_threshold_seconds: Refresh access token this many
                seconds before it expires. Default is 60.

        Raises:
            ValueError: If neither settings nor config is provided.
        """
        if settings is None and config is None:
            raise ValueError(
                "Either 'settings' or 'config' must be provided to PDNDAuthManager"
            )

        self.settings = settings
        self.token_endpoint = token_endpoint
        self.client_assertion_threshold_seconds = client_assertion_threshold_seconds
        self.access_token_threshold_seconds = access_token_threshold_seconds

        # Convert settings to config if needed
        if config is not None:
            self.config = config
        elif settings is not None:
            self.config = settings.to_config()
        else:
            # This should never happen due to validation above
            raise ValueError("No configuration available")

        # Cached tokens
        self._client_assertion: str | None = None
        self._access_token: str | None = None

    def get_client_assertion(self) -> str:
        """Get a valid client assertion, generating one if needed.

        This method returns a cached client assertion if it's still valid
        (not expired and not within the threshold). Otherwise, it generates
        a new one.

        Returns:
            Client assertion JWT string.

        Raises:
            JWTGenerationError: If client assertion generation fails.
            KeyFileError: If private key cannot be read.
        """
        # Check if we need to generate a new assertion
        if self._should_regenerate_client_assertion():
            self._client_assertion = create_client_assertion(self.config)

        return self._client_assertion  # type: ignore

    def _should_regenerate_client_assertion(self) -> bool:
        """Check if client assertion should be regenerated.

        Returns:
            True if assertion is None, expired, or within threshold.
        """
        if self._client_assertion is None:
            return True

        ttl = _get_jwt_ttl(self._client_assertion)
        if ttl is None:
            return True

        return ttl <= self.client_assertion_threshold_seconds

    def client_assertion_ttl(self) -> int | None:
        """Get time until client assertion expires.

        Returns:
            Seconds until expiration, or None if no assertion cached.
        """
        if self._client_assertion is None:
            return None
        return _get_jwt_ttl(self._client_assertion)

    def is_client_assertion_expired(self) -> bool:
        """Check if client assertion is expired.

        Returns:
            True if no assertion or if expired.
        """
        if self._client_assertion is None:
            return True

        ttl = _get_jwt_ttl(self._client_assertion)
        if ttl is None:
            return True

        return ttl <= 0

    def get_access_token(self) -> str:
        """Get a valid access token, obtaining one if needed.

        This method returns a cached access token if it's still valid
        (not expired and not within the threshold). Otherwise, it obtains
        a new one from the PDND token endpoint.

        Returns:
            Access token string.

        Raises:
            TokenRequestError: If the token request fails.
            TokenResponseError: If the token response is invalid.
            ValueError: If token_endpoint is not set.
        """
        # Check if we need to obtain a new token
        if self._should_refresh_access_token():
            self._refresh_access_token()

        return self._access_token  # type: ignore

    def _should_refresh_access_token(self) -> bool:
        """Check if access token should be refreshed.

        Returns:
            True if token is None, expired, or within threshold.
        """
        if self._access_token is None:
            return True

        ttl = _get_jwt_ttl(self._access_token)
        if ttl is None:
            return True

        return ttl <= self.access_token_threshold_seconds

    def _refresh_access_token(self, force_new_assertion: bool = False) -> None:
        """Refresh the access token from PDND.

        Args:
            force_new_assertion: If True, regenerate client assertion first.

        Raises:
            TokenRequestError: If the token request fails.
            TokenResponseError: If the token response is invalid.
            ValueError: If token_endpoint is not set.
        """
        if self.token_endpoint is None:
            raise ValueError(
                "token_endpoint must be set to obtain access tokens. "
                "Pass token_endpoint to PDNDAuthManager constructor."
            )

        # Force regeneration if requested
        if force_new_assertion:
            self._client_assertion = None

        # Get client assertion (will regenerate if needed)
        client_assertion = self.get_client_assertion()

        # Create token config
        token_config = TokenConfig(
            client_id=self.config.issuer,  # issuer is typically the client_id
            client_assertion=client_assertion,
            token_endpoint=self.token_endpoint,
        )

        try:
            # Get access token
            response = get_access_token(token_config)
            self._access_token = response.access_token
        except TokenResponseError as e:
            # Check if error is due to invalid/expired assertion
            if e.error == "invalid_client" and not force_new_assertion:
                # Retry with new assertion
                self._refresh_access_token(force_new_assertion=True)
            else:
                raise

    def access_token_ttl(self) -> int | None:
        """Get time until access token expires.

        Returns:
            Seconds until expiration, or None if no token cached.
        """
        if self._access_token is None:
            return None
        return _get_jwt_ttl(self._access_token)

    def is_access_token_expired(self) -> bool:
        """Check if access token is expired.

        Returns:
            True if no token or if expired.
        """
        if self._access_token is None:
            return True

        ttl = _get_jwt_ttl(self._access_token)
        if ttl is None:
            return True

        return ttl <= 0

    def get_security(self, validate_expiration: bool = False) -> Security:
        """Get a Security object with a valid access token.

        This is the recommended way to get authentication for SDK usage.
        The Security object can be passed directly to SDK initialization.

        Args:
            validate_expiration: If True, Security will validate token
                expiration on creation. Default False since we've already
                validated.

        Returns:
            Security object with bearer token set.

        Example:
            >>> auth = PDNDAuthManager(settings=settings, token_endpoint=endpoint)
            >>> security = auth.get_security()
            >>> sdk = Anncsu(security=security)
        """
        token = self.get_access_token()
        return Security(bearer=token, validate_expiration=validate_expiration)

    def get_refresh_callback(self) -> Callable[[], str]:
        """Get a callback function for token refresh.

        This callback can be passed to TokenValidationHook to automatically
        refresh tokens when they expire.

        Returns:
            Callable that returns a new access token string.

        Example:
            >>> auth = PDNDAuthManager(settings=settings, token_endpoint=endpoint)
            >>> register_token_validation_hook(
            ...     hooks,
            ...     refresh_callback=auth.get_refresh_callback(),
            ... )
        """

        def refresh() -> str:
            # Force refresh by clearing cached token
            self._access_token = None
            return self.get_access_token()

        return refresh


__all__ = [
    "PDNDAuthManager",
]
