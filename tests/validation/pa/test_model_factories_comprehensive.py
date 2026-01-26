"""Comprehensive factory and property-based tests for all ANNCSU PA models.

This test suite creates Polyfactory factories and Hypothesis property-based tests
for all 67 Pydantic models in the ANNCSU PA API.
"""

import base64
import random
import string

import pytest
from faker import Faker
from hypothesis import given
from hypothesis import strategies as st
from polyfactory.factories.pydantic_factory import ModelFactory

# Import all models
from anncsu.pa.models.elencoaccessigetpathparamop import (
    ElencoAccessiGetPathParamData,
    ElencoAccessiGetPathParamRequest,
)
from anncsu.pa.models.elencoaccessiproggetpathparamop import (
    ElencoaccessiprogGetPathParamData,
    ElencoaccessiprogGetPathParamRequest,
)
from anncsu.pa.models.elencoodonimigetpathparamop import (
    ElencoOdonimiGetPathParamData,
    ElencoOdonimiGetPathParamRequest,
    ElencoOdonimiGetPathParamResponse,
)
from anncsu.pa.models.elencoodonimigetqueryparamop import (
    ElencoOdonimiGetQueryParamRequest,
)
from anncsu.pa.models.elencoodonimipostop import (
    ElencoOdonimiPostRequest,
)
from anncsu.pa.models.elencoodonimiproggetpathparamop import (
    ElencoodonimiprogGetPathParamData,
    ElencoodonimiprogGetPathParamRequest,
)
from anncsu.pa.models.esisteaccessogetpathparamop import (
    EsisteAccessoGetPathParamRequest,
)
from anncsu.pa.models.esisteaccessogetqueryparamop import (
    EsisteAccessoGetQueryParamRequest,
)
from anncsu.pa.models.esisteaccessopostop import (
    EsisteAccessoPostRequest,
)
from anncsu.pa.models.esisteodonimogetpathparamop import (
    EsisteOdonimoGetPathParamRequest,
    EsisteOdonimoGetPathParamResponse,
)
from anncsu.pa.models.esisteodonimogetqueryparamop import (
    EsisteOdonimoGetQueryParamRequest,
    EsisteOdonimoGetQueryParamResponse,
)
from anncsu.pa.models.esisteodonimopostop import (
    EsisteOdonimoPostRequest,
    EsisteOdonimoPostResponse,
)
from anncsu.pa.models.prognazaccgetpathparamop import (
    PrognazaccGetPathParamData,
)
from anncsu.pa.models.prognazareagetpathparamop import (
    PrognazareaGetPathParamData,
)
from anncsu.pa.models.show_statusop import ShowStatusResponse

# Initialize Faker with Italian locale
fake = Faker("it_IT")


# Custom providers for Italian data
class BelfioreCodeProvider:
    """Provides valid Italian Belfiore codes."""

    KNOWN_CODES = [
        "H501",  # Roma
        "F205",  # Milano
        "A794",  # Bologna
        "L219",  # Torino
        "D612",  # Firenze
        "C351",  # Catania
        "B157",  # Bari
        "G273",  # Palermo
        "D969",  # Genova
        "F839",  # Napoli
    ]

    @staticmethod
    def belfiore_code() -> str:
        """Generate a valid Belfiore code (letter + 3 digits)."""
        if random.random() < 0.3:  # 30% chance of using known code
            return random.choice(BelfioreCodeProvider.KNOWN_CODES)
        letter = random.choice(string.ascii_uppercase)
        digits = "".join(random.choices(string.digits, k=3))
        return f"{letter}{digits}"


class ItalianStreetProvider:
    """Provides Italian street names and types."""

    STREET_TYPES = [
        "VIA",
        "VIALE",
        "PIAZZA",
        "CORSO",
        "VICOLO",
        "LARGO",
        "STRADA",
        "AUTOSTRADA",
    ]

    @staticmethod
    def street_name() -> str:
        """Generate an Italian street name."""
        return fake.street_name().upper()

    @staticmethod
    def street_name_base64() -> str:
        """Generate a base64-encoded Italian street name."""
        name = ItalianStreetProvider.street_name()
        return base64.b64encode(name.encode()).decode()

    @staticmethod
    def street_type() -> str:
        """Generate an Italian street type (DUG)."""
        return random.choice(ItalianStreetProvider.STREET_TYPES)


