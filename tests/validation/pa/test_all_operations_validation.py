"""Comprehensive validation tests for all 25 ANNCSU API operations.

This test suite validates response schemas for all operations defined in the
OpenAPI specification against actual API responses.
"""

from pathlib import Path
from unittest.mock import Mock

import httpx
import pytest

from anncsu.common.validation import ResponseValidator


class TestEsisteOdonimoOperations:
    """Tests for esisteodonimo operations (check if street name exists)."""

    @pytest.fixture
    def spec_path(self):
        """Fixture providing path to OpenAPI spec."""
        return (
            Path(__file__).parent.parent.parent.parent
            / "oas"
            / "dev"
            / "Specifica API - ANNCSU – Consultazione per le PA.yaml"
        )

    @pytest.fixture
    def validator(self, spec_path):
        """Fixture providing ResponseValidator instance."""
        return ResponseValidator(spec_path)

    def test_esiste_odonimo_get_query_param_success(self, validator):
        """Test validation of esisteOdonimoGetQueryParam 200 response."""
        response = Mock(spec=httpx.Response)
        response.status_code = 200
        response.headers = {"content-type": "application/json"}
        response.content = b'{"res": "esisteodonimo", "data": true}'
        response.json.return_value = {"res": "esisteodonimo", "data": True}

        is_valid, errors = validator.validate_response(
            response, "esisteOdonimoGetQueryParam"
        )

        assert is_valid is True
        assert len(errors) == 0

    def test_esiste_odonimo_post_success(self, validator):
        """Test validation of esisteOdonimoPost 200 response."""
        response = Mock(spec=httpx.Response)
        response.status_code = 200
        response.headers = {"content-type": "application/json"}
        response.content = b'{"res": "esisteodonimo", "data": false}'
        response.json.return_value = {"res": "esisteodonimo", "data": False}

        is_valid, errors = validator.validate_response(response, "esisteOdonimoPost")

        assert is_valid is True
        assert len(errors) == 0

    def test_esiste_odonimo_get_path_param_success(self, validator):
        """Test validation of esisteOdonimoGetPathParam 200 response."""
        response = Mock(spec=httpx.Response)
        response.status_code = 200
        response.headers = {"content-type": "application/json"}
        response.content = b'{"res": "esisteodonimo", "data": true}'
        response.json.return_value = {"res": "esisteodonimo", "data": True}

        is_valid, errors = validator.validate_response(
            response, "esisteOdonimoGetPathParam"
        )

        assert is_valid is True
        assert len(errors) == 0

    def test_esiste_odonimo_error_400(self, validator):
        """Test validation of esisteOdonimoGetQueryParam 400 error response."""
        response = Mock(spec=httpx.Response)
        response.status_code = 400
        response.headers = {"content-type": "application/problem+json"}
        response.content = (
            b'{"title": "Bad Request", "detail": "Invalid codcom parameter"}'
        )
        response.json.return_value = {
            "title": "Bad Request",
            "detail": "Invalid codcom parameter",
        }

        is_valid, errors = validator.validate_response(
            response, "esisteOdonimoGetQueryParam"
        )

        assert is_valid is True
        assert len(errors) == 0


