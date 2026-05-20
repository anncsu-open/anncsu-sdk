# SPDX-FileCopyrightText: 2025-present Geobeyond <info@geobeyond.it>
# SPDX-License-Identifier: MIT
"""Tests for Accesso model validation.

Business rules from OAS spec (operazione_civico ∈ {I, R, S}):

1. operazione_civico must be one of "I", "R", "S"
2. progr_civico is required for R and S, optional for I
3. numero and metrico are mutually exclusive (XOR), required for I/R
4. For S, the following fields are NOT allowed:
   - numero, esponente, specificita, metrico, sezione_censimento,
     isolato, coordinate
5. esponente, specificita, sezione_censimento, isolato are allowed
   only for I and R (not S)
6. maxLength constraints from OAS:
   - progr_civico: 15
   - codice_civico_comunale: 30
   - numero: 5
   - esponente: 15
   - specificita: 5
   - metrico: 6
   - sezione_censimento: 13
   - operazione_civico: 1
   - isolato: 4
7. Coordinate field is validated via ValidatedCoordinate (Italy bounds,
   X/Y dependency, metodo 1-4, maxLength X/Y/Z)
"""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from anncsu.accessi.errors.accesso_validation import (
    AccessoMaxLengthError,
    AccessoValidationError,
    FieldNotAllowedForDeleteError,
    FieldNotAllowedForOperationError,
    NumeroMetricoMutexError,
    OperazioneCivicoError,
    ProgrCivicoRequiredError,
)
from anncsu.accessi.models.validated import ValidatedAccesso
from anncsu.coordinate.errors.coordinate_validation import (
    CoordinateRangeError,
)


def get_validation_error_cause(exc_info) -> Exception:
    """Extract the original error from Pydantic's ValidationError."""
    errors = exc_info.value.errors()
    if errors and "ctx" in errors[0] and "error" in errors[0]["ctx"]:
        return errors[0]["ctx"]["error"]
    return exc_info.value


# ---------------------------------------------------------------------------
# 1. operazione_civico validation
# ---------------------------------------------------------------------------


class TestAccessoOperazioneCivicoValidation:
    """Tests for operazione_civico field validation."""

    def test_operazione_civico_I_valid(self) -> None:
        """Test that operazione_civico='I' (insert) is accepted."""
        accesso = ValidatedAccesso(operazione_civico="I", numero="12")
        assert accesso.operazione_civico == "I"

    def test_operazione_civico_R_valid(self) -> None:
        """Test that operazione_civico='R' (replace) is accepted."""
        accesso = ValidatedAccesso(
            operazione_civico="R", progr_civico="1370588", numero="12"
        )
        assert accesso.operazione_civico == "R"

    def test_operazione_civico_S_valid(self) -> None:
        """Test that operazione_civico='S' (delete) is accepted."""
        accesso = ValidatedAccesso(operazione_civico="S", progr_civico="1370588")
        assert accesso.operazione_civico == "S"

    def test_operazione_civico_invalid_value_raises(self) -> None:
        """Test that operazione_civico='X' raises OperazioneCivicoError."""
        with pytest.raises(ValidationError) as exc_info:
            ValidatedAccesso(operazione_civico="X")
        cause = get_validation_error_cause(exc_info)
        assert isinstance(cause, OperazioneCivicoError)
        assert "X" in str(cause)

    def test_operazione_civico_lowercase_invalid(self) -> None:
        """Test that lowercase operazione_civico='i' is invalid."""
        with pytest.raises(ValidationError) as exc_info:
            ValidatedAccesso(operazione_civico="i", numero="12")
        cause = get_validation_error_cause(exc_info)
        assert isinstance(cause, OperazioneCivicoError)

    def test_operazione_civico_missing_invalid(self) -> None:
        """Test that absent operazione_civico raises validation error.

        operazione_civico is required by OAS spec.
        """
        with pytest.raises(ValidationError) as exc_info:
            ValidatedAccesso(numero="12")
        cause = get_validation_error_cause(exc_info)
        assert isinstance(cause, OperazioneCivicoError)


