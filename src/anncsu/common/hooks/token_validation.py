"""Token validation hook for pre-request token expiration checking.

This module provides a BeforeRequestHook that validates the access token
before each API request, preventing unnecessary HTTP calls with expired tokens.

Features:
- Validates token expiration before each request
- Optional expiration threshold (raise error N seconds before actual expiration)
- Optional auto-refresh callback to automatically renew expired tokens

Example:
    Basic usage (raises TokenExpiredError for expired tokens):

    >>> from anncsu.common.hooks import TokenValidationHook, register_token_validation_hook
    >>> from anncsu.common.hooks.sdkhooks import SDKHooks
    >>>
    >>> hooks = SDKHooks()
    >>> register_token_validation_hook(hooks)

    With expiration threshold (raise error 60 seconds before expiration):

    >>> register_token_validation_hook(hooks, expiration_threshold_seconds=60)

    With auto-refresh callback:

    >>> def refresh_token():
    ...     # Your logic to get a new token
    ...     return get_access_token(token_config).access_token
    >>>
    >>> register_token_validation_hook(hooks, refresh_callback=refresh_token)
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Callable, Union

import httpx

from .types import BeforeRequestContext, BeforeRequestHook, Hooks

if TYPE_CHECKING:
    from anncsu.common.security import Security


class TokenRefreshError(Exception):
    """Exception raised when token refresh fails.

    Attributes:
        message: Error message describing the failure.
        cause: Original exception that caused the refresh failure.
    """

    def __init__(self, message: str, cause: Exception | None = None):
        super().__init__(message)
        self.cause = cause


class TokenValidationHook(BeforeRequestHook):
    """Hook that validates token expiration before each API request.

    This hook checks if the bearer token in the Security configuration
    is expired (or will expire soon) before allowing the request to proceed.

    Attributes:
        expiration_threshold_seconds: Number of seconds before actual expiration
            to consider the token as expired. Default is 0 (only check actual expiration).
        refresh_callback: Optional callback function that returns a new token string.
            If provided, the hook will attempt to refresh expired tokens automatically.
    """

    def __init__(
        self,
        expiration_threshold_seconds: int = 0,
        refresh_callback: Callable[[], str] | None = None,
    ):
        """Initialize the token validation hook.

        Args:
            expiration_threshold_seconds: Number of seconds before actual expiration
                to consider the token as expired. Use this to refresh tokens early
                and avoid race conditions. Default is 0.
            refresh_callback: Optional callback function that returns a new token.
                If provided and the token is expired, this function will be called
                to obtain a new token. The callback should return the new token string,
                or raise an exception if refresh fails.
        """
        self.expiration_threshold_seconds = expiration_threshold_seconds
        self.refresh_callback = refresh_callback

    def before_request(
        self, hook_ctx: BeforeRequestContext, request: httpx.Request
    ) -> Union[httpx.Request, Exception]:
        """Validate token expiration before the request is sent.

        Args:
            hook_ctx: Hook context containing security configuration.
            request: The HTTP request about to be sent.

        Returns:
            The original request if token is valid, or an Exception if invalid.
        """
        # Import here to avoid circular imports
        from anncsu.common.security import Security, TokenExpiredError

        # Get security from context
        security = hook_ctx.security_source

        # If no security configured, allow request
        if security is None:
            return request

        # If security is not a Security instance, allow request
        if not isinstance(security, Security):
            return request

        # If no bearer token, allow request (let API handle it)
        if security.bearer is None:
            return request

        # Check token expiration with threshold
        ttl = security.time_until_expiration()

        # If we can't determine TTL, allow request
        if ttl is None:
            return request

        # Check if token is expired or will expire within threshold
        if ttl <= self.expiration_threshold_seconds:
            # Token is expired or expiring soon
            if self.refresh_callback is not None:
                # Try to refresh the token
                return self._try_refresh_token(security, request)
            else:
                # No refresh callback, return error
                return TokenExpiredError(
                    f"Access token has expired or will expire within "
                    f"{self.expiration_threshold_seconds} seconds. "
                    f"Time until expiration: {ttl} seconds. "
                    "Please obtain a new access token using get_access_token().",
                    expired_at=self._get_exp_from_security(security),
                    current_time=self._get_current_time(),
                )

        # Token is valid
        return request

    def _try_refresh_token(
        self, security: "Security", original_request: httpx.Request
    ) -> Union[httpx.Request, Exception]:
        """Attempt to refresh the token using the callback.

        Args:
            security: Security instance to update with new token.
            original_request: The original HTTP request to return on success.

        Returns:
            The original request if refresh succeeds, or an Exception if it fails.
        """
        from anncsu.common.security import Security

        try:
            new_token = self.refresh_callback()

            if new_token is None:
                return TokenRefreshError(
                    "Token refresh callback returned None. "
                    "Please ensure your refresh callback returns a valid token string."
                )

            # Validate the new token is not also expired
            # Create a temporary Security to check expiration
            temp_security = Security(bearer=new_token, validate_expiration=False)
            new_ttl = temp_security.time_until_expiration()

            if new_ttl is not None and new_ttl <= 0:
                return TokenRefreshError(
                    "Token refresh callback returned an expired token. "
                    "Please ensure your refresh callback returns a valid, non-expired token."
                )

            # Update the original security's bearer token
            # Note: Pydantic models are immutable by default, so we use object.__setattr__
            object.__setattr__(security, "bearer", new_token)

            # Return the original request to proceed with the updated token
            return original_request

        except TokenRefreshError:
            # Re-raise TokenRefreshError as-is
            raise
        except Exception as e:
            return TokenRefreshError(
                f"Token refresh failed: {e}",
                cause=e,
            )

    def _get_exp_from_security(self, security: "Security") -> int | None:
        """Get expiration timestamp from security token."""
        import time

        ttl = security.time_until_expiration()
        if ttl is None:
            return None
        return int(time.time()) + ttl

    def _get_current_time(self) -> int:
        """Get current Unix timestamp."""
        import time

        return int(time.time())


def register_token_validation_hook(
    hooks: "Hooks",
    expiration_threshold_seconds: int = 0,
    refresh_callback: Callable[[], str] | None = None,
) -> TokenValidationHook:
    """Register a token validation hook with the SDK hooks system.

    This is a convenience function to create and register a TokenValidationHook.

    Args:
        hooks: The SDK hooks instance to register with.
        expiration_threshold_seconds: Number of seconds before actual expiration
            to consider the token as expired. Default is 0.
        refresh_callback: Optional callback function that returns a new token.

    Returns:
        The created TokenValidationHook instance.

    Example:
        >>> from anncsu.common.hooks.sdkhooks import SDKHooks
        >>> from anncsu.common.hooks import register_token_validation_hook
        >>>
        >>> hooks = SDKHooks()
        >>> hook = register_token_validation_hook(
        ...     hooks,
        ...     expiration_threshold_seconds=60,
        ...     refresh_callback=my_refresh_function,
        ... )
    """
    hook = TokenValidationHook(
        expiration_threshold_seconds=expiration_threshold_seconds,
        refresh_callback=refresh_callback,
    )
    hooks.register_before_request_hook(hook)
    return hook