class TestEsisteAccessoOperations:
    """Tests for esisteaccesso operations (check if civic number exists)."""

    @pytest.fixture
    def spec_path(self):
        """Fixture providing path to OpenAPI spec."""
        return (
            Path(__file__).parent.parent.parent.parent
            / "oas"
            / "dev"
            / "Specifica API - ANNCSU – Consultazione per le PA.yaml"
        )

    @pytest.fixture
    def validator(self, spec_path):
        """Fixture providing ResponseValidator instance."""
        return ResponseValidator(spec_path)

    def test_esiste_accesso_get_query_param_success(self, validator):
        """Test validation of esisteAccessoGetQueryParam 200 response."""
        response = Mock(spec=httpx.Response)
        response.status_code = 200
        response.headers = {"content-type": "application/json"}
        response.content = b'{"res": "esisteaccesso", "data": true}'
        response.json.return_value = {"res": "esisteaccesso", "data": True}

        is_valid, errors = validator.validate_response(
            response, "esisteAccessoGetQueryParam"
        )

        assert is_valid is True
        assert len(errors) == 0

    def test_esiste_accesso_post_success(self, validator):
        """Test validation of esisteAccessoPost 200 response."""
        response = Mock(spec=httpx.Response)
        response.status_code = 200
        response.headers = {"content-type": "application/json"}
        response.content = b'{"res": "esisteaccesso", "data": false}'
        response.json.return_value = {"res": "esisteaccesso", "data": False}

        is_valid, errors = validator.validate_response(response, "esisteAccessoPost")

        assert is_valid is True
        assert len(errors) == 0

    def test_esiste_accesso_get_path_param_success(self, validator):
        """Test validation of esisteAccessoGetPathParam 200 response."""
        response = Mock(spec=httpx.Response)
        response.status_code = 200
        response.headers = {"content-type": "application/json"}
        response.content = b'{"res": "esisteaccesso", "data": true}'
        response.json.return_value = {"res": "esisteaccesso", "data": True}

        is_valid, errors = validator.validate_response(
            response, "esisteAccessoGetPathParam"
        )

        assert is_valid is True
        assert len(errors) == 0


class TestElencoOdonimiOperations:
    """Tests for elencoodonimi operations (list street names)."""

    @pytest.fixture
    def spec_path(self):
        """Fixture providing path to OpenAPI spec."""
        return (
            Path(__file__).parent.parent.parent.parent
            / "oas"
            / "dev"
            / "Specifica API - ANNCSU – Consultazione per le PA.yaml"
        )

    @pytest.fixture
    def validator(self, spec_path):
        """Fixture providing ResponseValidator instance."""
        return ResponseValidator(spec_path)

    def test_elenco_odonimi_get_query_param_success(self, validator):
        """Test validation of elencoOdonimiGetQueryParam 200 response."""
        response = Mock(spec=httpx.Response)
        response.status_code = 200
        response.headers = {"content-type": "application/json"}
        response_data = {
            "res": "elencoodonimi",
            "data": [
                {
                    "dug": "VIA",
                    "denomuff": "ROMA",
                    "denomloc": None,
                    "denomlingua1": None,
                    "denomlingua2": None,
                }
            ],
        }
        response.content = str(response_data).encode()
        response.json.return_value = response_data

        is_valid, errors = validator.validate_response(
            response, "elencoOdonimiGetQueryParam"
        )

        assert is_valid is True
        assert len(errors) == 0

    def test_elenco_odonimi_post_success(self, validator):
        """Test validation of elencoOdonimiPost 200 response."""
        response = Mock(spec=httpx.Response)
        response.status_code = 200
        response.headers = {"content-type": "application/json"}
        response_data = {
            "res": "elencoodonimi",
            "data": [
                {
                    "dug": "AUTOSTRADA",
                    "denomuff": "ROMA AEROPORTO DI FIUMICINO",
                    "denomloc": "ROMA-FIUMICINO",
                    "denomlingua1": None,
                    "denomlingua2": None,
                }
            ],
        }
        response.content = str(response_data).encode()
        response.json.return_value = response_data

        is_valid, errors = validator.validate_response(response, "elencoOdonimiPost")

        assert is_valid is True
        assert len(errors) == 0

    def test_elenco_odonimi_get_path_param_success(self, validator):
        """Test validation of elencoOdonimiGetPathParam 200 response."""
        response = Mock(spec=httpx.Response)
        response.status_code = 200
        response.headers = {"content-type": "application/json"}
        response_data = {
            "res": "elencoodonimi",
            "data": [
                {
                    "dug": "PIAZZA",
                    "denomuff": "SAN PIETRO",
                    "denomloc": None,
                    "denomlingua1": None,
                    "denomlingua2": None,
                }
            ],
        }
        response.content = str(response_data).encode()
        response.json.return_value = response_data

        is_valid, errors = validator.validate_response(
            response, "elencoOdonimiGetPathParam"
        )

        assert is_valid is True
        assert len(errors) == 0

    def test_elenco_odonimi_not_found_404(self, validator):
        """Test validation of elencoOdonimiGetQueryParam 404 response."""
        response = Mock(spec=httpx.Response)
        response.status_code = 404
        response.headers = {"content-type": "application/problem+json"}
        response.content = b'{"title": "Not Found", "detail": "No streets found"}'
        response.json.return_value = {
            "title": "Not Found",
            "detail": "No streets found",
        }

        is_valid, errors = validator.validate_response(
            response, "elencoOdonimiGetQueryParam"
        )

        assert is_valid is True
        assert len(errors) == 0


