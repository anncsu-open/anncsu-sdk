"""Integration tests for SDK instantiation and basic usage.

These tests verify that the SDK can be instantiated correctly after
the refactoring and that basic functionality works as expected.
"""

import pytest


class TestSdkInstantiation:
    """Test SDK instantiation with various configurations."""

    def test_sdk_can_be_instantiated(self):
        """Test that Anncsu SDK can be instantiated with default config."""
        from anncsu.pa import AnncsuConsultazione

        sdk = AnncsuConsultazione()
        assert sdk is not None
        assert hasattr(sdk, "queryparam")
        assert hasattr(sdk, "json_post")
        assert hasattr(sdk, "pathparam")
        assert hasattr(sdk, "status")

    def test_sdk_has_correct_attributes(self):
        """Test that SDK has all expected endpoint attributes."""
        from anncsu.pa import AnncsuConsultazione

        sdk = AnncsuConsultazione()
        # Check that all endpoint modules are accessible
        assert sdk.queryparam is not None
        assert sdk.json_post is not None
        assert sdk.pathparam is not None
        assert sdk.status is not None

    def test_sdk_configuration_is_set(self):
        """Test that SDK configuration is properly initialized."""
        from anncsu.pa import AnncsuConsultazione

        sdk = AnncsuConsultazione()
        assert hasattr(sdk, "sdk_configuration")
        assert sdk.sdk_configuration is not None

    def test_sdk_with_custom_server_url(self):
        """Test SDK instantiation with custom server URL."""
        from anncsu.pa import AnncsuConsultazione

        custom_url = "https://custom.example.com"
        sdk = AnncsuConsultazione(server_url=custom_url)
        assert sdk is not None

    def test_sdk_context_manager(self):
        """Test that SDK can be used as a context manager."""
        from anncsu.pa import AnncsuConsultazione

        with AnncsuConsultazione() as sdk:
            assert sdk is not None
            assert hasattr(sdk, "queryparam")

    def test_sdk_async_context_manager(self):
        """Test that SDK can be used as an async context manager."""
        import asyncio

        from anncsu.pa import AnncsuConsultazione

        async def test_async():
            async with AnncsuConsultazione() as sdk:
                assert sdk is not None
                assert hasattr(sdk, "queryparam")

        # Run the async test
        asyncio.run(test_async())


class TestSdkWithSecurityConfiguration:
    """Test SDK with security configuration."""

    def test_sdk_with_security_parameter(self):
        """Test SDK instantiation with security parameter."""
        from anncsu.common import Security
        from anncsu.pa import AnncsuConsultazione

        security = Security(bearer="test-pdnd-voucher-token")
        sdk = AnncsuConsultazione(security=security)

        assert sdk is not None
        assert sdk.sdk_configuration.security is not None
        assert sdk.sdk_configuration.security.bearer == "test-pdnd-voucher-token"

    def test_sdk_without_security_parameter(self):
        """Test SDK instantiation without security parameter (optional)."""
        from anncsu.pa import AnncsuConsultazione

        sdk = AnncsuConsultazione()

        assert sdk is not None
        assert sdk.sdk_configuration.security is None

    def test_sdk_with_jwt_bearer_token(self):
        """Test SDK with realistic JWT bearer token."""
        from anncsu.common import Security
        from anncsu.pa import AnncsuConsultazione

        jwt_token = "eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJ0ZXN0In0.signature"
        security = Security(bearer=jwt_token)
        sdk = AnncsuConsultazione(security=security)

        assert sdk.sdk_configuration.security.bearer == jwt_token

    def test_security_is_stored_in_configuration(self):
        """Test that security is properly stored in SDK configuration."""
        from anncsu.common import Security
        from anncsu.pa import AnncsuConsultazione

        security = Security(bearer="stored-token")
        sdk = AnncsuConsultazione(security=security)

        # Security should be accessible via configuration
        assert hasattr(sdk.sdk_configuration, "security")
        assert sdk.sdk_configuration.security == security

    def test_sdk_with_none_security(self):
        """Test SDK instantiation with explicit None security."""
        from anncsu.pa import AnncsuConsultazione

        sdk = AnncsuConsultazione(security=None)

        assert sdk is not None
        assert sdk.sdk_configuration.security is None

    def test_multiple_sdks_with_different_security(self):
        """Test multiple SDK instances with different security configs."""
        from anncsu.common import Security
        from anncsu.pa import AnncsuConsultazione

        security1 = Security(bearer="token-1")
        security2 = Security(bearer="token-2")

        sdk1 = AnncsuConsultazione(security=security1)
        sdk2 = AnncsuConsultazione(security=security2)

        assert sdk1.sdk_configuration.security.bearer == "token-1"
        assert sdk2.sdk_configuration.security.bearer == "token-2"
        assert (
            sdk1.sdk_configuration.security.bearer
            != sdk2.sdk_configuration.security.bearer
        )