# ---------------------------------------------------------------------------
# 2. progr_civico dependency on operazione_civico
# ---------------------------------------------------------------------------


class TestAccessoProgrCivicoDependency:
    """Tests for progr_civico requirement based on operazione_civico."""

    def test_insert_without_progr_civico_valid(self) -> None:
        """Test that I (insert) does not require progr_civico (assigned by API)."""
        accesso = ValidatedAccesso(operazione_civico="I", numero="12")
        assert accesso.progr_civico is None

    def test_replace_requires_progr_civico(self) -> None:
        """Test that R (replace) requires progr_civico."""
        with pytest.raises(ValidationError) as exc_info:
            ValidatedAccesso(operazione_civico="R", numero="12")
        cause = get_validation_error_cause(exc_info)
        assert isinstance(cause, ProgrCivicoRequiredError)
        assert "R" in str(cause)

    def test_delete_requires_progr_civico(self) -> None:
        """Test that S (delete) requires progr_civico."""
        with pytest.raises(ValidationError) as exc_info:
            ValidatedAccesso(operazione_civico="S")
        cause = get_validation_error_cause(exc_info)
        assert isinstance(cause, ProgrCivicoRequiredError)
        assert "S" in str(cause)

    def test_replace_with_progr_civico_valid(self) -> None:
        """Test that R with progr_civico is valid."""
        accesso = ValidatedAccesso(
            operazione_civico="R", progr_civico="1370588", numero="12"
        )
        assert accesso.progr_civico == "1370588"


# ---------------------------------------------------------------------------
# 3. numero / metrico mutual exclusion
# ---------------------------------------------------------------------------


class TestAccessoNumeroMetricoMutex:
    """Tests for numero/metrico mutual exclusion rule.

    For I/R operations, exactly one of numero or metrico must be provided
    (an accesso is either civico-numbered or metrico-identified).
    For S, neither should be valued.
    """

    def test_insert_with_numero_only_valid(self) -> None:
        """Test that I with only numero is valid (civico)."""
        accesso = ValidatedAccesso(operazione_civico="I", numero="12")
        assert accesso.numero == "12"

    def test_insert_with_metrico_only_valid(self) -> None:
        """Test that I with only metrico is valid (metric-identified)."""
        accesso = ValidatedAccesso(operazione_civico="I", metrico="300")
        assert accesso.metrico == "300"

    def test_insert_with_both_numero_and_metrico_invalid(self) -> None:
        """Test that I with BOTH numero and metrico raises NumeroMetricoMutexError."""
        with pytest.raises(ValidationError) as exc_info:
            ValidatedAccesso(operazione_civico="I", numero="12", metrico="300")
        cause = get_validation_error_cause(exc_info)
        assert isinstance(cause, NumeroMetricoMutexError)

    def test_insert_with_neither_numero_nor_metrico_invalid(self) -> None:
        """Test that I with NEITHER numero nor metrico raises NumeroMetricoMutexError."""
        with pytest.raises(ValidationError) as exc_info:
            ValidatedAccesso(operazione_civico="I")
        cause = get_validation_error_cause(exc_info)
        assert isinstance(cause, NumeroMetricoMutexError)

    def test_replace_with_numero_only_valid(self) -> None:
        """Test that R with only numero is valid."""
        accesso = ValidatedAccesso(
            operazione_civico="R", progr_civico="1370588", numero="12"
        )
        assert accesso.numero == "12"

    def test_replace_with_metrico_only_valid(self) -> None:
        """Test that R with only metrico is valid."""
        accesso = ValidatedAccesso(
            operazione_civico="R", progr_civico="1370588", metrico="300"
        )
        assert accesso.metrico == "300"


# ---------------------------------------------------------------------------
# 4. Fields not allowed for S (delete)
# ---------------------------------------------------------------------------


