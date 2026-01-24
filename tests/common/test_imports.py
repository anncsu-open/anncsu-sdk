"""Test imports for anncsu.common package.

This test suite verifies that all modules in the anncsu.common package
can be imported successfully. After refactoring, the base SDK infrastructure
is now in anncsu.common.sdk, with backward-compatible re-exports from
anncsu.common.types and anncsu.common.utils.
"""

import pytest


class TestCommonPackageImports:
    """Test that the anncsu.common package structure is correct."""

    def test_import_common_package(self):
        """Test that anncsu.common package can be imported."""
        import anncsu.common

        assert anncsu.common is not None

    def test_common_package_has_path(self):
        """Test that anncsu.common has a __path__ attribute."""
        import anncsu.common

        assert hasattr(anncsu.common, "__path__")


class TestCommonTypesImports:
    """Test imports from anncsu.common.types module (re-exports from sdk.types)."""

    def test_import_types_module(self):
        """Test that anncsu.common.types can be imported."""
        import anncsu.common.types

        assert anncsu.common.types is not None

    def test_import_basemodel(self):
        """Test that BaseModel can be imported."""
        from anncsu.common.types import BaseModel

        assert BaseModel is not None

    def test_import_nullable(self):
        """Test that Nullable can be imported."""
        from anncsu.common.types import Nullable

        assert Nullable is not None

    def test_import_optional_nullable(self):
        """Test that OptionalNullable can be imported."""
        from anncsu.common.types import OptionalNullable

        assert OptionalNullable is not None

    def test_import_unset(self):
        """Test that UNSET can be imported."""
        from anncsu.common.types import UNSET

        assert UNSET is not None

    def test_import_unset_sentinel(self):
        """Test that UNSET_SENTINEL can be imported."""
        from anncsu.common.types import UNSET_SENTINEL

        assert UNSET_SENTINEL is not None

    def test_import_unrecognized_types(self):
        """Test that UnrecognizedInt and UnrecognizedStr can be imported."""
        from anncsu.common.types import UnrecognizedInt, UnrecognizedStr

        assert UnrecognizedInt is not None
        assert UnrecognizedStr is not None


class TestCommonUtilsImports:
    """Test imports from anncsu.common.utils module (re-exports from sdk.utils)."""

    def test_import_utils_module(self):
        """Test that anncsu.common.utils can be imported."""
        import anncsu.common.utils

        assert anncsu.common.utils is not None

    def test_import_retry_config(self):
        """Test that RetryConfig can be imported."""
        from anncsu.common.utils import RetryConfig

        assert RetryConfig is not None

    def test_import_backoff_strategy(self):
        """Test that BackoffStrategy can be imported."""
        from anncsu.common.utils import BackoffStrategy

        assert BackoffStrategy is not None

    def test_import_serialized_request_body(self):
        """Test that SerializedRequestBody can be imported."""
        from anncsu.common.utils import SerializedRequestBody

        assert SerializedRequestBody is not None

    def test_import_field_metadata(self):
        """Test that FieldMetadata can be imported."""
        from anncsu.common.utils import FieldMetadata

        assert FieldMetadata is not None

    def test_import_query_param_metadata(self):
        """Test that QueryParamMetadata can be imported."""
        from anncsu.common.utils import QueryParamMetadata

        assert QueryParamMetadata is not None

    def test_import_path_param_metadata(self):
        """Test that PathParamMetadata can be imported."""
        from anncsu.common.utils import PathParamMetadata

        assert PathParamMetadata is not None

    def test_import_header_metadata(self):
        """Test that HeaderMetadata can be imported."""
        from anncsu.common.utils import HeaderMetadata

        assert HeaderMetadata is not None


class TestCommonErrorsImports:
    """Test imports from anncsu.common.errors module."""

    def test_import_errors_module(self):
        """Test that anncsu.common.errors can be imported."""
        import anncsu.common.errors

        assert anncsu.common.errors is not None

    def test_import_anncsu_base_error(self):
        """Test that AnncsuBaseError can be imported."""
        from anncsu.common.errors import AnncsuBaseError

        assert AnncsuBaseError is not None
        assert issubclass(AnncsuBaseError, Exception)

    def test_import_api_error(self):
        """Test that APIError can be imported."""
        from anncsu.common.errors import APIError

        assert APIError is not None

    def test_import_no_response_error(self):
        """Test that NoResponseError can be imported."""
        from anncsu.common.errors import NoResponseError

        assert NoResponseError is not None
        assert issubclass(NoResponseError, Exception)

    def test_import_response_validation_error(self):
        """Test that ResponseValidationError can be imported."""
        from anncsu.common.errors import ResponseValidationError

        assert ResponseValidationError is not None

    def test_api_error_inherits_from_base(self):
        """Test that APIError inherits from AnncsuBaseError."""
        from anncsu.common.errors import AnncsuBaseError, APIError

        assert issubclass(APIError, AnncsuBaseError)

    def test_response_validation_error_inherits_from_base(self):
        """Test that ResponseValidationError inherits from AnncsuBaseError."""
        from anncsu.common.errors import (
            AnncsuBaseError,
            ResponseValidationError,
        )

        assert issubclass(ResponseValidationError, AnncsuBaseError)


