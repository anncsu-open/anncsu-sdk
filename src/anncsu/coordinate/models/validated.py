# SPDX-FileCopyrightText: 2025-present Geobeyond <info@geobeyond.it>
# SPDX-License-Identifier: MIT
"""Validated Coordinate model with business rules.

This module provides a validated version of the Coordinate model that enforces
ANNCSU business rules:

1. X and Y must be provided together (both or neither)
2. When X and Y are present, metodo is REQUIRED and must be 1-4
3. When X and Y are absent, metodo must NOT be provided
4. Z can only be provided when X and Y are present
5. X range for Italy: 6.0 <= x <= 18.0
6. Y range for Italy: 36.0 <= y <= 47.0

Usage:
    from anncsu.coordinate.models import ValidatedCoordinate

    # Valid - no coordinates
    coord = ValidatedCoordinate()

    # Valid - coordinates with metodo
    coord = ValidatedCoordinate(x="12.4963655", y="41.9027835", metodo="4")

    # Invalid - coordinates without metodo (raises MetodoRequiredError)
    coord = ValidatedCoordinate(x="12.4963655", y="41.9027835")
"""

from __future__ import annotations

from typing import ClassVar, Optional

from pydantic import model_validator

from anncsu.coordinate.errors.coordinate_validation import (
    CoordinateDependencyError,
    CoordinateMaxLengthError,
    CoordinateRangeError,
    MetodoNotAllowedError,
    MetodoOutOfRangeError,
    MetodoRequiredError,
    QuotaNotAllowedError,
)
from anncsu.coordinate.models.richiestaoperazione import Coordinate
from anncsu.coordinate.models.rispostaoperazione import RispostaOperazione

# Coordinate bounds for Italy
X_MIN = 6.0
X_MAX = 18.0
Y_MIN = 36.0
Y_MAX = 47.0

# Valid metodo values
METODO_MIN = 1
METODO_MAX = 4

# API maxLength constraints (from OAS spec)
X_MAX_LENGTH = 12
Y_MAX_LENGTH = 12
Z_MAX_LENGTH = 7


class ValidatedCoordinate(Coordinate):
    """Coordinate model with ANNCSU business rule validation.

    This extends the generated Coordinate model to add validation for:
    - X/Y mutual dependency
    - metodo requirement when coordinates are present
    - metodo range validation (1-4)
    - X/Y range validation for Italy
    - Z dependency on X/Y

    Raises:
        MetodoRequiredError: When X and Y are provided but metodo is missing
        MetodoNotAllowedError: When metodo is provided without X and Y
        MetodoOutOfRangeError: When metodo is not between 1 and 4
        CoordinateDependencyError: When only X or only Y is provided
        CoordinateRangeError: When X or Y is outside Italy bounds
        QuotaNotAllowedError: When Z is provided without X and Y
    """

    @model_validator(mode="after")
    def validate_coordinate_rules(self) -> "ValidatedCoordinate":
        """Validate coordinate business rules."""
        # Get actual values (handle UNSET sentinel)
        x_val = self._get_value(self.x)
        y_val = self._get_value(self.y)
        z_val = self._get_value(self.z)
        metodo_val = self._get_value(self.metodo)

        has_x = x_val is not None
        has_y = y_val is not None
        has_z = z_val is not None
        has_metodo = metodo_val is not None

        # Rule 1: X and Y must be provided together
        if has_x and not has_y:
            raise CoordinateDependencyError(provided="X", missing="Y")
        if has_y and not has_x:
            raise CoordinateDependencyError(provided="Y", missing="X")

        # Rule 2 & 3: metodo depends on X/Y presence
        if has_x and has_y:
            # Coordinates present - metodo is required
            if not has_metodo:
                raise MetodoRequiredError(x=x_val, y=y_val)
            # Validate metodo range
            self._validate_metodo_range(metodo_val)
            # Validate coordinate ranges
            self._validate_x_range(x_val)
            self._validate_y_range(y_val)
            # Validate maxLength (API constraint)
            self._validate_max_length(x_val, "x", X_MAX_LENGTH)
            self._validate_max_length(y_val, "y", Y_MAX_LENGTH)
        else:
            # No coordinates - metodo must not be provided
            if has_metodo:
                raise MetodoNotAllowedError(metodo=metodo_val)

        # Rule 4: Z can only be provided with X and Y
        if has_z and not (has_x and has_y):
            raise QuotaNotAllowedError(z=z_val)

        # Validate Z maxLength
        if has_z:
            self._validate_max_length(z_val, "z", Z_MAX_LENGTH)

        return self

    def _get_value(self, field_value) -> Optional[str]:
        """Extract actual value from field, handling UNSET sentinel."""
        from anncsu.common.sdk.types import UNSET
        from anncsu.common.sdk.types.basemodel import Unset

        # Check for None
        if field_value is None:
            return None
        # Check for UNSET (instance of Unset class)
        if isinstance(field_value, Unset) or field_value is UNSET:
            return None
        return str(field_value)

    def _validate_metodo_range(self, metodo: str) -> None:
        """Validate metodo is between 1 and 4."""
        try:
            metodo_int = int(metodo)
            if metodo_int < METODO_MIN or metodo_int > METODO_MAX:
                raise MetodoOutOfRangeError(metodo=metodo)
        except ValueError:
            raise MetodoOutOfRangeError(metodo=metodo) from None

    def _validate_x_range(self, x: str) -> None:
        """Validate X coordinate is within Italy bounds."""
        try:
            x_float = float(x)
            if x_float < X_MIN or x_float > X_MAX:
                raise CoordinateRangeError(
                    coordinate_name="X",
                    value=x,
                    min_value=X_MIN,
                    max_value=X_MAX,
                )
        except ValueError:
            raise CoordinateRangeError(
                coordinate_name="X",
                value=x,
                min_value=X_MIN,
                max_value=X_MAX,
            ) from None

    def _validate_max_length(
        self, value: str, field_name: str, max_length: int
    ) -> None:
        """Validate that a coordinate string does not exceed API maxLength."""
        if len(value) > max_length:
            raise CoordinateMaxLengthError(
                field_name=field_name,
                value=value,
                max_length=max_length,
            )

    def _validate_y_range(self, y: str) -> None:
        """Validate Y coordinate is within Italy bounds."""
        try:
            y_float = float(y)
            if y_float < Y_MIN or y_float > Y_MAX:
                raise CoordinateRangeError(
                    coordinate_name="Y",
                    value=y,
                    min_value=Y_MIN,
                    max_value=Y_MAX,
                )
        except ValueError:
            raise CoordinateRangeError(
                coordinate_name="Y",
                value=y,
                min_value=Y_MIN,
                max_value=Y_MAX,
            ) from None


