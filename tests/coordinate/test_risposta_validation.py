# SPDX-FileCopyrightText: 2025-present Geobeyond <info@geobeyond.it>
# SPDX-License-Identifier: MIT
"""Tests for ValidatedRispostaOperazione model."""

from __future__ import annotations

import pytest

from anncsu.coordinate.errors.risposta_validation import (
    EsitoError,
    MissingEsitoError,
)
from anncsu.coordinate.models.validated import ValidatedRispostaOperazione


class TestValidatedRispostaOperazioneSuccess:
    """Tests for successful responses (esito='0')."""

    def test_esito_zero_is_success(self) -> None:
        """Test that esito='0' is considered success."""
        response = ValidatedRispostaOperazione.model_validate(
            {
                "esito": "0",
                "messaggio": "OK",
                "idRichiesta": "12345",
            }
        )
        assert response.is_success is True
        assert response.is_failure is False

    def test_esito_zero_with_dati(self) -> None:
        """Test successful response with dati array."""
        response = ValidatedRispostaOperazione.model_validate(
            {
                "esito": "0",
                "messaggio": "OK",
                "idRichiesta": "12345",
                "dati": [
                    {"progr_civico": "123", "numero": "1"},
                    {"progr_civico": "456", "numero": "2"},
                ],
            }
        )
        assert response.is_success is True
        assert len(response.dati) == 2

    def test_raise_for_status_success_no_exception(self) -> None:
        """Test that raise_for_status does not raise on success."""
        response = ValidatedRispostaOperazione.model_validate(
            {
                "esito": "0",
                "messaggio": "OK",
            }
        )
        # Should not raise
        response.raise_for_status()


class TestValidatedRispostaOperazioneFailure:
    """Tests for failed responses (esito != '0')."""

    def test_esito_non_zero_is_failure(self) -> None:
        """Test that esito != '0' is considered failure."""
        response = ValidatedRispostaOperazione.model_validate(
            {
                "esito": "1",
                "messaggio": "Errore generico",
            }
        )
        assert response.is_success is False
        assert response.is_failure is True

    def test_esito_error_code_130(self) -> None:
        """Test failure with specific error code (metodo validation)."""
        response = ValidatedRispostaOperazione.model_validate(
            {
                "esito": "130",
                "messaggio": "Il metodo deve essere obbligatorio e compreso tra 1 e 4",
                "idRichiesta": "186820",
            }
        )
        assert response.is_success is False
        assert response.esito == "130"

    def test_esito_none_is_failure(self) -> None:
        """Test that missing esito is considered failure."""
        response = ValidatedRispostaOperazione.model_validate(
            {
                "messaggio": "Some message",
            }
        )
        assert response.is_success is False
        assert response.is_failure is True

    def test_raise_for_status_failure_raises_esito_error(self) -> None:
        """Test that raise_for_status raises EsitoError on failure."""
        response = ValidatedRispostaOperazione.model_validate(
            {
                "esito": "130",
                "messaggio": "Il metodo deve essere obbligatorio",
                "idRichiesta": "186820",
            }
        )
        with pytest.raises(EsitoError) as exc_info:
            response.raise_for_status()

        error = exc_info.value
        assert error.esito == "130"
        assert error.messaggio == "Il metodo deve essere obbligatorio"
        assert error.id_richiesta == "186820"

    def test_raise_for_status_missing_esito_raises_missing_error(self) -> None:
        """Test that raise_for_status raises MissingEsitoError when esito is None."""
        response = ValidatedRispostaOperazione.model_validate(
            {
                "messaggio": "Some message",
                "idRichiesta": "12345",
            }
        )
        with pytest.raises(MissingEsitoError) as exc_info:
            response.raise_for_status()

        error = exc_info.value
        assert error.id_richiesta == "12345"


class TestValidatedRispostaOperazioneEdgeCases:
    """Tests for edge cases."""

    def test_esito_string_zero_vs_int_zero(self) -> None:
        """Test that only string '0' is success, not int 0."""
        # String "0" is success
        response = ValidatedRispostaOperazione.model_validate({"esito": "0"})
        assert response.is_success is True

    def test_esito_empty_string_is_failure(self) -> None:
        """Test that empty string esito is failure."""
        response = ValidatedRispostaOperazione.model_validate({"esito": ""})
        assert response.is_success is False

    def test_esito_whitespace_is_failure(self) -> None:
        """Test that whitespace esito is failure."""
        response = ValidatedRispostaOperazione.model_validate({"esito": " "})
        assert response.is_success is False

    def test_esito_ok_string_is_failure(self) -> None:
        """Test that 'OK' string is NOT success (only '0' is success)."""
        response = ValidatedRispostaOperazione.model_validate(
            {
                "esito": "OK",
                "messaggio": "Operazione completata",
            }
        )
        # "OK" is NOT the success code, only "0" is
        assert response.is_success is False

    def test_json_error_message_extraction(self) -> None:
        """Test extraction of codice from JSON-like error message."""
        response = ValidatedRispostaOperazione.model_validate(
            {
                "esito": "1",
                "messaggio": '{"id":"186820","messaggio":"Errore","codice":"130"}',
            }
        )
        with pytest.raises(EsitoError) as exc_info:
            response.raise_for_status()

        error = exc_info.value
        assert error.codice == "130"

    def test_plain_text_error_message(self) -> None:
        """Test that plain text message doesn't break codice extraction."""
        response = ValidatedRispostaOperazione.model_validate(
            {
                "esito": "1",
                "messaggio": "Plain text error message",
            }
        )
        with pytest.raises(EsitoError) as exc_info:
            response.raise_for_status()

        error = exc_info.value
        assert error.codice is None
        assert error.messaggio == "Plain text error message"


class TestEsitoErrorFormatting:
    """Tests for EsitoError string formatting."""

    def test_esito_error_str_full(self) -> None:
        """Test EsitoError string representation with all fields."""
        error = EsitoError(
            esito="130",
            messaggio="Il metodo deve essere obbligatorio",
            codice="130",
            id_richiesta="186820",
        )
        error_str = str(error)
        assert "Esito=130" in error_str
        assert "Codice=130" in error_str
        assert "Il metodo deve essere obbligatorio" in error_str
        assert "ID=186820" in error_str

    def test_esito_error_str_minimal(self) -> None:
        """Test EsitoError string representation with minimal fields."""
        error = EsitoError(esito="1")
        error_str = str(error)
        assert "Esito=1" in error_str
        assert "Codice" not in error_str
        assert "ID" not in error_str

    def test_missing_esito_error_str(self) -> None:
        """Test MissingEsitoError string representation."""
        error = MissingEsitoError(id_richiesta="12345")
        error_str = str(error)
        assert "missing 'esito'" in error_str.lower()
        assert "12345" in error_str