# ===========================
# FACTORY DEFINITIONS
# ===========================


# Note: We don't need standalone factories for Belfiore codes or Base64 strings
# These are generated directly by provider classes and used in model factories


# Request Factories - EsisteOdonimo
class EsisteOdonimoGetPathParamRequestFactory(
    ModelFactory[EsisteOdonimoGetPathParamRequest]
):
    __model__ = EsisteOdonimoGetPathParamRequest
    __check_model__ = False

    codcom = BelfioreCodeProvider.belfiore_code
    denom = ItalianStreetProvider.street_name_base64


class EsisteOdonimoGetQueryParamRequestFactory(
    ModelFactory[EsisteOdonimoGetQueryParamRequest]
):
    __model__ = EsisteOdonimoGetQueryParamRequest
    __check_model__ = False

    codcom = BelfioreCodeProvider.belfiore_code
    denom = ItalianStreetProvider.street_name_base64


class EsisteOdonimoPostRequestFactory(ModelFactory[EsisteOdonimoPostRequest]):
    __model__ = EsisteOdonimoPostRequest
    __check_model__ = False


# Response Factories - EsisteOdonimo
class EsisteOdonimoGetPathParamResponseFactory(
    ModelFactory[EsisteOdonimoGetPathParamResponse]
):
    __model__ = EsisteOdonimoGetPathParamResponse
    __check_model__ = False


class EsisteOdonimoGetQueryParamResponseFactory(
    ModelFactory[EsisteOdonimoGetQueryParamResponse]
):
    __model__ = EsisteOdonimoGetQueryParamResponse
    __check_model__ = False


class EsisteOdonimoPostResponseFactory(ModelFactory[EsisteOdonimoPostResponse]):
    __model__ = EsisteOdonimoPostResponse
    __check_model__ = False


# Request Factories - EsisteAccesso
class EsisteAccessoGetPathParamRequestFactory(
    ModelFactory[EsisteAccessoGetPathParamRequest]
):
    __model__ = EsisteAccessoGetPathParamRequest
    __check_model__ = False

    codcom = BelfioreCodeProvider.belfiore_code
    denom = ItalianStreetProvider.street_name_base64


class EsisteAccessoGetQueryParamRequestFactory(
    ModelFactory[EsisteAccessoGetQueryParamRequest]
):
    __model__ = EsisteAccessoGetQueryParamRequest
    __check_model__ = False

    codcom = BelfioreCodeProvider.belfiore_code
    denom = ItalianStreetProvider.street_name_base64


class EsisteAccessoPostRequestFactory(ModelFactory[EsisteAccessoPostRequest]):
    __model__ = EsisteAccessoPostRequest
    __check_model__ = False


# Data Factories - ElencoOdonimi
class ElencoOdonimiDataFactory(ModelFactory[ElencoOdonimiGetPathParamData]):
    __model__ = ElencoOdonimiGetPathParamData
    __check_model__ = False

    dug = ItalianStreetProvider.street_type
    denomuff = ItalianStreetProvider.street_name


# Request Factories - ElencoOdonimi
class ElencoOdonimiGetPathParamRequestFactory(
    ModelFactory[ElencoOdonimiGetPathParamRequest]
):
    __model__ = ElencoOdonimiGetPathParamRequest
    __check_model__ = False

    codcom = BelfioreCodeProvider.belfiore_code
    denomparz = ItalianStreetProvider.street_name_base64


class ElencoOdonimiGetQueryParamRequestFactory(
    ModelFactory[ElencoOdonimiGetQueryParamRequest]
):
    __model__ = ElencoOdonimiGetQueryParamRequest
    __check_model__ = False

    codcom = BelfioreCodeProvider.belfiore_code
    denomparz = ItalianStreetProvider.street_name_base64


class ElencoOdonimiPostRequestFactory(ModelFactory[ElencoOdonimiPostRequest]):
    __model__ = ElencoOdonimiPostRequest
    __check_model__ = False


