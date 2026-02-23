# SPDX-FileCopyrightText: 2025-present Geobeyond <info@geobeyond.it>
# SPDX-License-Identifier: MIT
"""Tests for Coordinate model validation.

Validation rules:
1. X and Y must be provided together (both or neither)
2. When X and Y are present, metodo is REQUIRED and must be 1-4
3. When X and Y are absent, metodo must NOT be provided
4. Z can only be provided when X and Y are present
5. X range for Italy: 6.0 <= x <= 18.0
6. Y range for Italy: 36.0 <= y <= 47.0
"""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from anncsu.coordinate.errors.coordinate_validation import (
    CoordinateDependencyError,
    CoordinateMaxLengthError,
    CoordinateRangeError,
    CoordinateValidationError,
    MetodoNotAllowedError,
    MetodoOutOfRangeError,
    MetodoRequiredError,
    QuotaNotAllowedError,
)
from anncsu.coordinate.models.validated import ValidatedCoordinate


def get_validation_error_cause(exc_info) -> Exception:
    """Extract the original error from Pydantic's ValidationError."""
    errors = exc_info.value.errors()
    if errors and "ctx" in errors[0] and "error" in errors[0]["ctx"]:
        return errors[0]["ctx"]["error"]
    return exc_info.value


class TestCoordinateMetodoValidation:
    """Tests for metodo field validation based on X/Y presence."""

    # --- When X and Y are ABSENT, metodo should NOT be provided ---

    def test_no_coordinates_no_metodo_valid(self) -> None:
        """Test that empty coordinate (no X, Y, metodo) is valid."""
        coord = ValidatedCoordinate()
        assert coord is not None

    def test_no_coordinates_with_metodo_invalid(self) -> None:
        """Test that metodo without X and Y raises MetodoNotAllowedError."""
        with pytest.raises(ValidationError) as exc_info:
            ValidatedCoordinate.model_validate({"metodo": "1"})
        cause = get_validation_error_cause(exc_info)
        assert isinstance(cause, MetodoNotAllowedError)
        assert "1" in str(cause)

    # --- When X and Y are PRESENT, metodo is REQUIRED (1-4) ---

    def test_coordinates_without_metodo_invalid(self) -> None:
        """Test that X and Y without metodo raises MetodoRequiredError."""
        with pytest.raises(ValidationError) as exc_info:
            ValidatedCoordinate.model_validate({"x": "12.4963655", "y": "41.9027835"})
        cause = get_validation_error_cause(exc_info)
        assert isinstance(cause, MetodoRequiredError)

    def test_coordinates_with_metodo_1_valid(self) -> None:
        """Test that metodo=1 is valid with coordinates."""
        coord = ValidatedCoordinate.model_validate(
            {
                "x": "12.4963655",
                "y": "41.9027835",
                "metodo": "1",
            }
        )
        assert coord.metodo == "1"

    def test_coordinates_with_metodo_2_valid(self) -> None:
        """Test that metodo=2 is valid with coordinates."""
        coord = ValidatedCoordinate.model_validate(
            {
                "x": "12.4963655",
                "y": "41.9027835",
                "metodo": "2",
            }
        )
        assert coord.metodo == "2"

    def test_coordinates_with_metodo_3_valid(self) -> None:
        """Test that metodo=3 is valid with coordinates."""
        coord = ValidatedCoordinate.model_validate(
            {
                "x": "12.4963655",
                "y": "41.9027835",
                "metodo": "3",
            }
        )
        assert coord.metodo == "3"

    def test_coordinates_with_metodo_4_valid(self) -> None:
        """Test that metodo=4 is valid with coordinates."""
        coord = ValidatedCoordinate.model_validate(
            {
                "x": "12.4963655",
                "y": "41.9027835",
                "metodo": "4",
            }
        )
        assert coord.metodo == "4"

    # --- metodo out of range (not 1-4) ---

    def test_coordinates_with_metodo_0_invalid(self) -> None:
        """Test that metodo=0 raises MetodoOutOfRangeError."""
        with pytest.raises(ValidationError) as exc_info:
            ValidatedCoordinate.model_validate(
                {
                    "x": "12.4963655",
                    "y": "41.9027835",
                    "metodo": "0",
                }
            )
        cause = get_validation_error_cause(exc_info)
        assert isinstance(cause, MetodoOutOfRangeError)
        assert "0" in str(cause)

    def test_coordinates_with_metodo_5_invalid(self) -> None:
        """Test that metodo=5 raises MetodoOutOfRangeError."""
        with pytest.raises(ValidationError) as exc_info:
            ValidatedCoordinate.model_validate(
                {
                    "x": "12.4963655",
                    "y": "41.9027835",
                    "metodo": "5",
                }
            )
        cause = get_validation_error_cause(exc_info)
        assert isinstance(cause, MetodoOutOfRangeError)
        assert "5" in str(cause)

    def test_coordinates_with_metodo_negative_invalid(self) -> None:
        """Test that negative metodo raises MetodoOutOfRangeError."""
        with pytest.raises(ValidationError) as exc_info:
            ValidatedCoordinate.model_validate(
                {
                    "x": "12.4963655",
                    "y": "41.9027835",
                    "metodo": "-1",
                }
            )
        cause = get_validation_error_cause(exc_info)
        assert isinstance(cause, MetodoOutOfRangeError)
        assert "-1" in str(cause)


