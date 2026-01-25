"""Tests for ResponseValidator."""

from pathlib import Path
from unittest.mock import Mock

import httpx
import pytest

from anncsu.common.validation import ResponseValidator, ValidationConfig


class TestValidationConfig:
    """Tests for ValidationConfig dataclass."""

    def test_default_config(self):
        """Test default configuration values."""
        config = ValidationConfig()
        assert config.enabled is False
        assert config.openapi_spec_path is None
        assert config.strict is True

    def test_custom_config(self):
        """Test custom configuration values."""
        spec_path = Path("/path/to/spec.yaml")
        config = ValidationConfig(
            enabled=True, openapi_spec_path=spec_path, strict=False
        )
        assert config.enabled is True
        assert config.openapi_spec_path == spec_path
        assert config.strict is False


class TestResponseValidator:
    """Tests for ResponseValidator class."""

    @pytest.fixture
    def spec_path(self):
        """Fixture providing path to test OpenAPI spec."""
        # Use the actual PA spec from the SDK (dev environment)
        # Path: tests/validation/test_response_validator.py -> project root -> oas/dev/
        return (
            Path(__file__).parent.parent.parent
            / "oas"
            / "dev"
            / "Specifica API - ANNCSU – Consultazione per le PA.yaml"
        )

    def test_validator_initialization(self, spec_path):
        """Test that validator initializes with valid spec."""
        validator = ResponseValidator(spec_path)
        assert validator.spec is not None
        assert validator.spec_path == spec_path

    def test_validator_missing_spec(self):
        """Test that validator raises error for missing spec file."""
        non_existent = Path("/does/not/exist.yaml")
        with pytest.raises(FileNotFoundError, match="OpenAPI spec not found"):
            ResponseValidator(non_existent)

    def test_validator_requires_dependencies(self, tmp_path, monkeypatch):
        """Test that helpful error is raised if dependencies missing."""
        # Create a minimal invalid spec file
        spec_file = tmp_path / "spec.yaml"
        spec_file.write_text("openapi: 3.0.0\n")

        # Mock ImportError for openapi_pydantic
        def mock_import(name, *args, **kwargs):
            if name == "openapi_pydantic" or name == "yaml":
                raise ImportError("No module named 'openapi_pydantic'")
            return __import__(name, *args, **kwargs)

        monkeypatch.setattr("builtins.__import__", mock_import)

        with pytest.raises(ImportError, match="requires openapi-pydantic"):
            ResponseValidator(spec_file)

    def test_find_operation(self, spec_path):
        """Test finding operation by operation ID."""
        validator = ResponseValidator(spec_path)

        # Test finding a known operation
        operation = validator._find_operation("esisteOdonimoGetQueryParam")
        assert operation is not None
        assert operation.operationId == "esisteOdonimoGetQueryParam"

        # Test operation not found
        not_found = validator._find_operation("nonExistentOperation")
        assert not_found is None

    def test_validate_response_success(self, spec_path):
        """Test validation of a successful response."""
        validator = ResponseValidator(spec_path)

        # Mock a successful response
        response = Mock(spec=httpx.Response)
        response.status_code = 200
        response.headers = {"content-type": "application/json"}
        response.content = b'{"res": "esisteodonimo", "data": true}'
        response.json.return_value = {"res": "esisteodonimo", "data": True}

        is_valid, errors = validator.validate_response(
            response, "esisteOdonimoGetQueryParam"
        )

        assert is_valid is True
        assert len(errors) == 0

    def test_validate_response_invalid_operation(self, spec_path):
        """Test validation with invalid operation ID."""
        validator = ResponseValidator(spec_path)

        response = Mock(spec=httpx.Response)
        response.status_code = 200

        is_valid, errors = validator.validate_response(response, "invalidOperationId")

        assert is_valid is False
        assert len(errors) == 1
        assert "not found" in errors[0]

    def test_validate_response_wrong_status_code(self, spec_path):
        """Test validation with unexpected status code."""
        validator = ResponseValidator(spec_path)

        response = Mock(spec=httpx.Response)
        response.status_code = 999  # Invalid status code
        response.headers = {"content-type": "application/json"}

        is_valid, errors = validator.validate_response(
            response, "esisteOdonimoGetQueryParam"
        )

        assert is_valid is False
        assert any(
            "No response schema defined for status code 999" in e for e in errors
        )

    def test_validate_response_wrong_content_type(self, spec_path):
        """Test validation with unexpected content type."""
        validator = ResponseValidator(spec_path)

        response = Mock(spec=httpx.Response)
        response.status_code = 200
        response.headers = {"content-type": "text/html"}
        response.content = b"<html></html>"

        is_valid, errors = validator.validate_response(
            response, "esisteOdonimoGetQueryParam"
        )

        assert is_valid is False
        assert any("Unexpected content type" in e for e in errors)

    def test_validate_response_invalid_json(self, spec_path):
        """Test validation with invalid JSON response."""
        validator = ResponseValidator(spec_path)

        response = Mock(spec=httpx.Response)
        response.status_code = 200
        response.headers = {"content-type": "application/json"}
        response.json.side_effect = ValueError("Invalid JSON")

        is_valid, errors = validator.validate_response(
            response, "esisteOdonimoGetQueryParam"
        )

        assert is_valid is False
        assert any("Failed to parse response JSON" in e for e in errors)


class TestResponseValidatorIntegration:
    """Integration tests for response validation in SDK context."""

    def test_validation_config_in_sdk_configuration(self):
        """Test that SDKConfiguration accepts validation parameters."""
        from anncsu.common.sdkconfiguration import SDKConfiguration

        # Create a mock logger that implements the Logger protocol
        class MockLogger:
            def debug(self, msg: str) -> None:
                pass

            def error(self, msg: str) -> None:
                pass

        config = SDKConfiguration(
            client=None,
            client_supplied=False,
            async_client=None,
            async_client_supplied=False,
            debug_logger=MockLogger(),
            validate_responses=True,
            openapi_spec_path=Path("/path/to/spec.yaml"),
        )

        assert config.validate_responses is True
        assert config.openapi_spec_path == Path("/path/to/spec.yaml")

    def test_validation_disabled_by_default(self):
        """Test that validation is disabled by default."""
        from anncsu.common.sdkconfiguration import SDKConfiguration

        # Create a mock logger
        class MockLogger:
            def debug(self, msg: str) -> None:
                pass

            def error(self, msg: str) -> None:
                pass

        config = SDKConfiguration(
            client=None,
            client_supplied=False,
            async_client=None,
            async_client_supplied=False,
            debug_logger=MockLogger(),
        )

        assert config.validate_responses is False
        assert config.openapi_spec_path is None