class TestElencoAccessiOperations:
    """Tests for elencoaccessi operations (list civic numbers)."""

    @pytest.fixture
    def spec_path(self):
        """Fixture providing path to OpenAPI spec."""
        return (
            Path(__file__).parent.parent.parent.parent
            / "oas"
            / "dev"
            / "Specifica API - ANNCSU – Consultazione per le PA.yaml"
        )

    @pytest.fixture
    def validator(self, spec_path):
        """Fixture providing ResponseValidator instance."""
        return ResponseValidator(spec_path)

    def test_elenco_accessi_get_query_param_success(self, validator):
        """Test validation of elencoAccessiGetQueryParam 200 response."""
        response = Mock(spec=httpx.Response)
        response.status_code = 200
        response.headers = {"content-type": "application/json"}
        response_data = {
            "res": "elencoaccessi",
            "data": [
                {
                    "civico": "1",
                    "esp": "A",
                    "specif": "ROSSO",
                    "metrico": "1200",
                }
            ],
        }
        response.content = str(response_data).encode()
        response.json.return_value = response_data

        is_valid, errors = validator.validate_response(
            response, "elencoAccessiGetQueryParam"
        )

        assert is_valid is True
        assert len(errors) == 0

    def test_elenco_accessi_post_success(self, validator):
        """Test validation of elencoAccessiPost 200 response."""
        response = Mock(spec=httpx.Response)
        response.status_code = 200
        response.headers = {"content-type": "application/json"}
        response_data = {
            "res": "elencoaccessi",
            "data": [{"civico": "42", "esp": "", "specif": "", "metrico": "5400"}],
        }
        response.content = str(response_data).encode()
        response.json.return_value = response_data

        is_valid, errors = validator.validate_response(response, "elencoAccessiPost")

        assert is_valid is True
        assert len(errors) == 0

    def test_elenco_accessi_get_path_param_success(self, validator):
        """Test validation of elencoAccessiGetPathParam 200 response."""
        response = Mock(spec=httpx.Response)
        response.status_code = 200
        response.headers = {"content-type": "application/json"}
        response_data = {
            "res": "elencoaccessi",
            "data": [{"civico": "10", "esp": "B", "specif": "BIS", "metrico": "2500"}],
        }
        response.content = str(response_data).encode()
        response.json.return_value = response_data

        is_valid, errors = validator.validate_response(
            response, "elencoAccessiGetPathParam"
        )

        assert is_valid is True
        assert len(errors) == 0


