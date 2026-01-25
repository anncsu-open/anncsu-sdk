"""Integration tests for queryparam.py using pytest-httpx.

These tests mock HTTP responses at the httpx level to exercise
the full Speakeasy-generated code path including:
- Request building
- Query parameter serialization
- Response unmarshalling
- Error handling
"""

import pytest
from pytest_httpx import HTTPXMock

from anncsu.common import Security
from anncsu.pa import AnncsuConsultazione, errors

# Base URL for mocking
BASE_URL = "https://modipa.agenziaentrate.gov.it/govway/rest/in/AgenziaEntrate-PDND/anncsu-consultazione/v1"


class TestEsisteOdonimoGetQueryParam:
    """Tests for esiste_odonimo_get_query_param endpoint."""

    def test_esiste_odonimo_returns_true(self, httpx_mock: HTTPXMock):
        """Test successful response when odonimo exists."""
        httpx_mock.add_response(
            url=f"{BASE_URL}/esisteodonimo?codcom=H501&denom=VklBIFJPTUE%3D",
            json={"res": "OK", "data": True},
            status_code=200,
        )

        security = Security(bearer="test-token")
        sdk = AnncsuConsultazione(security=security)

        response = sdk.queryparam.esiste_odonimo_get_query_param(
            codcom="H501",
            denom="VklBIFJPTUE=",  # "VIA ROMA" base64 encoded
        )

        assert response.res == "OK"
        assert response.data is True

    def test_esiste_odonimo_returns_false(self, httpx_mock: HTTPXMock):
        """Test successful response when odonimo does not exist."""
        httpx_mock.add_response(
            url=f"{BASE_URL}/esisteodonimo?codcom=H501&denom=VklBIElORVNJU1RFTlRF",
            json={"res": "OK", "data": False},
            status_code=200,
        )

        security = Security(bearer="test-token")
        sdk = AnncsuConsultazione(security=security)

        response = sdk.queryparam.esiste_odonimo_get_query_param(
            codcom="H501",
            denom="VklBIElORVNJU1RFTlRF",  # "VIA INESISTENTE" base64 encoded
        )

        assert response.res == "OK"
        assert response.data is False

    def test_esiste_odonimo_bad_request(self, httpx_mock: HTTPXMock):
        """Test 400 Bad Request error handling."""
        httpx_mock.add_response(
            url=f"{BASE_URL}/esisteodonimo?codcom=INVALID&denom=dGVzdA%3D%3D",
            json={"title": "Bad Request", "detail": "Invalid codcom format"},
            status_code=400,
            headers={"Content-Type": "application/problem+json"},
        )

        security = Security(bearer="test-token")
        sdk = AnncsuConsultazione(security=security)

        with pytest.raises(
            errors.EsisteOdonimoGetQueryParamBadRequestError
        ) as exc_info:
            sdk.queryparam.esiste_odonimo_get_query_param(
                codcom="INVALID",
                denom="dGVzdA==",
            )

        assert exc_info.value.data.title == "Bad Request"
        assert exc_info.value.data.detail == "Invalid codcom format"

    def test_esiste_odonimo_unprocessable_entity(self, httpx_mock: HTTPXMock):
        """Test 422 Unprocessable Entity error handling."""
        httpx_mock.add_response(
            url=f"{BASE_URL}/esisteodonimo?codcom=H501&denom=not-base64",
            json={
                "title": "Unprocessable Entity",
                "detail": "denom must be base64 encoded",
            },
            status_code=422,
            headers={"Content-Type": "application/problem+json"},
        )

        security = Security(bearer="test-token")
        sdk = AnncsuConsultazione(security=security)

        with pytest.raises(
            errors.EsisteOdonimoGetQueryParamUnprocessableEntityError
        ) as exc_info:
            sdk.queryparam.esiste_odonimo_get_query_param(
                codcom="H501",
                denom="not-base64",
            )

        assert exc_info.value.data.title == "Unprocessable Entity"

    def test_esiste_odonimo_internal_server_error(self, httpx_mock: HTTPXMock):
        """Test 500 Internal Server Error handling."""
        httpx_mock.add_response(
            url=f"{BASE_URL}/esisteodonimo?codcom=H501&denom=dGVzdA%3D%3D",
            json={
                "title": "Internal Server Error",
                "detail": "Database unavailable",
            },
            status_code=500,
            headers={"Content-Type": "application/problem+json"},
        )

        security = Security(bearer="test-token")
        sdk = AnncsuConsultazione(security=security)

        with pytest.raises(
            errors.EsisteOdonimoGetQueryParamInternalServerError
        ) as exc_info:
            sdk.queryparam.esiste_odonimo_get_query_param(
                codcom="H501",
                denom="dGVzdA==",
            )

        assert exc_info.value.data.title == "Internal Server Error"

    def test_esiste_odonimo_with_authorization_header(self, httpx_mock: HTTPXMock):
        """Test that Authorization header is sent correctly."""
        httpx_mock.add_response(
            url=f"{BASE_URL}/esisteodonimo?codcom=H501&denom=VklBIFJPTUE%3D",
            json={"res": "OK", "data": True},
            status_code=200,
        )

        security = Security(bearer="my-pdnd-token")
        sdk = AnncsuConsultazione(security=security)

        response = sdk.queryparam.esiste_odonimo_get_query_param(
            codcom="H501",
            denom="VklBIFJPTUE=",
        )

        assert response.data is True

        # Verify the Authorization header was sent
        requests = httpx_mock.get_requests()
        assert len(requests) == 1
        assert "Authorization" in requests[0].headers
        assert requests[0].headers["Authorization"] == "Bearer my-pdnd-token"


