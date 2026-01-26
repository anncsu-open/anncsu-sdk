"""Integration tests for coordinate/jsonpost.py using pytest-httpx.

These tests mock HTTP responses at the httpx level to exercise
the full Speakeasy-generated code path for coordinate management endpoints.
"""

import pytest
from pytest_httpx import HTTPXMock

from anncsu.coordinate import AnncsuCoordinate, errors, models

# Base URL for mocking (production)
BASE_URL = (
    "https://modipa.agenziaentrate.it/govway/rest/in/AgenziaEntrate/anncsuaccessi/v1"
)


class TestGestioneCoordinate:
    """Tests for gestionecoordinate endpoint."""

    def test_gestionecoordinate_success(self, httpx_mock: HTTPXMock):
        """Test successful coordinate operation."""
        httpx_mock.add_response(
            method="POST",
            url=f"{BASE_URL}/gestionecoordinate",
            json={
                "idRichiesta": "REQ-12345",
                "esito": "OK",
                "messaggio": "Operazione completata con successo",
                "dati": [
                    {
                        "progr_civico": "00001",
                        "codcom": "H501",
                        "coordinata_x_comune": "12.4964",
                        "coordinata_y_comune": "41.9028",
                        "coordinata_z_comune": "21",
                    }
                ],
            },
            status_code=200,
        )

        security = models.Security(bearer="test-token")
        sdk = AnncsuCoordinate(security=security)

        response = sdk.json_post.gestionecoordinate(
            richiesta=models.Richiesta(
                accesso=models.Accesso(
                    codcom="H501",
                    progr_civico="00001",
                    coordinate=models.Coordinate(
                        x="12.4964",
                        y="41.9028",
                        z="21",
                        metodo="1",
                    ),
                )
            )
        )

        assert response.id_richiesta == "REQ-12345"
        assert response.esito == "OK"
        assert response.messaggio == "Operazione completata con successo"
        assert len(response.dati) == 1
        assert response.dati[0].codcom == "H501"

    def test_gestionecoordinate_with_dict_input(self, httpx_mock: HTTPXMock):
        """Test coordinate operation with TypedDict input."""
        httpx_mock.add_response(
            method="POST",
            url=f"{BASE_URL}/gestionecoordinate",
            json={
                "idRichiesta": "REQ-67890",
                "esito": "OK",
                "messaggio": "Coordinate aggiornate",
                "dati": [],
            },
            status_code=200,
        )

        security = models.Security(bearer="test-token")
        sdk = AnncsuCoordinate(security=security)

        # Using TypedDict style input
        response = sdk.json_post.gestionecoordinate(
            richiesta={
                "accesso": {
                    "codcom": "H501",
                    "progr_civico": "00002",
                    "coordinate": {
                        "x": "12.5000",
                        "y": "41.9000",
                    },
                }
            }
        )

        assert response.esito == "OK"

    def test_gestionecoordinate_bad_request(self, httpx_mock: HTTPXMock):
        """Test 400 Bad Request error handling."""
        httpx_mock.add_response(
            method="POST",
            url=f"{BASE_URL}/gestionecoordinate",
            json={
                "id": "ERR-400",
                "codice": "BAD_REQUEST",
                "messaggio": "Codice comune non valido",
            },
            status_code=400,
            headers={"Content-Type": "application/problem+json"},
        )

        security = models.Security(bearer="test-token")
        sdk = AnncsuCoordinate(security=security)

        with pytest.raises(errors.RispostaErrore) as exc_info:
            sdk.json_post.gestionecoordinate(
                richiesta=models.Richiesta(
                    accesso=models.Accesso(
                        codcom="INVALID",
                        progr_civico="00001",
                    )
                )
            )

        assert exc_info.value.data.codice == "BAD_REQUEST"
        assert exc_info.value.data.messaggio == "Codice comune non valido"

    def test_gestionecoordinate_unauthorized(self, httpx_mock: HTTPXMock):
        """Test 401 Unauthorized error handling."""
        httpx_mock.add_response(
            method="POST",
            url=f"{BASE_URL}/gestionecoordinate",
            json={
                "id": "ERR-401",
                "codice": "UNAUTHORIZED",
                "messaggio": "Token non valido o scaduto",
            },
            status_code=401,
            headers={"Content-Type": "application/problem+json"},
        )

        security = models.Security(bearer="invalid-token")
        sdk = AnncsuCoordinate(security=security)

        with pytest.raises(errors.RispostaErrore) as exc_info:
            sdk.json_post.gestionecoordinate(
                richiesta=models.Richiesta(
                    accesso=models.Accesso(
                        codcom="H501",
                        progr_civico="00001",
                    )
                )
            )

        assert exc_info.value.data.codice == "UNAUTHORIZED"

    def test_gestionecoordinate_not_found(self, httpx_mock: HTTPXMock):
        """Test 404 Not Found error handling."""
        httpx_mock.add_response(
            method="POST",
            url=f"{BASE_URL}/gestionecoordinate",
            json={
                "id": "ERR-404",
                "codice": "NOT_FOUND",
                "messaggio": "Accesso non trovato",
            },
            status_code=404,
            headers={"Content-Type": "application/problem+json"},
        )

        security = models.Security(bearer="test-token")
        sdk = AnncsuCoordinate(security=security)

        with pytest.raises(errors.RispostaErrore) as exc_info:
            sdk.json_post.gestionecoordinate(
                richiesta=models.Richiesta(
                    accesso=models.Accesso(
                        codcom="H501",
                        progr_civico="99999",
                    )
                )
            )

        assert exc_info.value.data.codice == "NOT_FOUND"

    def test_gestionecoordinate_internal_server_error(self, httpx_mock: HTTPXMock):
        """Test 500 Internal Server Error handling."""
        httpx_mock.add_response(
            method="POST",
            url=f"{BASE_URL}/gestionecoordinate",
            json={
                "id": "ERR-500",
                "codice": "INTERNAL_ERROR",
                "messaggio": "Errore interno del server",
            },
            status_code=500,
            headers={"Content-Type": "application/problem+json"},
        )

        security = models.Security(bearer="test-token")
        sdk = AnncsuCoordinate(security=security)

        with pytest.raises(errors.RispostaErrore):
            sdk.json_post.gestionecoordinate(
                richiesta=models.Richiesta(
                    accesso=models.Accesso(
                        codcom="H501",
                        progr_civico="00001",
                    )
                )
            )

    def test_gestionecoordinate_with_security(self, httpx_mock: HTTPXMock):
        """Test SDK operation with security configured."""
        httpx_mock.add_response(
            method="POST",
            url=f"{BASE_URL}/gestionecoordinate",
            json={
                "idRichiesta": "REQ-AUTH",
                "esito": "OK",
                "messaggio": "Autenticazione verificata",
                "dati": [],
            },
            status_code=200,
        )

        security = models.Security(bearer="my-pdnd-voucher-token")
        sdk = AnncsuCoordinate(security=security)

        response = sdk.json_post.gestionecoordinate(
            richiesta=models.Richiesta(
                accesso=models.Accesso(
                    codcom="H501",
                    progr_civico="00001",
                )
            )
        )

        assert response.esito == "OK"

        # Verify the request was sent
        requests = httpx_mock.get_requests()
        assert len(requests) == 1
        assert requests[0].method == "POST"

    def test_gestionecoordinate_request_body_json(self, httpx_mock: HTTPXMock):
        """Test that request body is sent as JSON."""
        httpx_mock.add_response(
            method="POST",
            url=f"{BASE_URL}/gestionecoordinate",
            json={
                "idRichiesta": "REQ-BODY",
                "esito": "OK",
                "messaggio": "Body ricevuto",
                "dati": [],
            },
            status_code=200,
        )

        security = models.Security(bearer="test-token")
        sdk = AnncsuCoordinate(security=security)

        sdk.json_post.gestionecoordinate(
            richiesta=models.Richiesta(
                accesso=models.Accesso(
                    codcom="H501",
                    progr_civico="00001",
                    coordinate=models.Coordinate(
                        x="12.4964",
                        y="41.9028",
                    ),
                )
            )
        )

        # Verify request was POST with JSON content type
        requests = httpx_mock.get_requests()
        assert len(requests) == 1
        assert requests[0].method == "POST"
        content_type = requests[0].headers.get("Content-Type", "")
        assert "application/json" in content_type

    def test_gestionecoordinate_generic_4xx_error(self, httpx_mock: HTTPXMock):
        """Test generic 4XX error handling."""
        httpx_mock.add_response(
            method="POST",
            url=f"{BASE_URL}/gestionecoordinate",
            text="Forbidden",
            status_code=403,
        )

        security = models.Security(bearer="test-token")
        sdk = AnncsuCoordinate(security=security)

        with pytest.raises(errors.APIError) as exc_info:
            sdk.json_post.gestionecoordinate(
                richiesta=models.Richiesta(
                    accesso=models.Accesso(
                        codcom="H501",
                        progr_civico="00001",
                    )
                )
            )

        assert "API error occurred" in str(exc_info.value)

    def test_gestionecoordinate_generic_5xx_error(self, httpx_mock: HTTPXMock):
        """Test generic 5XX error handling."""
        httpx_mock.add_response(
            method="POST",
            url=f"{BASE_URL}/gestionecoordinate",
            text="Service Unavailable",
            status_code=503,
        )

        security = models.Security(bearer="test-token")
        sdk = AnncsuCoordinate(security=security)

        with pytest.raises(errors.APIError):
            sdk.json_post.gestionecoordinate(
                richiesta=models.Richiesta(
                    accesso=models.Accesso(
                        codcom="H501",
                        progr_civico="00001",
                    )
                )
            )