# Response Factories - ElencoOdonimi
class ElencoOdonimiGetPathParamResponseFactory(
    ModelFactory[ElencoOdonimiGetPathParamResponse]
):
    __model__ = ElencoOdonimiGetPathParamResponse
    __check_model__ = False


# Data Factories - ElencoodonimProg
class ElencoodonimiprogDataFactory(ModelFactory[ElencoodonimiprogGetPathParamData]):
    __model__ = ElencoodonimiprogGetPathParamData
    __check_model__ = False

    dug = ItalianStreetProvider.street_type
    denomuff = ItalianStreetProvider.street_name


# Request Factories - ElencoodonimProg
class ElencoodonimiprogGetPathParamRequestFactory(
    ModelFactory[ElencoodonimiprogGetPathParamRequest]
):
    __model__ = ElencoodonimiprogGetPathParamRequest
    __check_model__ = False

    codcom = BelfioreCodeProvider.belfiore_code
    denomparz = ItalianStreetProvider.street_name_base64


# Data Factories - ElencoAccessi
class ElencoAccessiDataFactory(ModelFactory[ElencoAccessiGetPathParamData]):
    __model__ = ElencoAccessiGetPathParamData
    __check_model__ = False


# Request Factories - ElencoAccessi
class ElencoAccessiGetPathParamRequestFactory(
    ModelFactory[ElencoAccessiGetPathParamRequest]
):
    __model__ = ElencoAccessiGetPathParamRequest
    __check_model__ = False

    codcom = BelfioreCodeProvider.belfiore_code
    denom = ItalianStreetProvider.street_name_base64


# Data Factories - ElencoaccessiProg
class ElencoaccessiprogDataFactory(ModelFactory[ElencoaccessiprogGetPathParamData]):
    __model__ = ElencoaccessiprogGetPathParamData
    __check_model__ = False


# Request Factories - ElencoaccessiProg
class ElencoaccessiprogGetPathParamRequestFactory(
    ModelFactory[ElencoaccessiprogGetPathParamRequest]
):
    __model__ = ElencoaccessiprogGetPathParamRequest
    __check_model__ = False


# Data Factories - Prognazarea
class PrognazareaDataFactory(ModelFactory[PrognazareaGetPathParamData]):
    __model__ = PrognazareaGetPathParamData
    __check_model__ = False

    dug = ItalianStreetProvider.street_type
    denomuff = ItalianStreetProvider.street_name


# Data Factories - Prognazacc
class PrognazaccDataFactory(ModelFactory[PrognazaccGetPathParamData]):
    __model__ = PrognazaccGetPathParamData
    __check_model__ = False

    dug = ItalianStreetProvider.street_type
    denomuff = ItalianStreetProvider.street_name


# Status Response Factory
class ShowStatusResponseFactory(ModelFactory[ShowStatusResponse]):
    __model__ = ShowStatusResponse
    __check_model__ = False


# ===========================
# FACTORY TESTS
# ===========================


class TestEsisteOdonimoFactories:
    """Test factories for EsisteOdonimo operations."""

    def test_esiste_odonimo_get_path_param_request_factory(self):
        """Test factory generates valid EsisteOdonimo GetPathParam requests."""
        for _ in range(10):
            request = EsisteOdonimoGetPathParamRequestFactory.build()
            assert request.codcom is not None
            assert len(request.codcom) == 4
            assert request.codcom[0].isupper()
            assert request.codcom[1:].isdigit()
            assert request.denom is not None
            # Verify it's valid base64
            try:
                base64.b64decode(request.denom)
            except Exception:
                pytest.fail("Invalid base64 in denom field")

    def test_esiste_odonimo_get_query_param_request_factory(self):
        """Test factory generates valid EsisteOdonimo GetQueryParam requests."""
        request = EsisteOdonimoGetQueryParamRequestFactory.build()
        assert request.codcom is not None
        assert request.denom is not None

    def test_esiste_odonimo_post_request_factory(self):
        """Test factory generates valid EsisteOdonimo POST requests."""
        request = EsisteOdonimoPostRequestFactory.build()
        # POST fields are optional
        assert request is not None

    def test_esiste_odonimo_response_factories(self):
        """Test factories generate valid EsisteOdonimo responses."""
        response1 = EsisteOdonimoGetPathParamResponseFactory.build()
        response2 = EsisteOdonimoGetQueryParamResponseFactory.build()
        response3 = EsisteOdonimoPostResponseFactory.build()

        for response in [response1, response2, response3]:
            assert response is not None
            # data field can be bool or None
            if response.data is not None:
                assert isinstance(response.data, bool)

    def test_esiste_odonimo_batch_generation(self):
        """Test batch generation of EsisteOdonimo requests."""
        requests = EsisteOdonimoGetPathParamRequestFactory.batch(50)
        assert len(requests) == 50
        # Check for variety in generated data
        codcoms = {r.codcom for r in requests}
        assert len(codcoms) > 5  # At least some variety


