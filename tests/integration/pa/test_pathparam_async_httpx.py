"""Async integration tests for pathparam.py using pytest-httpx.

These tests mock HTTP responses at the httpx level to exercise
the full Speakeasy-generated async code path for path parameter endpoints.
"""

import pytest
from pytest_httpx import HTTPXMock

from anncsu.common import Security
from anncsu.pa import AnncsuConsultazione, errors

# Base URL for mocking
BASE_URL = "https://modipa.agenziaentrate.gov.it/govway/rest/in/AgenziaEntrate-PDND/anncsu-consultazione/v1"


class TestEsisteOdonimoGetPathParamAsync:
    """Async tests for esiste_odonimo_get_path_param endpoint."""

    @pytest.mark.asyncio
    async def test_esiste_odonimo_returns_true(self, httpx_mock: HTTPXMock):
        """Test successful async response when odonimo exists."""
        httpx_mock.add_response(
            url=f"{BASE_URL}/esisteodonimo/H501/VklBIFJPTUE=",
            json={"res": "OK", "data": True},
            status_code=200,
        )

        security = Security(bearer="test-token")
        sdk = AnncsuConsultazione(security=security)

        response = await sdk.pathparam.esiste_odonimo_get_path_param_async(
            codcom="H501",
            denom="VklBIFJPTUE=",
        )

        assert response.res == "OK"
        assert response.data is True

    @pytest.mark.asyncio
    async def test_esiste_odonimo_returns_false(self, httpx_mock: HTTPXMock):
        """Test successful async response when odonimo does not exist."""
        httpx_mock.add_response(
            url=f"{BASE_URL}/esisteodonimo/H501/VklBIElORVNJU1RFTlRF",
            json={"res": "OK", "data": False},
            status_code=200,
        )

        security = Security(bearer="test-token")
        sdk = AnncsuConsultazione(security=security)

        response = await sdk.pathparam.esiste_odonimo_get_path_param_async(
            codcom="H501",
            denom="VklBIElORVNJU1RFTlRF",
        )

        assert response.res == "OK"
        assert response.data is False

    @pytest.mark.asyncio
    async def test_esiste_odonimo_bad_request(self, httpx_mock: HTTPXMock):
        """Test 400 Bad Request error handling in async."""
        httpx_mock.add_response(
            url=f"{BASE_URL}/esisteodonimo/INVALID/dGVzdA==",
            json={"title": "Bad Request", "detail": "Invalid codcom format"},
            status_code=400,
            headers={"Content-Type": "application/problem+json"},
        )

        security = Security(bearer="test-token")
        sdk = AnncsuConsultazione(security=security)

        with pytest.raises(errors.EsisteOdonimoGetPathParamBadRequestError) as exc_info:
            await sdk.pathparam.esiste_odonimo_get_path_param_async(
                codcom="INVALID",
                denom="dGVzdA==",
            )

        assert exc_info.value.data.title == "Bad Request"

    @pytest.mark.asyncio
    async def test_esiste_odonimo_unprocessable_entity(self, httpx_mock: HTTPXMock):
        """Test 422 Unprocessable Entity error handling in async."""
        httpx_mock.add_response(
            url=f"{BASE_URL}/esisteodonimo/H501/not-base64",
            json={
                "title": "Unprocessable Entity",
                "detail": "denom must be base64 encoded",
            },
            status_code=422,
            headers={"Content-Type": "application/problem+json"},
        )

        security = Security(bearer="test-token")
        sdk = AnncsuConsultazione(security=security)

        with pytest.raises(errors.EsisteOdonimoGetPathParamUnprocessableEntityError):
            await sdk.pathparam.esiste_odonimo_get_path_param_async(
                codcom="H501",
                denom="not-base64",
            )

    @pytest.mark.asyncio
    async def test_esiste_odonimo_internal_server_error(self, httpx_mock: HTTPXMock):
        """Test 500 Internal Server Error handling in async."""
        httpx_mock.add_response(
            url=f"{BASE_URL}/esisteodonimo/H501/dGVzdA==",
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
            await sdk.pathparam.esiste_odonimo_get_path_param_async(
                codcom="H501",
                denom="dGVzdA==",
            )


class TestElencoOdonimiGetPathParamAsync:
    """Async tests for elenco_odonimi_get_path_param endpoint."""

    @pytest.mark.asyncio
    async def test_elenco_odonimi_returns_list(self, httpx_mock: HTTPXMock):
        """Test successful async response with list of odonimi."""
        httpx_mock.add_response(
            url=f"{BASE_URL}/elencoodonimi/H501/Uk9NQQ==",
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

        response = await sdk.pathparam.elenco_odonimi_get_path_param_async(
            codcom="H501",
            denomparz="Uk9NQQ==",
        )

        assert response.res == "OK"
        assert len(response.data) == 2
        assert response.data[0].dug == "VIA"

    @pytest.mark.asyncio
    async def test_elenco_odonimi_empty_list(self, httpx_mock: HTTPXMock):
        """Test async response with empty list."""
        httpx_mock.add_response(
            url=f"{BASE_URL}/elencoodonimi/H501/WFlaWg==",
            json={"res": "OK", "data": []},
            status_code=200,
        )

        security = Security(bearer="test-token")
        sdk = AnncsuConsultazione(security=security)

        response = await sdk.pathparam.elenco_odonimi_get_path_param_async(
            codcom="H501",
            denomparz="WFlaWg==",
        )

        assert response.res == "OK"
        assert response.data == []

    @pytest.mark.asyncio
    async def test_elenco_odonimi_bad_request(self, httpx_mock: HTTPXMock):
        """Test 400 Bad Request for async elenco_odonimi."""
        httpx_mock.add_response(
            url=f"{BASE_URL}/elencoodonimi/BAD/dGVzdA==",
            json={"title": "Bad Request", "detail": "codcom not found"},
            status_code=400,
            headers={"Content-Type": "application/problem+json"},
        )

        security = Security(bearer="test-token")
        sdk = AnncsuConsultazione(security=security)

        with pytest.raises(errors.ElencoOdonimiGetPathParamBadRequestError):
            await sdk.pathparam.elenco_odonimi_get_path_param_async(
                codcom="BAD",
                denomparz="dGVzdA==",
            )


class TestElencoAccessiGetPathParamAsync:
    """Async tests for elenco_accessi_get_path_param endpoint."""

    @pytest.mark.asyncio
    async def test_elenco_accessi_returns_list(self, httpx_mock: HTTPXMock):
        """Test successful async response with list of accessi."""
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

        response = await sdk.pathparam.elenco_accessi_get_path_param_async(
            codcom="H501",
            denom="VklBIFJPTUE=",
            accparz="MQ==",
        )

        assert response.res == "OK"
        assert len(response.data) == 2


class TestEsisteAccessoGetPathParamAsync:
    """Async tests for esiste_accesso_get_path_param endpoint."""

    @pytest.mark.asyncio
    async def test_esiste_accesso_returns_true(self, httpx_mock: HTTPXMock):
        """Test successful async response when accesso exists."""
        httpx_mock.add_response(
            method="GET",
            json={"res": "OK", "data": True},
            status_code=200,
        )

        security = Security(bearer="test-token")
        sdk = AnncsuConsultazione(security=security)

        response = await sdk.pathparam.esiste_accesso_get_path_param_async(
            codcom="H501",
            denom="VklBIFJPTUE=",
            accesso="MQ==",
        )

        assert response.res == "OK"
        assert response.data is True


class TestElencoodonimiprogGetPathParamAsync:
    """Async tests for elencoodonimiprog_get_path_param endpoint."""

    @pytest.mark.asyncio
    async def test_elencoodonimiprog_returns_list(self, httpx_mock: HTTPXMock):
        """Test successful async response with progressive list of odonimi."""
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

        response = await sdk.pathparam.elencoodonimiprog_get_path_param_async(
            codcom="H501",
            denomparz="Uk9NQQ==",
        )

        assert response.res == "OK"
        assert len(response.data) == 1
        assert response.data[0].prognaz == "12345678901234567890"

    @pytest.mark.asyncio
    async def test_elencoodonimiprog_bad_request(self, httpx_mock: HTTPXMock):
        """Test 400 Bad Request error handling in async."""
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
            await sdk.pathparam.elencoodonimiprog_get_path_param_async(
                codcom="INVALID",
                denomparz="dGVzdA==",
            )

        assert exc_info.value.data.title == "Bad Request"


class TestElencoaccessiprogGetPathParamAsync:
    """Async tests for elencoaccessiprog_get_path_param endpoint."""

    @pytest.mark.asyncio
    async def test_elencoaccessiprog_returns_list(self, httpx_mock: HTTPXMock):
        """Test successful async response with progressive list of accessi."""
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

        response = await sdk.pathparam.elencoaccessiprog_get_path_param_async(
            prognaz="12345678901234567890",
            accparz="MQ==",
        )

        assert response.res == "OK"
        assert len(response.data) == 1
        assert response.data[0].coord_x == "12.4964"

    @pytest.mark.asyncio
    async def test_elencoaccessiprog_bad_request(self, httpx_mock: HTTPXMock):
        """Test 400 Bad Request error handling in async."""
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
            await sdk.pathparam.elencoaccessiprog_get_path_param_async(
                prognaz="INVALID",
                accparz="dGVzdA==",
            )

        assert exc_info.value.data.title == "Bad Request"


class TestPrognazareaGetPathParamAsync:
    """Async tests for prognazarea_get_path_param endpoint."""

    @pytest.mark.asyncio
    async def test_prognazarea_returns_data(self, httpx_mock: HTTPXMock):
        """Test successful async response with area data."""
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

        response = await sdk.pathparam.prognazarea_get_path_param_async(
            prognaz="12345678901234567890",
        )

        assert response.res == "OK"
        assert len(response.data) == 1
        assert response.data[0].prognaz == "12345678901234567890"

    @pytest.mark.asyncio
    async def test_prognazarea_bad_request(self, httpx_mock: HTTPXMock):
        """Test 400 Bad Request error handling in async."""
        httpx_mock.add_response(
            method="GET",
            json={"title": "Bad Request", "detail": "Invalid prognaz format"},
            status_code=400,
            headers={"Content-Type": "application/problem+json"},
        )

        security = Security(bearer="test-token")
        sdk = AnncsuConsultazione(security=security)

        with pytest.raises(errors.PrognazareaGetPathParamBadRequestError) as exc_info:
            await sdk.pathparam.prognazarea_get_path_param_async(
                prognaz="INVALID",
            )

        assert exc_info.value.data.title == "Bad Request"


class TestPrognazaccGetPathParamAsync:
    """Async tests for prognazacc_get_path_param endpoint."""

    @pytest.mark.asyncio
    async def test_prognazacc_returns_data(self, httpx_mock: HTTPXMock):
        """Test successful async response with access data."""
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

        response = await sdk.pathparam.prognazacc_get_path_param_async(
            prognazacc="12345678901234567891",
        )

        assert response.res == "OK"
        assert len(response.data) == 1
        assert response.data[0].prognazacc == "12345678901234567891"
        assert response.data[0].coord_x == "12.4964"

    @pytest.mark.asyncio
    async def test_prognazacc_bad_request(self, httpx_mock: HTTPXMock):
        """Test 400 Bad Request error handling in async."""
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
            await sdk.pathparam.prognazacc_get_path_param_async(
                prognazacc="INVALID",
            )

        assert exc_info.value.data.title == "Bad Request"


class TestAsyncPathParamWithCustomServerUrl:
    """Async tests for custom server URL configuration."""

    @pytest.mark.asyncio
    async def test_with_custom_server_url(self, httpx_mock: HTTPXMock):
        """Test async SDK with custom server URL."""
        custom_url = "https://modipa-val.agenziaentrate.it/govway/rest/in/AgenziaEntrate-PDND/anncsu-consultazione/v1"

        httpx_mock.add_response(
            url=f"{custom_url}/esisteodonimo/H501/VklBIFJPTUE=",
            json={"res": "OK", "data": True},
            status_code=200,
        )

        security = Security(bearer="test-token")
        sdk = AnncsuConsultazione(security=security, server_url=custom_url)

        response = await sdk.pathparam.esiste_odonimo_get_path_param_async(
            codcom="H501",
            denom="VklBIFJPTUE=",
        )

        assert response.data is True


class TestAsyncPathParamGenericErrors:
    """Async tests for generic error handling."""

    @pytest.mark.asyncio
    async def test_404_not_found(self, httpx_mock: HTTPXMock):
        """Test 404 Not Found error handling in async."""
        httpx_mock.add_response(
            url=f"{BASE_URL}/esisteodonimo/H501/VklBIFJPTUE=",
            text="Not Found",
            status_code=404,
        )

        security = Security(bearer="test-token")
        sdk = AnncsuConsultazione(security=security)

        with pytest.raises(errors.APIError):
            await sdk.pathparam.esiste_odonimo_get_path_param_async(
                codcom="H501",
                denom="VklBIFJPTUE=",
            )

    @pytest.mark.asyncio
    async def test_503_service_unavailable(self, httpx_mock: HTTPXMock):
        """Test 503 Service Unavailable error handling in async."""
        httpx_mock.add_response(
            url=f"{BASE_URL}/esisteodonimo/H501/VklBIFJPTUE=",
            text="Service Unavailable",
            status_code=503,
        )

        security = Security(bearer="test-token")
        sdk = AnncsuConsultazione(security=security)

        with pytest.raises(errors.APIError):
            await sdk.pathparam.esiste_odonimo_get_path_param_async(
                codcom="H501",
                denom="VklBIFJPTUE=",
            )
