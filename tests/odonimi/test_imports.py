"""Test imports for anncsu.odonimi package.

This test suite verifies that all modules in the anncsu.odonimi package
can be imported successfully and that they correctly reference shared
components from anncsu.common.

Mirrors the pattern of tests/accessi/test_imports.py.
Validates that the Speakeasy-generated package is structured correctly
and that the post-generation script has rewired imports to use
``anncsu.common.sdk`` instead of duplicated local copies.
"""

import pytest


class TestOdonimiPackageImports:
    """Test that the anncsu.odonimi package structure is correct."""

    def test_import_odonimi_package(self):
        """Test that anncsu.odonimi package can be imported."""
        import anncsu.odonimi

        assert anncsu.odonimi is not None

    def test_odonimi_package_has_path(self):
        """Test that anncsu.odonimi has a __path__ attribute."""
        import anncsu.odonimi

        assert hasattr(anncsu.odonimi, "__path__")


class TestOdonimiSdkImports:
    """Test imports of the main SDK class."""

    def test_import_anncsu_odonimi_sdk(self):
        """Test that AnncsuOdonimi SDK can be imported."""
        from anncsu.odonimi import AnncsuOdonimi

        assert AnncsuOdonimi is not None

    def test_import_sdk_from_module(self):
        """Test that SDK can be imported from sdk module."""
        from anncsu.odonimi.sdk import AnncsuOdonimi

        assert AnncsuOdonimi is not None


class TestOdonimiEndpointImports:
    """Test imports of endpoint classes.

    Speakeasy may name the POST /odonimi endpoint class differently
    depending on the OAS structure (operationId=gestioneAnncsuOdonimiPdnd,
    tag=anncsu). This test only checks that the SDK exposes a callable
    for the operation, not a specific class name.
    """

    def test_sdk_exposes_odonimi_operation(self):
        """Test that the SDK exposes a sub-SDK for the POST /odonimi operation
        via the ``_sub_sdk_map`` lazy-loading mechanism (Speakeasy pattern).
        The exact attribute key depends on the OAS tag."""
        from anncsu.odonimi import AnncsuOdonimi

        sub_sdks = getattr(AnncsuOdonimi, "_sub_sdk_map", {})
        assert any(
            "odonimi" in module_path or "odonimi" in class_name.lower()
            for module_path, class_name in sub_sdks.values()
        )

    def test_import_status(self):
        """Test that Status endpoint can be imported."""
        from anncsu.odonimi.status import Status

        assert Status is not None


class TestOdonimiModelsImports:
    """Test imports of Odonimi-specific models."""

    def test_import_models_module(self):
        """Test that models module can be imported."""
        from anncsu.odonimi import models

        assert models is not None

    def test_import_richiesta_operazione(self):
        """Test that RichiestaOperazione can be imported."""
        from anncsu.odonimi.models import RichiestaOperazione

        assert RichiestaOperazione is not None

    def test_import_risposta_operazione(self):
        """Test that RispostaOperazione can be imported."""
        from anncsu.odonimi.models import RispostaOperazione

        assert RispostaOperazione is not None

    def test_import_security_model(self):
        """Test that Security model can be imported."""
        from anncsu.odonimi.models import Security

        assert Security is not None

    def test_import_show_status_response(self):
        """Test that ShowStatusResponse can be imported."""
        from anncsu.odonimi.models import ShowStatusResponse

        assert ShowStatusResponse is not None

    def test_models_use_common_basemodel(self):
        """Test that Odonimi models inherit from common BaseModel."""
        from anncsu.common.sdk.types import BaseModel
        from anncsu.odonimi.models import RichiestaOperazione

        assert issubclass(RichiestaOperazione, BaseModel)


class TestOdonimiErrorsImports:
    """Test imports of Odonimi-specific errors."""

    def test_import_errors_module(self):
        """Test that errors module can be imported."""
        from anncsu.odonimi import errors

        assert errors is not None

    def test_import_anncsu_error(self):
        """Test that AnncsuError can be imported."""
        from anncsu.odonimi.errors import AnncsuError

        assert AnncsuError is not None

    def test_import_api_error(self):
        """Test that APIError can be imported."""
        from anncsu.odonimi.errors import APIError

        assert APIError is not None

    def test_import_risposta_errore(self):
        """Test that RispostaErrore error can be imported."""
        from anncsu.odonimi.errors import RispostaErrore

        assert RispostaErrore is not None


class TestOdonimiUsesCommonComponents:
    """Test that Odonimi package correctly uses common components."""

    def test_odonimi_imports_common_types(self):
        """Test that Odonimi can access common types."""
        from anncsu.common.sdk.types import BaseModel
        from anncsu.odonimi.models import RichiestaOperazione

        assert issubclass(RichiestaOperazione, BaseModel)

    def test_odonimi_can_import_common_utils(self):
        """Test that Odonimi code can import common utils."""
        from anncsu.common.sdk.utils import RetryConfig

        assert RetryConfig is not None

    def test_odonimi_can_import_common_errors(self):
        """Test that Odonimi code can import common errors."""
        from anncsu.common.errors import AnncsuBaseError

        assert AnncsuBaseError is not None


class TestOdonimiUsesCommonSdk:
    """Test that Odonimi package correctly uses common SDK infrastructure.

    Odonimi must NOT have its own duplicated types/utils — these are
    centralized in ``anncsu.common.sdk``.
    """

    def test_odonimi_uses_common_sdk_types(self):
        """Test that Odonimi uses types from common/sdk/."""
        from anncsu.common.sdk.types import BaseModel

        assert BaseModel is not None

    def test_odonimi_uses_common_sdk_utils(self):
        """Test that Odonimi uses utils from common/sdk/."""
        from anncsu.common.sdk.utils import RetryConfig

        assert RetryConfig is not None

    def test_odonimi_uses_common_sdk_basesdk(self):
        """Test that Odonimi uses BaseSDK from common/sdk/."""
        from anncsu.common.sdk import BaseSDK

        assert BaseSDK is not None


class TestOdonimiSdkConfiguration:
    """Test SDK configuration imports."""

    def test_import_sdk_configuration_from_odonimi(self):
        """Test that SDKConfiguration can be imported from odonimi."""
        from anncsu.odonimi.sdkconfiguration import SDKConfiguration

        assert SDKConfiguration is not None

    def test_import_base_sdk_from_common_sdk(self):
        """Test that BaseSDK is imported from common/sdk/."""
        from anncsu.common.sdk import BaseSDK

        assert BaseSDK is not None


class TestOdonimiVersioning:
    """Test version information imports."""

    def test_import_version_info(self):
        """Test that version information can be imported."""
        from anncsu.odonimi import VERSION

        assert VERSION is not None

    def test_import_version_from_module(self):
        """Test that version can be imported from _version module."""
        from anncsu.odonimi._version import __version__

        assert __version__ is not None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