class ValidatedRispostaOperazione(RispostaOperazione):
    """RispostaOperazione model with success/failure validation.

    This extends the generated RispostaOperazione model to add:
    - is_success property based on esito value
    - Validation that esito is present

    ANNCSU API convention:
    - esito="0" means SUCCESS
    - esito=any other value means FAILURE
    - messaggio contains the textual description ("OK", error message, etc.)

    Usage:
        from anncsu.coordinate.models.validated import ValidatedRispostaOperazione

        # Parse API response
        response = ValidatedRispostaOperazione.model_validate(api_response)

        if response.is_success:
            print(f"Success: {response.messaggio}")
        else:
            print(f"Failed: {response.messaggio}")
    """

    # Success esito code
    SUCCESS_ESITO: ClassVar[str] = "0"

    @property
    def is_success(self) -> bool:
        """Check if the operation was successful.

        Returns:
            True if esito equals "0", False otherwise.
        """
        return self.esito == self.SUCCESS_ESITO

    @property
    def is_failure(self) -> bool:
        """Check if the operation failed.

        Returns:
            True if esito is not "0" or is None, False otherwise.
        """
        return not self.is_success

    def raise_for_status(self) -> None:
        """Raise an error if the operation failed.

        Raises:
            MissingEsitoError: If esito is None
            EsitoError: If esito indicates failure (not "0")
        """
        from anncsu.coordinate.errors.risposta_validation import (
            EsitoError,
            MissingEsitoError,
        )

        if self.esito is None:
            raise MissingEsitoError(id_richiesta=self.id_richiesta)

        if self.is_failure:
            # Try to extract codice from messaggio if it's JSON-like
            codice = None
            if self.messaggio and "codice" in self.messaggio.lower():
                try:
                    import json

                    msg_data = json.loads(self.messaggio)
                    codice = msg_data.get("codice")
                except (json.JSONDecodeError, TypeError):
                    pass

            raise EsitoError(
                esito=self.esito,
                messaggio=self.messaggio,
                codice=codice,
                id_richiesta=self.id_richiesta,
            )


__all__ = ["ValidatedCoordinate", "ValidatedRispostaOperazione"]
