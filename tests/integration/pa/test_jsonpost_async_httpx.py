"""Async integration tests for pa/jsonpost.py using pytest-httpx.

These tests mock HTTP responses at the httpx level to exercise
the full Speakeasy-generated async code path for JSON POST endpoints.
"""

import pytest
from pytest_httpx import HTTPXMock

from anncsu.common import Security
from anncsu.pa import AnncsuConsultazione, errors

# Base URL for mocking
BASE_URL = "https://modipa.agenziaentrate.gov.it/govway/rest/in/AgenziaEntrate-PDND/anncsu-consultazione/v1"


class TestEsisteOdonimoPostAsync:
    """Async tests for esiste_odonimo_post endpoint."""

    @pytest.mark.asyncio
    async def test_esiste_odonimo_returns_true(self, httpx_mock: HTTPXMock):
        """Test successful async POST response when odonimo exists."""
        httpx_mock.add_response(
            method="POST",
            url=f"{BASE_URL}/esisteodonimo",
            json={"res": "OK", "data": True},
            status_code=200,
        )

        security = Security(bearer="test-token")
        sdk = AnncsuConsultazione(security=security)

        response = await sdk.json_post.esiste_odonimo_post_async(
            codcom="H501",
            denom="VklBIFJPTUE=",
        )

        assert response.res == "OK"
        assert response.data is True

    @pytest.mark.asyncio
    async def test_esiste_odonimo_returns_false(self, httpx_mock: HTTPXMock):
        """Test successful async POST response when odonimo does not exist."""
        httpx_mock.add_response(
            method="POST",
            url=f"{BASE_URL}/esisteodonimo",
            json={"res": "OK", "data": False},
            status_code=200,
        )

        security = Security(bearer="test-token")
        sdk = AnncsuConsultazione(security=security)

        response = await sdk.json_post.esiste_odonimo_post_async(
            codcom="H501",
            denom="VklBIElORVNJU1RFTlRF",
        )

        assert response.res == "OK"
        assert response.data is False

    @pytest.mark.asyncio
    async def test_esiste_odonimo_bad_request(self, httpx_mock: HTTPXMock):
        """Test 400 Bad Request error handling in async POST."""
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
            await sdk.json_post.esiste_odonimo_post_async(
                codcom="INVALID",
                denom="dGVzdA==",
            )

        assert exc_info.value.data.title == "Bad Request"

    @pytest.mark.asyncio
    async def test_esiste_odonimo_unprocessable_entity(self, httpx_mock: HTTPXMock):
        """Test 422 Unprocessable Entity error handling in async POST."""
        httpx_mock.add_response(
            method="POST",
            url=f"{BASE_URL}/esisteodonimo",
            json={
                "title": "Unprocessable Entity",
                "detail": "denom must be base64 encoded",
            },
            status_code=422,
            headers={"Content-Type": "application/problem+json"},
        )

        security = Security(bearer="test-token")
        sdk = AnncsuConsultazione(security=security)

        with pytest.raises(errors.EsisteOdonimoPostUnprocessableEntityError):
            await sdk.json_post.esiste_odonimo_post_async(
                codcom="H501",
                denom="not-base64",
            )

    @pytest.mark.asyncio
    async def test_esiste_odonimo_internal_server_error(self, httpx_mock: HTTPXMock):
        """Test 500 Internal Server Error handling in async POST."""
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
            await sdk.json_post.esiste_odonimo_post_async(
                codcom="H501",
                denom="dGVzdA==",
            )


