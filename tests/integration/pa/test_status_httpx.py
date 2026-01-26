"""Integration tests for pa/status.py using pytest-httpx.

These tests mock HTTP responses at the httpx level to exercise
the full Speakeasy-generated code path for the status endpoint.
"""

import pytest
from pytest_httpx import HTTPXMock

from anncsu.common import Security
from anncsu.pa import AnncsuConsultazione, errors

# Base URL for mocking
BASE_URL = "https://modipa.agenziaentrate.gov.it/govway/rest/in/AgenziaEntrate-PDND/anncsu-consultazione/v1"


class TestShowStatus:
    """Tests for show_status endpoint."""

    def test_show_status_returns_ok(self, httpx_mock: HTTPXMock):
        """Test successful status response."""
        httpx_mock.add_response(
            method="GET",
            url=f"{BASE_URL}/status",
            json={"status": "OK"},
            status_code=200,
            headers={"Content-Type": "application/problem+json"},
        )

        security = Security(bearer="test-token")
        sdk = AnncsuConsultazione(security=security)

        response = sdk.status.show_status()

        assert response.status == "OK"

    def test_show_status_service_unavailable(self, httpx_mock: HTTPXMock):
        """Test 503 Service Unavailable error handling."""
        httpx_mock.add_response(
            method="GET",
            url=f"{BASE_URL}/status",
            json={"status": "UNAVAILABLE"},
            status_code=503,
            headers={"Content-Type": "application/problem+json"},
        )

        security = Security(bearer="test-token")
        sdk = AnncsuConsultazione(security=security)

        with pytest.raises(errors.ServiceUnavailableError) as exc_info:
            sdk.status.show_status()

        assert exc_info.value.data.status == "UNAVAILABLE"

    def test_show_status_generic_5xx_error(self, httpx_mock: HTTPXMock):
        """Test generic 5XX error handling."""
        httpx_mock.add_response(
            method="GET",
            url=f"{BASE_URL}/status",
            text="Internal Server Error",
            status_code=500,
        )

        security = Security(bearer="test-token")
        sdk = AnncsuConsultazione(security=security)

        with pytest.raises(errors.APIError):
            sdk.status.show_status()

    def test_show_status_generic_4xx_error(self, httpx_mock: HTTPXMock):
        """Test generic 4XX error handling."""
        httpx_mock.add_response(
            method="GET",
            url=f"{BASE_URL}/status",
            text="Not Found",
            status_code=404,
        )

        security = Security(bearer="test-token")
        sdk = AnncsuConsultazione(security=security)

        with pytest.raises(errors.APIError):
            sdk.status.show_status()

    def test_show_status_with_authorization_header(self, httpx_mock: HTTPXMock):
        """Test that Authorization header is sent correctly."""
        httpx_mock.add_response(
            method="GET",
            url=f"{BASE_URL}/status",
            json={"status": "OK"},
            status_code=200,
            headers={"Content-Type": "application/problem+json"},
        )

        security = Security(bearer="my-pdnd-token")
        sdk = AnncsuConsultazione(security=security)

        response = sdk.status.show_status()

        assert response.status == "OK"

        # Verify the Authorization header was sent
        requests = httpx_mock.get_requests()
        assert len(requests) == 1
        assert "Authorization" in requests[0].headers
        assert requests[0].headers["Authorization"] == "Bearer my-pdnd-token"


class TestShowStatusAsync:
    """Async tests for show_status endpoint."""

    @pytest.mark.asyncio
    async def test_show_status_returns_ok(self, httpx_mock: HTTPXMock):
        """Test successful async status response."""
        httpx_mock.add_response(
            method="GET",
            url=f"{BASE_URL}/status",
            json={"status": "OK"},
            status_code=200,
            headers={"Content-Type": "application/problem+json"},
        )

        security = Security(bearer="test-token")
        sdk = AnncsuConsultazione(security=security)

        response = await sdk.status.show_status_async()

        assert response.status == "OK"

    @pytest.mark.asyncio
    async def test_show_status_service_unavailable(self, httpx_mock: HTTPXMock):
        """Test 503 Service Unavailable error handling in async."""
        httpx_mock.add_response(
            method="GET",
            url=f"{BASE_URL}/status",
            json={"status": "UNAVAILABLE"},
            status_code=503,
            headers={"Content-Type": "application/problem+json"},
        )

        security = Security(bearer="test-token")
        sdk = AnncsuConsultazione(security=security)

        with pytest.raises(errors.ServiceUnavailableError) as exc_info:
            await sdk.status.show_status_async()

        assert exc_info.value.data.status == "UNAVAILABLE"

    @pytest.mark.asyncio
    async def test_show_status_generic_5xx_error(self, httpx_mock: HTTPXMock):
        """Test generic 5XX error handling in async."""
        httpx_mock.add_response(
            method="GET",
            url=f"{BASE_URL}/status",
            text="Internal Server Error",
            status_code=500,
        )

        security = Security(bearer="test-token")
        sdk = AnncsuConsultazione(security=security)

        with pytest.raises(errors.APIError):
            await sdk.status.show_status_async()

    @pytest.mark.asyncio
    async def test_show_status_generic_4xx_error(self, httpx_mock: HTTPXMock):
        """Test generic 4XX error handling in async."""
        httpx_mock.add_response(
            method="GET",
            url=f"{BASE_URL}/status",
            text="Not Found",
            status_code=404,
        )

        security = Security(bearer="test-token")
        sdk = AnncsuConsultazione(security=security)

        with pytest.raises(errors.APIError):
            await sdk.status.show_status_async()


class TestShowStatusWithCustomServerUrl:
    """Tests for custom server URL with status endpoint."""

    def test_with_validation_environment(self, httpx_mock: HTTPXMock):
        """Test SDK with validation environment URL."""
        custom_url = "https://modipa-val.agenziaentrate.it/govway/rest/in/AgenziaEntrate-PDND/anncsu-consultazione/v1"

        httpx_mock.add_response(
            method="GET",
            url=f"{custom_url}/status",
            json={"status": "OK"},
            status_code=200,
            headers={"Content-Type": "application/problem+json"},
        )

        security = Security(bearer="test-token")
        sdk = AnncsuConsultazione(security=security, server_url=custom_url)

        response = sdk.status.show_status()

        assert response.status == "OK"

    @pytest.mark.asyncio
    async def test_async_with_custom_server_url(self, httpx_mock: HTTPXMock):
        """Test async SDK with custom server URL."""
        custom_url = "https://modipa-val.agenziaentrate.it/govway/rest/in/AgenziaEntrate-PDND/anncsu-consultazione/v1"

        httpx_mock.add_response(
            method="GET",
            url=f"{custom_url}/status",
            json={"status": "OK"},
            status_code=200,
            headers={"Content-Type": "application/problem+json"},
        )

        security = Security(bearer="test-token")
        sdk = AnncsuConsultazione(security=security, server_url=custom_url)

        response = await sdk.status.show_status_async()

        assert response.status == "OK"
