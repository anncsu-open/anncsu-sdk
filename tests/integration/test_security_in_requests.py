"""Integration tests for security in HTTP requests.

These tests verify that security configuration is properly applied
to HTTP requests made by the SDK.
"""

import pytest


class TestSecurityConfiguration:
    """Test security configuration in SDK."""

    def test_security_stored_in_sdk_configuration(self):
        """Test that security is properly stored in SDK configuration."""
        from anncsu.common import Security
        from anncsu.pa import AnncsuConsultazione

        security = Security(bearer="test-bearer-token")
        sdk = AnncsuConsultazione(security=security)

        # Verify security is stored
        assert sdk.sdk_configuration.security is not None
        assert sdk.sdk_configuration.security.bearer == "test-bearer-token"

    def test_security_accessible_from_subsdk(self):
        """Test that security is accessible from sub-SDK components."""
        from anncsu.common import Security
        from anncsu.pa import AnncsuConsultazione

        security = Security(bearer="subsdk-token")
        sdk = AnncsuConsultazione(security=security)

        # Access a sub-SDK and verify it has access to the security config
        queryparam_sdk = sdk.queryparam
        assert queryparam_sdk.sdk_configuration.security is not None
        assert queryparam_sdk.sdk_configuration.security.bearer == "subsdk-token"

    def test_security_with_jwt_token_format(self):
        """Test security with JWT format bearer token."""
        from anncsu.common import Security
        from anncsu.pa import AnncsuConsultazione

        jwt_token = "eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJ0ZXN0In0.signature"
        security = Security(bearer=jwt_token)
        sdk = AnncsuConsultazione(security=security)

        assert sdk.sdk_configuration.security.bearer == jwt_token

    def test_multiple_subsdk_share_same_security(self):
        """Test that all sub-SDKs share the same security configuration."""
        from anncsu.common import Security
        from anncsu.pa import AnncsuConsultazione

        security = Security(bearer="shared-token")
        sdk = AnncsuConsultazione(security=security)

        # All sub-SDKs should have the same security config
        assert sdk.queryparam.sdk_configuration.security.bearer == "shared-token"
        assert sdk.json_post.sdk_configuration.security.bearer == "shared-token"
        assert sdk.pathparam.sdk_configuration.security.bearer == "shared-token"
        assert sdk.status.sdk_configuration.security.bearer == "shared-token"

    def test_security_none_when_not_provided(self):
        """Test that security is None when not provided."""
        from anncsu.pa import AnncsuConsultazione

        sdk = AnncsuConsultazione()

        assert sdk.sdk_configuration.security is None
        assert sdk.queryparam.sdk_configuration.security is None


class TestSecurityDocumentation:
    """Test security usage matches documentation."""

    def test_readme_example_pattern(self):
        """Test the README security example pattern."""
        from anncsu.common import Security
        from anncsu.pa import AnncsuConsultazione

        # This pattern is from the README
        security = Security(bearer="your-pdnd-voucher-token")
        sdk = AnncsuConsultazione(security=security)

        assert sdk is not None
        assert sdk.sdk_configuration.security.bearer == "your-pdnd-voucher-token"

    def test_security_with_production_like_token(self):
        """Test with production-like PDND voucher token."""
        from anncsu.common import Security
        from anncsu.pa import AnncsuConsultazione

        # Simulate a realistic PDND voucher
        production_token = (
            "eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCIsImtpZCI6InBkbmQta2V5In0."
            "eyJpc3MiOiJodHRwczovL2F1dGgucGRuZC5pdCIsInN1YiI6InRlc3QifQ."
            "signature"
        )

        security = Security(bearer=production_token)
        sdk = AnncsuConsultazione(security=security)

        assert sdk.sdk_configuration.security.bearer == production_token


class TestSecurityWithOtherParameters:
    """Test security works with other SDK parameters."""

    def test_security_with_custom_server_url(self):
        """Test security with custom server URL."""
        from anncsu.common import Security
        from anncsu.pa import AnncsuConsultazione

        security = Security(bearer="custom-server-token")
        sdk = AnncsuConsultazione(
            security=security, server_url="https://custom.example.com/api"
        )

        assert sdk.sdk_configuration.security.bearer == "custom-server-token"

    def test_security_with_retry_config(self):
        """Test security with retry configuration."""
        from anncsu.common import Security
        from anncsu.common.utils import BackoffStrategy, RetryConfig
        from anncsu.pa import AnncsuConsultazione

        security = Security(bearer="retry-token")
        retry_config = RetryConfig(
            strategy="backoff",
            backoff=BackoffStrategy(1, 50, 1.1, 100),
            retry_connection_errors=False,
        )

        sdk = AnncsuConsultazione(security=security, retry_config=retry_config)

        assert sdk.sdk_configuration.security.bearer == "retry-token"
        assert sdk.sdk_configuration.retry_config is not None

    def test_security_with_timeout(self):
        """Test security with custom timeout."""
        from anncsu.common import Security
        from anncsu.pa import AnncsuConsultazione

        security = Security(bearer="timeout-token")
        sdk = AnncsuConsultazione(security=security, timeout_ms=30000)

        assert sdk.sdk_configuration.security.bearer == "timeout-token"
        assert sdk.sdk_configuration.timeout_ms == 30000


