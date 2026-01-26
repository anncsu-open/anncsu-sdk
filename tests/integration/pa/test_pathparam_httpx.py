"""Integration tests for pathparam.py using pytest-httpx.

These tests mock HTTP responses at the httpx level to exercise
the full Speakeasy-generated code path for path parameter endpoints.
"""

import pytest
from pytest_httpx import HTTPXMock

from anncsu.common import Security
from anncsu.pa import AnncsuConsultazione, errors

# Base URL for mocking
BASE_URL = "https://modipa.agenziaentrate.gov.it/govway/rest/in/AgenziaEntrate-PDND/anncsu-consultazione/v1"


class TestEsisteOdonimoGetPathParam:
    """Tests for esiste_odonimo_get_path_param endpoint."""

    def test_esiste_odonimo_returns_true(self, httpx_mock: HTTPXMock):
        """Test successful response when odonimo exists."""
        httpx_mock.add_response(
            url=f"{BASE_URL}/esisteodonimo/H501/VklBIFJPTUE=",
            json={"res": "OK", "data": True},
            status_code=200,
        )

        security = Security(bearer="test-token")
        sdk = AnncsuConsultazione(security=security)

        response = sdk.pathparam.esiste_odonimo_get_path_param(
            codcom="H501",
            denom="VklBIFJPTUE=",
        )

        assert response.res == "OK"
        assert response.data is True

    def test_esiste_odonimo_returns_false(self, httpx_mock: HTTPXMock):
        """Test successful response when odonimo does not exist."""
        httpx_mock.add_response(
            method="GET",
            json={"res": "OK", "data": False},
            status_code=200,
        )

        security = Security(bearer="test-token")
        sdk = AnncsuConsultazione(security=security)

        response = sdk.pathparam.esiste_odonimo_get_path_param(
            codcom="H501",
            denom="VklBIElORVNJU1RFTlRF",
        )

        assert response.res == "OK"
        assert response.data is False

    def test_esiste_odonimo_bad_request(self, httpx_mock: HTTPXMock):
        """Test 400 Bad Request error handling."""
        httpx_mock.add_response(
            method="GET",
            json={"title": "Bad Request", "detail": "Invalid codcom format"},
            status_code=400,
            headers={"Content-Type": "application/problem+json"},
        )

        security = Security(bearer="test-token")
        sdk = AnncsuConsultazione(security=security)

        with pytest.raises(errors.EsisteOdonimoGetPathParamBadRequestError) as exc_info:
            sdk.pathparam.esiste_odonimo_get_path_param(
                codcom="INVALID",
                denom="dGVzdA==",
            )

        assert exc_info.value.data.title == "Bad Request"

    def test_esiste_odonimo_internal_server_error(self, httpx_mock: HTTPXMock):
        """Test 500 Internal Server Error handling."""
        httpx_mock.add_response(
            method="GET",
            json={
                "title": "Internal Server Error",
                "detail": "Database unavailable",
            },
            status_code=500,
            headers={"Content-Type": "application/problem+json"},
        )

        security = Security(bearer="test-token")
        sdk = AnncsuConsultazione(security=security)

        with pytest.raises(errors.EsisteOdonimoGetPathParamInternalServerError):
            sdk.pathparam.esiste_odonimo_get_path_param(
                codcom="H501",
                denom="dGVzdA==",
            )

    def test_esiste_odonimo_with_authorization_header(self, httpx_mock: HTTPXMock):
        """Test that Authorization header is sent correctly."""
        httpx_mock.add_response(
            url=f"{BASE_URL}/esisteodonimo/H501/VklBIFJPTUE=",
            json={"res": "OK", "data": True},
            status_code=200,
        )

        security = Security(bearer="my-pdnd-token")
        sdk = AnncsuConsultazione(security=security)

        response = sdk.pathparam.esiste_odonimo_get_path_param(
            codcom="H501",
            denom="VklBIFJPTUE=",
        )

        assert response.data is True

        # Verify the Authorization header was sent
        requests = httpx_mock.get_requests()
        assert len(requests) == 1
        assert "Authorization" in requests[0].headers
        assert requests[0].headers["Authorization"] == "Bearer my-pdnd-token"