class TestElencoOdonimiPostAsync:
    """Async tests for elenco_odonimi_post endpoint."""

    @pytest.mark.asyncio
    async def test_elenco_odonimi_returns_list(self, httpx_mock: HTTPXMock):
        """Test successful async POST response with list of odonimi."""
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

        response = await sdk.json_post.elenco_odonimi_post_async(
            codcom="H501",
            denomparz="Uk9NQQ==",
        )

        assert response.res == "OK"
        assert len(response.data) == 2
        assert response.data[0].dug == "VIA"

    @pytest.mark.asyncio
    async def test_elenco_odonimi_empty_list(self, httpx_mock: HTTPXMock):
        """Test async POST response with empty list."""
        httpx_mock.add_response(
            method="POST",
            url=f"{BASE_URL}/elencoodonimi",
            json={"res": "OK", "data": []},
            status_code=200,
        )

        security = Security(bearer="test-token")
        sdk = AnncsuConsultazione(security=security)

        response = await sdk.json_post.elenco_odonimi_post_async(
            codcom="H501",
            denomparz="WFlaWg==",
        )

        assert response.res == "OK"
        assert response.data == []

    @pytest.mark.asyncio
    async def test_elenco_odonimi_bad_request(self, httpx_mock: HTTPXMock):
        """Test 400 Bad Request for async elenco_odonimi POST."""
        httpx_mock.add_response(
            method="POST",
            url=f"{BASE_URL}/elencoodonimi",
            json={"title": "Bad Request", "detail": "codcom not found"},
            status_code=400,
            headers={"Content-Type": "application/problem+json"},
        )

        security = Security(bearer="test-token")
        sdk = AnncsuConsultazione(security=security)

        with pytest.raises(errors.ElencoOdonimiPostBadRequestError):
            await sdk.json_post.elenco_odonimi_post_async(
                codcom="BAD",
                denomparz="dGVzdA==",
            )


class TestElencoAccessiPostAsync:
    """Async tests for elenco_accessi_post endpoint."""

    @pytest.mark.asyncio
    async def test_elenco_accessi_returns_list(self, httpx_mock: HTTPXMock):
        """Test successful async POST response with list of accessi."""
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

        response = await sdk.json_post.elenco_accessi_post_async(
            codcom="H501",
            denom="VklBIFJPTUE=",
            accparz="MQ==",
        )

        assert response.res == "OK"
        assert len(response.data) == 2


class TestEsisteAccessoPostAsync:
    """Async tests for esiste_accesso_post endpoint."""

    @pytest.mark.asyncio
    async def test_esiste_accesso_returns_true(self, httpx_mock: HTTPXMock):
        """Test successful async POST response when accesso exists."""
        httpx_mock.add_response(
            method="POST",
            url=f"{BASE_URL}/esisteaccesso",
            json={"res": "OK", "data": True},
            status_code=200,
        )

        security = Security(bearer="test-token")
        sdk = AnncsuConsultazione(security=security)

        response = await sdk.json_post.esiste_accesso_post_async(
            codcom="H501",
            denom="VklBIFJPTUE=",
            accesso="MQ==",
        )

        assert response.res == "OK"
        assert response.data is True


class TestElencoodonimiprogPostAsync:
    """Async tests for elencoodonimiprog_post endpoint."""

    @pytest.mark.asyncio
    async def test_elencoodonimiprog_returns_list(self, httpx_mock: HTTPXMock):
        """Test successful async response with progressive list of odonimi."""
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

        response = await sdk.json_post.elencoodonimiprog_post_async(
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
            method="POST",
            url=f"{BASE_URL}/elencoodonimiprog",
            json={"title": "Bad Request", "detail": "Invalid codcom format"},
            status_code=400,
            headers={"Content-Type": "application/problem+json"},
        )

        security = Security(bearer="test-token")
        sdk = AnncsuConsultazione(security=security)

        with pytest.raises(errors.ElencoodonimiprogPostBadRequestError) as exc_info:
            await sdk.json_post.elencoodonimiprog_post_async(
                codcom="INVALID",
                denomparz="dGVzdA==",
            )

        assert exc_info.value.data.title == "Bad Request"


class TestElencoaccessiprogPostAsync:
    """Async tests for elencoaccessiprog_post endpoint."""

    @pytest.mark.asyncio
    async def test_elencoaccessiprog_returns_list(self, httpx_mock: HTTPXMock):
        """Test successful async response with progressive list of accessi."""
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

        response = await sdk.json_post.elencoaccessiprog_post_async(
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
            method="POST",
            url=f"{BASE_URL}/elencoaccessiprog",
            json={"title": "Bad Request", "detail": "Invalid prognaz format"},
            status_code=400,
            headers={"Content-Type": "application/problem+json"},
        )

        security = Security(bearer="test-token")
        sdk = AnncsuConsultazione(security=security)

        with pytest.raises(errors.ElencoaccessiprogPostBadRequestError) as exc_info:
            await sdk.json_post.elencoaccessiprog_post_async(
                prognaz="INVALID",
                accparz="dGVzdA==",
            )

        assert exc_info.value.data.title == "Bad Request"