class TestAccessoFieldsNotAllowedForDelete:
    """Tests that S (delete) rejects fields meant for I/R."""

    def test_delete_with_numero_invalid(self) -> None:
        """Test that S with numero raises FieldNotAllowedForDeleteError."""
        with pytest.raises(ValidationError) as exc_info:
            ValidatedAccesso(operazione_civico="S", progr_civico="1370588", numero="12")
        cause = get_validation_error_cause(exc_info)
        assert isinstance(cause, FieldNotAllowedForDeleteError)
        assert "numero" in str(cause).lower()

    def test_delete_with_metrico_invalid(self) -> None:
        """Test that S with metrico raises FieldNotAllowedForDeleteError."""
        with pytest.raises(ValidationError) as exc_info:
            ValidatedAccesso(
                operazione_civico="S", progr_civico="1370588", metrico="300"
            )
        cause = get_validation_error_cause(exc_info)
        assert isinstance(cause, FieldNotAllowedForDeleteError)

    def test_delete_with_esponente_invalid(self) -> None:
        """Test that S with esponente raises FieldNotAllowedForOperationError."""
        with pytest.raises(ValidationError) as exc_info:
            ValidatedAccesso(
                operazione_civico="S", progr_civico="1370588", esponente="A"
            )
        cause = get_validation_error_cause(exc_info)
        assert isinstance(
            cause, (FieldNotAllowedForOperationError, FieldNotAllowedForDeleteError)
        )

    def test_delete_with_specificita_invalid(self) -> None:
        """Test that S with specificita raises FieldNotAllowedForOperationError."""
        with pytest.raises(ValidationError) as exc_info:
            ValidatedAccesso(
                operazione_civico="S",
                progr_civico="1370588",
                specificita="ROSSO",
            )
        cause = get_validation_error_cause(exc_info)
        assert isinstance(
            cause, (FieldNotAllowedForOperationError, FieldNotAllowedForDeleteError)
        )

    def test_delete_with_sezione_censimento_invalid(self) -> None:
        """Test that S with sezione_censimento raises an error."""
        with pytest.raises(ValidationError) as exc_info:
            ValidatedAccesso(
                operazione_civico="S",
                progr_civico="1370588",
                sezione_censimento="9",
            )
        cause = get_validation_error_cause(exc_info)
        assert isinstance(
            cause, (FieldNotAllowedForOperationError, FieldNotAllowedForDeleteError)
        )

    def test_delete_with_isolato_invalid(self) -> None:
        """Test that S with isolato raises an error."""
        with pytest.raises(ValidationError) as exc_info:
            ValidatedAccesso(
                operazione_civico="S", progr_civico="1370588", isolato="101"
            )
        cause = get_validation_error_cause(exc_info)
        assert isinstance(
            cause, (FieldNotAllowedForOperationError, FieldNotAllowedForDeleteError)
        )

    def test_delete_minimal_valid(self) -> None:
        """Test that S with only the required fields (codcom, prognaz, progr_civico)
        is valid. Note: codcom/prognaz are on Richiesta, not Accesso."""
        accesso = ValidatedAccesso(operazione_civico="S", progr_civico="1370588")
        assert accesso.operazione_civico == "S"
        assert accesso.progr_civico == "1370588"


# ---------------------------------------------------------------------------
# 5. maxLength constraints from OAS
# ---------------------------------------------------------------------------