class TestEsisteAccessoGetPathParam:
    """Tests for esiste_accesso_get_path_param endpoint."""

    def test_esiste_accesso_returns_true(self, httpx_mock: HTTPXMock):
        """Test successful response when accesso exists."""
        httpx_mock.add_response(
            method="GET",
            json={"res": "OK", "data": True},
            status_code=200,
        )

        security = Security(bearer="test-token")
        sdk = AnncsuConsultazione(security=security)

        response = sdk.pathparam.esiste_accesso_get_path_param(
            codcom="H501",
            denom="VklBIFJPTUE=",
            accesso="MQ==",
        )

        assert response.res == "OK"
        assert response.data is True

    def test_esiste_accesso_returns_false(self, httpx_mock: HTTPXMock):
        """Test successful response when accesso does not exist."""
        httpx_mock.add_response(
            method="GET",
            json={"res": "OK", "data": False},
            status_code=200,
        )

        security = Security(bearer="test-token")
        sdk = AnncsuConsultazione(security=security)

        response = sdk.pathparam.esiste_accesso_get_path_param(
            codcom="H501",
            denom="VklBIFJPTUE=",
            accesso="OTk5",  # "999" base64 encoded
        )

        assert response.data is False


class TestElencoOdonimiGetPathParam:
    """Tests for elenco_odonimi_get_path_param endpoint."""

    def test_elenco_odonimi_returns_list(self, httpx_mock: HTTPXMock):
        """Test successful response with list of odonimi."""
        httpx_mock.add_response(
            method="GET",
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

        response = sdk.pathparam.elenco_odonimi_get_path_param(
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
            method="GET",
            json={"res": "OK", "data": []},
            status_code=200,
        )

        security = Security(bearer="test-token")
        sdk = AnncsuConsultazione(security=security)

        response = sdk.pathparam.elenco_odonimi_get_path_param(
            codcom="H501",
            denomparz="WFlaWg==",
        )

        assert response.data == []


class TestElencoAccessiGetPathParam:
    """Tests for elenco_accessi_get_path_param endpoint."""

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

        response = sdk.pathparam.elenco_accessi_get_path_param(
            codcom="H501",
            denom="VklBIFJPTUE=",
            accparz="MQ==",
        )

        assert response.res == "OK"
        assert len(response.data) == 2
        assert response.data[0].civico == "1"


class TestElencoOdonimiProgGetPathParam:
    """Tests for elencoodonimiprog_get_path_param endpoint."""

    def test_elencoodonimiprog_returns_list(self, httpx_mock: HTTPXMock):
        """Test successful response with progressive list of odonimi."""
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
                ],
            },
            status_code=200,
        )

        security = Security(bearer="test-token")
        sdk = AnncsuConsultazione(security=security)

        response = sdk.pathparam.elencoodonimiprog_get_path_param(
            codcom="H501",
            denomparz="Uk9NQQ==",
        )

        assert response.res == "OK"
        assert len(response.data) == 1
        assert response.data[0].prognaz == "12345678901234567890"
        assert response.data[0].dug == "VIA"
        assert response.data[0].denomuff == "ROMA"

    def test_elencoodonimiprog_empty_list(self, httpx_mock: HTTPXMock):
        """Test response with empty list."""
        httpx_mock.add_response(
            method="GET",
            json={"res": "OK", "data": []},
            status_code=200,
        )

        security = Security(bearer="test-token")
        sdk = AnncsuConsultazione(security=security)

        response = sdk.pathparam.elencoodonimiprog_get_path_param(
            codcom="H501",
            denomparz="WFlaWg==",
        )

        assert response.res == "OK"
        assert response.data == []

    def test_elencoodonimiprog_bad_request(self, httpx_mock: HTTPXMock):
        """Test 400 Bad Request error handling."""
        httpx_mock.add_response(
            method="GET",
            json={"title": "Bad Request", "detail": "Invalid codcom format"},
            status_code=400,
            headers={"Content-Type": "application/problem+json"},
        )

        security = Security(bearer="test-token")
        sdk = AnncsuConsultazione(security=security)

        with pytest.raises(
            errors.ElencoodonimiprogGetPathParamBadRequestError
        ) as exc_info:
            sdk.pathparam.elencoodonimiprog_get_path_param(
                codcom="INVALID",
                denomparz="dGVzdA==",
            )

        assert exc_info.value.data.title == "Bad Request"

    def test_elencoodonimiprog_internal_server_error(self, httpx_mock: HTTPXMock):
        """Test 500 Internal Server Error handling."""
        httpx_mock.add_response(
            method="GET",
            json={
                "title": "Internal Server Error",
                "detail": "Database unavailable",
            },
            status_code=500,
            headers={"Content-Type": "application/problem+json"},
        )

        security = Security(bearer="test-token")
        sdk = AnncsuConsultazione(security=security)

        with pytest.raises(errors.ElencoodonimiprogGetPathParamInternalServerError):
            sdk.pathparam.elencoodonimiprog_get_path_param(
                codcom="H501",
                denomparz="dGVzdA==",
            )