class TestCommonHooksImports:
    """Test imports from anncsu.common.hooks module."""

    def test_import_hooks_module(self):
        """Test that anncsu.common.hooks can be imported."""
        import anncsu.common.hooks

        assert anncsu.common.hooks is not None

    def test_import_sdk_hooks(self):
        """Test that SDKHooks can be imported."""
        from anncsu.common.hooks import SDKHooks

        assert SDKHooks is not None

    def test_import_hook_contexts(self):
        """Test that hook context classes can be imported."""
        from anncsu.common.hooks import (
            AfterErrorContext,
            AfterSuccessContext,
            BeforeRequestContext,
        )

        assert BeforeRequestContext is not None
        assert AfterSuccessContext is not None
        assert AfterErrorContext is not None


class TestCommonSDKInfrastructureImports:
    """Test imports of SDK infrastructure from anncsu.common.sdk."""

    def test_import_sdk_package(self):
        """Test that anncsu.common.sdk package can be imported."""
        import anncsu.common.sdk

        assert anncsu.common.sdk is not None

    def test_import_base_sdk_from_sdk_package(self):
        """Test that BaseSDK can be imported from common.sdk."""
        from anncsu.common.sdk import BaseSDK

        assert BaseSDK is not None

    def test_import_http_client_from_sdk_package(self):
        """Test that HttpClient can be imported from common.sdk."""
        from anncsu.common.sdk import HttpClient

        assert HttpClient is not None

    def test_import_async_http_client_from_sdk_package(self):
        """Test that AsyncHttpClient can be imported from common.sdk."""
        from anncsu.common.sdk import AsyncHttpClient

        assert AsyncHttpClient is not None

    def test_import_sdk_configuration_protocol(self):
        """Test that SDKConfigurationProtocol can be imported."""
        from anncsu.common.sdk import SDKConfigurationProtocol

        assert SDKConfigurationProtocol is not None

    def test_import_sdk_configuration(self):
        """Test that SDKConfiguration can be imported."""
        from anncsu.common.sdkconfiguration import SDKConfiguration

        assert SDKConfiguration is not None


class TestCommonSDKUtilsImports:
    """Test imports from anncsu.common.sdk.utils module."""

    def test_import_sdk_utils_module(self):
        """Test that anncsu.common.sdk.utils can be imported."""
        import anncsu.common.sdk.utils

        assert anncsu.common.sdk.utils is not None

    def test_import_get_security(self):
        """Test that get_security can be imported."""
        from anncsu.common.sdk.utils import get_security

        assert get_security is not None

    def test_import_marshal_json(self):
        """Test that marshal_json can be imported."""
        from anncsu.common.sdk.utils import marshal_json

        assert marshal_json is not None

    def test_import_unmarshal_json(self):
        """Test that unmarshal_json can be imported."""
        from anncsu.common.sdk.utils import unmarshal_json

        assert unmarshal_json is not None

    def test_import_generate_url(self):
        """Test that generate_url can be imported."""
        from anncsu.common.sdk.utils import generate_url

        assert generate_url is not None

    def test_import_template_url(self):
        """Test that template_url can be imported."""
        from anncsu.common.sdk.utils import template_url

        assert template_url is not None

    def test_import_logger(self):
        """Test that Logger can be imported."""
        from anncsu.common.sdk.utils import Logger

        assert Logger is not None


class TestCommonSDKTypesImports:
    """Test imports from anncsu.common.sdk.types module."""

    def test_import_sdk_types_module(self):
        """Test that anncsu.common.sdk.types can be imported."""
        import anncsu.common.sdk.types

        assert anncsu.common.sdk.types is not None

    def test_import_basemodel_from_sdk_types(self):
        """Test that BaseModel can be imported from sdk.types."""
        from anncsu.common.sdk.types import BaseModel

        assert BaseModel is not None

    def test_import_unset_from_sdk_types(self):
        """Test that UNSET can be imported from sdk.types."""
        from anncsu.common.sdk.types import UNSET

        assert UNSET is not None


class TestBackwardCompatibility:
    """Test backward compatibility of import paths."""

    def test_types_backward_compatible(self):
        """Test that imports from common.types work (re-exports from sdk.types)."""
        from anncsu.common.sdk.types import (
            UNSET as SDK_UNSET,
        )
        from anncsu.common.sdk.types import (
            BaseModel as SDKBaseModel,
        )
        from anncsu.common.types import UNSET, BaseModel

        # They should be the same objects
        assert BaseModel is SDKBaseModel
        assert UNSET is SDK_UNSET

    def test_utils_backward_compatible(self):
        """Test that imports from common.utils work (re-exports from sdk.utils)."""
        from anncsu.common.sdk.utils import (
            FieldMetadata as SDKFieldMetadata,
        )
        from anncsu.common.sdk.utils import (
            RetryConfig as SDKRetryConfig,
        )
        from anncsu.common.utils import FieldMetadata, RetryConfig

        # They should be the same objects
        assert RetryConfig is SDKRetryConfig
        assert FieldMetadata is SDKFieldMetadata


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
