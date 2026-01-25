"""Integration tests for jsonpost.py using pytest-httpx.

These tests mock HTTP responses at the httpx level to exercise
the full Speakeasy-generated code path for JSON POST endpoints.
"""

import pytest
from pytest_httpx import HTTPXMock

from anncsu.common import Security
from anncsu.pa import AnncsuConsultazione, errors

# Base URL for mocking
BASE_URL = "https://modipa.agenziaentrate.gov.it/govway/rest/in/AgenziaEntrate-PDND/anncsu-consultazione/v1"


class TestEsisteOdonimoPost:
    """Tests for esiste_odonimo_post endpoint."""

    def test_esiste_odonimo_returns_true(self, httpx_mock: HTTPXMock):
        """Test successful response when odonimo exists."""
        httpx_mock.add_response(
            method="POST",
            url=f"{BASE_URL}/esisteodonimo",
            json={"res": "OK", "data": True},
            status_code=200,
        )

        security = Security(bearer="test-token")
        sdk = AnncsuConsultazione(security=security)

        response = sdk.json_post.esiste_odonimo_post(
            codcom="H501",
            denom="VklBIFJPTUE=",
        )

        assert response.res == "OK"
        assert response.data is True

    def test_esiste_odonimo_returns_false(self, httpx_mock: HTTPXMock):
        """Test successful response when odonimo does not exist."""
        httpx_mock.add_response(
            method="POST",
            url=f"{BASE_URL}/esisteodonimo",
            json={"res": "OK", "data": False},
            status_code=200,
        )

        security = Security(bearer="test-token")
        sdk = AnncsuConsultazione(security=security)

        response = sdk.json_post.esiste_odonimo_post(
            codcom="H501",
            denom="VklBIElORVNJU1RFTlRF",
        )

        assert response.res == "OK"
        assert response.data is False

    def test_esiste_odonimo_bad_request(self, httpx_mock: HTTPXMock):
        """Test 400 Bad Request error handling."""
        httpx_mock.add_response(
            method="POST",
            url=f"{BASE_URL}/esisteodonimo",
            json={"title": "Bad Request", "detail": "Invalid codcom format"},
            status_code=400,
            headers={"Content-Type": "application/problem+json"},
        )

        security = Security(bearer="test-token")
        sdk = AnncsuConsultazione(security=security)

        with pytest.raises(errors.EsisteOdonimoPostBadRequestError) as exc_info:
            sdk.json_post.esiste_odonimo_post(
                codcom="INVALID",
                denom="dGVzdA==",
            )

        assert exc_info.value.data.title == "Bad Request"

    def test_esiste_odonimo_internal_server_error(self, httpx_mock: HTTPXMock):
        """Test 500 Internal Server Error handling."""
        httpx_mock.add_response(
            method="POST",
            url=f"{BASE_URL}/esisteodonimo",
            json={
                "title": "Internal Server Error",
                "detail": "Database unavailable",
            },
            status_code=500,
            headers={"Content-Type": "application/problem+json"},
        )

        security = Security(bearer="test-token")
        sdk = AnncsuConsultazione(security=security)

        with pytest.raises(errors.EsisteOdonimoPostInternalServerError):
            sdk.json_post.esiste_odonimo_post(
                codcom="H501",
                denom="dGVzdA==",
            )

    def test_esiste_odonimo_with_authorization_header(self, httpx_mock: HTTPXMock):
        """Test that Authorization header is sent correctly."""
        httpx_mock.add_response(
            method="POST",
            url=f"{BASE_URL}/esisteodonimo",
            json={"res": "OK", "data": True},
            status_code=200,
        )

        security = Security(bearer="my-pdnd-token")
        sdk = AnncsuConsultazione(security=security)

        response = sdk.json_post.esiste_odonimo_post(
            codcom="H501",
            denom="VklBIFJPTUE=",
        )

        assert response.data is True

        # Verify the Authorization header was sent
        requests = httpx_mock.get_requests()
        assert len(requests) == 1
        assert "Authorization" in requests[0].headers
        assert requests[0].headers["Authorization"] == "Bearer my-pdnd-token"

    def test_esiste_odonimo_request_body(self, httpx_mock: HTTPXMock):
        """Test that request body is sent correctly."""
        httpx_mock.add_response(
            method="POST",
            url=f"{BASE_URL}/esisteodonimo",
            json={"res": "OK", "data": True},
            status_code=200,
        )

        security = Security(bearer="test-token")
        sdk = AnncsuConsultazione(security=security)

        sdk.json_post.esiste_odonimo_post(
            codcom="H501",
            denom="VklBIFJPTUE=",
        )

        # Verify request body
        requests = httpx_mock.get_requests()
        assert len(requests) == 1
        assert requests[0].method == "POST"
        # Body should be JSON
        assert "application/json" in requests[0].headers.get("Content-Type", "")