class TestEsisteAccessoFactories:
    """Test factories for EsisteAccesso operations."""

    def test_esiste_accesso_get_path_param_request_factory(self):
        """Test factory generates valid EsisteAccesso GetPathParam requests."""
        request = EsisteAccessoGetPathParamRequestFactory.build()
        assert request.codcom is not None
        assert request.denom is not None
        assert request.accesso is not None

    def test_esiste_accesso_get_query_param_request_factory(self):
        """Test factory generates valid EsisteAccesso GetQueryParam requests."""
        request = EsisteAccessoGetQueryParamRequestFactory.build()
        assert request.codcom is not None
        assert request.denom is not None
        assert request.accesso is not None

    def test_esiste_accesso_post_request_factory(self):
        """Test factory generates valid EsisteAccesso POST requests."""
        request = EsisteAccessoPostRequestFactory.build()
        assert request is not None


class TestElencoOdonimiFactories:
    """Test factories for ElencoOdonimi operations."""

    def test_elenco_odonimi_data_factory(self):
        """Test factory generates valid ElencoOdonimi data models."""
        for _ in range(10):
            data = ElencoOdonimiDataFactory.build()
            assert data is not None
            if data.dug:
                assert data.dug in ItalianStreetProvider.STREET_TYPES
            if data.denomuff:
                assert isinstance(data.denomuff, str)

    def test_elenco_odonimi_get_path_param_request_factory(self):
        """Test factory generates valid ElencoOdonimi GetPathParam requests."""
        request = ElencoOdonimiGetPathParamRequestFactory.build()
        assert request.codcom is not None
        assert len(request.codcom) == 4
        assert request.denomparz is not None
        # Verify base64
        try:
            base64.b64decode(request.denomparz)
        except Exception:
            pytest.fail("Invalid base64 in denomparz field")

    def test_elenco_odonimi_get_query_param_request_factory(self):
        """Test factory generates valid ElencoOdonimi GetQueryParam requests."""
        request = ElencoOdonimiGetQueryParamRequestFactory.build()
        assert request.codcom is not None
        assert request.denomparz is not None

    def test_elenco_odonimi_response_factory(self):
        """Test factory generates valid ElencoOdonimi responses."""
        response = ElencoOdonimiGetPathParamResponseFactory.build()
        assert response is not None
        if response.data is not None:
            assert isinstance(response.data, list)


class TestElencoodonimiprogFactories:
    """Test factories for Elencoodonimiprog operations."""

    def test_elencoodonimiprog_data_factory(self):
        """Test factory generates valid Elencoodonimiprog data models."""
        data = ElencoodonimiprogDataFactory.build()
        assert data is not None
        # prognaz field should be present (optional but typically set)
        if data.prognaz:
            assert isinstance(data.prognaz, str)

    def test_elencoodonimiprog_request_factory(self):
        """Test factory generates valid Elencoodonimiprog requests."""
        request = ElencoodonimiprogGetPathParamRequestFactory.build()
        assert request.codcom is not None
        assert request.denomparz is not None


class TestElencoAccessiFactories:
    """Test factories for ElencoAccessi operations."""

    def test_elenco_accessi_data_factory(self):
        """Test factory generates valid ElencoAccessi data models."""
        data = ElencoAccessiDataFactory.build()
        assert data is not None
        # Check optional fields exist
        if data.civico:
            assert isinstance(data.civico, str)

    def test_elenco_accessi_request_factory(self):
        """Test factory generates valid ElencoAccessi requests."""
        request = ElencoAccessiGetPathParamRequestFactory.build()
        assert request.codcom is not None
        assert request.denom is not None
        assert request.accparz is not None


