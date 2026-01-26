# SPDX-FileCopyrightText: 2025-present Geobeyond <info@geobeyond.it>
# SPDX-License-Identifier: MIT
"""Custom errors for RispostaOperazione validation.

These errors provide specific error types for response validation failures,
enabling precise error handling in client code.
"""

from __future__ import annotations

from dataclasses import dataclass


class RispostaValidationError(ValueError):
    """Base error for response validation failures."""

    pass


@dataclass
class EsitoError(RispostaValidationError):
    """Error when esito indicates operation failure.

    Attributes:
        esito: The esito code returned by the API
        messaggio: The error message from the API
        codice: Optional error code from the API
        id_richiesta: Optional request ID
    """

    esito: str
    messaggio: str | None = None
    codice: str | None = None
    id_richiesta: str | None = None

    def __str__(self) -> str:
        parts = [f"Esito={self.esito}"]
        if self.codice:
            parts.append(f"Codice={self.codice}")
        if self.messaggio:
            parts.append(f"Messaggio='{self.messaggio}'")
        if self.id_richiesta:
            parts.append(f"ID={self.id_richiesta}")
        return f"Operation failed: {', '.join(parts)}"


@dataclass
class MissingEsitoError(RispostaValidationError):
    """Error when esito field is missing from response.

    Attributes:
        id_richiesta: Optional request ID
    """

    id_richiesta: str | None = None

    def __str__(self) -> str:
        msg = "Response missing 'esito' field"
        if self.id_richiesta:
            msg += f" (ID={self.id_richiesta})"
        return msg


__all__ = [
    "RispostaValidationError",
    "EsitoError",
    "MissingEsitoError",
]