class TestCoordinateXYDependency:
    """Tests for X and Y mutual dependency."""

    def test_only_x_without_y_invalid(self) -> None:
        """Test that providing only X raises CoordinateDependencyError."""
        with pytest.raises(ValidationError) as exc_info:
            ValidatedCoordinate.model_validate({"x": "12.4963655"})
        cause = get_validation_error_cause(exc_info)
        assert isinstance(cause, CoordinateDependencyError)
        assert "Y" in str(cause)

    def test_only_y_without_x_invalid(self) -> None:
        """Test that providing only Y raises CoordinateDependencyError."""
        with pytest.raises(ValidationError) as exc_info:
            ValidatedCoordinate.model_validate({"y": "41.9027835"})
        cause = get_validation_error_cause(exc_info)
        assert isinstance(cause, CoordinateDependencyError)
        assert "X" in str(cause)


class TestCoordinateRangeValidation:
    """Tests for X and Y coordinate range validation (Italy bounds)."""

    # --- X range: 6.0 <= x <= 18.0 ---

    def test_x_at_minimum_valid(self) -> None:
        """Test that X=6.0 (minimum for Italy) is valid."""
        coord = ValidatedCoordinate.model_validate(
            {
                "x": "6.0",
                "y": "41.0",
                "metodo": "1",
            }
        )
        assert coord.x == "6.0"

    def test_x_at_maximum_valid(self) -> None:
        """Test that X=18.0 (maximum for Italy) is valid."""
        coord = ValidatedCoordinate.model_validate(
            {
                "x": "18.0",
                "y": "41.0",
                "metodo": "1",
            }
        )
        assert coord.x == "18.0"

    def test_x_below_minimum_invalid(self) -> None:
        """Test that X<6.0 raises CoordinateRangeError."""
        with pytest.raises(ValidationError) as exc_info:
            ValidatedCoordinate.model_validate(
                {
                    "x": "5.9",
                    "y": "41.0",
                    "metodo": "1",
                }
            )
        cause = get_validation_error_cause(exc_info)
        assert isinstance(cause, CoordinateRangeError)
        assert "X" in str(cause)
        assert "5.9" in str(cause)

    def test_x_above_maximum_invalid(self) -> None:
        """Test that X>18.0 raises CoordinateRangeError."""
        with pytest.raises(ValidationError) as exc_info:
            ValidatedCoordinate.model_validate(
                {
                    "x": "18.1",
                    "y": "41.0",
                    "metodo": "1",
                }
            )
        cause = get_validation_error_cause(exc_info)
        assert isinstance(cause, CoordinateRangeError)
        assert "X" in str(cause)
        assert "18.1" in str(cause)

    # --- Y range: 36.0 <= y <= 47.0 ---

    def test_y_at_minimum_valid(self) -> None:
        """Test that Y=36.0 (minimum for Italy) is valid."""
        coord = ValidatedCoordinate.model_validate(
            {
                "x": "12.0",
                "y": "36.0",
                "metodo": "1",
            }
        )
        assert coord.y == "36.0"

    def test_y_at_maximum_valid(self) -> None:
        """Test that Y=47.0 (maximum for Italy) is valid."""
        coord = ValidatedCoordinate.model_validate(
            {
                "x": "12.0",
                "y": "47.0",
                "metodo": "1",
            }
        )
        assert coord.y == "47.0"

    def test_y_below_minimum_invalid(self) -> None:
        """Test that Y<36.0 raises CoordinateRangeError."""
        with pytest.raises(ValidationError) as exc_info:
            ValidatedCoordinate.model_validate(
                {
                    "x": "12.0",
                    "y": "35.9",
                    "metodo": "1",
                }
            )
        cause = get_validation_error_cause(exc_info)
        assert isinstance(cause, CoordinateRangeError)
        assert "Y" in str(cause)
        assert "35.9" in str(cause)

    def test_y_above_maximum_invalid(self) -> None:
        """Test that Y>47.0 raises CoordinateRangeError."""
        with pytest.raises(ValidationError) as exc_info:
            ValidatedCoordinate.model_validate(
                {
                    "x": "12.0",
                    "y": "47.1",
                    "metodo": "1",
                }
            )
        cause = get_validation_error_cause(exc_info)
        assert isinstance(cause, CoordinateRangeError)
        assert "Y" in str(cause)
        assert "47.1" in str(cause)


