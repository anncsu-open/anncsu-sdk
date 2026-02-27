"""Integration tests for coordinate/status.py using pytest-httpx.

These tests mock HTTP responses at the httpx level to exercise
the full Speakeasy-generated code path for status endpoint.
"""

import pytest
from pytest_httpx import HTTPXMock

from anncsu.coordinate import AnncsuCoordinate, errors, models

# Base URL for mocking (production)
BASE_URL = "https://modipa.agenziaentrate.gov.it/govway/rest/in/AgenziaEntrate/anncsuaccessi/v1"


class TestShowStatus:
    """Tests for show_status endpoint."""

    def test_show_status_success(self, httpx_mock: HTTPXMock):
        """Test successful status response."""
        httpx_mock.add_response(
            method="GET",
            url=f"{BASE_URL}/status",
            json={"status": "UP"},
            status_code=200,
            headers={"Content-Type": "application/problem+json"},
        )

        security = models.Security(bearer="test-token")
        sdk = AnncsuCoordinate(security=security)

        response = sdk.status.show_status()

        assert response.status == "UP"

    def test_show_status_healthy(self, httpx_mock: HTTPXMock):
        """Test healthy status response."""
        httpx_mock.add_response(
            method="GET",
            url=f"{BASE_URL}/status",
            json={"status": "healthy"},
            status_code=200,
            headers={"Content-Type": "application/problem+json"},
        )

        security = models.Security(bearer="test-token")
        sdk = AnncsuCoordinate(security=security)

        response = sdk.status.show_status()

        assert response.status == "healthy"

    def test_show_status_service_unavailable(self, httpx_mock: HTTPXMock):
        """Test 503 Service Unavailable error."""
        httpx_mock.add_response(
            method="GET",
            url=f"{BASE_URL}/status",
            json={
                "status": "DOWN",
            },
            status_code=503,
            headers={"Content-Type": "application/problem+json"},
        )

        security = models.Security(bearer="test-token")
        sdk = AnncsuCoordinate(security=security)

        with pytest.raises(errors.ServiceUnavailableError) as exc_info:
            sdk.status.show_status()

        assert exc_info.value.data.status == "DOWN"

    def test_show_status_generic_4xx_error(self, httpx_mock: HTTPXMock):
        """Test generic 4XX error handling."""
        httpx_mock.add_response(
            method="GET",
            url=f"{BASE_URL}/status",
            text="Bad Request",
            status_code=400,
        )

        security = models.Security(bearer="test-token")
        sdk = AnncsuCoordinate(security=security)

        with pytest.raises(errors.APIError) as exc_info:
            sdk.status.show_status()

        assert "API error occurred" in str(exc_info.value)

    def test_show_status_generic_5xx_error(self, httpx_mock: HTTPXMock):
        """Test generic 5XX error handling."""
        httpx_mock.add_response(
            method="GET",
            url=f"{BASE_URL}/status",
            text="Internal Server Error",
            status_code=500,
        )

        security = models.Security(bearer="test-token")
        sdk = AnncsuCoordinate(security=security)

        with pytest.raises(errors.APIError):
            sdk.status.show_status()

    def test_show_status_with_security(self, httpx_mock: HTTPXMock):
        """Test SDK operation with security configured."""
        httpx_mock.add_response(
            method="GET",
            url=f"{BASE_URL}/status",
            json={"status": "UP"},
            status_code=200,
            headers={"Content-Type": "application/problem+json"},
        )

        security = models.Security(bearer="my-pdnd-token")
        sdk = AnncsuCoordinate(security=security)

        response = sdk.status.show_status()

        assert response.status == "UP"

        # Verify the request was sent
        requests = httpx_mock.get_requests()
        assert len(requests) == 1
        assert requests[0].method == "GET"

    def test_show_status_without_security(self, httpx_mock: HTTPXMock):
        """Test status endpoint without security (should still work)."""
        httpx_mock.add_response(
            method="GET",
            url=f"{BASE_URL}/status",
            json={"status": "UP"},
            status_code=200,
            headers={"Content-Type": "application/problem+json"},
        )

        sdk = AnncsuCoordinate()  # No security

        response = sdk.status.show_status()

        assert response.status == "UP"


class TestShowStatusWithCustomServerUrl:
    """Tests for status with custom server URL."""

    def test_with_validation_environment(self, httpx_mock: HTTPXMock):
        """Test SDK with validation environment URL."""
        val_url = "https://modipa-val.agenziaentrate.it/govway/rest/in/AgenziaEntrate/anncsuaccessi/v1"

        httpx_mock.add_response(
            method="GET",
            url=f"{val_url}/status",
            json={"status": "UP"},
            status_code=200,
            headers={"Content-Type": "application/problem+json"},
        )

        security = models.Security(bearer="test-token")
        sdk = AnncsuCoordinate(security=security, server_url=val_url)

        response = sdk.status.show_status()

        assert response.status == "UP"

    def test_with_server_url_override_in_method(self, httpx_mock: HTTPXMock):
        """Test server URL override at method level."""
        custom_url = "https://custom-server.example.com/api/v1"

        httpx_mock.add_response(
            method="GET",
            url=f"{custom_url}/status",
            json={"status": "CUSTOM"},
            status_code=200,
            headers={"Content-Type": "application/problem+json"},
        )

        security = models.Security(bearer="test-token")
        sdk = AnncsuCoordinate(security=security)  # Default URL

        response = sdk.status.show_status(server_url=custom_url)

        assert response.status == "CUSTOM"


class TestShowStatusTimeout:
    """Tests for status endpoint timeout handling."""

    def test_show_status_with_custom_timeout(self, httpx_mock: HTTPXMock):
        """Test status with custom timeout."""
        httpx_mock.add_response(
            method="GET",
            url=f"{BASE_URL}/status",
            json={"status": "UP"},
            status_code=200,
            headers={"Content-Type": "application/problem+json"},
        )

        security = models.Security(bearer="test-token")
        sdk = AnncsuCoordinate(security=security)

        response = sdk.status.show_status(timeout_ms=5000)

        assert response.status == "UP"