class TestEsisteAccessoPost:
    """Tests for esiste_accesso_post endpoint."""

    def test_esiste_accesso_returns_true(self, httpx_mock: HTTPXMock):
        """Test successful response when accesso exists."""
        httpx_mock.add_response(
            method="POST",
            url=f"{BASE_URL}/esisteaccesso",
            json={"res": "OK", "data": True},
            status_code=200,
        )

        security = Security(bearer="test-token")
        sdk = AnncsuConsultazione(security=security)

        response = sdk.json_post.esiste_accesso_post(
            codcom="H501",
            denom="VklBIFJPTUE=",
            accesso="MQ==",
        )

        assert response.res == "OK"
        assert response.data is True

    def test_esiste_accesso_returns_false(self, httpx_mock: HTTPXMock):
        """Test successful response when accesso does not exist."""
        httpx_mock.add_response(
            method="POST",
            url=f"{BASE_URL}/esisteaccesso",
            json={"res": "OK", "data": False},
            status_code=200,
        )

        security = Security(bearer="test-token")
        sdk = AnncsuConsultazione(security=security)

        response = sdk.json_post.esiste_accesso_post(
            codcom="H501",
            denom="VklBIFJPTUE=",
            accesso="OTk5",
        )

        assert response.data is False


class TestElencoOdonimiPost:
    """Tests for elenco_odonimi_post endpoint."""

    def test_elenco_odonimi_returns_list(self, httpx_mock: HTTPXMock):
        """Test successful response with list of odonimi."""
        httpx_mock.add_response(
            method="POST",
            url=f"{BASE_URL}/elencoodonimi",
            json={
                "res": "OK",
                "data": [
                    {
                        "dug": "VIA",
                        "denomuff": "ROMA",
                        "denomloc": None,
                        "denomlingua1": None,
                        "denomlingua2": None,
                    },
                    {
                        "dug": "PIAZZA",
                        "denomuff": "ROMA",
                        "denomloc": None,
                        "denomlingua1": None,
                        "denomlingua2": None,
                    },
                ],
            },
            status_code=200,
        )

        security = Security(bearer="test-token")
        sdk = AnncsuConsultazione(security=security)

        response = sdk.json_post.elenco_odonimi_post(
            codcom="H501",
            denomparz="Uk9NQQ==",
        )

        assert response.res == "OK"
        assert len(response.data) == 2
        assert response.data[0].dug == "VIA"
        assert response.data[1].dug == "PIAZZA"

    def test_elenco_odonimi_empty_list(self, httpx_mock: HTTPXMock):
        """Test response with empty list."""
        httpx_mock.add_response(
            method="POST",
            url=f"{BASE_URL}/elencoodonimi",
            json={"res": "OK", "data": []},
            status_code=200,
        )

        security = Security(bearer="test-token")
        sdk = AnncsuConsultazione(security=security)

        response = sdk.json_post.elenco_odonimi_post(
            codcom="H501",
            denomparz="WFlaWg==",
        )

        assert response.data == []