class TestCoordinateZValidation:
    """Tests for Z (quota) validation."""

    def test_z_without_x_y_invalid(self) -> None:
        """Test that Z without X and Y raises QuotaNotAllowedError."""
        with pytest.raises(ValidationError) as exc_info:
            ValidatedCoordinate.model_validate({"z": "100"})
        cause = get_validation_error_cause(exc_info)
        assert isinstance(cause, QuotaNotAllowedError)
        assert "100" in str(cause)

    def test_z_with_x_y_valid(self) -> None:
        """Test that Z can be set when X and Y are provided."""
        coord = ValidatedCoordinate.model_validate(
            {
                "x": "12.0",
                "y": "41.0",
                "z": "100",
                "metodo": "1",
            }
        )
        assert coord.z == "100"

    def test_z_optional_when_x_y_provided(self) -> None:
        """Test that Z is optional when X and Y are provided."""
        coord = ValidatedCoordinate.model_validate(
            {
                "x": "12.0",
                "y": "41.0",
                "metodo": "1",
            }
        )
        # Z should not be set
        serialized = coord.model_dump(exclude_unset=True)
        assert "z" not in serialized or serialized.get("z") is None


class TestCoordinateMaxLengthValidation:
    """Tests for coordinate field maxLength validation (API constraint)."""

    def test_x_exceeds_max_length_invalid(self) -> None:
        """X with more than 12 characters should raise CoordinateMaxLengthError."""
        with pytest.raises(ValidationError) as exc_info:
            ValidatedCoordinate.model_validate(
                {
                    "x": "12.3476928612",  # 14 chars
                    "y": "41.7942647",
                    "metodo": "3",
                }
            )
        cause = get_validation_error_cause(exc_info)
        assert isinstance(cause, CoordinateMaxLengthError)
        assert "x" in str(cause)
        assert "12" in str(cause)  # max_length

    def test_y_exceeds_max_length_invalid(self) -> None:
        """Y with more than 12 characters should raise CoordinateMaxLengthError."""
        with pytest.raises(ValidationError) as exc_info:
            ValidatedCoordinate.model_validate(
                {
                    "x": "12.4922309",
                    "y": "41.7942647923",  # 13 chars
                    "metodo": "3",
                }
            )
        cause = get_validation_error_cause(exc_info)
        assert isinstance(cause, CoordinateMaxLengthError)
        assert "y" in str(cause)
        assert "12" in str(cause)  # max_length

    def test_z_exceeds_max_length_invalid(self) -> None:
        """Z with more than 7 characters should raise CoordinateMaxLengthError."""
        with pytest.raises(ValidationError) as exc_info:
            ValidatedCoordinate.model_validate(
                {
                    "x": "12.4922309",
                    "y": "41.8902102",
                    "z": "12345678",  # 8 chars
                    "metodo": "3",
                }
            )
        cause = get_validation_error_cause(exc_info)
        assert isinstance(cause, CoordinateMaxLengthError)
        assert "z" in str(cause)
        assert "7" in str(cause)  # max_length

    def test_x_exactly_12_chars_valid(self) -> None:
        """X with exactly 12 characters should be valid."""
        coord = ValidatedCoordinate.model_validate(
            {
                "x": "12.49223090",  # 12 chars
                "y": "41.8902102",
                "metodo": "3",
            }
        )
        assert coord.x == "12.49223090"

    def test_y_exactly_12_chars_valid(self) -> None:
        """Y with exactly 12 characters should be valid."""
        coord = ValidatedCoordinate.model_validate(
            {
                "x": "12.4922309",
                "y": "41.89021020",  # 12 chars
                "metodo": "3",
            }
        )
        assert coord.y == "41.89021020"

    def test_z_exactly_7_chars_valid(self) -> None:
        """Z with exactly 7 characters should be valid."""
        coord = ValidatedCoordinate.model_validate(
            {
                "x": "12.4922309",
                "y": "41.8902102",
                "z": "1234567",  # 7 chars
                "metodo": "3",
            }
        )
        assert coord.z == "1234567"