class TestSdkWithRetryConfiguration:
    """Test SDK with retry configuration using common utilities."""

    def test_sdk_with_retry_config(self):
        """Test SDK instantiation with retry configuration from common."""
        from anncsu.common.utils import BackoffStrategy, RetryConfig
        from anncsu.pa import AnncsuConsultazione

        retry_config = RetryConfig(
            strategy="backoff",
            backoff=BackoffStrategy(
                initial_interval=500,
                max_interval=60000,
                exponent=1.5,
                max_elapsed_time=300000,
            ),
            retry_connection_errors=True,
        )

        sdk = AnncsuConsultazione(retry_config=retry_config)
        assert sdk is not None

    def test_retry_config_import_from_common(self):
        """Test that RetryConfig can be imported from common."""
        from anncsu.common.utils import BackoffStrategy, RetryConfig

        retry_config = RetryConfig(
            strategy="backoff",
            backoff=BackoffStrategy(1, 50, 1.1, 100),
            retry_connection_errors=False,
        )
        assert retry_config is not None
        assert retry_config.strategy == "backoff"


class TestEndpointAccess:
    """Test accessing SDK endpoints."""

    def test_queryparam_endpoint_accessible(self):
        """Test that queryparam endpoint is accessible."""
        from anncsu.pa import AnncsuConsultazione

        sdk = AnncsuConsultazione()
        assert hasattr(sdk.queryparam, "esiste_odonimo_get_query_param")

    def test_json_post_endpoint_accessible(self):
        """Test that json_post endpoint is accessible."""
        from anncsu.pa import AnncsuConsultazione

        sdk = AnncsuConsultazione()
        assert hasattr(sdk.json_post, "esiste_odonimo_post")

    def test_pathparam_endpoint_accessible(self):
        """Test that pathparam endpoint is accessible."""
        from anncsu.pa import AnncsuConsultazione

        sdk = AnncsuConsultazione()
        assert hasattr(sdk.pathparam, "esiste_odonimo_get_path_param")

    def test_status_endpoint_accessible(self):
        """Test that status endpoint is accessible."""
        from anncsu.pa import AnncsuConsultazione

        sdk = AnncsuConsultazione()
        assert hasattr(sdk.status, "show_status")


class TestModelsUsage:
    """Test usage of models with the SDK."""

    def test_request_model_can_be_instantiated(self):
        """Test that request models can be instantiated."""
        from anncsu.pa.models import EsisteOdonimoGetQueryParamRequest

        request = EsisteOdonimoGetQueryParamRequest(codcom="H501", denom="VklBIFJPTUE=")
        assert request is not None
        assert request.codcom == "H501"
        assert request.denom == "VklBIFJPTUE="

    def test_model_uses_common_basemodel(self):
        """Test that models inherit from common BaseModel."""
        from anncsu.common.types import BaseModel
        from anncsu.pa.models import EsisteOdonimoGetQueryParamRequest

        request = EsisteOdonimoGetQueryParamRequest(codcom="H501", denom="VklBIFJPTUE=")
        assert isinstance(request, BaseModel)


class TestErrorHandling:
    """Test error handling with common error classes."""

    def test_anncsu_error_can_be_caught(self):
        """Test that AnncsuError can be imported and caught."""
        from anncsu.pa.errors import AnncsuError

        # Verify it's an Exception subclass
        assert issubclass(AnncsuError, Exception)

    def test_common_base_error_accessible(self):
        """Test that AnncsuBaseError from common is accessible."""
        from anncsu.common.errors import AnncsuBaseError

        assert issubclass(AnncsuBaseError, Exception)

    def test_api_error_accessible(self):
        """Test that APIError from common is accessible."""
        from anncsu.common.errors import AnncsuBaseError, APIError

        assert issubclass(APIError, AnncsuBaseError)


class TestNamespacePackage:
    """Test that the anncsu namespace package works correctly."""

    def test_anncsu_namespace_exists(self):
        """Test that anncsu namespace package exists."""
        import anncsu

        assert anncsu is not None

    def test_anncsu_has_common_subpackage(self):
        """Test that anncsu.common is accessible."""
        import anncsu.common

        assert anncsu.common is not None

    def test_anncsu_has_pa_subpackage(self):
        """Test that anncsu.pa is accessible."""
        import anncsu.pa

        assert anncsu.pa is not None

    def test_common_and_pa_are_separate(self):
        """Test that common and pa are separate packages."""
        import anncsu.common
        import anncsu.pa

        # They should have different paths
        assert anncsu.common.__path__ != anncsu.pa.__path__