class TestElencoAccessiProgGetPathParam:
    """Tests for elencoaccessiprog_get_path_param endpoint."""

    def test_elencoaccessiprog_returns_list(self, httpx_mock: HTTPXMock):
        """Test successful response with progressive list of accessi."""
        httpx_mock.add_response(
            method="GET",
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

        response = sdk.pathparam.elencoaccessiprog_get_path_param(
            prognaz="12345678901234567890",
            accparz="MQ==",
        )

        assert response.res == "OK"
        assert len(response.data) == 1
        assert response.data[0].prognazacc == "12345678901234567890"
        assert response.data[0].civico == "1"
        assert response.data[0].coord_x == "12.4964"
        assert response.data[0].coord_y == "41.9028"

    def test_elencoaccessiprog_empty_list(self, httpx_mock: HTTPXMock):
        """Test response with empty list."""
        httpx_mock.add_response(
            method="GET",
            json={"res": "OK", "data": []},
            status_code=200,
        )

        security = Security(bearer="test-token")
        sdk = AnncsuConsultazione(security=security)

        response = sdk.pathparam.elencoaccessiprog_get_path_param(
            prognaz="00000000000000000000",
            accparz="OTk5",
        )

        assert response.res == "OK"
        assert response.data == []

    def test_elencoaccessiprog_bad_request(self, httpx_mock: HTTPXMock):
        """Test 400 Bad Request error handling."""
        httpx_mock.add_response(
            method="GET",
            json={"title": "Bad Request", "detail": "Invalid prognaz format"},
            status_code=400,
            headers={"Content-Type": "application/problem+json"},
        )

        security = Security(bearer="test-token")
        sdk = AnncsuConsultazione(security=security)

        with pytest.raises(
            errors.ElencoaccessiprogGetPathParamBadRequestError
        ) as exc_info:
            sdk.pathparam.elencoaccessiprog_get_path_param(
                prognaz="INVALID",
                accparz="dGVzdA==",
            )

        assert exc_info.value.data.title == "Bad Request"

    def test_elencoaccessiprog_internal_server_error(self, httpx_mock: HTTPXMock):
        """Test 500 Internal Server Error handling."""
        httpx_mock.add_response(
            method="GET",
            json={
                "title": "Internal Server Error",
                "detail": "Database unavailable",
            },
            status_code=500,
            headers={"Content-Type": "application/problem+json"},
        )

        security = Security(bearer="test-token")
        sdk = AnncsuConsultazione(security=security)

        with pytest.raises(errors.ElencoaccessiprogGetPathParamInternalServerError):
            sdk.pathparam.elencoaccessiprog_get_path_param(
                prognaz="12345678901234567890",
                accparz="dGVzdA==",
            )


class TestPrognazareaGetPathParam:
    """Tests for prognazarea_get_path_param endpoint."""

    def test_prognazarea_returns_data(self, httpx_mock: HTTPXMock):
        """Test successful response with area data."""
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
                ],
            },
            status_code=200,
        )

        security = Security(bearer="test-token")
        sdk = AnncsuConsultazione(security=security)

        response = sdk.pathparam.prognazarea_get_path_param(
            prognaz="12345678901234567890",
        )

        assert response.res == "OK"
        assert len(response.data) == 1
        assert response.data[0].prognaz == "12345678901234567890"
        assert response.data[0].dug == "VIA"

    def test_prognazarea_empty_list(self, httpx_mock: HTTPXMock):
        """Test response with empty list."""
        httpx_mock.add_response(
            method="GET",
            json={"res": "OK", "data": []},
            status_code=200,
        )

        security = Security(bearer="test-token")
        sdk = AnncsuConsultazione(security=security)

        response = sdk.pathparam.prognazarea_get_path_param(
            prognaz="00000000000000000000",
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

        with pytest.raises(errors.PrognazareaGetPathParamBadRequestError) as exc_info:
            sdk.pathparam.prognazarea_get_path_param(
                prognaz="INVALID",
            )

        assert exc_info.value.data.title == "Bad Request"

    def test_prognazarea_internal_server_error(self, httpx_mock: HTTPXMock):
        """Test 500 Internal Server Error handling."""
        httpx_mock.add_response(
            method="GET",
            json={
                "title": "Internal Server Error",
                "detail": "Database unavailable",
            },
            status_code=500,
            headers={"Content-Type": "application/problem+json"},
        )

        security = Security(bearer="test-token")
        sdk = AnncsuConsultazione(security=security)

        with pytest.raises(errors.PrognazareaGetPathParamInternalServerError):
            sdk.pathparam.prognazarea_get_path_param(
                prognaz="12345678901234567890",
            )


class TestPrognazaccGetPathParam:
    """Tests for prognazacc_get_path_param endpoint."""

    def test_prognazacc_returns_data(self, httpx_mock: HTTPXMock):
        """Test successful response with access data."""
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

        response = sdk.pathparam.prognazacc_get_path_param(
            prognazacc="12345678901234567891",
        )

        assert response.res == "OK"
        assert len(response.data) == 1
        assert response.data[0].prognaz == "12345678901234567890"
        assert response.data[0].prognazacc == "12345678901234567891"
        assert response.data[0].coord_x == "12.4964"
        assert response.data[0].coord_y == "41.9028"

    def test_prognazacc_empty_list(self, httpx_mock: HTTPXMock):
        """Test response with empty list."""
        httpx_mock.add_response(
            method="GET",
            json={"res": "OK", "data": []},
            status_code=200,
        )

        security = Security(bearer="test-token")
        sdk = AnncsuConsultazione(security=security)

        response = sdk.pathparam.prognazacc_get_path_param(
            prognazacc="00000000000000000000",
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

        with pytest.raises(errors.PrognazaccGetPathParamBadRequestError) as exc_info:
            sdk.pathparam.prognazacc_get_path_param(
                prognazacc="INVALID",
            )

        assert exc_info.value.data.title == "Bad Request"

    def test_prognazacc_internal_server_error(self, httpx_mock: HTTPXMock):
        """Test 500 Internal Server Error handling."""
        httpx_mock.add_response(
            method="GET",
            json={
                "title": "Internal Server Error",
                "detail": "Database unavailable",
            },
            status_code=500,
            headers={"Content-Type": "application/problem+json"},
        )

        security = Security(bearer="test-token")
        sdk = AnncsuConsultazione(security=security)

        with pytest.raises(errors.PrognazaccGetPathParamInternalServerError):
            sdk.pathparam.prognazacc_get_path_param(
                prognazacc="12345678901234567891",
            )


class TestPathParamErrorHandling:
    """Tests for error handling in path param endpoints."""

    def test_404_not_found(self, httpx_mock: HTTPXMock):
        """Test 404 Not Found error handling."""
        httpx_mock.add_response(
            url=f"{BASE_URL}/esisteodonimo/H501/VklBIFJPTUE=",
            text="Not Found",
            status_code=404,
        )

        security = Security(bearer="test-token")
        sdk = AnncsuConsultazione(security=security)

        with pytest.raises(errors.APIError):
            sdk.pathparam.esiste_odonimo_get_path_param(
                codcom="H501",
                denom="VklBIFJPTUE=",
            )

    def test_503_service_unavailable(self, httpx_mock: HTTPXMock):
        """Test 503 Service Unavailable error handling."""
        httpx_mock.add_response(
            url=f"{BASE_URL}/esisteodonimo/H501/VklBIFJPTUE=",
            text="Service Unavailable",
            status_code=503,
        )

        security = Security(bearer="test-token")
        sdk = AnncsuConsultazione(security=security)

        with pytest.raises(errors.APIError):
            sdk.pathparam.esiste_odonimo_get_path_param(
                codcom="H501",
                denom="VklBIFJPTUE=",
            )


class TestPathParamWithCustomServerUrl:
    """Tests for custom server URL with path params."""

    def test_with_validation_environment(self, httpx_mock: HTTPXMock):
        """Test SDK with validation environment URL."""
        custom_url = "https://modipa-val.agenziaentrate.it/govway/rest/in/AgenziaEntrate-PDND/anncsu-consultazione/v1"

        httpx_mock.add_response(
            url=f"{custom_url}/esisteodonimo/H501/VklBIFJPTUE=",
            json={"res": "OK", "data": True},
            status_code=200,
        )

        security = Security(bearer="test-token")
        sdk = AnncsuConsultazione(security=security, server_url=custom_url)

        response = sdk.pathparam.esiste_odonimo_get_path_param(
            codcom="H501",
            denom="VklBIFJPTUE=",
        )

        assert response.data is True