class TestPrognazareaPostAsync:
    """Async tests for prognazarea_post endpoint."""

    @pytest.mark.asyncio
    async def test_prognazarea_returns_data(self, httpx_mock: HTTPXMock):
        """Test successful async response with area data."""
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

        response = await sdk.json_post.prognazarea_post_async(
            prognaz="12345678901234567890",
        )

        assert response.res == "OK"
        assert len(response.data) == 1
        assert response.data[0].prognaz == "12345678901234567890"

    @pytest.mark.asyncio
    async def test_prognazarea_bad_request(self, httpx_mock: HTTPXMock):
        """Test 400 Bad Request error handling in async."""
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
            await sdk.json_post.prognazarea_post_async(
                prognaz="INVALID",
            )

        assert exc_info.value.data.title == "Bad Request"


class TestPrognazaccPostAsync:
    """Async tests for prognazacc_post endpoint."""

    @pytest.mark.asyncio
    async def test_prognazacc_returns_data(self, httpx_mock: HTTPXMock):
        """Test successful async response with access data."""
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

        response = await sdk.json_post.prognazacc_post_async(
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
            await sdk.json_post.prognazacc_post_async(
                prognazacc="INVALID",
            )

        assert exc_info.value.data.title == "Bad Request"


class TestAsyncPostWithCustomServerUrl:
    """Async tests for custom server URL configuration with POST."""

    @pytest.mark.asyncio
    async def test_with_custom_server_url(self, httpx_mock: HTTPXMock):
        """Test async SDK POST with custom server URL."""
        custom_url = "https://modipa-val.agenziaentrate.it/govway/rest/in/AgenziaEntrate-PDND/anncsu-consultazione/v1"

        httpx_mock.add_response(
            method="POST",
            url=f"{custom_url}/esisteodonimo",
            json={"res": "OK", "data": True},
            status_code=200,
        )

        security = Security(bearer="test-token")
        sdk = AnncsuConsultazione(security=security, server_url=custom_url)

        response = await sdk.json_post.esiste_odonimo_post_async(
            codcom="H501",
            denom="VklBIFJPTUE=",
        )

        assert response.data is True


class TestAsyncPostGenericErrors:
    """Async tests for generic error handling with POST."""

    @pytest.mark.asyncio
    async def test_404_not_found(self, httpx_mock: HTTPXMock):
        """Test 404 Not Found error handling in async POST."""
        httpx_mock.add_response(
            method="POST",
            url=f"{BASE_URL}/esisteodonimo",
            text="Not Found",
            status_code=404,
        )

        security = Security(bearer="test-token")
        sdk = AnncsuConsultazione(security=security)

        with pytest.raises(errors.APIError):
            await sdk.json_post.esiste_odonimo_post_async(
                codcom="H501",
                denom="VklBIFJPTUE=",
            )

    @pytest.mark.asyncio
    async def test_503_service_unavailable(self, httpx_mock: HTTPXMock):
        """Test 503 Service Unavailable error handling in async POST."""
        httpx_mock.add_response(
            method="POST",
            url=f"{BASE_URL}/esisteodonimo",
            text="Service Unavailable",
            status_code=503,
        )

        security = Security(bearer="test-token")
        sdk = AnncsuConsultazione(security=security)

        with pytest.raises(errors.APIError):
            await sdk.json_post.esiste_odonimo_post_async(
                codcom="H501",
                denom="VklBIFJPTUE=",
            )


class TestAsyncPostRequestBody:
    """Async tests for request body handling in POST."""

    @pytest.mark.asyncio
    async def test_request_body_is_json(self, httpx_mock: HTTPXMock):
        """Test that async POST request body is sent as JSON."""
        httpx_mock.add_response(
            method="POST",
            url=f"{BASE_URL}/esisteodonimo",
            json={"res": "OK", "data": True},
            status_code=200,
        )

        security = Security(bearer="test-token")
        sdk = AnncsuConsultazione(security=security)

        await sdk.json_post.esiste_odonimo_post_async(
            codcom="H501",
            denom="VklBIFJPTUE=",
        )

        requests = httpx_mock.get_requests()
        assert len(requests) == 1
        assert requests[0].method == "POST"
        content_type = requests[0].headers.get("Content-Type", "")
        assert "application/json" in content_type