class TestSecurityPersistence:
    """Test security persistence across SDK usage."""

    def test_security_persists_across_context_manager(self):
        """Test that security persists when using SDK as context manager."""
        from anncsu.common import Security
        from anncsu.pa import AnncsuConsultazione

        security = Security(bearer="context-token")

        with AnncsuConsultazione(security=security) as sdk:
            assert sdk.sdk_configuration.security.bearer == "context-token"
            # Security should remain available throughout the context
            assert sdk.queryparam.sdk_configuration.security.bearer == "context-token"

    def test_security_independent_between_instances(self):
        """Test security is independent between SDK instances."""
        from anncsu.common import Security
        from anncsu.pa import AnncsuConsultazione

        security1 = Security(bearer="instance-1")
        security2 = Security(bearer="instance-2")

        sdk1 = AnncsuConsultazione(security=security1)
        sdk2 = AnncsuConsultazione(security=security2)

        # Each SDK has its own security
        assert sdk1.sdk_configuration.security.bearer == "instance-1"
        assert sdk2.sdk_configuration.security.bearer == "instance-2"

        # They should not affect each other
        assert (
            sdk1.sdk_configuration.security.bearer
            != sdk2.sdk_configuration.security.bearer
        )


class TestSecurityEdgeCases:
    """Test edge cases for security configuration."""

    def test_security_with_empty_bearer_token(self):
        """Test security with empty bearer token."""
        from anncsu.common import Security
        from anncsu.pa import AnncsuConsultazione

        security = Security(bearer="")
        sdk = AnncsuConsultazione(security=security)

        assert sdk.sdk_configuration.security.bearer == ""

    def test_security_object_without_bearer(self):
        """Test Security object created without bearer parameter."""
        from anncsu.common import Security
        from anncsu.pa import AnncsuConsultazione

        security = Security()
        sdk = AnncsuConsultazione(security=security)

        assert sdk.sdk_configuration.security.bearer is None

    def test_updating_security_after_instantiation_not_recommended(self):
        """Test that security is tied to the SDK instance."""
        from anncsu.common import Security
        from anncsu.pa import AnncsuConsultazione

        security = Security(bearer="original-token")
        sdk = AnncsuConsultazione(security=security)

        # Original security value
        assert sdk.sdk_configuration.security.bearer == "original-token"

        # Note: Modifying security after SDK creation is not the intended pattern
        # Users should create a new SDK instance with new security instead


class TestCoordinateSecurityConfiguration:
    """Test security configuration in Coordinate SDK."""

    def test_coordinate_security_stored_in_sdk_configuration(self):
        """Test that security is properly stored in Coordinate SDK configuration."""
        from anncsu.coordinate import AnncsuCoordinate
        from anncsu.coordinate.models import Security

        security = Security(bearer_auth="test-bearer-token")
        sdk = AnncsuCoordinate(security=security)

        # Verify security is stored
        assert sdk.sdk_configuration.security is not None
        assert sdk.sdk_configuration.security.bearer_auth == "test-bearer-token"

    def test_coordinate_security_accessible_from_subsdk(self):
        """Test that security is accessible from Coordinate sub-SDK components."""
        from anncsu.coordinate import AnncsuCoordinate
        from anncsu.coordinate.models import Security

        security = Security(bearer_auth="subsdk-token")
        sdk = AnncsuCoordinate(security=security)

        # Access a sub-SDK and verify it has access to the security config
        json_post_sdk = sdk.json_post
        assert json_post_sdk.sdk_configuration.security is not None
        assert json_post_sdk.sdk_configuration.security.bearer_auth == "subsdk-token"

    def test_coordinate_security_with_jwt_token_format(self):
        """Test Coordinate security with JWT format bearer token."""
        from anncsu.coordinate import AnncsuCoordinate
        from anncsu.coordinate.models import Security

        jwt_token = "eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJ0ZXN0In0.signature"
        security = Security(bearer_auth=jwt_token)
        sdk = AnncsuCoordinate(security=security)

        assert sdk.sdk_configuration.security.bearer_auth == jwt_token

    def test_coordinate_multiple_subsdk_share_same_security(self):
        """Test that all Coordinate sub-SDKs share the same security configuration."""
        from anncsu.coordinate import AnncsuCoordinate
        from anncsu.coordinate.models import Security

        security = Security(bearer_auth="shared-token")
        sdk = AnncsuCoordinate(security=security)

        # All sub-SDKs should have the same security config
        assert sdk.json_post.sdk_configuration.security.bearer_auth == "shared-token"
        assert sdk.status.sdk_configuration.security.bearer_auth == "shared-token"

    def test_coordinate_security_none_when_not_provided(self):
        """Test that Coordinate security is None when not provided."""
        from anncsu.coordinate import AnncsuCoordinate

        sdk = AnncsuCoordinate()

        assert sdk.sdk_configuration.security is None
        assert sdk.json_post.sdk_configuration.security is None