class TestCoordinateValidationErrorHierarchy:
    """Tests for error hierarchy and catchability."""

    def test_all_errors_inherit_from_base(self) -> None:
        """Test that all validation errors can be caught with base class."""
        errors_to_test = [
            ({"metodo": "1"}, MetodoNotAllowedError),
            ({"x": "12.0", "y": "41.0"}, MetodoRequiredError),
            ({"x": "12.0", "y": "41.0", "metodo": "5"}, MetodoOutOfRangeError),
            ({"x": "12.0"}, CoordinateDependencyError),
            ({"x": "5.0", "y": "41.0", "metodo": "1"}, CoordinateRangeError),
            ({"z": "100"}, QuotaNotAllowedError),
            (
                {"x": "12.3476928612", "y": "41.0", "metodo": "1"},
                CoordinateMaxLengthError,
            ),
        ]

        for data, expected_error in errors_to_test:
            with pytest.raises(ValidationError) as exc_info:
                ValidatedCoordinate.model_validate(data)
            cause = get_validation_error_cause(exc_info)
            assert isinstance(cause, CoordinateValidationError)
            assert isinstance(cause, expected_error)

    def test_errors_are_value_errors(self) -> None:
        """Test that all validation errors are also ValueErrors."""
        with pytest.raises(ValidationError) as exc_info:
            ValidatedCoordinate.model_validate({"x": "12.0", "y": "41.0"})
        cause = get_validation_error_cause(exc_info)
        assert isinstance(cause, ValueError)


class TestCoordinateIntegration:
    """Integration tests for Coordinate validation."""

    def test_full_valid_coordinate_roma(self) -> None:
        """Test a fully valid coordinate for Roma."""
        coord = ValidatedCoordinate.model_validate(
            {
                "x": "12.4963655",
                "y": "41.9027835",
                "z": "21",
                "metodo": "4",
            }
        )
        assert coord.x == "12.4963655"
        assert coord.y == "41.9027835"
        assert coord.z == "21"
        assert coord.metodo == "4"

    def test_full_valid_coordinate_milano(self) -> None:
        """Test a fully valid coordinate for Milano."""
        coord = ValidatedCoordinate.model_validate(
            {
                "x": "9.1859243",
                "y": "45.4654219",
                "metodo": "2",
            }
        )
        assert coord.x == "9.1859243"
        assert coord.y == "45.4654219"
        assert coord.metodo == "2"

    def test_serialization_preserves_values(self) -> None:
        """Test that serialization preserves validated values."""
        coord = ValidatedCoordinate.model_validate(
            {
                "x": "12.4963655",
                "y": "41.9027835",
                "metodo": "4",
            }
        )
        serialized = coord.model_dump()
        assert serialized["x"] == "12.4963655"
        assert serialized["y"] == "41.9027835"
        assert serialized["metodo"] == "4"

    def test_empty_coordinate_serialization(self) -> None:
        """Test that empty coordinate serializes correctly."""
        coord = ValidatedCoordinate()
        serialized = coord.model_dump(exclude_unset=True)
        # Should be empty or have no coordinate fields
        assert "x" not in serialized or serialized.get("x") is None
        assert "y" not in serialized or serialized.get("y") is None
        assert "metodo" not in serialized or serialized.get("metodo") is None