class TestElencoodonimiProgOperations:
    """Tests for elencoodonimiprog operations (list streets with national progressive)."""

    @pytest.fixture
    def spec_path(self):
        """Fixture providing path to OpenAPI spec."""
        return (
            Path(__file__).parent.parent.parent.parent
            / "oas"
            / "dev"
            / "Specifica API - ANNCSU – Consultazione per le PA.yaml"
        )

    @pytest.fixture
    def validator(self, spec_path):
        """Fixture providing ResponseValidator instance."""
        return ResponseValidator(spec_path)

    def test_elencoodonimi_prog_get_query_param_success(self, validator):
        """Test validation of elencoodonimiprogGetQueryParam 200 response."""
        response = Mock(spec=httpx.Response)
        response.status_code = 200
        response.headers = {"content-type": "application/json"}
        response_data = {
            "res": "elencoodonimiprog",
            "data": [
                {
                    "prognaz": "919572",
                    "dug": "AUTOSTRADA",
                    "denomuff": "ROMA AEROPORTO DI FIUMICINO",
                    "denomloc": None,
                    "denomlingua1": None,
                    "denomlingua2": None,
                }
            ],
        }
        response.content = str(response_data).encode()
        response.json.return_value = response_data

        is_valid, errors = validator.validate_response(
            response, "elencoodonimiprogGetQueryParam"
        )

        assert is_valid is True
        assert len(errors) == 0

    def test_elencoodonimi_prog_post_success(self, validator):
        """Test validation of elencoodonimiprogPost 200 response."""
        response = Mock(spec=httpx.Response)
        response.status_code = 200
        response.headers = {"content-type": "application/json"}
        response_data = {
            "res": "elencoodonimiprog",
            "data": [
                {
                    "prognaz": "123456",
                    "dug": "VIA",
                    "denomuff": "GARIBALDI",
                    "denomloc": None,
                    "denomlingua1": None,
                    "denomlingua2": None,
                }
            ],
        }
        response.content = str(response_data).encode()
        response.json.return_value = response_data

        is_valid, errors = validator.validate_response(
            response, "elencoodonimiprogPost"
        )

        assert is_valid is True
        assert len(errors) == 0

    def test_elencoodonimi_prog_get_path_param_success(self, validator):
        """Test validation of elencoodonimiprogGetPathParam 200 response."""
        response = Mock(spec=httpx.Response)
        response.status_code = 200
        response.headers = {"content-type": "application/json"}
        response_data = {
            "res": "elencoodonimiprog",
            "data": [
                {
                    "prognaz": "789012",
                    "dug": "CORSO",
                    "denomuff": "VITTORIO EMANUELE",
                    "denomloc": "C. VITTORIO EMANUELE",
                    "denomlingua1": None,
                    "denomlingua2": None,
                }
            ],
        }
        response.content = str(response_data).encode()
        response.json.return_value = response_data

        is_valid, errors = validator.validate_response(
            response, "elencoodonimiprogGetPathParam"
        )

        assert is_valid is True
        assert len(errors) == 0


class TestElencoaccessiProgOperations:
    """Tests for elencoaccessiprog operations (list civic numbers with national progressive)."""

    @pytest.fixture
    def spec_path(self):
        """Fixture providing path to OpenAPI spec."""
        return (
            Path(__file__).parent.parent.parent.parent
            / "oas"
            / "dev"
            / "Specifica API - ANNCSU – Consultazione per le PA.yaml"
        )

    @pytest.fixture
    def validator(self, spec_path):
        """Fixture providing ResponseValidator instance."""
        return ResponseValidator(spec_path)

    def test_elencoaccessiprog_get_query_param_success(self, validator):
        """Test validation of elencoaccessiprogGetQueryParam 200 response."""
        response = Mock(spec=httpx.Response)
        response.status_code = 200
        response.headers = {"content-type": "application/json"}
        response_data = {
            "res": "elencoaccessiprog",
            "data": [
                {
                    "prognazacc": "6744962",
                    "civico": "1",
                    "esp": "A",
                    "specif": "ROSSO",
                    "metrico": "1200",
                    "coordX": "12.5349017",
                    "coordY": "44.0191923",
                    "quota": "50",
                    "metodo": "4",
                }
            ],
        }
        response.content = str(response_data).encode()
        response.json.return_value = response_data

        is_valid, errors = validator.validate_response(
            response, "elencoaccessiprogGetQueryParam"
        )

        assert is_valid is True
        assert len(errors) == 0

    def test_elencoaccessiprog_post_success(self, validator):
        """Test validation of elencoaccessiprogPost 200 response."""
        response = Mock(spec=httpx.Response)
        response.status_code = 200
        response.headers = {"content-type": "application/json"}
        response_data = {
            "res": "elencoaccessiprog",
            "data": [
                {
                    "prognazacc": "1234567",
                    "civico": "42",
                    "esp": "",
                    "specif": "",
                    "metrico": "3000",
                    "coordX": "11.2567890",
                    "coordY": "43.7692105",
                    "quota": "100",
                    "metodo": "3",
                }
            ],
        }
        response.content = str(response_data).encode()
        response.json.return_value = response_data

        is_valid, errors = validator.validate_response(
            response, "elencoaccessiprogPost"
        )

        assert is_valid is True
        assert len(errors) == 0

    def test_elencoaccessiprog_get_path_param_success(self, validator):
        """Test validation of elencoaccessiprogGetPathParam 200 response."""
        response = Mock(spec=httpx.Response)
        response.status_code = 200
        response.headers = {"content-type": "application/json"}
        response_data = {
            "res": "elencoaccessiprog",
            "data": [
                {
                    "prognazacc": "9876543",
                    "civico": "100",
                    "esp": "C",
                    "specif": "INTERNO 5",
                    "metrico": "8000",
                    "coordX": "12.4963655",
                    "coordY": "41.9027835",
                    "quota": "25",
                    "metodo": "2",
                }
            ],
        }
        response.content = str(response_data).encode()
        response.json.return_value = response_data

        is_valid, errors = validator.validate_response(
            response, "elencoaccessiprogGetPathParam"
        )

        assert is_valid is True
        assert len(errors) == 0