class TestAccessoMaxLengthValidation:
    """Tests for maxLength enforcement on string fields."""

    def test_progr_civico_max_length_15_exceeded_raises(self) -> None:
        """Test that progr_civico longer than 15 raises AccessoMaxLengthError."""
        with pytest.raises(ValidationError) as exc_info:
            ValidatedAccesso(
                operazione_civico="R",
                progr_civico="1234567890123456",  # 16 chars
                numero="12",
            )
        cause = get_validation_error_cause(exc_info)
        assert isinstance(cause, AccessoMaxLengthError)
        assert "progr_civico" in str(cause)

    def test_codice_civico_comunale_max_length_30_exceeded(self) -> None:
        """Test codice_civico_comunale maxLength=30."""
        long_code = "A" * 31
        with pytest.raises(ValidationError) as exc_info:
            ValidatedAccesso(
                operazione_civico="I",
                numero="12",
                codice_civico_comunale=long_code,
            )
        cause = get_validation_error_cause(exc_info)
        assert isinstance(cause, AccessoMaxLengthError)

    def test_numero_max_length_5_exceeded(self) -> None:
        """Test numero maxLength=5."""
        with pytest.raises(ValidationError) as exc_info:
            ValidatedAccesso(operazione_civico="I", numero="123456")
        cause = get_validation_error_cause(exc_info)
        assert isinstance(cause, AccessoMaxLengthError)

    def test_esponente_max_length_15_exceeded(self) -> None:
        """Test esponente maxLength=15."""
        with pytest.raises(ValidationError) as exc_info:
            ValidatedAccesso(operazione_civico="I", numero="12", esponente="A" * 16)
        cause = get_validation_error_cause(exc_info)
        assert isinstance(cause, AccessoMaxLengthError)

    def test_specificita_max_length_5_exceeded(self) -> None:
        """Test specificita maxLength=5."""
        with pytest.raises(ValidationError) as exc_info:
            ValidatedAccesso(operazione_civico="I", numero="12", specificita="ROSSOX")
        cause = get_validation_error_cause(exc_info)
        assert isinstance(cause, AccessoMaxLengthError)

    def test_metrico_max_length_6_exceeded(self) -> None:
        """Test metrico maxLength=6."""
        with pytest.raises(ValidationError) as exc_info:
            ValidatedAccesso(operazione_civico="I", metrico="1234567")
        cause = get_validation_error_cause(exc_info)
        assert isinstance(cause, AccessoMaxLengthError)

    def test_sezione_censimento_max_length_13_exceeded(self) -> None:
        """Test sezione_censimento maxLength=13."""
        with pytest.raises(ValidationError) as exc_info:
            ValidatedAccesso(
                operazione_civico="I",
                numero="12",
                sezione_censimento="1" * 14,
            )
        cause = get_validation_error_cause(exc_info)
        assert isinstance(cause, AccessoMaxLengthError)

    def test_isolato_max_length_4_exceeded(self) -> None:
        """Test isolato maxLength=4."""
        with pytest.raises(ValidationError) as exc_info:
            ValidatedAccesso(operazione_civico="I", numero="12", isolato="12345")
        cause = get_validation_error_cause(exc_info)
        assert isinstance(cause, AccessoMaxLengthError)

    def test_all_fields_at_max_length_valid(self) -> None:
        """Test that all fields exactly at maxLength are accepted."""
        accesso = ValidatedAccesso(
            operazione_civico="I",
            numero="12345",  # 5
            esponente="A" * 15,  # 15
            specificita="ROSSO",  # 5
            sezione_censimento="1" * 13,  # 13
            isolato="1234",  # 4
            codice_civico_comunale="C" * 30,  # 30
        )
        assert accesso.numero == "12345"


# ---------------------------------------------------------------------------
# 6. Coordinate integration (delegated to ValidatedCoordinate)
# ---------------------------------------------------------------------------


class TestAccessoCoordinateIntegration:
    """Tests that coordinate field uses ValidatedCoordinate validation."""

    def test_accesso_with_valid_coordinates(self) -> None:
        """Test accesso with valid Italian coordinates."""
        accesso = ValidatedAccesso(
            operazione_civico="I",
            numero="12",
            coordinate={
                "x": "13.1022000",
                "y": "41.8847600",
                "metodo": "3",
            },
        )
        assert accesso.coordinate is not None
        assert accesso.coordinate.x == "13.1022000"

    def test_accesso_with_out_of_range_x_invalid(self) -> None:
        """Test that out-of-Italy X coordinate is rejected via ValidatedCoordinate."""
        with pytest.raises(ValidationError) as exc_info:
            ValidatedAccesso(
                operazione_civico="I",
                numero="12",
                coordinate={
                    "x": "99.0",  # outside Italy bounds (6-18)
                    "y": "41.8847600",
                    "metodo": "3",
                },
            )
        cause = get_validation_error_cause(exc_info)
        # Can be CoordinateRangeError directly or wrapped
        assert isinstance(cause, (CoordinateRangeError, ValidationError))

    def test_delete_with_coordinate_invalid(self) -> None:
        """Test that S with coordinate raises FieldNotAllowedForDeleteError."""
        with pytest.raises(ValidationError) as exc_info:
            ValidatedAccesso(
                operazione_civico="S",
                progr_civico="1370588",
                coordinate={
                    "x": "13.1022000",
                    "y": "41.8847600",
                    "metodo": "3",
                },
            )
        cause = get_validation_error_cause(exc_info)
        assert isinstance(
            cause, (FieldNotAllowedForOperationError, FieldNotAllowedForDeleteError)
        )

    def test_accesso_without_coordinates_valid(self) -> None:
        """Test that accesso without coordinates is valid (coordinates optional)."""
        accesso = ValidatedAccesso(operazione_civico="I", numero="12")
        assert accesso.coordinate is None