class TestElencoAccessiPost:
    """Tests for elenco_accessi_post endpoint."""

    def test_elenco_accessi_returns_list(self, httpx_mock: HTTPXMock):
        """Test successful response with list of accessi."""
        httpx_mock.add_response(
            method="POST",
            url=f"{BASE_URL}/elencoaccessi",
            json={
                "res": "OK",
                "data": [
                    {
                        "civico": "1",
                        "esp": None,
                        "specif": None,
                        "metrico": None,
                    },
                    {
                        "civico": "2",
                        "esp": "A",
                        "specif": None,
                        "metrico": None,
                    },
                ],
            },
            status_code=200,
        )

        security = Security(bearer="test-token")
        sdk = AnncsuConsultazione(security=security)

        response = sdk.json_post.elenco_accessi_post(
            codcom="H501",
            denom="VklBIFJPTUE=",
            accparz="MQ==",
        )

        assert response.res == "OK"
        assert len(response.data) == 2
        assert response.data[0].civico == "1"


class TestElencoOdonimiProgPost:
    """Tests for elencoodonimiprog_post endpoint."""

    def test_elencoodonimiprog_returns_list(self, httpx_mock: HTTPXMock):
        """Test successful response with progressive list of odonimi."""
        httpx_mock.add_response(
            method="POST",
            url=f"{BASE_URL}/elencoodonimiprog",
            json={
                "res": "OK",
                "data": [
                    {
                        "prognaz": "12345678901234567890",
                        "dug": "VIA",
                        "denomuff": "ROMA",
                        "denomloc": None,
                        "denomlingua1": None,
                        "denomlingua2": None,
                    },
                ],
            },
            status_code=200,
        )

        security = Security(bearer="test-token")
        sdk = AnncsuConsultazione(security=security)

        response = sdk.json_post.elencoodonimiprog_post(
            codcom="H501",
            denomparz="Uk9NQQ==",
        )

        assert response.res == "OK"
        assert len(response.data) == 1
        assert response.data[0].prognaz == "12345678901234567890"
        assert response.data[0].dug == "VIA"

    def test_elencoodonimiprog_empty_list(self, httpx_mock: HTTPXMock):
        """Test response with empty list."""
        httpx_mock.add_response(
            method="POST",
            url=f"{BASE_URL}/elencoodonimiprog",
            json={"res": "OK", "data": []},
            status_code=200,
        )

        security = Security(bearer="test-token")
        sdk = AnncsuConsultazione(security=security)

        response = sdk.json_post.elencoodonimiprog_post(
            codcom="H501",
            denomparz="WFlaWg==",
        )

        assert response.res == "OK"
        assert response.data == []

    def test_elencoodonimiprog_bad_request(self, httpx_mock: HTTPXMock):
        """Test 400 Bad Request error handling."""
        httpx_mock.add_response(
            method="POST",
            url=f"{BASE_URL}/elencoodonimiprog",
            json={"title": "Bad Request", "detail": "Invalid codcom format"},
            status_code=400,
            headers={"Content-Type": "application/problem+json"},
        )

        security = Security(bearer="test-token")
        sdk = AnncsuConsultazione(security=security)

        with pytest.raises(errors.ElencoodonimiprogPostBadRequestError) as exc_info:
            sdk.json_post.elencoodonimiprog_post(
                codcom="INVALID",
                denomparz="dGVzdA==",
            )

        assert exc_info.value.data.title == "Bad Request"

    def test_elencoodonimiprog_internal_server_error(self, httpx_mock: HTTPXMock):
        """Test 500 Internal Server Error handling."""
        httpx_mock.add_response(
            method="POST",
            url=f"{BASE_URL}/elencoodonimiprog",
            json={
                "title": "Internal Server Error",
                "detail": "Database unavailable",
            },
            status_code=500,
            headers={"Content-Type": "application/problem+json"},
        )

        security = Security(bearer="test-token")
        sdk = AnncsuConsultazione(security=security)

        with pytest.raises(errors.ElencoodonimiprogPostInternalServerError):
            sdk.json_post.elencoodonimiprog_post(
                codcom="H501",
                denomparz="dGVzdA==",
            )


