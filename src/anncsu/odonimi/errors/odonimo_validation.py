# SPDX-FileCopyrightText: 2025-present Geobeyond <info@geobeyond.it>
# SPDX-License-Identifier: MIT
"""Custom errors for Odonimo validation.

These errors are raised when odonimo data does not meet ANNCSU business
rules for the I (insert), R (replace), or S (delete) operations defined
by ``tipo_operazione``.
"""

from __future__ import annotations

from dataclasses import dataclass


class OdonimoValidationError(ValueError):
    """Base error for odonimo validation failures.

    All odonimo validation errors inherit from this class, so a single
    ``except OdonimoValidationError`` catches any validation problem.
    """

    pass


@dataclass
class TipoOperazioneError(OdonimoValidationError):
    """Raised when tipo_operazione is missing or not one of {I, R, S}.

    Per OAS spec: tipo_operazione is an enum [I, R, S], no nullable,
    always required.
    """

    value: object

    def __str__(self) -> str:
        if self.value is None:
            return (
                "Il campo 'tipo_operazione' e' obbligatorio e deve essere "
                "uno di: 'I' (inserimento), 'R' (aggiornamento), 'S' (soppressione)."
            )
        return (
            f"Il campo 'tipo_operazione' deve essere 'I', 'R' o 'S'. "
            f"Valore fornito: {self.value!r}"
        )


@dataclass
class CodcomRequiredError(OdonimoValidationError):
    """Raised when codcom is missing.

    Per OAS spec: codcom is mandatory for every operation (no nullable).
    """

    def __str__(self) -> str:
        return "Il campo 'codcom' e' obbligatorio per tutte le operazioni."


@dataclass
class ProgrNazionaleRequiredError(OdonimoValidationError):
    """Raised when progr_nazionale is missing for R (replace) or S (delete).

    Per OAS spec: progr_nazionale is mandatory for tipo_operazione='R','S'
    because it identifies the existing odonimo to act on. For 'I' it is
    assigned by the API.
    """

    operazione: str

    def __str__(self) -> str:
        return (
            f"Il campo 'progr_nazionale' e' obbligatorio per "
            f"tipo_operazione='{self.operazione}'. "
            f"Per 'I' (inserimento) e' assegnato da ANNCSU."
        )


@dataclass
class DugRequiredError(OdonimoValidationError):
    """Raised when dug is missing for I (insert) or R (replace).

    Per OAS spec: dug is mandatory for tipo_operazione='I','R' (no
    nullable). It identifies the street type ("VIA", "PIAZZA", etc.).
    """

    operazione: str

    def __str__(self) -> str:
        return (
            f"Il campo 'dug' e' obbligatorio per tipo_operazione='{self.operazione}'. "
            f"Per 'S' (soppressione) non deve essere valorizzato."
        )


@dataclass
class DugNotAllowedForDeleteError(OdonimoValidationError):
    """Raised when dug is set on tipo_operazione='S' (delete).

    Per OAS spec: dug is "non ammesso per soppressione".
    """

    value: str

    def __str__(self) -> str:
        return (
            f"Il campo 'dug' non e' valorizzabile per tipo_operazione='S' "
            f"(soppressione). Valore fornito: {self.value!r}"
        )


@dataclass
class OdonimoMaxLengthError(OdonimoValidationError):
    """Raised when a string field exceeds its OAS maxLength constraint.

    OAS constraints:
        progr_nazionale: 10        codice_comunale: 30
        dug: 30                    denom_delibera: 120
        denom_in_lingua_1: 150     denom_in_lingua_2: 150
        denom_localita: 151        provvedimento.protocollo: 70
        aut_prefettura.protocollo_pref: 70
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


@dataclass
class FlagDeliberaMissingFieldsError(OdonimoValidationError):
    """Raised when provvedimento.flag_delibera is '0' or '1' but
    provvedimento.data or provvedimento.protocollo are missing.

    Per OAS spec: "I valori 0 e 1 rendono obbligatorie le informazioni
    data e protocollo".
    """

    flag_delibera: str
    missing_fields: tuple[str, ...]

    def __str__(self) -> str:
        fields_str = ", ".join(f"'{f}'" for f in self.missing_fields)
        return (
            f"Quando 'provvedimento.flag_delibera' = '{self.flag_delibera}', "
            f"i seguenti campi del provvedimento sono obbligatori: {fields_str}."
        )


@dataclass
class PrefetturaMutexError(OdonimoValidationError):
    """Raised when aut_prefettura.data_pref and protocollo_pref are not
    both set (one without the other is invalid).

    Per OAS spec: "data_pref obbligatoria se è presente il protocollo_pref"
    and "protocollo_pref obbligatorio se è presente data_pref".
    """

    has_data_pref: bool
    has_protocollo_pref: bool

    def __str__(self) -> str:
        if self.has_data_pref:
            return (
                "Il campo 'aut_prefettura.protocollo_pref' e' obbligatorio "
                "quando 'aut_prefettura.data_pref' e' valorizzato."
            )
        return (
            "Il campo 'aut_prefettura.data_pref' e' obbligatorio quando "
            "'aut_prefettura.protocollo_pref' e' valorizzato."
        )


__all__ = [
    "OdonimoValidationError",
    "TipoOperazioneError",
    "CodcomRequiredError",
    "ProgrNazionaleRequiredError",
    "DugRequiredError",
    "DugNotAllowedForDeleteError",
    "OdonimoMaxLengthError",
    "FlagDeliberaMissingFieldsError",
    "PrefetturaMutexError",
]