class TestCrossPackageImports:
    """Test that cross-package imports work correctly."""

    def test_pa_can_use_common_types(self):
        """Test that PA package can use types from common."""
        from anncsu.common.types import BaseModel
        from anncsu.pa.models import EsisteOdonimoGetQueryParamRequest

        # PA models should use common BaseModel
        assert issubclass(EsisteOdonimoGetQueryParamRequest, BaseModel)

    def test_pa_can_use_common_utils(self):
        """Test that PA package can use utils from common."""
        from anncsu.common.utils import RetryConfig
        from anncsu.pa import AnncsuConsultazione

        # Should be able to create SDK with common retry config
        sdk = AnncsuConsultazione(retry_config=RetryConfig("backoff", None, False))
        assert sdk is not None

    def test_common_does_not_depend_on_pa(self):
        """Test that common package doesn't import from pa."""
        import anncsu.common.errors
        import anncsu.common.types
        import anncsu.common.utils

        # Common should be importable without PA being imported
        # This verifies proper separation of concerns
        assert anncsu.common.types is not None
        assert anncsu.common.utils is not None
        assert anncsu.common.errors is not None


class TestCoordinateSdkInstantiation:
    """Test AnncsuCoordinate SDK instantiation with various configurations."""

    def test_coordinate_sdk_can_be_instantiated(self):
        """Test that AnncsuCoordinate SDK can be instantiated with default config."""
        from anncsu.coordinate import AnncsuCoordinate

        sdk = AnncsuCoordinate()
        assert sdk is not None
        assert hasattr(sdk, "json_post")
        assert hasattr(sdk, "status")

    def test_coordinate_sdk_has_correct_attributes(self):
        """Test that Coordinate SDK has all expected endpoint attributes."""
        from anncsu.coordinate import AnncsuCoordinate

        sdk = AnncsuCoordinate()
        # Check that all endpoint modules are accessible
        assert sdk.json_post is not None
        assert sdk.status is not None

    def test_coordinate_sdk_configuration_is_set(self):
        """Test that Coordinate SDK configuration is properly initialized."""
        from anncsu.coordinate import AnncsuCoordinate

        sdk = AnncsuCoordinate()
        assert hasattr(sdk, "sdk_configuration")
        assert sdk.sdk_configuration is not None

    def test_coordinate_sdk_with_custom_server_url(self):
        """Test Coordinate SDK instantiation with custom server URL."""
        from anncsu.coordinate import AnncsuCoordinate

        custom_url = "https://custom.example.com"
        sdk = AnncsuCoordinate(server_url=custom_url)
        assert sdk is not None

    def test_coordinate_sdk_context_manager(self):
        """Test that Coordinate SDK can be used as a context manager."""
        from anncsu.coordinate import AnncsuCoordinate

        with AnncsuCoordinate() as sdk:
            assert sdk is not None
            assert hasattr(sdk, "json_post")

    def test_coordinate_sdk_async_context_manager(self):
        """Test that Coordinate SDK can be used as an async context manager."""
        import asyncio

        from anncsu.coordinate import AnncsuCoordinate

        async def test_async():
            async with AnncsuCoordinate() as sdk:
                assert sdk is not None
                assert hasattr(sdk, "json_post")

        asyncio.run(test_async())


class TestCoordinateSdkWithSecurityConfiguration:
    """Test Coordinate SDK with security configuration."""

    def test_coordinate_sdk_with_security_parameter(self):
        """Test Coordinate SDK instantiation with security parameter."""
        from anncsu.coordinate import AnncsuCoordinate
        from anncsu.coordinate.models import Security

        security = Security(bearer_auth="test-pdnd-voucher-token")
        sdk = AnncsuCoordinate(security=security)

        assert sdk is not None
        assert sdk.sdk_configuration.security is not None
        assert sdk.sdk_configuration.security.bearer_auth == "test-pdnd-voucher-token"

    def test_coordinate_sdk_without_security_parameter(self):
        """Test Coordinate SDK instantiation without security parameter."""
        from anncsu.coordinate import AnncsuCoordinate

        sdk = AnncsuCoordinate()

        assert sdk is not None
        assert sdk.sdk_configuration.security is None

    def test_coordinate_sdk_with_jwt_bearer_token(self):
        """Test Coordinate SDK with realistic JWT bearer token."""
        from anncsu.coordinate import AnncsuCoordinate
        from anncsu.coordinate.models import Security

        jwt_token = "eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJ0ZXN0In0.signature"
        security = Security(bearer_auth=jwt_token)
        sdk = AnncsuCoordinate(security=security)

        assert sdk.sdk_configuration.security.bearer_auth == jwt_token

    def test_coordinate_multiple_sdks_with_different_security(self):
        """Test multiple Coordinate SDK instances with different security configs."""
        from anncsu.coordinate import AnncsuCoordinate
        from anncsu.coordinate.models import Security

        security1 = Security(bearer_auth="token-1")
        security2 = Security(bearer_auth="token-2")

        sdk1 = AnncsuCoordinate(security=security1)
        sdk2 = AnncsuCoordinate(security=security2)

        assert sdk1.sdk_configuration.security.bearer_auth == "token-1"
        assert sdk2.sdk_configuration.security.bearer_auth == "token-2"
        assert (
            sdk1.sdk_configuration.security.bearer_auth
            != sdk2.sdk_configuration.security.bearer_auth
        )


