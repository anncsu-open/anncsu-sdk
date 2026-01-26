"""Test imports for anncsu.coordinate package.

This test suite verifies that all modules in the anncsu.coordinate package
can be imported successfully and that they correctly reference
shared components from anncsu.common.
"""

import pytest


class TestCoordinatePackageImports:
    """Test that the anncsu.coordinate package structure is correct."""

    def test_import_coordinate_package(self):
        """Test that anncsu.coordinate package can be imported."""
        import anncsu.coordinate

        assert anncsu.coordinate is not None

    def test_coordinate_package_has_path(self):
        """Test that anncsu.coordinate has a __path__ attribute."""
        import anncsu.coordinate

        assert hasattr(anncsu.coordinate, "__path__")


class TestCoordinateSdkImports:
    """Test imports of the main SDK class."""

    def test_import_anncsu_coordinate_sdk(self):
        """Test that AnncsuCoordinate SDK can be imported."""
        from anncsu.coordinate import AnncsuCoordinate

        assert AnncsuCoordinate is not None

    def test_import_sdk_from_module(self):
        """Test that SDK can be imported from sdk module."""
        from anncsu.coordinate.sdk import AnncsuCoordinate

        assert AnncsuCoordinate is not None


class TestCoordinateEndpointImports:
    """Test imports of endpoint classes."""

    def test_import_json_post(self):
        """Test that JSONPost endpoint can be imported."""
        from anncsu.coordinate.jsonpost import JSONPost

        assert JSONPost is not None

    def test_import_status(self):
        """Test that Status endpoint can be imported."""
        from anncsu.coordinate.status import Status

        assert Status is not None


class TestCoordinateModelsImports:
    """Test imports of Coordinate-specific models."""

    def test_import_models_module(self):
        """Test that models module can be imported."""
        from anncsu.coordinate import models

        assert models is not None

    def test_import_richiesta_operazione(self):
        """Test that RichiestaOperazione can be imported."""
        from anncsu.coordinate.models import RichiestaOperazione

        assert RichiestaOperazione is not None

    def test_import_risposta_operazione(self):
        """Test that RispostaOperazione can be imported."""
        from anncsu.coordinate.models import RispostaOperazione

        assert RispostaOperazione is not None

    def test_import_security_model(self):
        """Test that Security model can be imported."""
        from anncsu.coordinate.models import Security

        assert Security is not None

    def test_import_show_status_response(self):
        """Test that ShowStatusResponse can be imported."""
        from anncsu.coordinate.models import ShowStatusResponse

        assert ShowStatusResponse is not None

    def test_models_use_common_basemodel(self):
        """Test that Coordinate models inherit from common BaseModel."""
        from anncsu.common.sdk.types import BaseModel
        from anncsu.coordinate.models import RichiestaOperazione

        assert issubclass(RichiestaOperazione, BaseModel)


class TestCoordinateErrorsImports:
    """Test imports of Coordinate-specific errors."""

    def test_import_errors_module(self):
        """Test that errors module can be imported."""
        from anncsu.coordinate import errors

        assert errors is not None

    def test_import_anncsu_error(self):
        """Test that AnncsuError can be imported."""
        from anncsu.coordinate.errors import AnncsuError

        assert AnncsuError is not None

    def test_import_api_error(self):
        """Test that APIError can be imported."""
        from anncsu.coordinate.errors import APIError

        assert APIError is not None

    def test_import_risposta_errore(self):
        """Test that RispostaErrore error can be imported."""
        from anncsu.coordinate.errors import RispostaErrore

        assert RispostaErrore is not None


class TestCoordinateUsesCommonComponents:
    """Test that Coordinate package correctly uses common components."""

    def test_coordinate_imports_common_types(self):
        """Test that Coordinate can access common types."""
        from anncsu.common.sdk.types import BaseModel
        from anncsu.coordinate.models import RichiestaOperazione

        # Verify the model uses the common BaseModel
        assert issubclass(RichiestaOperazione, BaseModel)

    def test_coordinate_can_import_common_utils(self):
        """Test that Coordinate code can import common utils."""
        from anncsu.common.sdk.utils import RetryConfig

        assert RetryConfig is not None

    def test_coordinate_can_import_common_errors(self):
        """Test that Coordinate code can import common errors."""
        from anncsu.common.errors import AnncsuBaseError

        assert AnncsuBaseError is not None


class TestCoordinateUsesCommonSdk:
    """Test that Coordinate package correctly uses common SDK infrastructure.

    Note: After refactoring, Coordinate does not have its own types/ and utils/ modules.
    These are centralized in common/sdk/. Code in Coordinate should import from
    anncsu.common.sdk directly.
    """

    def test_coordinate_uses_common_sdk_types(self):
        """Test that Coordinate should use types from common/sdk/."""
        from anncsu.common.sdk.types import BaseModel

        assert BaseModel is not None

    def test_coordinate_uses_common_sdk_utils(self):
        """Test that Coordinate should use utils from common/sdk/."""
        from anncsu.common.sdk.utils import RetryConfig

        assert RetryConfig is not None

    def test_coordinate_uses_common_sdk_basesdk(self):
        """Test that Coordinate should use BaseSDK from common/sdk/."""
        from anncsu.common.sdk import BaseSDK

        assert BaseSDK is not None


class TestCoordinateSdkConfiguration:
    """Test SDK configuration imports."""

    def test_import_sdk_configuration_from_coordinate(self):
        """Test that SDKConfiguration can be imported from coordinate."""
        from anncsu.coordinate.sdkconfiguration import SDKConfiguration

        assert SDKConfiguration is not None

    def test_import_base_sdk_from_common_sdk(self):
        """Test that BaseSDK is imported from common/sdk/."""
        from anncsu.common.sdk import BaseSDK

        assert BaseSDK is not None


class TestCoordinateVersioning:
    """Test version information imports."""

    def test_import_version_info(self):
        """Test that version information can be imported."""
        from anncsu.coordinate import VERSION

        assert VERSION is not None

    def test_import_version_from_module(self):
        """Test that version can be imported from _version module."""
        from anncsu.coordinate._version import __version__

        assert __version__ is not None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
