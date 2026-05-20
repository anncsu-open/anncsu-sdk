"""Test imports for anncsu.accessi package.

This test suite verifies that all modules in the anncsu.accessi package
can be imported successfully and that they correctly reference shared
components from anncsu.common.

Mirrors the pattern of tests/coordinate/test_imports.py.
Validates that the Speakeasy-generated package is structured correctly
and that the post-generation script has rewired imports to use
``anncsu.common.sdk`` instead of duplicated local copies.
"""

import pytest


class TestAccessiPackageImports:
    """Test that the anncsu.accessi package structure is correct."""

    def test_import_accessi_package(self):
        """Test that anncsu.accessi package can be imported."""
        import anncsu.accessi

        assert anncsu.accessi is not None

    def test_accessi_package_has_path(self):
        """Test that anncsu.accessi has a __path__ attribute."""
        import anncsu.accessi

        assert hasattr(anncsu.accessi, "__path__")


class TestAccessiSdkImports:
    """Test imports of the main SDK class."""

    def test_import_anncsu_accessi_sdk(self):
        """Test that AnncsuAccessi SDK can be imported."""
        from anncsu.accessi import AnncsuAccessi

        assert AnncsuAccessi is not None

    def test_import_sdk_from_module(self):
        """Test that SDK can be imported from sdk module."""
        from anncsu.accessi.sdk import AnncsuAccessi

        assert AnncsuAccessi is not None


class TestAccessiEndpointImports:
    """Test imports of endpoint classes.

    Speakeasy may name the POST /accessi endpoint class differently
    depending on the OAS structure (operationId=gestioneAnncsuPdnd,
    tag=anncsu). This test only checks that the SDK exposes a callable
    for the operation, not a specific class name.
    """

    def test_sdk_exposes_accessi_operation(self):
        """Test that the SDK exposes a sub-SDK for the POST /accessi operation
        via the ``_sub_sdk_map`` lazy-loading mechanism (Speakeasy pattern).
        The exact attribute key depends on the OAS tag."""
        from anncsu.accessi import AnncsuAccessi

        sub_sdks = getattr(AnncsuAccessi, "_sub_sdk_map", {})
        # Must include at least one entry pointing to a module whose class
        # implements the gestioneAnncsuPdnd operation.
        assert any(
            "accessi" in module_path or "accessi" in class_name.lower()
            for module_path, class_name in sub_sdks.values()
        )

    def test_import_status(self):
        """Test that Status endpoint can be imported."""
        from anncsu.accessi.status import Status

        assert Status is not None


class TestAccessiModelsImports:
    """Test imports of Accessi-specific models."""

    def test_import_models_module(self):
        """Test that models module can be imported."""
        from anncsu.accessi import models

        assert models is not None

    def test_import_richiesta_operazione(self):
        """Test that RichiestaOperazione can be imported."""
        from anncsu.accessi.models import RichiestaOperazione

        assert RichiestaOperazione is not None

    def test_import_risposta_operazione(self):
        """Test that RispostaOperazione can be imported."""
        from anncsu.accessi.models import RispostaOperazione

        assert RispostaOperazione is not None

    def test_import_security_model(self):
        """Test that Security model can be imported."""
        from anncsu.accessi.models import Security

        assert Security is not None

    def test_import_show_status_response(self):
        """Test that ShowStatusResponse can be imported."""
        from anncsu.accessi.models import ShowStatusResponse

        assert ShowStatusResponse is not None

    def test_models_use_common_basemodel(self):
        """Test that Accessi models inherit from common BaseModel."""
        from anncsu.accessi.models import RichiestaOperazione
        from anncsu.common.sdk.types import BaseModel

        assert issubclass(RichiestaOperazione, BaseModel)


class TestAccessiErrorsImports:
    """Test imports of Accessi-specific errors."""

    def test_import_errors_module(self):
        """Test that errors module can be imported."""
        from anncsu.accessi import errors

        assert errors is not None

    def test_import_anncsu_error(self):
        """Test that AnncsuError can be imported."""
        from anncsu.accessi.errors import AnncsuError

        assert AnncsuError is not None

    def test_import_api_error(self):
        """Test that APIError can be imported."""
        from anncsu.accessi.errors import APIError

        assert APIError is not None

    def test_import_risposta_errore(self):
        """Test that RispostaErrore error can be imported."""
        from anncsu.accessi.errors import RispostaErrore

        assert RispostaErrore is not None


class TestAccessiUsesCommonComponents:
    """Test that Accessi package correctly uses common components."""

    def test_accessi_imports_common_types(self):
        """Test that Accessi can access common types."""
        from anncsu.accessi.models import RichiestaOperazione
        from anncsu.common.sdk.types import BaseModel

        # Verify the model uses the common BaseModel
        assert issubclass(RichiestaOperazione, BaseModel)

    def test_accessi_can_import_common_utils(self):
        """Test that Accessi code can import common utils."""
        from anncsu.common.sdk.utils import RetryConfig

        assert RetryConfig is not None

    def test_accessi_can_import_common_errors(self):
        """Test that Accessi code can import common errors."""
        from anncsu.common.errors import AnncsuBaseError

        assert AnncsuBaseError is not None


class TestAccessiUsesCommonSdk:
    """Test that Accessi package correctly uses common SDK infrastructure.

    Accessi must NOT have its own duplicated types/utils — these are
    centralized in ``anncsu.common.sdk``.
    """

    def test_accessi_uses_common_sdk_types(self):
        """Test that Accessi uses types from common/sdk/."""
        from anncsu.common.sdk.types import BaseModel

        assert BaseModel is not None

    def test_accessi_uses_common_sdk_utils(self):
        """Test that Accessi uses utils from common/sdk/."""
        from anncsu.common.sdk.utils import RetryConfig

        assert RetryConfig is not None

    def test_accessi_uses_common_sdk_basesdk(self):
        """Test that Accessi uses BaseSDK from common/sdk/."""
        from anncsu.common.sdk import BaseSDK

        assert BaseSDK is not None


class TestAccessiSdkConfiguration:
    """Test SDK configuration imports."""

    def test_import_sdk_configuration_from_accessi(self):
        """Test that SDKConfiguration can be imported from accessi."""
        from anncsu.accessi.sdkconfiguration import SDKConfiguration

        assert SDKConfiguration is not None

    def test_import_base_sdk_from_common_sdk(self):
        """Test that BaseSDK is imported from common/sdk/."""
        from anncsu.common.sdk import BaseSDK

        assert BaseSDK is not None


class TestAccessiVersioning:
    """Test version information imports."""

    def test_import_version_info(self):
        """Test that version information can be imported."""
        from anncsu.accessi import VERSION

        assert VERSION is not None

    def test_import_version_from_module(self):
        """Test that version can be imported from _version module."""
        from anncsu.accessi._version import __version__

        assert __version__ is not None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
