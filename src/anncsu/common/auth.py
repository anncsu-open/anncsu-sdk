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
import warnings
from pathlib import Path
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
from anncsu.common.session import (
    Session,
    clear_session,
    load_session,
    save_session,
)

if TYPE_CHECKING:
    from anncsu.common.config import APIType, ClientAssertionSettings
    from anncsu.common.modi import ModIHeaderGenerator


# Default thresholds
DEFAULT_CLIENT_ASSERTION_THRESHOLD = 86400  # 1 day in seconds
DEFAULT_ACCESS_TOKEN_THRESHOLD = 60  # 60 seconds


def _get_jwt_payload(token: str) -> dict | None:
    """Decode JWT payload without signature verification.

    Args:
        token: JWT token string.

    Returns:
        Payload dictionary, or None if decoding fails.
    """
    try:
        parts = token.split(".")
        if len(parts) != 3:
            return None

        # Decode payload
        payload_b64 = parts[1] + "=" * (4 - len(parts[1]) % 4)
        return json.loads(base64.urlsafe_b64decode(payload_b64))
    except Exception:
        return None


def _get_jwt_exp(token: str) -> int | None:
    """Extract expiration timestamp from a JWT token.

    Args:
        token: JWT token string.

    Returns:
        Expiration timestamp (Unix epoch) or None if cannot be extracted.
    """
    payload = _get_jwt_payload(token)
    if payload is None:
        return None
    return payload.get("exp")