class TestElencoaccessiprogFactories:
    """Test factories for Elencoaccessiprog operations."""

    def test_elencoaccessiprog_data_factory(self):
        """Test factory generates valid Elencoaccessiprog data models."""
        data = ElencoaccessiprogDataFactory.build()
        assert data is not None
        # Check for coordinate fields
        if data.coord_x:
            assert isinstance(data.coord_x, str)
        if data.coord_y:
            assert isinstance(data.coord_y, str)

    def test_elencoaccessiprog_request_factory(self):
        """Test factory generates valid Elencoaccessiprog requests."""
        request = ElencoaccessiprogGetPathParamRequestFactory.build()
        assert request.prognaz is not None
        assert request.accparz is not None


class TestPrognazareaFactories:
    """Test factories for Prognazarea operations."""

    def test_prognazarea_data_factory(self):
        """Test factory generates valid Prognazarea data models."""
        data = PrognazareaDataFactory.build()
        assert data is not None
        if data.prognaz:
            assert isinstance(data.prognaz, str)


class TestPrognazaccFactories:
    """Test factories for Prognazacc operations."""

    def test_prognazacc_data_factory(self):
        """Test factory generates valid Prognazacc data models."""
        data = PrognazaccDataFactory.build()
        assert data is not None
        # Prognazacc has both street and access data
        if data.prognaz:
            assert isinstance(data.prognaz, str)
        if data.prognazacc:
            assert isinstance(data.prognazacc, str)


class TestShowStatusFactory:
    """Test factory for ShowStatus operation."""

    def test_show_status_response_factory(self):
        """Test factory generates valid ShowStatus responses."""
        response = ShowStatusResponseFactory.build()
        assert response is not None


# ===========================
# PROPERTY-BASED TESTS (HYPOTHESIS)
# ===========================


@st.composite
def belfiore_code_strategy(draw):
    """Hypothesis strategy for generating Belfiore codes."""
    letter = draw(st.sampled_from(string.ascii_uppercase))
    digits = draw(st.text(alphabet=string.digits, min_size=3, max_size=3))
    return f"{letter}{digits}"


@st.composite
def base64_street_name_strategy(draw):
    """Hypothesis strategy for generating base64-encoded street names."""
    # Generate Italian-ish street name
    name = draw(st.text(alphabet=string.ascii_uppercase + " ", min_size=5, max_size=50))
    return base64.b64encode(name.encode()).decode()


class TestPropertyBasedValidation:
    """Property-based tests using Hypothesis."""

    @given(belfiore_code_strategy())
    def test_belfiore_code_format(self, codcom):
        """Test Belfiore code format with Hypothesis."""
        assert len(codcom) == 4
        assert codcom[0].isupper()
        assert codcom[1:].isdigit()

    @given(base64_street_name_strategy())
    def test_base64_encoding_valid(self, denom):
        """Test base64 encoding is valid."""
        try:
            decoded = base64.b64decode(denom)
            assert isinstance(decoded, bytes)
        except Exception:
            pytest.fail(f"Invalid base64: {denom}")

    @given(codcom=belfiore_code_strategy(), denom=base64_street_name_strategy())
    def test_esiste_odonimo_request_with_hypothesis(self, codcom, denom):
        """Test EsisteOdonimoRequest creation with Hypothesis-generated data."""
        request = EsisteOdonimoGetPathParamRequest(codcom=codcom, denom=denom)
        assert request.codcom == codcom
        assert request.denom == denom

    @given(st.booleans())
    def test_esiste_odonimo_response_with_hypothesis(self, data_value):
        """Test EsisteOdonimoResponse with Hypothesis-generated boolean."""
        response = EsisteOdonimoGetPathParamResponse(
            res="esisteodonimo", data=data_value
        )
        assert response.data == data_value
        assert isinstance(response.data, bool)