class TestElencoAccessiProgPost:
    """Tests for elencoaccessiprog_post endpoint."""

    def test_elencoaccessiprog_returns_list(self, httpx_mock: HTTPXMock):
        """Test successful response with progressive list of accessi."""
        httpx_mock.add_response(
            method="POST",
            url=f"{BASE_URL}/elencoaccessiprog",
            json={
                "res": "OK",
                "data": [
                    {
                        "prognazacc": "12345678901234567890",
                        "civico": "1",
                        "esp": "A",
                        "specif": None,
                        "metrico": None,
                        "coordX": "12.4964",
                        "coordY": "41.9028",
                        "quota": "10",
                        "metodo": "GPS",
                    },
                ],
            },
            status_code=200,
        )

        security = Security(bearer="test-token")
        sdk = AnncsuConsultazione(security=security)

        response = sdk.json_post.elencoaccessiprog_post(
            prognaz="12345678901234567890",
            accparz="MQ==",
        )

        assert response.res == "OK"
        assert len(response.data) == 1
        assert response.data[0].prognazacc == "12345678901234567890"
        assert response.data[0].coord_x == "12.4964"

    def test_elencoaccessiprog_empty_list(self, httpx_mock: HTTPXMock):
        """Test response with empty list."""
        httpx_mock.add_response(
            method="POST",
            url=f"{BASE_URL}/elencoaccessiprog",
            json={"res": "OK", "data": []},
            status_code=200,
        )

        security = Security(bearer="test-token")
        sdk = AnncsuConsultazione(security=security)

        response = sdk.json_post.elencoaccessiprog_post(
            prognaz="00000000000000000000",
            accparz="OTk5",
        )

        assert response.res == "OK"
        assert response.data == []

    def test_elencoaccessiprog_bad_request(self, httpx_mock: HTTPXMock):
        """Test 400 Bad Request error handling."""
        httpx_mock.add_response(
            method="POST",
            url=f"{BASE_URL}/elencoaccessiprog",
            json={"title": "Bad Request", "detail": "Invalid prognaz format"},
            status_code=400,
            headers={"Content-Type": "application/problem+json"},
        )

        security = Security(bearer="test-token")
        sdk = AnncsuConsultazione(security=security)

        with pytest.raises(errors.ElencoaccessiprogPostBadRequestError) as exc_info:
            sdk.json_post.elencoaccessiprog_post(
                prognaz="INVALID",
                accparz="dGVzdA==",
            )

        assert exc_info.value.data.title == "Bad Request"

    def test_elencoaccessiprog_internal_server_error(self, httpx_mock: HTTPXMock):
        """Test 500 Internal Server Error handling."""
        httpx_mock.add_response(
            method="POST",
            url=f"{BASE_URL}/elencoaccessiprog",
            json={
                "title": "Internal Server Error",
                "detail": "Database unavailable",
            },
            status_code=500,
            headers={"Content-Type": "application/problem+json"},
        )

        security = Security(bearer="test-token")
        sdk = AnncsuConsultazione(security=security)

        with pytest.raises(errors.ElencoaccessiprogPostInternalServerError):
            sdk.json_post.elencoaccessiprog_post(
                prognaz="12345678901234567890",
                accparz="dGVzdA==",
            )