def extract_voucher_audience(access_token: str) -> str | None:
    """Extract the audience (aud) claim from a PDND voucher.

    The aud claim in the PDND voucher is the authoritative URL
    of the e-service. It can be used to auto-correct hardcoded
    server URLs that may differ from the actual GovWay endpoint.

    Args:
        access_token: The PDND voucher JWT string.

    Returns:
        The audience URL string, or None if it cannot be extracted.
    """
    payload = _get_jwt_payload(access_token)
    if payload is None:
        return None
    aud = payload.get("aud")
    if isinstance(aud, str):
        return aud
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
    - Generates and caches client assertions (with API-specific purpose_id)
    - Obtains and caches access tokens
    - Automatically regenerates tokens when expired or expiring soon
    - Provides a refresh callback for TokenValidationHook integration

    Each API type requires its own PDNDAuthManager instance because each
    uses a different purpose_id for authentication.

    Attributes:
        api_type: The API type this manager authenticates for.
        settings: Optional ClientAssertionSettings (converted to config).
        config: ClientAssertionConfig for generating client assertions.
        token_endpoint: PDND token endpoint URL.
        client_assertion_threshold_seconds: Regenerate assertion this many seconds
            before expiration (default: 86400 = 1 day).
        access_token_threshold_seconds: Refresh token this many seconds before
            expiration (default: 60).

    Example:
        >>> from anncsu.common.config import APIType
        >>> auth = PDNDAuthManager(
        ...     api_type=APIType.PA,
        ...     settings=ClientAssertionSettings(),
        ...     token_endpoint="https://auth.uat.interop.pagopa.it/token.oauth2",
        ... )
        >>> security = auth.get_security()
    """

    def __init__(
        self,
        *,
        api_type: "APIType",
        settings: "ClientAssertionSettings | None" = None,
        config: ClientAssertionConfig | None = None,
        token_endpoint: str | None = None,
        client_assertion_threshold_seconds: int = DEFAULT_CLIENT_ASSERTION_THRESHOLD,
        access_token_threshold_seconds: int = DEFAULT_ACCESS_TOKEN_THRESHOLD,
        session_persistence: bool = False,
        config_dir: Path | None = None,
        modi_audience: str | None = None,
        server_url: str | None = None,
    ):
        """Initialize the PDND Auth Manager.

        Args:
            api_type: The API type (REQUIRED). Determines which purpose_id
                to use for client assertion generation and which session file
                to use for token persistence.
            settings: ClientAssertionSettings to load configuration from.
                Will be converted to ClientAssertionConfig using api_type.
            config: ClientAssertionConfig for generating client assertions.
                Takes precedence over settings if both provided.
            token_endpoint: PDND token endpoint URL for obtaining access tokens.
            client_assertion_threshold_seconds: Regenerate client assertion
                this many seconds before it expires. Default is 86400 (1 day).
            access_token_threshold_seconds: Refresh access token this many
                seconds before it expires. Default is 60.
            session_persistence: If True, load/save session to file.
                Default is False.
            config_dir: Custom config directory for session file.
                Defaults to ~/.anncsu/
            modi_audience: Audience URL for ModI headers (required for APIs
                that need ModI security headers like Coordinate API).
                This MUST match server_url for INTEGRITY_REST_02 compliance.
            server_url: The API server URL. Used to validate modi_audience
                when both are provided. If modi_audience differs from server_url,
                an AudienceMismatchError is raised.

        Raises:
            ValueError: If api_type is None or if neither settings nor config is provided.
            EmptyPurposeIDError: If the purpose_id for the API is empty.
            AudienceMismatchError: If modi_audience doesn't match server_url.
        """
        if api_type is None:
            raise ValueError(
                "api_type is required. Each API requires its own authentication "
                "because each uses a different purpose_id."
            )

        if settings is None and config is None:
            raise ValueError(
                "Either 'settings' or 'config' must be provided to PDNDAuthManager"
            )

        # Validate that modi_audience matches server_url when both are provided
        if modi_audience is not None and server_url is not None:
            self._validate_audience_matches_server(modi_audience, server_url)

        self.api_type = api_type
        self.settings = settings
        self.token_endpoint = token_endpoint
        self.client_assertion_threshold_seconds = client_assertion_threshold_seconds
        self.access_token_threshold_seconds = access_token_threshold_seconds
        self.session_persistence = session_persistence
        self.config_dir = config_dir

        # Convert settings to config if needed (using api_type for purpose_id)
        if config is not None:
            self.config = config
        elif settings is not None:
            self.config = settings.to_config(api_type)
        else:
            # This should never happen due to validation above
            raise ValueError("No configuration available")

        # Validate audience/token_endpoint environment consistency
        self._check_environment_mismatch()

        # Cached tokens
        self._client_assertion: str | None = None
        self._access_token: str | None = None

        # ModI header generator (optional, for APIs requiring ModI security)
        self._modi_generator: "ModIHeaderGenerator | None" = None
        self._init_modi_generator(settings, modi_audience)

        # Load session from file if persistence is enabled
        if self.session_persistence:
            self._load_session()

    def _init_modi_generator(
        self,
        settings: "ClientAssertionSettings | None",
        modi_audience: str | None,
    ) -> None:
        """Initialize the ModI header generator if audit context is configured.

        Args:
            settings: ClientAssertionSettings with optional ModI audit context.
            modi_audience: Audience URL for ModI JWTs.
        """
        if settings is None:
            return

        if not settings.has_modi_audit_context:
            return

        if modi_audience is None:
            return

        # Import here to avoid circular imports
        from anncsu.common.modi import (
            ModIHeaderGenerator,
            create_modi_config_from_settings,
        )

        # Create ModI config from settings
        modi_config = create_modi_config_from_settings(settings, modi_audience)

        # Get audit context
        audit_context = settings.get_modi_audit_context()

        # Create generator
        self._modi_generator = ModIHeaderGenerator(modi_config, audit_context)

    @staticmethod
    def _validate_audience_matches_server(
        modi_audience: str,
        server_url: str,
    ) -> None:
        """Validate that ModI audience matches the API server URL.

        Per ModI INTEGRITY_REST_02, the audience (aud) claim in the JWT
        MUST match the API server URL. A mismatch will cause 400
        InteroperabilityInvalidRequest errors from the API.

        Args:
            modi_audience: The configured ModI audience.
            server_url: The actual API server URL.

        Raises:
            AudienceMismatchError: If the audience doesn't match the server URL.
        """
        from urllib.parse import urlparse

        from anncsu.common.errors import AudienceMismatchError

        # Parse both URLs
        audience_parsed = urlparse(modi_audience)
        server_parsed = urlparse(server_url)

        # Check if domains match (the most common mistake)
        if audience_parsed.netloc != server_parsed.netloc:
            raise AudienceMismatchError(
                modi_audience=modi_audience,
                server_url=server_url,
            )

        # If domains match but paths are completely different, also raise
        # (allows for minor path differences like trailing slash)
        if modi_audience.rstrip("/") != server_url.rstrip("/"):
            raise AudienceMismatchError(
                modi_audience=modi_audience,
                server_url=server_url,
            )

    def _check_environment_mismatch(self) -> None:
        """Check if audience and token_endpoint refer to different PDND environments.

        Emits a UserWarning if one refers to UAT and the other to production.
        This is a common misconfiguration that causes authentication failures.
        """
        if self.token_endpoint is None:
            return

        audience = getattr(self.config, "audience", None)
        if audience is None:
            return

        audience_is_uat = ".uat." in audience
        endpoint_is_uat = ".uat." in self.token_endpoint

        if audience_is_uat != endpoint_is_uat:
            aud_env = "UAT" if audience_is_uat else "production"
            endpoint_env = "UAT" if endpoint_is_uat else "production"
            warnings.warn(
                f"PDND environment mismatch: PDND_AUDIENCE refers to {aud_env} "
                f"({audience}) but token_endpoint refers to {endpoint_env} "
                f"({self.token_endpoint}). "
                f"Authentication will likely fail. "
                f"Check your .env configuration.",
                UserWarning,
                stacklevel=2,
            )

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
            self._save_session()

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
            self._save_session()
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
            >>> sdk = AnncsuConsultazione(security=security)
        """
        token = self.get_access_token()
        return Security(bearer=token, validate_expiration=validate_expiration)

    @property
    def has_modi_generator(self) -> bool:
        """Check if ModI header generator is configured.

        Returns:
            True if ModI headers can be generated for requests.
        """
        return self._modi_generator is not None

    def get_modi_headers(self, payload: dict) -> dict[str, str]:
        """Generate ModI security headers for a request payload.

        This method generates fresh ModI JWTs for each call. The headers
        include:
        - Agid-JWT-Signature: Contains digest of the payload (INTEGRITY_REST_02)
        - Agid-JWT-TrackingEvidence: Contains audit information (AUDIT_REST_02)

        Args:
            payload: The request body dictionary to sign.

        Returns:
            Dictionary with ModI headers, or empty dict if no generator configured.

        Example:
            >>> auth = PDNDAuthManager(
            ...     settings=settings,
            ...     token_endpoint=endpoint,
            ...     modi_audience="https://modipa-val.anpr.interno.it",
            ... )
            >>> payload = {"codcom": "H501", "operazione": "M"}
            >>> headers = auth.get_modi_headers(payload)
            >>> # headers = {"Agid-JWT-Signature": "...", "Agid-JWT-TrackingEvidence": "..."}
        """
        if self._modi_generator is None:
            return {}

        return self._modi_generator.generate_headers(payload)

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

    def _load_session(self) -> None:
        """Load session from file if it exists and tokens are valid.

        Only loads tokens if:
        - Session file exists for this API type
        - Token endpoint matches (or session has no endpoint)
        - Tokens are not expired
        """
        session = load_session(api_type=self.api_type, config_dir=self.config_dir)
        if session is None:
            return

        # Check if token endpoint matches
        if (
            self.token_endpoint is not None
            and session.token_endpoint != self.token_endpoint
        ):
            return

        # Load client assertion if valid
        if session.client_assertion is not None:
            ttl = _get_jwt_ttl(session.client_assertion)
            if ttl is not None and ttl > 0:
                self._client_assertion = session.client_assertion

        # Load access token if valid
        if session.access_token is not None:
            ttl = _get_jwt_ttl(session.access_token)
            if ttl is not None and ttl > 0:
                self._access_token = session.access_token

    def _save_session(self) -> None:
        """Save current session to file."""
        if not self.session_persistence:
            return

        if self.token_endpoint is None:
            return

        session = Session(
            client_assertion=self._client_assertion,
            access_token=self._access_token,
            token_endpoint=self.token_endpoint,
        )
        save_session(session, api_type=self.api_type, config_dir=self.config_dir)

    def clear_session(self) -> None:
        """Clear the session file and cached tokens for this API type."""
        self._client_assertion = None
        self._access_token = None
        if self.session_persistence:
            clear_session(api_type=self.api_type, config_dir=self.config_dir)


__all__ = [
    "PDNDAuthManager",
    "extract_voucher_audience",
]
