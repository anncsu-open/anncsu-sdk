# SPDX-FileCopyrightText: 2025-present Geobeyond <info@geobeyond.it>
# SPDX-License-Identifier: MIT
"""Custom errors for Coordinate validation.

These errors are raised when coordinate data does not meet ANNCSU business rules.
"""

from __future__ import annotations

from dataclasses import dataclass


class CoordinateValidationError(ValueError):
    """Base error for coordinate validation failures.

    All coordinate validation errors inherit from this class,
    making it easy to catch any validation error with a single except clause.

    Example:
        try:
            coord = ValidatedCoordinate(x="12.0", y="41.0")  # missing metodo
        except CoordinateValidationError as e:
            print(f"Validation failed: {e}")
    """

    pass


@dataclass
class MetodoRequiredError(CoordinateValidationError):
    """Raised when metodo is missing but X and Y coordinates are provided.

    According to ANNCSU rules, when coordinates (X, Y) are provided,
    the metodo field is mandatory.
    """

    x: str
    y: str

    def __str__(self) -> str:
        return (
            f"Il campo 'metodo' e' obbligatorio quando X e Y sono valorizzati. "
            f"Coordinate fornite: X={self.x}, Y={self.y}"
        )


@dataclass
class MetodoNotAllowedError(CoordinateValidationError):
    """Raised when metodo is provided without X and Y coordinates.

    According to ANNCSU rules, metodo must not be set when
    coordinates are not provided.
    """

    metodo: str

    def __str__(self) -> str:
        return (
            f"Il campo 'metodo' non deve essere valorizzato in assenza di X e Y. "
            f"Metodo fornito: {self.metodo}"
        )


@dataclass
class MetodoOutOfRangeError(CoordinateValidationError):
    """Raised when metodo value is not between 1 and 4.

    Valid metodo values are: 1, 2, 3, 4
    """

    metodo: str
    min_value: int = 1
    max_value: int = 4

    def __str__(self) -> str:
        return (
            f"Il campo 'metodo' deve essere compreso tra {self.min_value} e {self.max_value}. "
            f"Valore fornito: {self.metodo}"
        )


@dataclass
class CoordinateDependencyError(CoordinateValidationError):
    """Raised when X is provided without Y or vice versa.

    X and Y coordinates must be provided together.
    """

    provided: str
    missing: str

    def __str__(self) -> str:
        return (
            f"Coordinata {self.missing} obbligatoria se viene valorizzata {self.provided}. "
            f"Fornire entrambe le coordinate X e Y."
        )


@dataclass
class CoordinateRangeError(CoordinateValidationError):
    """Raised when X or Y coordinate is outside Italy bounds.

    Valid ranges for Italy:
    - X (longitude): 6.0 <= x <= 18.0
    - Y (latitude): 36.0 <= y <= 47.0
    """

    coordinate_name: str
    value: str
    min_value: float
    max_value: float

    def __str__(self) -> str:
        return (
            f"Coordinata {self.coordinate_name} fuori range. "
            f"Valori ammessi in Italia: {self.min_value} <= {self.coordinate_name} <= {self.max_value}. "
            f"Valore fornito: {self.value}"
        )


@dataclass
class QuotaNotAllowedError(CoordinateValidationError):
    """Raised when Z (quota) is provided without X and Y coordinates.

    According to ANNCSU rules, quota can only be set when
    both X and Y coordinates are provided.
    """

    z: str

    def __str__(self) -> str:
        return (
            f"La quota (Z) non deve essere valorizzata in assenza di X e Y. "
            f"Quota fornita: {self.z}"
        )


@dataclass
class CoordinateMaxLengthError(CoordinateValidationError):
    """Raised when a coordinate string exceeds the API maxLength constraint.

    The ANNCSU API enforces maxLength on coordinate fields:
    - x: 12 characters
    - y: 12 characters
    - z: 7 characters
    """

    field_name: str
    value: str
    max_length: int

    def __str__(self) -> str:
        return (
            f"Il campo '{self.field_name}' supera la lunghezza massima consentita. "
            f"Massimo {self.max_length} caratteri, forniti {len(self.value)}. "
            f"Valore: {self.value}"
        )


__all__ = [
    "CoordinateValidationError",
    "MetodoRequiredError",
    "MetodoNotAllowedError",
    "MetodoOutOfRangeError",
    "CoordinateDependencyError",
    "CoordinateRangeError",
    "QuotaNotAllowedError",
    "CoordinateMaxLengthError",
]