class TestPrognazareaPost:
    """Tests for prognazarea_post endpoint."""

    def test_prognazarea_returns_data(self, httpx_mock: HTTPXMock):
        """Test successful response with area data."""
        httpx_mock.add_response(
            method="POST",
            url=f"{BASE_URL}/prognazarea",
            json={
                "res": "OK",
                "data": [
                    {
                        "prognaz": "12345678901234567890",
                        "dug": "VIA",
                        "denomuff": "ROMA",
                        "denomloc": None,
                        "denomlingua1": None,
                        "denomlingua2": None,
                    },
                ],
            },
            status_code=200,
        )

        security = Security(bearer="test-token")
        sdk = AnncsuConsultazione(security=security)

        response = sdk.json_post.prognazarea_post(
            prognaz="12345678901234567890",
        )

        assert response.res == "OK"
        assert len(response.data) == 1
        assert response.data[0].prognaz == "12345678901234567890"

    def test_prognazarea_empty_list(self, httpx_mock: HTTPXMock):
        """Test response with empty list."""
        httpx_mock.add_response(
            method="POST",
            url=f"{BASE_URL}/prognazarea",
            json={"res": "OK", "data": []},
            status_code=200,
        )

        security = Security(bearer="test-token")
        sdk = AnncsuConsultazione(security=security)

        response = sdk.json_post.prognazarea_post(
            prognaz="00000000000000000000",
        )

        assert response.res == "OK"
        assert response.data == []

    def test_prognazarea_bad_request(self, httpx_mock: HTTPXMock):
        """Test 400 Bad Request error handling."""
        httpx_mock.add_response(
            method="POST",
            url=f"{BASE_URL}/prognazarea",
            json={"title": "Bad Request", "detail": "Invalid prognaz format"},
            status_code=400,
            headers={"Content-Type": "application/problem+json"},
        )

        security = Security(bearer="test-token")
        sdk = AnncsuConsultazione(security=security)

        with pytest.raises(errors.PrognazareaPostBadRequestError) as exc_info:
            sdk.json_post.prognazarea_post(
                prognaz="INVALID",
            )

        assert exc_info.value.data.title == "Bad Request"

    def test_prognazarea_internal_server_error(self, httpx_mock: HTTPXMock):
        """Test 500 Internal Server Error handling."""
        httpx_mock.add_response(
            method="POST",
            url=f"{BASE_URL}/prognazarea",
            json={
                "title": "Internal Server Error",
                "detail": "Database unavailable",
            },
            status_code=500,
            headers={"Content-Type": "application/problem+json"},
        )

        security = Security(bearer="test-token")
        sdk = AnncsuConsultazione(security=security)

        with pytest.raises(errors.PrognazareaPostInternalServerError):
            sdk.json_post.prognazarea_post(
                prognaz="12345678901234567890",
            )


class TestPrognazaccPost:
    """Tests for prognazacc_post endpoint."""

    def test_prognazacc_returns_data(self, httpx_mock: HTTPXMock):
        """Test successful response with access data."""
        httpx_mock.add_response(
            method="POST",
            url=f"{BASE_URL}/prognazacc",
            json={
                "res": "OK",
                "data": [
                    {
                        "prognaz": "12345678901234567890",
                        "dug": "VIA",
                        "denomuff": "ROMA",
                        "denomloc": None,
                        "denomlingua1": None,
                        "denomlingua2": None,
                        "prognazacc": "12345678901234567891",
                        "civico": "1",
                        "esp": "A",
                        "specif": None,
                        "metrico": None,
                        "coordX": "12.4964",
                        "coordY": "41.9028",
                        "quota": "10",
                        "metodo": "GPS",
                    },
                ],
            },
            status_code=200,
        )

        security = Security(bearer="test-token")
        sdk = AnncsuConsultazione(security=security)

        response = sdk.json_post.prognazacc_post(
            prognazacc="12345678901234567891",
        )

        assert response.res == "OK"
        assert len(response.data) == 1
        assert response.data[0].prognazacc == "12345678901234567891"
        assert response.data[0].coord_x == "12.4964"

    def test_prognazacc_empty_list(self, httpx_mock: HTTPXMock):
        """Test response with empty list."""
        httpx_mock.add_response(
            method="POST",
            url=f"{BASE_URL}/prognazacc",
            json={"res": "OK", "data": []},
            status_code=200,
        )

        security = Security(bearer="test-token")
        sdk = AnncsuConsultazione(security=security)

        response = sdk.json_post.prognazacc_post(
            prognazacc="00000000000000000000",
        )

        assert response.res == "OK"
        assert response.data == []

    def test_prognazacc_bad_request(self, httpx_mock: HTTPXMock):
        """Test 400 Bad Request error handling."""
        httpx_mock.add_response(
            method="POST",
            url=f"{BASE_URL}/prognazacc",
            json={
                "title": "Bad Request",
                "detail": "Invalid prognazacc format",
            },
            status_code=400,
            headers={"Content-Type": "application/problem+json"},
        )

        security = Security(bearer="test-token")
        sdk = AnncsuConsultazione(security=security)

        with pytest.raises(errors.PrognazaccPostBadRequestError) as exc_info:
            sdk.json_post.prognazacc_post(
                prognazacc="INVALID",
            )

        assert exc_info.value.data.title == "Bad Request"

    def test_prognazacc_internal_server_error(self, httpx_mock: HTTPXMock):
        """Test 500 Internal Server Error handling."""
        httpx_mock.add_response(
            method="POST",
            url=f"{BASE_URL}/prognazacc",
            json={
                "title": "Internal Server Error",
                "detail": "Database unavailable",
            },
            status_code=500,
            headers={"Content-Type": "application/problem+json"},
        )

        security = Security(bearer="test-token")
        sdk = AnncsuConsultazione(security=security)

        with pytest.raises(errors.PrognazaccPostInternalServerError):
            sdk.json_post.prognazacc_post(
                prognazacc="12345678901234567891",
            )


