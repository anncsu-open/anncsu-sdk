# SPDX-FileCopyrightText: 2025-present Geobeyond <info@geobeyond.it>
# SPDX-License-Identifier: MIT
"""Custom errors for Accesso validation.

These errors are raised when accesso data does not meet ANNCSU business
rules for the I (insert), R (replace), or S (delete) operations defined
by ``operazione_civico``.
"""

from __future__ import annotations

from dataclasses import dataclass


class AccessoValidationError(ValueError):
    """Base error for accesso validation failures.

    All accesso validation errors inherit from this class, so a single
    ``except AccessoValidationError`` catches any validation problem.

    Example:
        try:
            accesso = ValidatedAccesso(operazione_civico="X")
        except AccessoValidationError as e:
            print(f"Validation failed: {e}")
    """

    pass


@dataclass
class OperazioneCivicoError(AccessoValidationError):
    """Raised when operazione_civico is missing or not one of {I, R, S}.

    Per OAS spec: operazione_civico ∈ {"I", "R", "S"} (mandatory, maxLength 1).
    """

    value: str | None

    def __str__(self) -> str:
        if self.value is None:
            return (
                "Il campo 'operazione_civico' e' obbligatorio e deve essere "
                "uno di: 'I' (inserimento), 'R' (aggiornamento), 'S' (soppressione)."
            )
        return (
            f"Il campo 'operazione_civico' deve essere 'I', 'R' o 'S'. "
            f"Valore fornito: {self.value!r}"
        )


@dataclass
class ProgrCivicoRequiredError(AccessoValidationError):
    """Raised when progr_civico is missing for R (replace) or S (delete).

    Per OAS spec: progr_civico is mandatory for operazione_civico='R','S'
    because it identifies the existing accesso to act on. For 'I' it is
    optional (assigned by the API).
    """

    operazione: str

    def __str__(self) -> str:
        return (
            f"Il campo 'progr_civico' e' obbligatorio per operazione_civico='{self.operazione}'. "
            f"Per 'I' (inserimento) e' opzionale e viene assegnato da ANNCSU."
        )


@dataclass
class NumeroMetricoMutexError(AccessoValidationError):
    """Raised when numero/metrico mutex rule is violated.

    Per OAS spec: an accesso is identified either by 'numero' (civico)
    OR 'metrico' (system metric). For I/R operations exactly one must be
    provided. Both or neither violates the rule.
    """

    has_numero: bool
    has_metrico: bool

    def __str__(self) -> str:
        if self.has_numero and self.has_metrico:
            return (
                "I campi 'numero' e 'metrico' sono mutuamente esclusivi: "
                "un accesso e' identificato da 'numero' (civico) OPPURE 'metrico', "
                "mai entrambi."
            )
        return (
            "Per operazione_civico='I'/'R' e' obbligatorio specificare "
            "uno tra 'numero' (accesso civico) e 'metrico' (accesso metrico)."
        )


@dataclass
class FieldNotAllowedForDeleteError(AccessoValidationError):
    """Raised when a field is set on operazione_civico='S' (delete).

    Per OAS spec: for S operation, the only meaningful fields are
    progr_civico (identifier) and data_valid_amm (end date).
    Numero/metrico must NOT be valued; identifying fields like esponente,
    specificita, sezione_censimento, isolato, and coordinate are also
    rejected (they make sense only for I/R).
    """

    field_name: str
    value: str

    def __str__(self) -> str:
        return (
            f"Il campo '{self.field_name}' non e' valorizzabile per "
            f"operazione_civico='S' (soppressione). Valore fornito: {self.value!r}"
        )


@dataclass
class FieldNotAllowedForOperationError(AccessoValidationError):
    """Generic guard for fields that are operation-specific.

    Used as a slightly more generic variant of FieldNotAllowedForDeleteError
    when the rule applies beyond just S (currently only S in practice, but
    kept distinct for forward compatibility with future operation codes).
    """

    field_name: str
    value: str
    operazione: str

    def __str__(self) -> str:
        return (
            f"Il campo '{self.field_name}' non e' valorizzabile per "
            f"operazione_civico='{self.operazione}'. Valore fornito: {self.value!r}"
        )


@dataclass
class SezioneCensimentoRequiredError(AccessoValidationError):
    """Raised when sezione_censimento is missing for I (insert) or R (replace).

    Per OAS spec: ``sezione_censimento`` has no ``nullable: true`` and is
    described as "da valorizzare solo per operazione_civico='I','R'".
    Missing it triggers a server-side rejection like
    ``Sezione di censimento:   non presente nel Comune <X>``; catching it
    locally gives a clearer message before the API call.
    """

    operazione: str

    def __str__(self) -> str:
        return (
            f"Il campo 'sezione_censimento' e' obbligatorio per "
            f"operazione_civico='{self.operazione}'. "
            f"Per 'S' (soppressione) non deve essere valorizzato."
        )


@dataclass
class AccessoMaxLengthError(AccessoValidationError):
    """Raised when a string field exceeds its OAS maxLength constraint.

    OAS constraints:
        progr_civico: 15        numero: 5            esponente: 15
        codice_civico_comunale: 30                    specificita: 5
        metrico: 6              sezione_censimento: 13               isolato: 4
        operazione_civico: 1
    """

    field_name: str
    value: str
    max_length: int

    def __str__(self) -> str:
        return (
            f"Il campo '{self.field_name}' supera la lunghezza massima consentita. "
            f"Massimo {self.max_length} caratteri, forniti {len(self.value)}. "
            f"Valore: {self.value!r}"
        )


__all__ = [
    "AccessoValidationError",
    "OperazioneCivicoError",
    "ProgrCivicoRequiredError",
    "NumeroMetricoMutexError",
    "FieldNotAllowedForDeleteError",
    "FieldNotAllowedForOperationError",
    "SezioneCensimentoRequiredError",
    "AccessoMaxLengthError",
]