# ---------------------------------------------------------------------------
# 7. Error hierarchy
# ---------------------------------------------------------------------------


class TestAccessoValidationErrorHierarchy:
    """Tests that all errors inherit from AccessoValidationError and ValueError."""

    def test_all_errors_inherit_from_accesso_validation_error(self) -> None:
        """Test that all specific errors are subclasses of AccessoValidationError."""
        for err_class in (
            OperazioneCivicoError,
            ProgrCivicoRequiredError,
            FieldNotAllowedForDeleteError,
            NumeroMetricoMutexError,
            FieldNotAllowedForOperationError,
            AccessoMaxLengthError,
        ):
            assert issubclass(err_class, AccessoValidationError)

    def test_accesso_validation_error_inherits_from_value_error(self) -> None:
        """Test that base AccessoValidationError is a ValueError subclass."""
        assert issubclass(AccessoValidationError, ValueError)

    def test_catch_any_error_with_base_class(self) -> None:
        """Test that catching AccessoValidationError catches all subclasses."""
        with pytest.raises(ValidationError) as exc_info:
            ValidatedAccesso(operazione_civico="X")
        cause = get_validation_error_cause(exc_info)
        assert isinstance(cause, AccessoValidationError)


# ---------------------------------------------------------------------------
# 8. Realistic integration scenarios
# ---------------------------------------------------------------------------


class TestAccessoIntegration:
    """End-to-end realistic scenarios for I/R/S operations."""

    def test_insert_complete_civico(self) -> None:
        """Realistic INSERT for a civico accesso."""
        accesso = ValidatedAccesso(
            operazione_civico="I",
            numero="12",
            esponente="A",
            sezione_censimento="9",
            coordinate={
                "x": "13.1022000",
                "y": "41.8847600",
                "metodo": "3",
            },
            data_valid_amm="08/10/2024",
        )
        assert accesso.operazione_civico == "I"
        assert accesso.numero == "12"
        assert accesso.coordinate.metodo == "3"

    def test_replace_with_new_coordinates(self) -> None:
        """Realistic REPLACE updating coordinates of an existing accesso."""
        accesso = ValidatedAccesso(
            operazione_civico="R",
            progr_civico="1370588",
            numero="12",
            coordinate={
                "x": "13.1022001",
                "y": "41.8847601",
                "metodo": "3",
            },
        )
        assert accesso.progr_civico == "1370588"

    def test_delete_minimal(self) -> None:
        """Realistic DELETE with only required identifier."""
        accesso = ValidatedAccesso(
            operazione_civico="S",
            progr_civico="1370588",
            data_valid_amm="31/12/2025",
        )
        assert accesso.operazione_civico == "S"
        assert accesso.data_valid_amm == "31/12/2025"

    def test_insert_metrico(self) -> None:
        """Realistic INSERT for a metrico (non-civico-numbered) accesso."""
        from anncsu.common.sdk.types.basemodel import Unset

        accesso = ValidatedAccesso(
            operazione_civico="I",
            metrico="300",
            coordinate={
                "x": "13.1022000",
                "y": "41.8847600",
                "metodo": "3",
            },
        )
        assert accesso.metrico == "300"
        # numero is left as UNSET sentinel (Speakeasy default for not-provided)
        assert isinstance(accesso.numero, Unset) or accesso.numero is None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