class TestJsonPostErrorHandling:
    """Tests for error handling in JSON POST endpoints."""

    def test_404_not_found(self, httpx_mock: HTTPXMock):
        """Test 404 Not Found error handling."""
        httpx_mock.add_response(
            method="POST",
            url=f"{BASE_URL}/esisteodonimo",
            text="Not Found",
            status_code=404,
        )

        security = Security(bearer="test-token")
        sdk = AnncsuConsultazione(security=security)

        with pytest.raises(errors.APIError):
            sdk.json_post.esiste_odonimo_post(
                codcom="H501",
                denom="VklBIFJPTUE=",
            )

    def test_503_service_unavailable(self, httpx_mock: HTTPXMock):
        """Test 503 Service Unavailable error handling."""
        httpx_mock.add_response(
            method="POST",
            url=f"{BASE_URL}/esisteodonimo",
            text="Service Unavailable",
            status_code=503,
        )

        security = Security(bearer="test-token")
        sdk = AnncsuConsultazione(security=security)

        with pytest.raises(errors.APIError):
            sdk.json_post.esiste_odonimo_post(
                codcom="H501",
                denom="VklBIFJPTUE=",
            )


class TestJsonPostWithCustomServerUrl:
    """Tests for custom server URL with JSON POST."""

    def test_with_validation_environment(self, httpx_mock: HTTPXMock):
        """Test SDK with validation environment URL."""
        custom_url = "https://modipa-val.agenziaentrate.it/govway/rest/in/AgenziaEntrate-PDND/anncsu-consultazione/v1"

        httpx_mock.add_response(
            method="POST",
            url=f"{custom_url}/esisteodonimo",
            json={"res": "OK", "data": True},
            status_code=200,
        )

        security = Security(bearer="test-token")
        sdk = AnncsuConsultazione(security=security, server_url=custom_url)

        response = sdk.json_post.esiste_odonimo_post(
            codcom="H501",
            denom="VklBIFJPTUE=",
        )

        assert response.data is True


class TestJsonPostWithoutSecurity:
    """Tests for JSON POST without security configuration."""

    def test_request_without_security(self, httpx_mock: HTTPXMock):
        """Test that POST requests work without security."""
        httpx_mock.add_response(
            method="POST",
            url=f"{BASE_URL}/esisteodonimo",
            json={"res": "OK", "data": True},
            status_code=200,
        )

        sdk = AnncsuConsultazione()  # No security

        response = sdk.json_post.esiste_odonimo_post(
            codcom="H501",
            denom="VklBIFJPTUE=",
        )

        assert response.data is True

        # Verify no Authorization header was sent
        requests = httpx_mock.get_requests()
        auth_header = requests[0].headers.get("Authorization")
        assert auth_header is None or auth_header == ""
