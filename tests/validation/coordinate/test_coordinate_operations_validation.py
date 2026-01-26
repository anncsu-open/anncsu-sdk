"""Validation tests for ANNCSU Coordinate API operations.

This test suite validates response schemas for the coordinate operations defined
in the OpenAPI specification against actual API responses.
"""

from pathlib import Path
from unittest.mock import Mock

import httpx
import pytest

from anncsu.common.validation import ResponseValidator


class TestGestioneCoordinateOperation:
    """Tests for gestionecoordinate operation (manage access coordinates)."""

    @pytest.fixture
    def spec_path(self):
        """Fixture providing path to OpenAPI spec."""
        return (
            Path(__file__).parent.parent.parent.parent
            / "oas"
            / "dev"
            / "Specifica API - ANNCSU - Aggiornamento coordinate.yml"
        )

    @pytest.fixture
    def validator(self, spec_path):
        """Fixture providing ResponseValidator instance."""
        return ResponseValidator(spec_path)

    def test_gestionecoordinate_success_200(self, validator):
        """Test validation of gestionecoordinate 200 response."""
        response = Mock(spec=httpx.Response)
        response.status_code = 200
        response.headers = {"content-type": "application/json"}
        response_data = {
            "esito": "OK",
            "messaggio": "Operazione completata con successo",
        }
        response.content = str(response_data).encode()
        response.json.return_value = response_data

        is_valid, errors = validator.validate_response(response, "gestionecoordinate")

        assert is_valid is True
        assert len(errors) == 0

    def test_gestionecoordinate_error_400(self, validator):
        """Test validation of gestionecoordinate 400 error response."""
        response = Mock(spec=httpx.Response)
        response.status_code = 400
        response.headers = {"content-type": "application/problem+json"}
        response_data = {
            "title": "Bad Request",
            "detail": "Invalid request parameters",
        }
        response.content = str(response_data).encode()
        response.json.return_value = response_data

        is_valid, errors = validator.validate_response(response, "gestionecoordinate")

        assert is_valid is True
        assert len(errors) == 0

    def test_gestionecoordinate_error_401(self, validator):
        """Test validation of gestionecoordinate 401 error response."""
        response = Mock(spec=httpx.Response)
        response.status_code = 401
        response.headers = {"content-type": "application/problem+json"}
        response_data = {
            "title": "Unauthorized",
            "detail": "Authentication required",
        }
        response.content = str(response_data).encode()
        response.json.return_value = response_data

        is_valid, errors = validator.validate_response(response, "gestionecoordinate")

        assert is_valid is True
        assert len(errors) == 0

    def test_gestionecoordinate_error_404(self, validator):
        """Test validation of gestionecoordinate 404 error response."""
        response = Mock(spec=httpx.Response)
        response.status_code = 404
        response.headers = {"content-type": "application/problem+json"}
        response_data = {"title": "Not Found", "detail": "Access not found"}
        response.content = str(response_data).encode()
        response.json.return_value = response_data

        is_valid, errors = validator.validate_response(response, "gestionecoordinate")

        assert is_valid is True
        assert len(errors) == 0

    def test_gestionecoordinate_error_500(self, validator):
        """Test validation of gestionecoordinate 500 error response."""
        response = Mock(spec=httpx.Response)
        response.status_code = 500
        response.headers = {"content-type": "application/problem+json"}
        response_data = {
            "title": "Internal Server Error",
            "detail": "An unexpected error occurred",
        }
        response.content = str(response_data).encode()
        response.json.return_value = response_data

        is_valid, errors = validator.validate_response(response, "gestionecoordinate")

        assert is_valid is True
        assert len(errors) == 0


class TestCoordinateStatusOperation:
    """Tests for status operation in Coordinate API."""

    @pytest.fixture
    def spec_path(self):
        """Fixture providing path to OpenAPI spec."""
        return (
            Path(__file__).parent.parent.parent.parent
            / "oas"
            / "dev"
            / "Specifica API - ANNCSU - Aggiornamento coordinate.yml"
        )

    @pytest.fixture
    def validator(self, spec_path):
        """Fixture providing ResponseValidator instance."""
        return ResponseValidator(spec_path)

    def test_show_status_success_200(self, validator):
        """Test validation of show_status 200 response."""
        response = Mock(spec=httpx.Response)
        response.status_code = 200
        response.headers = {"content-type": "application/problem+json"}
        response_data = {"status": "OK"}
        response.content = str(response_data).encode()
        response.json.return_value = response_data

        is_valid, errors = validator.validate_response(response, "show_status")

        assert is_valid is True
        assert len(errors) == 0

    def test_show_status_error_503(self, validator):
        """Test validation of show_status 503 error response."""
        response = Mock(spec=httpx.Response)
        response.status_code = 503
        response.headers = {"content-type": "application/problem+json"}
        response_data = {
            "title": "Service Unavailable",
            "detail": "Server is not available",
        }
        response.content = str(response_data).encode()
        response.json.return_value = response_data

        is_valid, errors = validator.validate_response(response, "show_status")

        assert is_valid is True
        assert len(errors) == 0


class TestCoordinateModelsValidation:
    """Tests for Coordinate models validation."""

    def test_richiesta_operazione_model_creation(self):
        """Test that RichiestaOperazione model can be created."""
        from anncsu.coordinate.models import RichiestaOperazione

        request = RichiestaOperazione()
        assert request is not None

    def test_risposta_operazione_model_creation(self):
        """Test that RispostaOperazione model can be created."""
        from anncsu.coordinate.models import RispostaOperazione

        response = RispostaOperazione()
        assert response is not None

    def test_security_model_creation(self):
        """Test that Security model can be created."""
        from anncsu.coordinate.models import Security

        security = Security(bearer_auth="test-token")
        assert security is not None
        assert security.bearer_auth == "test-token"

    def test_security_model_with_all_fields(self):
        """Test Security model with all optional fields."""
        from anncsu.coordinate.models import Security

        security = Security(
            bearer_auth="test-bearer",
            agid_jwt_signature="test-signature",
            agid_jwt_tracking_evidence="test-evidence",
        )
        assert security.bearer_auth == "test-bearer"
        assert security.agid_jwt_signature == "test-signature"
        assert security.agid_jwt_tracking_evidence == "test-evidence"


class TestCoordinateErrorsValidation:
    """Tests for Coordinate errors validation."""

    def test_risposta_errore_can_be_raised(self):
        """Test that RispostaErrore can be raised as an exception."""
        from anncsu.coordinate.errors import RispostaErrore

        assert issubclass(RispostaErrore, Exception)

    def test_api_error_can_be_raised(self):
        """Test that APIError can be raised as an exception."""
        from anncsu.coordinate.errors import APIError

        assert issubclass(APIError, Exception)

    def test_anncsu_error_is_base_error(self):
        """Test that APIError extends common AnncsuError."""
        from anncsu.common.errors import AnncsuError as CommonAnncsuError
        from anncsu.coordinate.errors import APIError

        assert issubclass(APIError, CommonAnncsuError)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