class TestPrognazAreaOperations:
    """Tests for prognazarea operations (get street by national progressive)."""

    @pytest.fixture
    def spec_path(self):
        """Fixture providing path to OpenAPI spec."""
        return (
            Path(__file__).parent.parent.parent.parent
            / "oas"
            / "dev"
            / "Specifica API - ANNCSU – Consultazione per le PA.yaml"
        )

    @pytest.fixture
    def validator(self, spec_path):
        """Fixture providing ResponseValidator instance."""
        return ResponseValidator(spec_path)

    def test_prognazarea_get_query_param_success(self, validator):
        """Test validation of prognazareaGetQueryParam 200 response."""
        response = Mock(spec=httpx.Response)
        response.status_code = 200
        response.headers = {"content-type": "application/json"}
        response_data = {
            "res": "prognazarea",
            "data": [
                {
                    "prognaz": "919572",
                    "dug": "AUTOSTRADA",
                    "denomuff": "ROMA AEROPORTO DI FIUMICINO",
                    "denomloc": None,
                    "denomlingua1": None,
                    "denomlingua2": None,
                }
            ],
        }
        response.content = str(response_data).encode()
        response.json.return_value = response_data

        is_valid, errors = validator.validate_response(
            response, "prognazareaGetQueryParam"
        )

        assert is_valid is True
        assert len(errors) == 0

    def test_prognazarea_post_success(self, validator):
        """Test validation of prognazareaPost 200 response."""
        response = Mock(spec=httpx.Response)
        response.status_code = 200
        response.headers = {"content-type": "application/json"}
        response_data = {
            "res": "prognazarea",
            "data": [
                {
                    "prognaz": "111222",
                    "dug": "VIA",
                    "denomuff": "NAZIONALE",
                    "denomloc": None,
                    "denomlingua1": None,
                    "denomlingua2": None,
                }
            ],
        }
        response.content = str(response_data).encode()
        response.json.return_value = response_data

        is_valid, errors = validator.validate_response(response, "prognazareaPost")

        assert is_valid is True
        assert len(errors) == 0

    def test_prognazarea_get_path_param_success(self, validator):
        """Test validation of prognazareaGetPathParam 200 response."""
        response = Mock(spec=httpx.Response)
        response.status_code = 200
        response.headers = {"content-type": "application/json"}
        response_data = {
            "res": "prognazarea",
            "data": [
                {
                    "prognaz": "333444",
                    "dug": "PIAZZA",
                    "denomuff": "DEL POPOLO",
                    "denomloc": "P.ZA DEL POPOLO",
                    "denomlingua1": None,
                    "denomlingua2": None,
                }
            ],
        }
        response.content = str(response_data).encode()
        response.json.return_value = response_data

        is_valid, errors = validator.validate_response(
            response, "prognazareaGetPathParam"
        )

        assert is_valid is True
        assert len(errors) == 0