class TestElencoOdonimiGetQueryParam:
    """Tests for elenco_odonimi_get_query_param endpoint."""

    def test_elenco_odonimi_returns_list(self, httpx_mock: HTTPXMock):
        """Test successful response with list of odonimi."""
        httpx_mock.add_response(
            url=f"{BASE_URL}/elencoodonimi?codcom=H501&denomparz=Uk9NQQ%3D%3D",
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

        response = sdk.queryparam.elenco_odonimi_get_query_param(
            codcom="H501",
            denomparz="Uk9NQQ==",  # "ROMA" base64 encoded
        )

        assert response.res == "OK"
        assert len(response.data) == 2
        assert response.data[0].dug == "VIA"
        assert response.data[0].denomuff == "ROMA"
        assert response.data[1].dug == "PIAZZA"

    def test_elenco_odonimi_empty_list(self, httpx_mock: HTTPXMock):
        """Test response with empty list when no odonimi found."""
        httpx_mock.add_response(
            url=f"{BASE_URL}/elencoodonimi?codcom=H501&denomparz=WFlaWg%3D%3D",
            json={"res": "OK", "data": []},
            status_code=200,
        )

        security = Security(bearer="test-token")
        sdk = AnncsuConsultazione(security=security)

        response = sdk.queryparam.elenco_odonimi_get_query_param(
            codcom="H501",
            denomparz="WFlaWg==",  # "XYZZ" base64 encoded
        )

        assert response.res == "OK"
        assert response.data == []

    def test_elenco_odonimi_bad_request(self, httpx_mock: HTTPXMock):
        """Test 400 Bad Request for elenco_odonimi."""
        httpx_mock.add_response(
            url=f"{BASE_URL}/elencoodonimi?codcom=BAD&denomparz=dGVzdA%3D%3D",
            json={"title": "Bad Request", "detail": "codcom not found"},
            status_code=400,
            headers={"Content-Type": "application/problem+json"},
        )

        security = Security(bearer="test-token")
        sdk = AnncsuConsultazione(security=security)

        with pytest.raises(errors.ElencoOdonimiGetQueryParamBadRequestError):
            sdk.queryparam.elenco_odonimi_get_query_param(
                codcom="BAD",
                denomparz="dGVzdA==",
            )


class TestElencoAccessiGetQueryParam:
    """Tests for elenco_accessi_get_query_param endpoint."""

    def test_elenco_accessi_returns_list(self, httpx_mock: HTTPXMock):
        """Test successful response with list of accessi."""
        httpx_mock.add_response(
            method="GET",
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

        response = sdk.queryparam.elenco_accessi_get_query_param(
            codcom="H501",
            denom="VklBIFJPTUE=",
            accparz="MQ==",  # "1" base64 encoded - partial access number
        )

        assert response.res == "OK"
        assert len(response.data) == 2
        assert response.data[0].civico == "1"
        assert response.data[1].esp == "A"


class TestEsisteAccessoGetQueryParam:
    """Tests for esiste_accesso_get_query_param endpoint."""

    def test_esiste_accesso_returns_true(self, httpx_mock: HTTPXMock):
        """Test successful response when accesso exists."""
        httpx_mock.add_response(
            method="GET",
            json={"res": "OK", "data": True},
            status_code=200,
        )

        security = Security(bearer="test-token")
        sdk = AnncsuConsultazione(security=security)

        response = sdk.queryparam.esiste_accesso_get_query_param(
            codcom="H501",
            denom="VklBIFJPTUE=",
            accesso="MQ==",  # "1" base64 encoded - access number
        )

        assert response.res == "OK"
        assert response.data is True


class TestCustomServerUrl:
    """Tests for custom server URL configuration."""

    def test_with_custom_server_url(self, httpx_mock: HTTPXMock):
        """Test SDK with custom server URL (e.g., validation environment)."""
        custom_url = "https://modipa-val.agenziaentrate.it/govway/rest/in/AgenziaEntrate-PDND/anncsu-consultazione/v1"

        httpx_mock.add_response(
            url=f"{custom_url}/esisteodonimo?codcom=H501&denom=VklBIFJPTUE%3D",
            json={"res": "OK", "data": True},
            status_code=200,
        )

        security = Security(bearer="test-token")
        sdk = AnncsuConsultazione(security=security, server_url=custom_url)

        response = sdk.queryparam.esiste_odonimo_get_query_param(
            codcom="H501",
            denom="VklBIFJPTUE=",
        )

        assert response.data is True


class TestWithoutSecurity:
    """Tests for SDK without security (should still work for request building)."""

    def test_request_without_security(self, httpx_mock: HTTPXMock):
        """Test that requests work without security (no Authorization header)."""
        httpx_mock.add_response(
            url=f"{BASE_URL}/esisteodonimo?codcom=H501&denom=VklBIFJPTUE%3D",
            json={"res": "OK", "data": True},
            status_code=200,
        )

        sdk = AnncsuConsultazione()  # No security

        response = sdk.queryparam.esiste_odonimo_get_query_param(
            codcom="H501",
            denom="VklBIFJPTUE=",
        )

        assert response.data is True

        # Verify no Authorization header was sent
        requests = httpx_mock.get_requests()
        assert len(requests) == 1
        auth_header = requests[0].headers.get("Authorization")
        assert auth_header is None or auth_header == ""


class TestQueryParamEncoding:
    """Tests for query parameter encoding."""

    def test_special_characters_in_denom(self, httpx_mock: HTTPXMock):
        """Test that special characters in base64 are properly URL encoded."""
        # Base64 with + and / characters
        base64_with_special = "VklBK1JPTUEvMQ=="

        httpx_mock.add_response(
            method="GET",
            json={"res": "OK", "data": True},
            status_code=200,
        )

        security = Security(bearer="test-token")
        sdk = AnncsuConsultazione(security=security)

        response = sdk.queryparam.esiste_odonimo_get_query_param(
            codcom="H501",
            denom=base64_with_special,
        )

        assert response.data is True

        # Verify the request was made
        requests = httpx_mock.get_requests()
        assert len(requests) == 1
        # Check that the URL contains the encoded parameter
        assert "denom=" in str(requests[0].url)


class TestTimeout:
    """Tests for timeout configuration."""

    def test_custom_timeout(self, httpx_mock: HTTPXMock):
        """Test SDK with custom timeout."""
        httpx_mock.add_response(
            url=f"{BASE_URL}/esisteodonimo?codcom=H501&denom=VklBIFJPTUE%3D",
            json={"res": "OK", "data": True},
            status_code=200,
        )

        security = Security(bearer="test-token")
        sdk = AnncsuConsultazione(security=security)

        response = sdk.queryparam.esiste_odonimo_get_query_param(
            codcom="H501",
            denom="VklBIFJPTUE=",
            timeout_ms=5000,
        )

        assert response.data is True


class TestGenericErrors:
    """Tests for generic error handling (4XX, 5XX)."""

    def test_404_not_found(self, httpx_mock: HTTPXMock):
        """Test 404 Not Found error handling."""
        httpx_mock.add_response(
            url=f"{BASE_URL}/esisteodonimo?codcom=H501&denom=VklBIFJPTUE%3D",
            text="Not Found",
            status_code=404,
        )

        security = Security(bearer="test-token")
        sdk = AnncsuConsultazione(security=security)

        with pytest.raises(errors.APIError) as exc_info:
            sdk.queryparam.esiste_odonimo_get_query_param(
                codcom="H501",
                denom="VklBIFJPTUE=",
            )

        assert "API error occurred" in str(exc_info.value)

    def test_503_service_unavailable(self, httpx_mock: HTTPXMock):
        """Test 503 Service Unavailable error handling."""
        httpx_mock.add_response(
            url=f"{BASE_URL}/esisteodonimo?codcom=H501&denom=VklBIFJPTUE%3D",
            text="Service Unavailable",
            status_code=503,
        )

        security = Security(bearer="test-token")
        sdk = AnncsuConsultazione(security=security)

        with pytest.raises(errors.APIError):
            sdk.queryparam.esiste_odonimo_get_query_param(
                codcom="H501",
                denom="VklBIFJPTUE=",
            )


class TestElencoodonimiprogGetQueryParam:
    """Tests for elencoodonimiprog_get_query_param endpoint."""

    def test_elencoodonimiprog_returns_list(self, httpx_mock: HTTPXMock):
        """Test successful response with list of odonimi with prognaz."""
        httpx_mock.add_response(
            method="GET",
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
                    {
                        "prognaz": "12345678901234567891",
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

        response = sdk.queryparam.elencoodonimiprog_get_query_param(
            codcom="H501",
            denomparz="Uk9NQQ==",
        )

        assert response.res == "OK"
        assert len(response.data) == 2
        assert response.data[0].prognaz == "12345678901234567890"
        assert response.data[0].dug == "VIA"

    def test_elencoodonimiprog_empty_list(self, httpx_mock: HTTPXMock):
        """Test response with empty list."""
        httpx_mock.add_response(
            method="GET",
            json={"res": "OK", "data": []},
            status_code=200,
        )

        security = Security(bearer="test-token")
        sdk = AnncsuConsultazione(security=security)

        response = sdk.queryparam.elencoodonimiprog_get_query_param(
            codcom="H501",
            denomparz="WFlaWg==",
        )

        assert response.res == "OK"
        assert response.data == []

    def test_elencoodonimiprog_bad_request(self, httpx_mock: HTTPXMock):
        """Test 400 Bad Request error handling."""
        httpx_mock.add_response(
            method="GET",
            json={"title": "Bad Request", "detail": "Invalid codcom"},
            status_code=400,
            headers={"Content-Type": "application/problem+json"},
        )

        security = Security(bearer="test-token")
        sdk = AnncsuConsultazione(security=security)

        with pytest.raises(errors.ElencoodonimiprogGetQueryParamBadRequestError):
            sdk.queryparam.elencoodonimiprog_get_query_param(
                codcom="INVALID",
                denomparz="dGVzdA==",
            )

    def test_elencoodonimiprog_internal_server_error(self, httpx_mock: HTTPXMock):
        """Test 500 Internal Server Error handling."""
        httpx_mock.add_response(
            method="GET",
            json={"title": "Internal Server Error", "detail": "Database error"},
            status_code=500,
            headers={"Content-Type": "application/problem+json"},
        )

        security = Security(bearer="test-token")
        sdk = AnncsuConsultazione(security=security)

        with pytest.raises(errors.ElencoodonimiprogGetQueryParamInternalServerError):
            sdk.queryparam.elencoodonimiprog_get_query_param(
                codcom="H501",
                denomparz="dGVzdA==",
            )


class TestElencoaccessiprogGetQueryParam:
    """Tests for elencoaccessiprog_get_query_param endpoint."""

    def test_elencoaccessiprog_returns_list(self, httpx_mock: HTTPXMock):
        """Test successful response with list of accessi with prognaz."""
        httpx_mock.add_response(
            method="GET",
            json={
                "res": "OK",
                "data": [
                    {
                        "prognazacc": "12345678901234567890123456",
                        "civico": "1",
                        "esp": None,
                        "specif": None,
                        "metrico": None,
                        "coordX": "12.4964",
                        "coordY": "41.9028",
                        "quota": "21",
                        "metodo": "1",
                    },
                    {
                        "prognazacc": "12345678901234567890123457",
                        "civico": "2",
                        "esp": "A",
                        "specif": None,
                        "metrico": None,
                        "coordX": "12.4965",
                        "coordY": "41.9029",
                        "quota": "22",
                        "metodo": "1",
                    },
                ],
            },
            status_code=200,
        )

        security = Security(bearer="test-token")
        sdk = AnncsuConsultazione(security=security)

        response = sdk.queryparam.elencoaccessiprog_get_query_param(
            prognaz="12345678901234567890",
            accparz="MQ==",
        )

        assert response.res == "OK"
        assert len(response.data) == 2
        assert response.data[0].prognazacc == "12345678901234567890123456"
        assert response.data[0].civico == "1"
        assert response.data[0].coord_x == "12.4964"

    def test_elencoaccessiprog_empty_list(self, httpx_mock: HTTPXMock):
        """Test response with empty list."""
        httpx_mock.add_response(
            method="GET",
            json={"res": "OK", "data": []},
            status_code=200,
        )

        security = Security(bearer="test-token")
        sdk = AnncsuConsultazione(security=security)

        response = sdk.queryparam.elencoaccessiprog_get_query_param(
            prognaz="12345678901234567890",
            accparz="OTk5OQ==",
        )

        assert response.res == "OK"
        assert response.data == []

    def test_elencoaccessiprog_bad_request(self, httpx_mock: HTTPXMock):
        """Test 400 Bad Request error handling."""
        httpx_mock.add_response(
            method="GET",
            json={"title": "Bad Request", "detail": "Invalid prognaz"},
            status_code=400,
            headers={"Content-Type": "application/problem+json"},
        )

        security = Security(bearer="test-token")
        sdk = AnncsuConsultazione(security=security)

        with pytest.raises(errors.ElencoaccessiprogGetQueryParamBadRequestError):
            sdk.queryparam.elencoaccessiprog_get_query_param(
                prognaz="INVALID",
                accparz="MQ==",
            )

    def test_elencoaccessiprog_internal_server_error(self, httpx_mock: HTTPXMock):
        """Test 500 Internal Server Error handling."""
        httpx_mock.add_response(
            method="GET",
            json={"title": "Internal Server Error", "detail": "Database error"},
            status_code=500,
            headers={"Content-Type": "application/problem+json"},
        )

        security = Security(bearer="test-token")
        sdk = AnncsuConsultazione(security=security)

        with pytest.raises(errors.ElencoaccessiprogGetQueryParamInternalServerError):
            sdk.queryparam.elencoaccessiprog_get_query_param(
                prognaz="12345678901234567890",
                accparz="MQ==",
            )


class TestPrognazareaGetQueryParam:
    """Tests for prognazarea_get_query_param endpoint."""

    def test_prognazarea_returns_list(self, httpx_mock: HTTPXMock):
        """Test successful response with odonimo data by prognaz."""
        httpx_mock.add_response(
            method="GET",
            json={
                "res": "OK",
                "data": [
                    {
                        "prognaz": "12345678901234567890",
                        "dug": "VIA",
                        "denomuff": "ROMA",
                        "denomloc": "ROMA CAPITALE",
                        "denomlingua1": None,
                        "denomlingua2": None,
                    }
                ],
            },
            status_code=200,
        )

        security = Security(bearer="test-token")
        sdk = AnncsuConsultazione(security=security)

        response = sdk.queryparam.prognazarea_get_query_param(
            prognaz="12345678901234567890",
        )

        assert response.res == "OK"
        assert len(response.data) == 1
        assert response.data[0].prognaz == "12345678901234567890"
        assert response.data[0].dug == "VIA"
        assert response.data[0].denomuff == "ROMA"

    def test_prognazarea_empty_list(self, httpx_mock: HTTPXMock):
        """Test response with empty list when prognaz not found."""
        httpx_mock.add_response(
            method="GET",
            json={"res": "OK", "data": []},
            status_code=200,
        )

        security = Security(bearer="test-token")
        sdk = AnncsuConsultazione(security=security)

        response = sdk.queryparam.prognazarea_get_query_param(
            prognaz="99999999999999999999",
        )

        assert response.res == "OK"
        assert response.data == []

    def test_prognazarea_bad_request(self, httpx_mock: HTTPXMock):
        """Test 400 Bad Request error handling."""
        httpx_mock.add_response(
            method="GET",
            json={"title": "Bad Request", "detail": "Invalid prognaz format"},
            status_code=400,
            headers={"Content-Type": "application/problem+json"},
        )

        security = Security(bearer="test-token")
        sdk = AnncsuConsultazione(security=security)

        with pytest.raises(errors.PrognazareaGetQueryParamBadRequestError):
            sdk.queryparam.prognazarea_get_query_param(
                prognaz="INVALID",
            )

    def test_prognazarea_internal_server_error(self, httpx_mock: HTTPXMock):
        """Test 500 Internal Server Error handling."""
        httpx_mock.add_response(
            method="GET",
            json={"title": "Internal Server Error", "detail": "Database error"},
            status_code=500,
            headers={"Content-Type": "application/problem+json"},
        )

        security = Security(bearer="test-token")
        sdk = AnncsuConsultazione(security=security)

        with pytest.raises(errors.PrognazareaGetQueryParamInternalServerError):
            sdk.queryparam.prognazarea_get_query_param(
                prognaz="12345678901234567890",
            )


class TestPrognazaccGetQueryParam:
    """Tests for prognazacc_get_query_param endpoint."""

    def test_prognazacc_returns_data(self, httpx_mock: HTTPXMock):
        """Test successful response with full accesso data."""
        httpx_mock.add_response(
            method="GET",
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
                        "prognazacc": "12345678901234567890123456",
                        "civico": "42",
                        "esp": "A",
                        "specif": None,
                        "metrico": None,
                        "coordX": "12.4964",
                        "coordY": "41.9028",
                        "quota": "21",
                        "metodo": "1",
                    }
                ],
            },
            status_code=200,
        )

        security = Security(bearer="test-token")
        sdk = AnncsuConsultazione(security=security)

        response = sdk.queryparam.prognazacc_get_query_param(
            prognazacc="12345678901234567890123456",
        )

        assert response.res == "OK"
        assert len(response.data) == 1
        assert response.data[0].prognaz == "12345678901234567890"
        assert response.data[0].prognazacc == "12345678901234567890123456"
        assert response.data[0].civico == "42"
        assert response.data[0].esp == "A"
        assert response.data[0].coord_x == "12.4964"
        assert response.data[0].coord_y == "41.9028"

    def test_prognazacc_empty_list(self, httpx_mock: HTTPXMock):
        """Test response with empty list when prognazacc not found."""
        httpx_mock.add_response(
            method="GET",
            json={"res": "OK", "data": []},
            status_code=200,
        )

        security = Security(bearer="test-token")
        sdk = AnncsuConsultazione(security=security)

        response = sdk.queryparam.prognazacc_get_query_param(
            prognazacc="99999999999999999999999999",
        )

        assert response.res == "OK"
        assert response.data == []

    def test_prognazacc_bad_request(self, httpx_mock: HTTPXMock):
        """Test 400 Bad Request error handling."""
        httpx_mock.add_response(
            method="GET",
            json={
                "title": "Bad Request",
                "detail": "Invalid prognazacc format",
            },
            status_code=400,
            headers={"Content-Type": "application/problem+json"},
        )

        security = Security(bearer="test-token")
        sdk = AnncsuConsultazione(security=security)

        with pytest.raises(errors.PrognazaccGetQueryParamBadRequestError):
            sdk.queryparam.prognazacc_get_query_param(
                prognazacc="INVALID",
            )

    def test_prognazacc_internal_server_error(self, httpx_mock: HTTPXMock):
        """Test 500 Internal Server Error handling."""
        httpx_mock.add_response(
            method="GET",
            json={"title": "Internal Server Error", "detail": "Database error"},
            status_code=500,
            headers={"Content-Type": "application/problem+json"},
        )

        security = Security(bearer="test-token")
        sdk = AnncsuConsultazione(security=security)

        with pytest.raises(errors.PrognazaccGetQueryParamInternalServerError):
            sdk.queryparam.prognazacc_get_query_param(
                prognazacc="12345678901234567890123456",
            )
