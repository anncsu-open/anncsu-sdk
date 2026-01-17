"""
Comprehensive test suite for the pdnd_token module.

Tests cover:
- TokenConfig validation
- TokenResponse validation
- get_access_token function (sync)
- get_access_token_async function (async)
- Error handling and exceptions
- Package exports
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import httpx
import pytest

from anncsu.common.pdnd_token import (
    CLIENT_ASSERTION_TYPE,
    GRANT_TYPE,
    TokenConfig,
    TokenError,
    TokenRequestError,
    TokenResponse,
    TokenResponseError,
    get_access_token,
    get_access_token_async,
)

# =============================================================================
# Test Fixtures
# =============================================================================


@pytest.fixture
def valid_token_config() -> TokenConfig:
    """Create a valid TokenConfig for testing."""
    return TokenConfig(
        client_id="43508172-aa22-46b0-8c01-3006e745c73c",
        client_assertion="eyJraWQiOiIzZkZyeHRodG53ZTZya0J0SjdUa0lfVUZTN2dFaEVOVzdHZjE5OGxNSVI4IiwiYWxnIjoiUlMyNTYiLCJ0eXAiOiJKV1QifQ.eyJpc3MiOiI0MzUwODE3Mi1hYTIyLTQ2YjAtOGMwMS0zMDA2ZTc0NWM3M2MifQ.signature",
        token_endpoint="https://auth.uat.interop.pagopa.it/token.oauth2",
    )


@pytest.fixture
def valid_token_response_data() -> dict:
    """Sample valid token response data."""
    return {
        "access_token": "eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0NTY3ODkwIn0.signature",
        "token_type": "Bearer",
        "expires_in": 600,
    }


# =============================================================================
# Test TokenConfig Validation
# =============================================================================


class TestTokenConfigValidation:
    """Tests for TokenConfig model validation."""

    def test_valid_config(self, valid_token_config: TokenConfig):
        """Test that a valid configuration is accepted."""
        assert valid_token_config.client_id == "43508172-aa22-46b0-8c01-3006e745c73c"
        assert (
            valid_token_config.token_endpoint
            == "https://auth.uat.interop.pagopa.it/token.oauth2"
        )
        assert valid_token_config.client_assertion_type == CLIENT_ASSERTION_TYPE
        assert valid_token_config.grant_type == GRANT_TYPE

    def test_config_with_custom_timeout(self):
        """Test configuration with custom timeout."""
        config = TokenConfig(
            client_id="test-client",
            client_assertion="test-assertion",
            token_endpoint="https://auth.example.com/token",
            timeout=60.0,
        )
        assert config.timeout == 60.0

    def test_config_requires_client_id(self):
        """Test that client_id is required."""
        with pytest.raises(ValueError, match="client_id"):
            TokenConfig(
                client_id="",  # Empty string
                client_assertion="test-assertion",
                token_endpoint="https://auth.example.com/token",
            )

    def test_config_requires_client_assertion(self):
        """Test that client_assertion is required."""
        with pytest.raises(ValueError, match="client_assertion"):
            TokenConfig(
                client_id="test-client",
                client_assertion="",  # Empty string
                token_endpoint="https://auth.example.com/token",
            )

    def test_config_requires_https_endpoint(self):
        """Test that token_endpoint must be HTTPS."""
        with pytest.raises(Exception, match="https://"):
            TokenConfig(
                client_id="test-client",
                client_assertion="test-assertion",
                token_endpoint="http://auth.example.com/token",  # HTTP, not HTTPS
            )

    def test_config_rejects_invalid_timeout(self):
        """Test that timeout must be positive."""
        with pytest.raises(ValueError):
            TokenConfig(
                client_id="test-client",
                client_assertion="test-assertion",
                token_endpoint="https://auth.example.com/token",
                timeout=0,  # Invalid
            )

    def test_config_default_values(self):
        """Test default values for optional fields."""
        config = TokenConfig(
            client_id="test-client",
            client_assertion="test-assertion",
            token_endpoint="https://auth.example.com/token",
        )
        assert config.client_assertion_type == CLIENT_ASSERTION_TYPE
        assert config.grant_type == GRANT_TYPE
        assert config.timeout == 30.0


# =============================================================================
# Test TokenResponse Validation
# =============================================================================


class TestTokenResponseValidation:
    """Tests for TokenResponse model validation."""

    def test_valid_response(self, valid_token_response_data: dict):
        """Test that a valid response is parsed correctly."""
        response = TokenResponse.model_validate(valid_token_response_data)
        assert response.access_token == valid_token_response_data["access_token"]
        assert response.token_type == "Bearer"
        assert response.expires_in == 600

    def test_response_with_minimal_data(self):
        """Test response with only required fields."""
        response = TokenResponse(
            access_token="test-token",
        )
        assert response.access_token == "test-token"
        assert response.token_type == "Bearer"  # Default
        assert response.expires_in is None  # Optional

    def test_response_with_custom_token_type(self):
        """Test response with custom token type."""
        response = TokenResponse(
            access_token="test-token",
            token_type="MAC",
        )
        assert response.token_type == "MAC"

    def test_response_without_expires_in(self):
        """Test response without expires_in field."""
        data = {
            "access_token": "test-token",
            "token_type": "Bearer",
        }
        response = TokenResponse.model_validate(data)
        assert response.expires_in is None


# =============================================================================
# Test Exception Classes
# =============================================================================


class TestExceptions:
    """Tests for exception classes."""

    def test_token_error_base_class(self):
        """Test TokenError is the base exception."""
        error = TokenError("Test error")
        assert str(error) == "Test error"
        assert isinstance(error, Exception)

    def test_token_request_error_with_details(self):
        """Test TokenRequestError with status code and body."""
        error = TokenRequestError(
            "Request failed",
            status_code=401,
            response_body='{"error": "invalid_client"}',
        )
        assert str(error) == "Request failed"
        assert error.status_code == 401
        assert error.response_body == '{"error": "invalid_client"}'

    def test_token_request_error_without_details(self):
        """Test TokenRequestError without optional details."""
        error = TokenRequestError("Request failed")
        assert error.status_code is None
        assert error.response_body is None

    def test_token_response_error_with_details(self):
        """Test TokenResponseError with OAuth2 error details."""
        error = TokenResponseError(
            "Token request failed",
            error="invalid_grant",
            error_description="The client assertion is invalid",
        )
        assert str(error) == "Token request failed"
        assert error.error == "invalid_grant"
        assert error.error_description == "The client assertion is invalid"

    def test_token_response_error_without_details(self):
        """Test TokenResponseError without optional details."""
        error = TokenResponseError("Token request failed")
        assert error.error is None
        assert error.error_description is None

    def test_exception_hierarchy(self):
        """Test that all exceptions inherit from TokenError."""
        assert issubclass(TokenRequestError, TokenError)
        assert issubclass(TokenResponseError, TokenError)


# =============================================================================
# Test get_access_token Function (Sync)
# =============================================================================


class TestGetAccessToken:
    """Tests for the get_access_token function."""

    def test_successful_token_request(
        self, valid_token_config: TokenConfig, valid_token_response_data: dict
    ):
        """Test successful token exchange."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = valid_token_response_data

        mock_client = MagicMock(spec=httpx.Client)
        mock_client.post.return_value = mock_response

        result = get_access_token(valid_token_config, client=mock_client)

        assert isinstance(result, TokenResponse)
        assert result.access_token == valid_token_response_data["access_token"]
        assert result.token_type == "Bearer"
        assert result.expires_in == 600

    def test_request_includes_correct_form_data(self, valid_token_config: TokenConfig):
        """Test that the request includes correct form data."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"access_token": "test-token"}

        mock_client = MagicMock(spec=httpx.Client)
        mock_client.post.return_value = mock_response

        get_access_token(valid_token_config, client=mock_client)

        # Verify the POST was called with correct parameters
        mock_client.post.assert_called_once()
        call_args = mock_client.post.call_args

        assert call_args.args[0] == valid_token_config.token_endpoint
        assert call_args.kwargs["data"]["client_id"] == valid_token_config.client_id
        assert (
            call_args.kwargs["data"]["client_assertion"]
            == valid_token_config.client_assertion
        )
        assert (
            call_args.kwargs["data"]["client_assertion_type"] == CLIENT_ASSERTION_TYPE
        )
        assert call_args.kwargs["data"]["grant_type"] == GRANT_TYPE
        assert (
            call_args.kwargs["headers"]["Content-Type"]
            == "application/x-www-form-urlencoded"
        )

    def test_timeout_error(self, valid_token_config: TokenConfig):
        """Test handling of timeout errors."""
        mock_client = MagicMock(spec=httpx.Client)
        mock_client.post.side_effect = httpx.TimeoutException("Connection timed out")

        with pytest.raises(TokenRequestError) as exc_info:
            get_access_token(valid_token_config, client=mock_client)

        assert "timed out" in str(exc_info.value)

    def test_connection_error(self, valid_token_config: TokenConfig):
        """Test handling of connection errors."""
        mock_client = MagicMock(spec=httpx.Client)
        mock_client.post.side_effect = httpx.ConnectError("Connection refused")

        with pytest.raises(TokenRequestError) as exc_info:
            get_access_token(valid_token_config, client=mock_client)

        assert "Failed to connect" in str(exc_info.value)

    def test_http_error_with_oauth_error(self, valid_token_config: TokenConfig):
        """Test handling of HTTP error with OAuth2 error response."""
        mock_response = MagicMock()
        mock_response.status_code = 400
        mock_response.json.return_value = {
            "error": "invalid_grant",
            "error_description": "The client assertion is expired",
        }

        mock_client = MagicMock(spec=httpx.Client)
        mock_client.post.return_value = mock_response

        with pytest.raises(TokenResponseError) as exc_info:
            get_access_token(valid_token_config, client=mock_client)

        assert exc_info.value.error == "invalid_grant"
        assert exc_info.value.error_description == "The client assertion is expired"

    def test_http_error_with_non_json_response(self, valid_token_config: TokenConfig):
        """Test handling of HTTP error with non-JSON response."""
        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_response.json.side_effect = ValueError("Invalid JSON")
        mock_response.text = "Internal Server Error"

        mock_client = MagicMock(spec=httpx.Client)
        mock_client.post.return_value = mock_response

        with pytest.raises(TokenRequestError) as exc_info:
            get_access_token(valid_token_config, client=mock_client)

        assert exc_info.value.status_code == 500
        assert exc_info.value.response_body == "Internal Server Error"

    def test_http_error_with_rfc7807_errors_array(
        self, valid_token_config: TokenConfig
    ):
        """Test handling of HTTP error with RFC 7807 Problem Details format (errors array)."""
        mock_response = MagicMock()
        mock_response.status_code = 400
        mock_response.json.return_value = {
            "title": "The request contains bad syntax or cannot be fulfilled.",
            "type": "about:blank",
            "status": 400,
            "detail": "Bad request",
            "errors": [
                {
                    "code": "015-0008",
                    "detail": "Unable to generate a token for the given request",
                }
            ],
            "correlationId": "f59d7bc7-df24-4361-8091-f62ff275c72b",
        }

        mock_client = MagicMock(spec=httpx.Client)
        mock_client.post.return_value = mock_response

        with pytest.raises(TokenResponseError) as exc_info:
            get_access_token(valid_token_config, client=mock_client)

        assert exc_info.value.error == "015-0008"
        assert (
            exc_info.value.error_description
            == "Unable to generate a token for the given request"
        )
        assert "correlationId: f59d7bc7-df24-4361-8091-f62ff275c72b" in str(
            exc_info.value
        )

    def test_http_error_with_rfc7807_title_detail_only(
        self, valid_token_config: TokenConfig
    ):
        """Test handling of RFC 7807 format with only title/detail (no errors array)."""
        mock_response = MagicMock()
        mock_response.status_code = 400
        mock_response.json.return_value = {
            "title": "Bad Request",
            "type": "about:blank",
            "status": 400,
            "detail": "The request could not be processed",
        }

        mock_client = MagicMock(spec=httpx.Client)
        mock_client.post.return_value = mock_response

        with pytest.raises(TokenResponseError) as exc_info:
            get_access_token(valid_token_config, client=mock_client)

        assert exc_info.value.error == "400"
        assert exc_info.value.error_description == "The request could not be processed"

    def test_http_error_with_rfc7807_title_only(self, valid_token_config: TokenConfig):
        """Test handling of RFC 7807 format with only title (no detail)."""
        mock_response = MagicMock()
        mock_response.status_code = 403
        mock_response.json.return_value = {
            "title": "Forbidden",
            "type": "about:blank",
            "status": 403,
        }

        mock_client = MagicMock(spec=httpx.Client)
        mock_client.post.return_value = mock_response

        with pytest.raises(TokenResponseError) as exc_info:
            get_access_token(valid_token_config, client=mock_client)

        assert exc_info.value.error == "403"
        assert exc_info.value.error_description == "Forbidden"

    def test_http_error_with_rfc7807_empty_errors_array(
        self, valid_token_config: TokenConfig
    ):
        """Test handling of RFC 7807 format with empty errors array."""
        mock_response = MagicMock()
        mock_response.status_code = 400
        mock_response.json.return_value = {
            "title": "Bad Request",
            "type": "about:blank",
            "status": 400,
            "detail": "Validation failed",
            "errors": [],
        }

        mock_client = MagicMock(spec=httpx.Client)
        mock_client.post.return_value = mock_response

        with pytest.raises(TokenResponseError) as exc_info:
            get_access_token(valid_token_config, client=mock_client)

        assert exc_info.value.error == "400"
        assert exc_info.value.error_description == "Validation failed"

    def test_http_error_with_rfc7807_multiple_errors(
        self, valid_token_config: TokenConfig
    ):
        """Test handling of RFC 7807 format with multiple errors (uses first)."""
        mock_response = MagicMock()
        mock_response.status_code = 400
        mock_response.json.return_value = {
            "title": "Multiple errors occurred",
            "type": "about:blank",
            "status": 400,
            "detail": "Multiple validation errors",
            "errors": [
                {"code": "ERR-001", "detail": "First error message"},
                {"code": "ERR-002", "detail": "Second error message"},
            ],
            "correlationId": "abc-123",
        }

        mock_client = MagicMock(spec=httpx.Client)
        mock_client.post.return_value = mock_response

        with pytest.raises(TokenResponseError) as exc_info:
            get_access_token(valid_token_config, client=mock_client)

        # Should use the first error
        assert exc_info.value.error == "ERR-001"
        assert exc_info.value.error_description == "First error message"
        assert "correlationId: abc-123" in str(exc_info.value)

    def test_http_error_with_rfc7807_error_without_code(
        self, valid_token_config: TokenConfig
    ):
        """Test handling of RFC 7807 error without code in errors array."""
        mock_response = MagicMock()
        mock_response.status_code = 400
        mock_response.json.return_value = {
            "title": "Bad Request",
            "type": "about:blank",
            "status": 400,
            "detail": "Bad request",
            "errors": [{"detail": "Error detail without code"}],
        }

        mock_client = MagicMock(spec=httpx.Client)
        mock_client.post.return_value = mock_response

        with pytest.raises(TokenResponseError) as exc_info:
            get_access_token(valid_token_config, client=mock_client)

        # Falls back to status code when error code is missing
        assert exc_info.value.error == "400"
        assert exc_info.value.error_description == "Error detail without code"

    def test_invalid_json_response(self, valid_token_config: TokenConfig):
        """Test handling of invalid JSON in successful response."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.side_effect = ValueError("Invalid JSON")

        mock_client = MagicMock(spec=httpx.Client)
        mock_client.post.return_value = mock_response

        with pytest.raises(TokenResponseError) as exc_info:
            get_access_token(valid_token_config, client=mock_client)

        assert "Invalid JSON response" in str(exc_info.value)

    def test_missing_access_token_in_response(self, valid_token_config: TokenConfig):
        """Test handling of response missing access_token."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "token_type": "Bearer"
        }  # Missing access_token

        mock_client = MagicMock(spec=httpx.Client)
        mock_client.post.return_value = mock_response

        with pytest.raises(TokenResponseError) as exc_info:
            get_access_token(valid_token_config, client=mock_client)

        assert "Invalid token response format" in str(exc_info.value)

    def test_creates_client_when_not_provided(self, valid_token_config: TokenConfig):
        """Test that a client is created when not provided."""
        with patch("anncsu.common.pdnd_token.httpx.Client") as mock_client_class:
            mock_client = MagicMock()
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = {"access_token": "test-token"}
            mock_client.post.return_value = mock_response
            mock_client_class.return_value = mock_client

            result = get_access_token(valid_token_config)

            mock_client_class.assert_called_once_with(
                timeout=valid_token_config.timeout
            )
            mock_client.close.assert_called_once()
            assert result.access_token == "test-token"


# =============================================================================
# Test get_access_token_async Function (Async)
# =============================================================================


class TestGetAccessTokenAsync:
    """Tests for the get_access_token_async function."""

    def test_successful_token_request(
        self, valid_token_config: TokenConfig, valid_token_response_data: dict
    ):
        """Test successful async token exchange."""
        import asyncio

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = valid_token_response_data

        mock_client = MagicMock(spec=httpx.AsyncClient)

        # Make post return a coroutine
        async def mock_post(*args, **kwargs):
            return mock_response

        mock_client.post = mock_post

        # Make aclose return a coroutine
        async def mock_aclose():
            pass

        mock_client.aclose = mock_aclose

        result = asyncio.run(
            get_access_token_async(valid_token_config, client=mock_client)
        )

        assert isinstance(result, TokenResponse)
        assert result.access_token == valid_token_response_data["access_token"]

    def test_timeout_error(self, valid_token_config: TokenConfig):
        """Test handling of timeout errors in async."""
        import asyncio

        mock_client = MagicMock(spec=httpx.AsyncClient)

        async def mock_post(*args, **kwargs):
            raise httpx.TimeoutException("Connection timed out")

        mock_client.post = mock_post

        async def mock_aclose():
            pass

        mock_client.aclose = mock_aclose

        with pytest.raises(TokenRequestError) as exc_info:
            asyncio.run(get_access_token_async(valid_token_config, client=mock_client))

        assert "timed out" in str(exc_info.value)

    def test_http_error_with_oauth_error(self, valid_token_config: TokenConfig):
        """Test handling of HTTP error with OAuth2 error response in async."""
        import asyncio

        mock_response = MagicMock()
        mock_response.status_code = 401
        mock_response.json.return_value = {
            "error": "invalid_client",
            "error_description": "Client authentication failed",
        }

        mock_client = MagicMock(spec=httpx.AsyncClient)

        async def mock_post(*args, **kwargs):
            return mock_response

        mock_client.post = mock_post

        async def mock_aclose():
            pass

        mock_client.aclose = mock_aclose

        with pytest.raises(TokenResponseError) as exc_info:
            asyncio.run(get_access_token_async(valid_token_config, client=mock_client))

        assert exc_info.value.error == "invalid_client"

    def test_http_error_with_rfc7807_errors_array_async(
        self, valid_token_config: TokenConfig
    ):
        """Test handling of RFC 7807 Problem Details format in async."""
        import asyncio

        mock_response = MagicMock()
        mock_response.status_code = 400
        mock_response.json.return_value = {
            "title": "The request contains bad syntax or cannot be fulfilled.",
            "type": "about:blank",
            "status": 400,
            "detail": "Bad request",
            "errors": [
                {
                    "code": "015-0008",
                    "detail": "Unable to generate a token for the given request",
                }
            ],
            "correlationId": "async-correlation-id",
        }

        mock_client = MagicMock(spec=httpx.AsyncClient)

        async def mock_post(*args, **kwargs):
            return mock_response

        mock_client.post = mock_post

        async def mock_aclose():
            pass

        mock_client.aclose = mock_aclose

        with pytest.raises(TokenResponseError) as exc_info:
            asyncio.run(get_access_token_async(valid_token_config, client=mock_client))

        assert exc_info.value.error == "015-0008"
        assert (
            exc_info.value.error_description
            == "Unable to generate a token for the given request"
        )
        assert "correlationId: async-correlation-id" in str(exc_info.value)

    def test_http_error_with_rfc7807_title_detail_only_async(
        self, valid_token_config: TokenConfig
    ):
        """Test handling of RFC 7807 format with only title/detail in async."""
        import asyncio

        mock_response = MagicMock()
        mock_response.status_code = 400
        mock_response.json.return_value = {
            "title": "Bad Request",
            "type": "about:blank",
            "status": 400,
            "detail": "The request could not be processed",
        }

        mock_client = MagicMock(spec=httpx.AsyncClient)

        async def mock_post(*args, **kwargs):
            return mock_response

        mock_client.post = mock_post

        async def mock_aclose():
            pass

        mock_client.aclose = mock_aclose

        with pytest.raises(TokenResponseError) as exc_info:
            asyncio.run(get_access_token_async(valid_token_config, client=mock_client))

        assert exc_info.value.error == "400"
        assert exc_info.value.error_description == "The request could not be processed"


# =============================================================================
# Test Package Exports
# =============================================================================


class TestPackageExports:
    """Tests for package-level exports."""

    def test_import_from_module(self):
        """Test importing directly from the module."""
        from anncsu.common.pdnd_token import (
            TokenConfig,
            TokenError,
            TokenRequestError,
            TokenResponse,
            TokenResponseError,
            get_access_token,
            get_access_token_async,
        )

        assert TokenConfig is not None
        assert TokenResponse is not None
        assert TokenError is not None
        assert TokenRequestError is not None
        assert TokenResponseError is not None
        assert get_access_token is not None
        assert get_access_token_async is not None

    def test_import_from_package(self):
        """Test importing from the anncsu.common package."""
        from anncsu.common import (
            TokenConfig,
            TokenError,
            TokenRequestError,
            TokenResponse,
            TokenResponseError,
            get_access_token,
            get_access_token_async,
        )

        assert TokenConfig is not None
        assert TokenResponse is not None
        assert TokenError is not None
        assert TokenRequestError is not None
        assert TokenResponseError is not None
        assert get_access_token is not None
        assert get_access_token_async is not None

    def test_constants_exported(self):
        """Test that constants are exported."""
        from anncsu.common.pdnd_token import CLIENT_ASSERTION_TYPE, GRANT_TYPE

        assert (
            CLIENT_ASSERTION_TYPE
            == "urn:ietf:params:oauth:client-assertion-type:jwt-bearer"
        )
        assert GRANT_TYPE == "client_credentials"


# =============================================================================
# Integration Tests
# =============================================================================


class TestIntegration:
    """Integration tests combining assertion and token modules."""

    def test_end_to_end_workflow_mock(self):
        """Test complete workflow from config to token (mocked)."""
        # Create token config (normally would use actual assertion)
        config = TokenConfig(
            client_id="test-client-id",
            client_assertion="mock-jwt-assertion",
            token_endpoint="https://auth.example.com/token.oauth2",
        )

        # Mock successful response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "access_token": "mock-access-token",
            "token_type": "Bearer",
            "expires_in": 600,
        }

        mock_client = MagicMock(spec=httpx.Client)
        mock_client.post.return_value = mock_response

        # Get token
        token_response = get_access_token(config, client=mock_client)

        # Verify result
        assert token_response.access_token == "mock-access-token"
        assert token_response.token_type == "Bearer"
        assert token_response.expires_in == 600

    def test_config_serialization(self, valid_token_config: TokenConfig):
        """Test that config can be serialized and deserialized."""
        # Serialize to dict
        config_dict = valid_token_config.model_dump()

        # Deserialize back
        restored_config = TokenConfig.model_validate(config_dict)

        assert restored_config.client_id == valid_token_config.client_id
        assert restored_config.token_endpoint == valid_token_config.token_endpoint
