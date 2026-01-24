"""Test imports for anncsu.pa package.

This test suite verifies that all modules in the anncsu.pa package
can be imported successfully and that they correctly reference
shared components from anncsu.common.
"""

import pytest


class TestPaPackageImports:
    """Test that the anncsu.pa package structure is correct."""

    def test_import_pa_package(self):
        """Test that anncsu.pa package can be imported."""
        import anncsu.pa

        assert anncsu.pa is not None

    def test_pa_package_has_path(self):
        """Test that anncsu.pa has a __path__ attribute."""
        import anncsu.pa

        assert hasattr(anncsu.pa, "__path__")


class TestPaSdkImports:
    """Test imports of the main SDK class."""

    def test_import_anncsu_sdk(self):
        """Test that Anncsu SDK can be imported."""
        from anncsu.pa import Anncsu

        assert Anncsu is not None

    def test_import_sdk_from_module(self):
        """Test that SDK can be imported from sdk module."""
        from anncsu.pa.sdk import Anncsu

        assert Anncsu is not None


class TestPaEndpointImports:
    """Test imports of endpoint classes."""

    def test_import_queryparam(self):
        """Test that Queryparam endpoint can be imported."""
        from anncsu.pa.queryparam import Queryparam

        assert Queryparam is not None

    def test_import_jsonpost(self):
        """Test that JSONPost endpoint can be imported."""
        from anncsu.pa.jsonpost import JSONPost

        assert JSONPost is not None

    def test_import_pathparam(self):
        """Test that Pathparam endpoint can be imported."""
        from anncsu.pa.pathparam import Pathparam

        assert Pathparam is not None

    def test_import_status(self):
        """Test that Status endpoint can be imported."""
        from anncsu.pa.status import Status

        assert Status is not None


class TestPaModelsImports:
    """Test imports of PA-specific models."""

    def test_import_models_module(self):
        """Test that models module can be imported."""
        from anncsu.pa import models

        assert models is not None

    def test_import_esiste_odonimo_request(self):
        """Test that EsisteOdonimoGetQueryParamRequest can be imported."""
        from anncsu.pa.models import EsisteOdonimoGetQueryParamRequest

        assert EsisteOdonimoGetQueryParamRequest is not None

    def test_import_esiste_odonimo_response(self):
        """Test that EsisteOdonimoGetQueryParamResponse can be imported."""
        from anncsu.pa.models import EsisteOdonimoGetQueryParamResponse

        assert EsisteOdonimoGetQueryParamResponse is not None

    def test_import_show_status_response(self):
        """Test that ShowStatusResponse can be imported."""
        from anncsu.pa.models import ShowStatusResponse

        assert ShowStatusResponse is not None

    def test_models_use_common_basemodel(self):
        """Test that PA models inherit from common BaseModel."""
        from anncsu.common.types import BaseModel
        from anncsu.pa.models import EsisteOdonimoGetQueryParamRequest

        assert issubclass(EsisteOdonimoGetQueryParamRequest, BaseModel)


class TestPaErrorsImports:
    """Test imports of PA-specific errors."""

    def test_import_errors_module(self):
        """Test that errors module can be imported."""
        from anncsu.pa import errors

        assert errors is not None

    def test_import_anncsu_error(self):
        """Test that AnncsuError can be imported (compatibility)."""
        from anncsu.pa.errors import AnncsuError

        assert AnncsuError is not None

    def test_import_api_error(self):
        """Test that APIError can be imported."""
        from anncsu.pa.errors import APIError

        assert APIError is not None

    def test_import_operation_specific_error(self):
        """Test that operation-specific errors can be imported."""
        from anncsu.pa.errors import EsisteOdonimoGetQueryParamBadRequestError

        assert EsisteOdonimoGetQueryParamBadRequestError is not None


class TestPaUsesCommonComponents:
    """Test that PA package correctly uses common components."""

    def test_pa_imports_common_types(self):
        """Test that PA can access common types."""
        from anncsu.common.types import BaseModel
        from anncsu.pa.models import EsisteOdonimoGetQueryParamRequest

        # Verify the model uses the common BaseModel
        assert issubclass(EsisteOdonimoGetQueryParamRequest, BaseModel)

    def test_pa_can_import_common_utils(self):
        """Test that PA code can import common utils."""
        # This tests the refactoring - PA should be able to use common utils
        from anncsu.common.utils import RetryConfig

        assert RetryConfig is not None

    def test_pa_can_import_common_errors(self):
        """Test that PA code can import common errors."""
        from anncsu.common.errors import AnncsuBaseError

        assert AnncsuBaseError is not None


class TestPaUsesCommonSdk:
    """Test that PA package correctly uses common SDK infrastructure.

    Note: After refactoring, PA no longer has its own types/ and utils/ modules.
    These are now centralized in common/sdk/. Code in PA should import from
    anncsu.common.sdk directly.
    """

    def test_pa_uses_common_sdk_types(self):
        """Test that PA should use types from common/sdk/."""
        from anncsu.common.sdk.types import BaseModel

        # Verify we can import from the correct location
        assert BaseModel is not None

    def test_pa_uses_common_sdk_utils(self):
        """Test that PA should use utils from common/sdk/."""
        from anncsu.common.sdk.utils import RetryConfig

        # Verify we can import from the correct location
        assert RetryConfig is not None

    def test_pa_uses_common_sdk_basesdk(self):
        """Test that PA should use BaseSDK from common/sdk/."""
        from anncsu.common.sdk import BaseSDK

        # Verify we can import from the correct location
        assert BaseSDK is not None


class TestSdkConfiguration:
    """Test SDK configuration imports."""

    def test_import_sdk_configuration_from_pa(self):
        """Test that SDKConfiguration can be imported from pa."""
        from anncsu.pa.sdkconfiguration import SDKConfiguration

        assert SDKConfiguration is not None

    def test_import_base_sdk_from_common_sdk(self):
        """Test that BaseSDK is imported from common/sdk/ (not pa/)."""
        from anncsu.common.sdk import BaseSDK

        assert BaseSDK is not None


class TestVersioning:
    """Test version information imports."""

    def test_import_version_info(self):
        """Test that version information can be imported."""
        from anncsu.pa import VERSION

        assert VERSION is not None

    def test_import_version_from_module(self):
        """Test that version can be imported from _version module."""
        from anncsu.pa._version import __version__

        assert __version__ is not None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