class TestPrognazAccOperations:
    """Tests for prognazacc operations (get access by national progressive access ID)."""

    @pytest.fixture
    def spec_path(self):
        """Fixture providing path to OpenAPI spec."""
        return (
            Path(__file__).parent.parent.parent.parent
            / "oas"
            / "dev"
            / "Specifica API - ANNCSU – Consultazione per le PA.yaml"
        )

    @pytest.fixture
    def validator(self, spec_path):
        """Fixture providing ResponseValidator instance."""
        return ResponseValidator(spec_path)

    def test_prognazacc_get_query_param_success(self, validator):
        """Test validation of prognazaccGetQueryParam 200 response."""
        response = Mock(spec=httpx.Response)
        response.status_code = 200
        response.headers = {"content-type": "application/json"}
        response_data = {
            "res": "elencoodonimiprog",
            "data": [
                {
                    "prognaz": "919572",
                    "dug": "AUTOSTRADA",
                    "denomuff": "ROMA AEROPORTO DI FIUMICINO",
                    "denomloc": None,
                    "denomlingua1": None,
                    "denomlingua2": None,
                    "prognazacc": "6744962",
                    "civico": "1",
                    "esp": "A",
                    "specif": "ROSSO",
                    "metrico": "1200",
                    "coordX": "12.5349017",
                    "coordY": "44.0191923",
                    "quota": "50",
                    "metodo": "4",
                }
            ],
        }
        response.content = str(response_data).encode()
        response.json.return_value = response_data

        is_valid, errors = validator.validate_response(
            response, "prognazaccGetQueryParam"
        )

        assert is_valid is True
        assert len(errors) == 0

    def test_prognazacc_post_success(self, validator):
        """Test validation of prognazaccPost 200 response."""
        response = Mock(spec=httpx.Response)
        response.status_code = 200
        response.headers = {"content-type": "application/json"}
        response_data = {
            "res": "elencoodonimiprog",
            "data": [
                {
                    "prognaz": "123456",
                    "dug": "VIA",
                    "denomuff": "CAVOUR",
                    "denomloc": None,
                    "denomlingua1": None,
                    "denomlingua2": None,
                    "prognazacc": "7891011",
                    "civico": "25",
                    "esp": "",
                    "specif": "",
                    "metrico": "2400",
                    "coordX": "11.3426163",
                    "coordY": "44.4938100",
                    "quota": "75",
                    "metodo": "3",
                }
            ],
        }
        response.content = str(response_data).encode()
        response.json.return_value = response_data

        is_valid, errors = validator.validate_response(response, "prognazaccPost")

        assert is_valid is True
        assert len(errors) == 0

    def test_prognazacc_get_path_param_success(self, validator):
        """Test validation of prognazaccGetPathParam 200 response."""
        response = Mock(spec=httpx.Response)
        response.status_code = 200
        response.headers = {"content-type": "application/json"}
        response_data = {
            "res": "elencoodonimiprog",
            "data": [
                {
                    "prognaz": "789012",
                    "dug": "CORSO",
                    "denomuff": "ITALIA",
                    "denomloc": "C. ITALIA",
                    "denomlingua1": None,
                    "denomlingua2": None,
                    "prognazacc": "1213141",
                    "civico": "50",
                    "esp": "B",
                    "specif": "BIS",
                    "metrico": "4200",
                    "coordX": "9.1859243",
                    "coordY": "45.4654219",
                    "quota": "120",
                    "metodo": "1",
                }
            ],
        }
        response.content = str(response_data).encode()
        response.json.return_value = response_data

        is_valid, errors = validator.validate_response(
            response, "prognazaccGetPathParam"
        )

        assert is_valid is True
        assert len(errors) == 0


class TestStatusOperation:
    """Tests for status operation (application health check)."""

    @pytest.fixture
    def spec_path(self):
        """Fixture providing path to OpenAPI spec."""
        return (
            Path(__file__).parent.parent.parent.parent
            / "oas"
            / "dev"
            / "Specifica API - ANNCSU – Consultazione per le PA.yaml"
        )

    @pytest.fixture
    def validator(self, spec_path):
        """Fixture providing ResponseValidator instance."""
        return ResponseValidator(spec_path)

    def test_status_success_200(self, validator):
        """Test validation of show_status 200 response."""
        response = Mock(spec=httpx.Response)
        response.status_code = 200
        response.headers = {"content-type": "application/problem+json"}
        response.content = b'{"status": "OK"}'
        response.json.return_value = {"status": "OK"}

        is_valid, errors = validator.validate_response(response, "show_status")

        assert is_valid is True
        assert len(errors) == 0

    def test_status_service_unavailable_503(self, validator):
        """Test validation of show_status 503 response."""
        response = Mock(spec=httpx.Response)
        response.status_code = 503
        response.headers = {"content-type": "application/problem+json"}
        response.content = b'{"status": "Service Unavailable"}'
        response.json.return_value = {"status": "Service Unavailable"}

        is_valid, errors = validator.validate_response(response, "show_status")

        assert is_valid is True
        assert len(errors) == 0