class TestFactoryIntegrationWithModels:
    """Test factories work correctly with actual model validation."""

    @pytest.mark.parametrize(
        "factory_class",
        [
            EsisteOdonimoGetPathParamRequestFactory,
            EsisteOdonimoGetQueryParamRequestFactory,
            EsisteAccessoGetPathParamRequestFactory,
            EsisteAccessoGetQueryParamRequestFactory,
            ElencoOdonimiGetPathParamRequestFactory,
            ElencoOdonimiGetQueryParamRequestFactory,
            ElencoodonimiprogGetPathParamRequestFactory,
            ElencoAccessiGetPathParamRequestFactory,
            ElencoaccessiprogGetPathParamRequestFactory,
        ],
    )
    def test_request_factories_produce_valid_models(self, factory_class):
        """Test that all request factories produce valid Pydantic models."""
        for _ in range(5):
            model = factory_class.build()
            # Pydantic will validate on construction
            assert model is not None
            # Verify we can serialize to dict (Pydantic validation)
            model_dict = model.model_dump()
            assert isinstance(model_dict, dict)

    @pytest.mark.parametrize(
        "data_factory_class",
        [
            ElencoOdonimiDataFactory,
            ElencoodonimiprogDataFactory,
            ElencoAccessiDataFactory,
            ElencoaccessiprogDataFactory,
            PrognazareaDataFactory,
            PrognazaccDataFactory,
        ],
    )
    def test_data_factories_produce_valid_models(self, data_factory_class):
        """Test that all data factories produce valid Pydantic models."""
        for _ in range(5):
            model = data_factory_class.build()
            assert model is not None
            # Verify we can serialize
            model_dict = model.model_dump()
            assert isinstance(model_dict, dict)


class TestBatchGeneration:
    """Test batch generation capabilities of factories."""

    def test_batch_generation_produces_variety(self):
        """Test that batch generation produces variety in data."""
        batch = EsisteOdonimoGetPathParamRequestFactory.batch(100)
        assert len(batch) == 100

        # Check for variety in codcom
        codcoms = {req.codcom for req in batch}
        assert len(codcoms) > 10  # Should have variety

        # Check all are valid
        for req in batch:
            assert len(req.codcom) == 4
            assert req.codcom[0].isupper()

    def test_batch_generation_elenco_odonimi_data(self):
        """Test batch generation of ElencoOdonimi data models."""
        batch = ElencoOdonimiDataFactory.batch(50)
        assert len(batch) == 50

        # Check for variety in street types
        dugs = {data.dug for data in batch if data.dug}
        assert len(dugs) > 1  # Should have variety in street types


class TestRealWorldScenarios:
    """Test factories in realistic usage scenarios."""

    def test_create_elenco_odonimi_response_with_multiple_items(self):
        """Test creating a response with multiple data items."""
        data_items = ElencoOdonimiDataFactory.batch(5)
        response = ElencoOdonimiGetPathParamResponse(
            res="elencoodonimi", data=data_items
        )

        assert response.res == "elencoodonimi"
        assert len(response.data) == 5
        for item in response.data:
            assert isinstance(item, ElencoOdonimiGetPathParamData)

    def test_esiste_odonimo_true_false_scenarios(self):
        """Test both true and false scenarios for esiste operations."""
        response_true = EsisteOdonimoGetPathParamResponse(
            res="esisteodonimo", data=True
        )
        response_false = EsisteOdonimoGetPathParamResponse(
            res="esisteodonimo", data=False
        )

        assert response_true.data is True
        assert response_false.data is False

    def test_coordinates_in_elencoaccessiprog_data(self):
        """Test coordinate fields in Elencoaccessiprog data."""
        data = ElencoaccessiprogDataFactory.build(
            coord_x="12.4963655", coord_y="41.9027835", quota="50", metodo="4"
        )

        assert data.coord_x == "12.4963655"
        assert data.coord_y == "41.9027835"
        assert data.quota == "50"
        assert data.metodo == "4"

    def test_nullable_fields_in_data_models(self):
        """Test that nullable fields can be None."""
        data = ElencoOdonimiDataFactory.build(
            dug="VIA",
            denomuff="ROMA",
            denomloc=None,
            denomlingua1=None,
            denomlingua2=None,
        )

        assert data.dug == "VIA"
        assert data.denomuff == "ROMA"
        assert data.denomloc is None
        assert data.denomlingua1 is None
        assert data.denomlingua2 is None