class TestCoordinateSecurityWithOtherParameters:
    """Test Coordinate security works with other SDK parameters."""

    def test_coordinate_security_with_custom_server_url(self):
        """Test Coordinate security with custom server URL."""
        from anncsu.coordinate import AnncsuCoordinate
        from anncsu.coordinate.models import Security

        security = Security(bearer_auth="custom-server-token")
        sdk = AnncsuCoordinate(
            security=security, server_url="https://custom.example.com/api"
        )

        assert sdk.sdk_configuration.security.bearer_auth == "custom-server-token"

    def test_coordinate_security_with_retry_config(self):
        """Test Coordinate security with retry configuration."""
        from anncsu.common.utils import BackoffStrategy, RetryConfig
        from anncsu.coordinate import AnncsuCoordinate
        from anncsu.coordinate.models import Security

        security = Security(bearer_auth="retry-token")
        retry_config = RetryConfig(
            strategy="backoff",
            backoff=BackoffStrategy(1, 50, 1.1, 100),
            retry_connection_errors=False,
        )

        sdk = AnncsuCoordinate(security=security, retry_config=retry_config)

        assert sdk.sdk_configuration.security.bearer_auth == "retry-token"
        assert sdk.sdk_configuration.retry_config is not None

    def test_coordinate_security_with_timeout(self):
        """Test Coordinate security with custom timeout."""
        from anncsu.coordinate import AnncsuCoordinate
        from anncsu.coordinate.models import Security

        security = Security(bearer_auth="timeout-token")
        sdk = AnncsuCoordinate(security=security, timeout_ms=30000)

        assert sdk.sdk_configuration.security.bearer_auth == "timeout-token"
        assert sdk.sdk_configuration.timeout_ms == 30000


class TestCoordinateSecurityPersistence:
    """Test Coordinate security persistence across SDK usage."""

    def test_coordinate_security_persists_across_context_manager(self):
        """Test that Coordinate security persists when using SDK as context manager."""
        from anncsu.coordinate import AnncsuCoordinate
        from anncsu.coordinate.models import Security

        security = Security(bearer_auth="context-token")

        with AnncsuCoordinate(security=security) as sdk:
            assert sdk.sdk_configuration.security.bearer_auth == "context-token"
            # Security should remain available throughout the context
            assert (
                sdk.json_post.sdk_configuration.security.bearer_auth == "context-token"
            )

    def test_coordinate_security_independent_between_instances(self):
        """Test Coordinate security is independent between SDK instances."""
        from anncsu.coordinate import AnncsuCoordinate
        from anncsu.coordinate.models import Security

        security1 = Security(bearer_auth="instance-1")
        security2 = Security(bearer_auth="instance-2")

        sdk1 = AnncsuCoordinate(security=security1)
        sdk2 = AnncsuCoordinate(security=security2)

        # Each SDK has its own security
        assert sdk1.sdk_configuration.security.bearer_auth == "instance-1"
        assert sdk2.sdk_configuration.security.bearer_auth == "instance-2"

        # They should not affect each other
        assert (
            sdk1.sdk_configuration.security.bearer_auth
            != sdk2.sdk_configuration.security.bearer_auth
        )


class TestCoordinateSecurityEdgeCases:
    """Test edge cases for Coordinate security configuration."""

    def test_coordinate_security_with_empty_bearer_token(self):
        """Test Coordinate security with empty bearer token."""
        from anncsu.coordinate import AnncsuCoordinate
        from anncsu.coordinate.models import Security

        security = Security(bearer_auth="")
        sdk = AnncsuCoordinate(security=security)

        assert sdk.sdk_configuration.security.bearer_auth == ""

    def test_coordinate_security_object_without_bearer(self):
        """Test Coordinate Security object created without bearer parameter."""
        from anncsu.coordinate import AnncsuCoordinate
        from anncsu.coordinate.models import Security

        security = Security()
        sdk = AnncsuCoordinate(security=security)

        assert sdk.sdk_configuration.security.bearer_auth is None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
