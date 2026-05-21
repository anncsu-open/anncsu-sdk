# SPDX-FileCopyrightText: 2025-present Geobeyond <info@geobeyond.it>
# SPDX-License-Identifier: MIT
"""Validated Accesso model with ANNCSU business rules.

This module provides a validated version of the Accesso model that enforces
the business rules of the ANNCSU "Aggiornamento accessi" API.

Rules (derived from the OAS spec):

1. ``operazione_civico`` must be one of ``"I"`` (inserimento), ``"R"``
   (aggiornamento), ``"S"`` (soppressione).
2. ``progr_civico`` is mandatory for ``R`` and ``S``, optional for ``I``.
3. ``numero`` and ``metrico`` are mutually exclusive: exactly one must be
   provided for ``I``/``R`` (accesso civico XOR metrico). Neither is allowed
   for ``S``.
4. For ``S``, the following fields must NOT be valued: ``numero``,
   ``metrico``, ``esponente``, ``specificita``, ``sezione_censimento``,
   ``isolato``, ``coordinate``.
5. maxLength constraints from the OAS spec are enforced explicitly with a
   localized error message (Pydantic itself does not strictly enforce
   ``maxLength`` from OpenAPI).
6. ``coordinate``, when present, is re-validated through the existing
   ``ValidatedCoordinate`` model (Italy bounds, X/Y dependency, metodo
   1-4, maxLength X/Y/Z).
7. ``sezione_censimento`` is mandatory for ``I`` and ``R`` (OAS field has
   no ``nullable: true``); rule 4 already forbids it for ``S``.
"""

from __future__ import annotations

from typing import Optional

from pydantic import model_validator

from anncsu.accessi.errors.accesso_validation import (
    AccessoMaxLengthError,
    FieldNotAllowedForDeleteError,
    NumeroMetricoMutexError,
    OperazioneCivicoError,
    ProgrCivicoRequiredError,
    SezioneCensimentoRequiredError,
)
from anncsu.accessi.models.richiestaoperazione import Accesso
from anncsu.coordinate.models.validated import ValidatedCoordinate

VALID_OPERAZIONI = {"I", "R", "S"}

# maxLength constraints from OAS spec (in characters)
MAX_LENGTHS: dict[str, int] = {
    "progr_civico": 15,
    "codice_civico_comunale": 30,
    "numero": 5,
    "esponente": 15,
    "specificita": 5,
    "metrico": 6,
    "sezione_censimento": 13,
    "operazione_civico": 1,
    "isolato": 4,
}

# Fields not allowed when operazione_civico='S' (delete).
# Coordinate is handled separately because it's a nested model.
FIELDS_NOT_ALLOWED_FOR_DELETE: tuple[str, ...] = (
    "numero",
    "metrico",
    "esponente",
    "specificita",
    "sezione_censimento",
    "isolato",
)


class ValidatedAccesso(Accesso):
    """Accesso model with ANNCSU business rule validation.

    Extends the generated ``Accesso`` model from Speakeasy to enforce the
    operation-aware rules (I/R/S) and maxLength constraints described in
    the OAS spec.

    Raises:
        OperazioneCivicoError: ``operazione_civico`` missing or not in {I,R,S}
        ProgrCivicoRequiredError: ``progr_civico`` missing for R or S
        NumeroMetricoMutexError: both/neither numero and metrico for I/R
        FieldNotAllowedForDeleteError: forbidden field set for S operation
        AccessoMaxLengthError: a string field exceeds its OAS maxLength
        CoordinateValidationError (and subclasses): bubbled up from
            ``ValidatedCoordinate`` for invalid embedded coordinates
    """

    @model_validator(mode="after")
    def validate_accesso_rules(self) -> "ValidatedAccesso":
        """Apply ANNCSU business rules in a single pass."""
        op = self._get_value(self.operazione_civico)

        # Rule 1: operazione_civico must be I / R / S
        if op is None or op not in VALID_OPERAZIONI:
            raise OperazioneCivicoError(value=op)

        # Rule 5: maxLength constraints (run BEFORE other logic so the user
        # gets a precise error per field).
        self._validate_max_lengths()

        # Rule 4: forbidden fields for S
        if op == "S":
            self._validate_no_forbidden_fields_for_delete()
            # coordinate must NOT be set for S either
            if self.coordinate is not None:
                raise FieldNotAllowedForDeleteError(
                    field_name="coordinate",
                    value=str(self.coordinate.model_dump(exclude_unset=True)),
                )

        # Rule 2: progr_civico required for R and S
        if op in {"R", "S"} and not self._get_value(self.progr_civico):
            raise ProgrCivicoRequiredError(operazione=op)

        # Rule 3: numero / metrico mutual exclusion (only for I and R)
        if op in {"I", "R"}:
            has_numero = self._get_value(self.numero) is not None
            has_metrico = self._get_value(self.metrico) is not None
            if has_numero and has_metrico:
                raise NumeroMetricoMutexError(has_numero=True, has_metrico=True)
            if not has_numero and not has_metrico:
                raise NumeroMetricoMutexError(has_numero=False, has_metrico=False)

        # Rule 7 (issue #30): sezione_censimento required for I/R.
        # OAS declares the field without ``nullable: true`` — the API rejects
        # the request server-side if absent. Mirror that contract locally.
        if op in {"I", "R"} and self._get_value(self.sezione_censimento) is None:
            raise SezioneCensimentoRequiredError(operazione=op)

        # Rule 6: re-validate embedded coordinates via ValidatedCoordinate
        if self.coordinate is not None:
            payload = self.coordinate.model_dump(exclude_unset=True)
            # This raises CoordinateValidationError (subclass of ValueError)
            # if the embedded coordinates violate any rule.
            ValidatedCoordinate.model_validate(payload)

        return self

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _get_value(self, field_value) -> Optional[str]:
        """Extract actual value, treating UNSET sentinel and None as missing."""
        from anncsu.common.sdk.types import UNSET
        from anncsu.common.sdk.types.basemodel import Unset

        if field_value is None:
            return None
        if isinstance(field_value, Unset) or field_value is UNSET:
            return None
        s = str(field_value)
        # Treat empty string as missing for our business-rule purposes.
        return s if s else None

    def _validate_max_lengths(self) -> None:
        """Enforce OAS maxLength on every string field."""
        for field_name, max_length in MAX_LENGTHS.items():
            value = self._get_value(getattr(self, field_name, None))
            if value is not None and len(value) > max_length:
                raise AccessoMaxLengthError(
                    field_name=field_name,
                    value=value,
                    max_length=max_length,
                )

    def _validate_no_forbidden_fields_for_delete(self) -> None:
        """Reject fields that have no semantic meaning for S (delete)."""
        for field_name in FIELDS_NOT_ALLOWED_FOR_DELETE:
            value = self._get_value(getattr(self, field_name, None))
            if value is not None:
                raise FieldNotAllowedForDeleteError(
                    field_name=field_name,
                    value=value,
                )


__all__ = ["ValidatedAccesso"]
