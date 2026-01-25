"""Tests for custom validators."""

import pytest
from pydantic import ValidationError

from anncsu.common.validation import base64_validator, belfiore_code_validator


class TestBase64Validator:
    """Tests for base64_validator function."""

    def test_valid_base64(self):
        """Test that valid base64 strings pass validation."""
        valid_strings = [
            "VklBIFJPTUE=",  # "VIA ROMA"
            "SGVsbG8gV29ybGQ=",  # "Hello World"
            "dGVzdA==",  # "test"
            "",  # Empty string is valid base64
        ]

        for s in valid_strings:
            result = base64_validator(s)
            assert result == s

    def test_invalid_base64(self):
        """Test that invalid base64 strings raise ValueError."""
        invalid_strings = [
            "Not valid base64!",
            "!!!",
            "VklBIFJPTUE",  # Missing padding
        ]

        for s in invalid_strings:
            with pytest.raises(ValueError, match="Invalid base64"):
                base64_validator(s)

    def test_non_string_input(self):
        """Test that non-string inputs raise ValueError."""
        with pytest.raises(ValueError, match="must be a string"):
            base64_validator(123)

        with pytest.raises(ValueError, match="must be a string"):
            base64_validator(None)


class TestBelfioreCodeValidator:
    """Tests for belfiore_code_validator function."""

    def test_valid_belfiore_codes(self):
        """Test that valid Belfiore codes pass validation."""
        valid_codes = [
            "H501",  # Rome
            "F205",  # Milan
            "A794",  # Bologna
            "Z999",  # Valid format
        ]

        for code in valid_codes:
            result = belfiore_code_validator(code)
            assert result == code

    def test_invalid_belfiore_codes(self):
        """Test that invalid Belfiore codes raise ValueError."""
        invalid_codes = [
            "h501",  # Lowercase letter
            "H50",  # Too short
            "H5011",  # Too long
            "1501",  # Starts with digit
            "HH01",  # Two letters
            "H5O1",  # Letter instead of digit
            "",  # Empty
            "H 501",  # Space
        ]

        for code in invalid_codes:
            with pytest.raises(ValueError, match="Invalid Belfiore code"):
                belfiore_code_validator(code)

    def test_non_string_input(self):
        """Test that non-string inputs raise ValueError."""
        with pytest.raises(ValueError, match="must be a string"):
            belfiore_code_validator(123)

        with pytest.raises(ValueError, match="must be a string"):
            belfiore_code_validator(None)


class TestValidatorsIntegration:
    """Integration tests for validators with Pydantic models."""

    def test_validators_in_pydantic_model(self):
        """Test that validators work correctly when used in Pydantic models."""
        from anncsu.common.validation.examples import (
            EsisteOdonimoGetQueryParamRequestValidated,
        )

        # Valid data
        valid_request = EsisteOdonimoGetQueryParamRequestValidated(
            codcom="H501", denom="VklBIFJPTUE="
        )
        assert valid_request.codcom == "H501"
        assert valid_request.denom == "VklBIFJPTUE="

    def test_invalid_belfiore_in_model(self):
        """Test that invalid Belfiore code raises ValidationError in model."""
        from anncsu.common.validation.examples import (
            EsisteOdonimoGetQueryParamRequestValidated,
        )

        with pytest.raises(ValidationError) as exc_info:
            EsisteOdonimoGetQueryParamRequestValidated(
                codcom="INVALID", denom="VklBIFJPTUE="
            )

        errors = exc_info.value.errors()
        assert len(errors) >= 1
        assert errors[0]["loc"] == ("codcom",)
        # Either Field constraint (max_length) or custom validator will catch this
        error_msg = str(errors[0]["msg"])
        assert (
            "at most 4 characters" in error_msg or "Invalid Belfiore code" in error_msg
        )

    def test_invalid_base64_in_model(self):
        """Test that invalid base64 raises ValidationError in model."""
        from anncsu.common.validation.examples import (
            EsisteOdonimoGetQueryParamRequestValidated,
        )

        with pytest.raises(ValidationError) as exc_info:
            EsisteOdonimoGetQueryParamRequestValidated(
                codcom="H501", denom="Not valid base64!"
            )

        errors = exc_info.value.errors()
        assert len(errors) == 1
        assert errors[0]["loc"] == ("denom",)
        assert "Invalid base64" in str(errors[0]["msg"])

    def test_field_constraints(self):
        """Test that Pydantic Field constraints are enforced."""
        from anncsu.common.validation.examples import (
            EsisteOdonimoGetQueryParamRequestValidated,
        )

        # Test min_length constraint on denom
        with pytest.raises(ValidationError) as exc_info:
            EsisteOdonimoGetQueryParamRequestValidated(codcom="H501", denom="")

        errors = exc_info.value.errors()
        assert any("at least 1 character" in str(e["msg"]) for e in errors)

        # Test pattern constraint on codcom
        with pytest.raises(ValidationError) as exc_info:
            EsisteOdonimoGetQueryParamRequestValidated(
                codcom="abc", denom="VklBIFJPTUE="
            )

        errors = exc_info.value.errors()
        assert len(errors) > 0