class TestCoordinateSdkWithRetryConfiguration:
    """Test Coordinate SDK with retry configuration."""

    def test_coordinate_sdk_with_retry_config(self):
        """Test Coordinate SDK instantiation with retry configuration."""
        from anncsu.common.utils import BackoffStrategy, RetryConfig
        from anncsu.coordinate import AnncsuCoordinate

        retry_config = RetryConfig(
            strategy="backoff",
            backoff=BackoffStrategy(
                initial_interval=500,
                max_interval=60000,
                exponent=1.5,
                max_elapsed_time=300000,
            ),
            retry_connection_errors=True,
        )

        sdk = AnncsuCoordinate(retry_config=retry_config)
        assert sdk is not None


class TestCoordinateEndpointAccess:
    """Test accessing Coordinate SDK endpoints."""

    def test_json_post_endpoint_accessible(self):
        """Test that json_post endpoint is accessible."""
        from anncsu.coordinate import AnncsuCoordinate

        sdk = AnncsuCoordinate()
        assert hasattr(sdk.json_post, "gestionecoordinate")

    def test_status_endpoint_accessible(self):
        """Test that status endpoint is accessible."""
        from anncsu.coordinate import AnncsuCoordinate

        sdk = AnncsuCoordinate()
        assert hasattr(sdk.status, "show_status")


class TestCoordinateModelsUsage:
    """Test usage of Coordinate models with the SDK."""

    def test_coordinate_request_model_can_be_instantiated(self):
        """Test that Coordinate request models can be instantiated."""
        from anncsu.coordinate.models import RichiestaOperazione

        request = RichiestaOperazione()
        assert request is not None

    def test_coordinate_model_uses_common_basemodel(self):
        """Test that Coordinate models inherit from common BaseModel."""
        from anncsu.common.sdk.types import BaseModel
        from anncsu.coordinate.models import RichiestaOperazione

        request = RichiestaOperazione()
        assert isinstance(request, BaseModel)


class TestCoordinateErrorHandling:
    """Test error handling with Coordinate SDK."""

    def test_coordinate_anncsu_error_can_be_caught(self):
        """Test that AnncsuError can be imported from coordinate package."""
        from anncsu.coordinate.errors import AnncsuError

        assert issubclass(AnncsuError, Exception)

    def test_coordinate_api_error_accessible(self):
        """Test that APIError from coordinate is accessible and extends common AnncsuError."""
        from anncsu.common.errors import AnncsuError as CommonAnncsuError
        from anncsu.coordinate.errors import APIError

        assert issubclass(APIError, CommonAnncsuError)


class TestCoordinateNamespacePackage:
    """Test that anncsu.coordinate namespace works correctly."""

    def test_anncsu_has_coordinate_subpackage(self):
        """Test that anncsu.coordinate is accessible."""
        import anncsu.coordinate

        assert anncsu.coordinate is not None

    def test_common_and_coordinate_are_separate(self):
        """Test that common and coordinate are separate packages."""
        import anncsu.common
        import anncsu.coordinate

        # They should have different paths
        assert anncsu.common.__path__ != anncsu.coordinate.__path__

    def test_pa_and_coordinate_are_separate(self):
        """Test that pa and coordinate are separate packages."""
        import anncsu.coordinate
        import anncsu.pa

        # They should have different paths
        assert anncsu.pa.__path__ != anncsu.coordinate.__path__


class TestCoordinateCrossPackageImports:
    """Test that cross-package imports work correctly for Coordinate."""

    def test_coordinate_can_use_common_types(self):
        """Test that Coordinate package can use types from common."""
        from anncsu.common.sdk.types import BaseModel
        from anncsu.coordinate.models import RichiestaOperazione

        # Coordinate models should use common BaseModel
        assert issubclass(RichiestaOperazione, BaseModel)

    def test_coordinate_can_use_common_utils(self):
        """Test that Coordinate package can use utils from common."""
        from anncsu.common.utils import RetryConfig
        from anncsu.coordinate import AnncsuCoordinate

        # Should be able to create SDK with common retry config
        sdk = AnncsuCoordinate(retry_config=RetryConfig("backoff", None, False))
        assert sdk is not None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