class TestGestioneCoordinateWithCustomServerUrl:
    """Tests for coordinate operations with custom server URL."""

    def test_with_validation_environment(self, httpx_mock: HTTPXMock):
        """Test SDK with validation environment URL."""
        val_url = "https://modipa-val.agenziaentrate.it/govway/rest/in/AgenziaEntrate/anncsuaccessi/v1"

        httpx_mock.add_response(
            method="POST",
            url=f"{val_url}/gestionecoordinate",
            json={
                "idRichiesta": "REQ-VAL",
                "esito": "OK",
                "messaggio": "Test su ambiente di validazione",
                "dati": [],
            },
            status_code=200,
        )

        security = models.Security(bearer="test-token")
        sdk = AnncsuCoordinate(security=security, server_url=val_url)

        response = sdk.json_post.gestionecoordinate(
            richiesta=models.Richiesta(
                accesso=models.Accesso(
                    codcom="H501",
                    progr_civico="00001",
                )
            )
        )

        assert response.esito == "OK"
        assert response.messaggio == "Test su ambiente di validazione"


class TestGestioneCoordinateResponseData:
    """Tests for response data parsing."""

    def test_response_with_full_dati(self, httpx_mock: HTTPXMock):
        """Test response with complete dati structure."""
        httpx_mock.add_response(
            method="POST",
            url=f"{BASE_URL}/gestionecoordinate",
            json={
                "idRichiesta": "REQ-FULL",
                "esito": "OK",
                "messaggio": "Dati completi",
                "dati": [
                    {
                        "progr_civico": "00001",
                        "codice_civico_comunale": "123ABC",
                        "numero": "42",
                        "esponente": "A",
                        "specificita": "",
                        "metrico": "",
                        "sez_censimento": "001",
                        "data_inizio": "2024-01-01",
                        "data_fine": "",
                        "progr_nazionale": "12345678901234567890",
                        "codcom": "H501",
                        "coordinata_x_comune": "12.4964",
                        "coordinata_y_comune": "41.9028",
                        "coordinata_z_comune": "21",
                        "metodo": "1",
                    }
                ],
            },
            status_code=200,
        )

        security = models.Security(bearer="test-token")
        sdk = AnncsuCoordinate(security=security)

        response = sdk.json_post.gestionecoordinate(
            richiesta=models.Richiesta(
                accesso=models.Accesso(
                    codcom="H501",
                    progr_civico="00001",
                )
            )
        )

        assert len(response.dati) == 1
        dati = response.dati[0]
        assert dati.progr_civico == "00001"
        assert dati.numero == "42"
        assert dati.esponente == "A"
        assert dati.coordinata_x_comune == "12.4964"
        assert dati.coordinata_y_comune == "41.9028"
        assert dati.metodo == "1"

    def test_response_with_multiple_dati(self, httpx_mock: HTTPXMock):
        """Test response with multiple dati entries."""
        httpx_mock.add_response(
            method="POST",
            url=f"{BASE_URL}/gestionecoordinate",
            json={
                "idRichiesta": "REQ-MULTI",
                "esito": "OK",
                "messaggio": "Multipli accessi",
                "dati": [
                    {"progr_civico": "00001", "codcom": "H501"},
                    {"progr_civico": "00002", "codcom": "H501"},
                    {"progr_civico": "00003", "codcom": "H501"},
                ],
            },
            status_code=200,
        )

        security = models.Security(bearer="test-token")
        sdk = AnncsuCoordinate(security=security)

        response = sdk.json_post.gestionecoordinate(
            richiesta=models.Richiesta(
                accesso=models.Accesso(
                    codcom="H501",
                    progr_civico="00001",
                )
            )
        )

        assert len(response.dati) == 3

    def test_response_with_empty_dati(self, httpx_mock: HTTPXMock):
        """Test response with empty dati list."""
        httpx_mock.add_response(
            method="POST",
            url=f"{BASE_URL}/gestionecoordinate",
            json={
                "idRichiesta": "REQ-EMPTY",
                "esito": "OK",
                "messaggio": "Nessun dato",
                "dati": [],
            },
            status_code=200,
        )

        security = models.Security(bearer="test-token")
        sdk = AnncsuCoordinate(security=security)

        response = sdk.json_post.gestionecoordinate(
            richiesta=models.Richiesta(
                accesso=models.Accesso(
                    codcom="H501",
                    progr_civico="00001",
                )
            )
        )

        assert response.dati == []