class TestErrorResponsesAllOperations:
    """Tests for error responses across all operations."""

    @pytest.fixture
    def spec_path(self):
        """Fixture providing path to OpenAPI spec."""
        return (
            Path(__file__).parent.parent.parent.parent
            / "oas"
            / "dev"
            / "Specifica API - ANNCSU – Consultazione per le PA.yaml"
        )

    @pytest.fixture
    def validator(self, spec_path):
        """Fixture providing ResponseValidator instance."""
        return ResponseValidator(spec_path)

    @pytest.mark.parametrize(
        "operation_id",
        [
            "esisteOdonimoGetQueryParam",
            "esisteAccessoPost",
            "elencoOdonimiGetPathParam",
            "elencoAccessiGetQueryParam",
            "elencoodonimiprogPost",
            "elencoaccessiprogGetPathParam",
            "prognazareaGetQueryParam",
            "prognazaccPost",
        ],
    )
    def test_400_bad_request_error(self, validator, operation_id):
        """Test validation of 400 Bad Request error for various operations."""
        response = Mock(spec=httpx.Response)
        response.status_code = 400
        response.headers = {"content-type": "application/problem+json"}
        response.content = (
            b'{"title": "Bad Request", "detail": "Invalid parameter value"}'
        )
        response.json.return_value = {
            "title": "Bad Request",
            "detail": "Invalid parameter value",
        }

        is_valid, errors = validator.validate_response(response, operation_id)

        assert is_valid is True
        assert len(errors) == 0

    @pytest.mark.parametrize(
        "operation_id",
        [
            "elencoOdonimiGetQueryParam",
            "elencoAccessiPost",
            "elencoodonimiprogGetPathParam",
            "elencoaccessiprogGetQueryParam",
            "prognazareaPost",
            "prognazaccGetPathParam",
        ],
    )
    def test_404_not_found_error(self, validator, operation_id):
        """Test validation of 404 Not Found error for list operations."""
        response = Mock(spec=httpx.Response)
        response.status_code = 404
        response.headers = {"content-type": "application/problem+json"}
        response.content = b'{"title": "Not Found", "detail": "Resource not found"}'
        response.json.return_value = {
            "title": "Not Found",
            "detail": "Resource not found",
        }

        is_valid, errors = validator.validate_response(response, operation_id)

        assert is_valid is True
        assert len(errors) == 0

    @pytest.mark.parametrize(
        "operation_id",
        [
            "esisteOdonimoPost",
            "esisteAccessoPost",
            "elencoOdonimiPost",
            "elencoAccessiPost",
            "elencoodonimiprogPost",
            "elencoaccessiprogPost",
            "prognazareaPost",
            "prognazaccPost",
        ],
    )
    def test_422_unprocessable_entity_error(self, validator, operation_id):
        """Test validation of 422 Unprocessable Entity error for POST operations."""
        response = Mock(spec=httpx.Response)
        response.status_code = 422
        response.headers = {"content-type": "application/problem+json"}
        response.content = (
            b'{"title": "Unprocessable Entity", "detail": "Invalid JSON body"}'
        )
        response.json.return_value = {
            "title": "Unprocessable Entity",
            "detail": "Invalid JSON body",
        }

        is_valid, errors = validator.validate_response(response, operation_id)

        assert is_valid is True
        assert len(errors) == 0

    @pytest.mark.parametrize(
        "operation_id",
        [
            "esisteOdonimoGetQueryParam",
            "elencoOdonimiPost",
            "elencoaccessiprogGetPathParam",
            "prognazareaGetQueryParam",
        ],
    )
    def test_500_internal_server_error(self, validator, operation_id):
        """Test validation of 500 Internal Server Error."""
        response = Mock(spec=httpx.Response)
        response.status_code = 500
        response.headers = {"content-type": "application/problem+json"}
        response.content = (
            b'{"title": "Internal Server Error", "detail": "Server error occurred"}'
        )
        response.json.return_value = {
            "title": "Internal Server Error",
            "detail": "Server error occurred",
        }

        is_valid, errors = validator.validate_response(response, operation_id)

        assert is_valid is True
        assert len(errors) == 0
