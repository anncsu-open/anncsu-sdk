"""Model factory tests for Coordinate API using Polyfactory."""

import pytest
from polyfactory.factories.pydantic_factory import ModelFactory
from polyfactory.pytest_plugin import register_fixture

from anncsu.coordinate.models import (
    RichiestaOperazione,
    RispostaOperazione,
    Security,
)
from anncsu.coordinate.models.richiestaoperazione import (
    Accesso,
    Coordinate,
    Richiesta,
)
from anncsu.coordinate.models.rispostaoperazione import Dati


class CoordinateFactory(ModelFactory):
    """Factory for generating valid Coordinate instances."""

    __model__ = Coordinate
    __check_model__ = False

    @classmethod
    def x(cls) -> str:
        """Generate valid X coordinate for Italy (6.0 <= x <= 18.0)."""
        import random

        return str(round(random.uniform(6.0, 18.0), 6))

    @classmethod
    def y(cls) -> str:
        """Generate valid Y coordinate for Italy (36.0 <= y <= 47.0)."""
        import random

        return str(round(random.uniform(36.0, 47.0), 6))

    @classmethod
    def z(cls) -> str:
        """Generate valid Z coordinate (altitude in meters)."""
        import random

        return str(round(random.uniform(0, 3000), 2))

    @classmethod
    def metodo(cls) -> str:
        """Generate valid metodo (1-4)."""
        import random

        return str(random.randint(1, 4))


class BelfioreCodeFactory:
    """Factory for generating valid Belfiore codes."""

    @staticmethod
    def build() -> str:
        """Generate a random valid Belfiore code."""
        import random
        import string

        letter = random.choice(string.ascii_uppercase)
        number = random.randint(0, 999)
        return f"{letter}{number:03d}"


class AccessoFactory(ModelFactory):
    """Factory for generating valid Accesso instances."""

    __model__ = Accesso
    __check_model__ = False

    @classmethod
    def codcom(cls) -> str:
        """Generate a valid Belfiore code."""
        return BelfioreCodeFactory.build()

    @classmethod
    def progr_civico(cls) -> str:
        """Generate a valid progressive civic number."""
        import random

        return str(random.randint(1, 99999))

    @classmethod
    def coordinate(cls) -> Coordinate:
        """Generate valid coordinates."""
        return CoordinateFactory.build()


class RichiestaFactory(ModelFactory):
    """Factory for generating valid Richiesta instances."""

    __model__ = Richiesta
    __check_model__ = False

    @classmethod
    def accesso(cls) -> Accesso:
        """Generate a valid Accesso."""
        return AccessoFactory.build()


class RichiestaOperazioneFactory(ModelFactory):
    """Factory for generating valid RichiestaOperazione instances."""

    __model__ = RichiestaOperazione
    __check_model__ = False

    @classmethod
    def richiesta(cls) -> Richiesta:
        """Generate a valid Richiesta."""
        return RichiestaFactory.build()


class DatiFactory(ModelFactory):
    """Factory for generating valid Dati instances."""

    __model__ = Dati
    __check_model__ = False

    @classmethod
    def progr_civico(cls) -> str:
        """Generate a valid progressive civic number."""
        import random

        return str(random.randint(1, 99999))

    @classmethod
    def codcom(cls) -> str:
        """Generate a valid Belfiore code."""
        return BelfioreCodeFactory.build()

    @classmethod
    def numero(cls) -> str:
        """Generate a valid civic number."""
        import random

        return str(random.randint(1, 999))

    @classmethod
    def coordinata_x_comune(cls) -> str:
        """Generate valid X coordinate."""
        import random

        return str(round(random.uniform(6.0, 18.0), 6))

    @classmethod
    def coordinata_y_comune(cls) -> str:
        """Generate valid Y coordinate."""
        import random

        return str(round(random.uniform(36.0, 47.0), 6))

    @classmethod
    def metodo(cls) -> str:
        """Generate valid metodo (1-4)."""
        import random

        return str(random.randint(1, 4))


class RispostaOperazioneFactory(ModelFactory):
    """Factory for generating valid RispostaOperazione instances."""

    __model__ = RispostaOperazione
    __check_model__ = False

    @classmethod
    def esito(cls) -> str:
        """Generate a valid esito."""
        import random

        return random.choice(["OK", "KO", "WARNING"])

    @classmethod
    def messaggio(cls) -> str:
        """Generate a valid message."""
        import random

        messages = [
            "Operazione completata con successo",
            "Coordinate aggiornate",
            "Accesso non trovato",
            "Errore di validazione",
        ]
        return random.choice(messages)

    @classmethod
    def id_richiesta(cls) -> str:
        """Generate a valid request ID."""
        import uuid

        return str(uuid.uuid4())


class SecurityFactory(ModelFactory):
    """Factory for generating valid Security instances."""

    __model__ = Security
    __check_model__ = False

    @classmethod
    def bearer_auth(cls) -> str:
        """Generate a valid bearer token."""
        import secrets

        return f"eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9.{secrets.token_urlsafe(32)}"


# Register as pytest fixtures
coordinate_factory = register_fixture(CoordinateFactory)
accesso_factory = register_fixture(AccessoFactory)
richiesta_factory = register_fixture(RichiestaFactory)
richiesta_operazione_factory = register_fixture(RichiestaOperazioneFactory)
dati_factory = register_fixture(DatiFactory)
risposta_operazione_factory = register_fixture(RispostaOperazioneFactory)
security_factory = register_fixture(SecurityFactory)


class TestCoordinateFactory:
    """Tests for Coordinate model factory."""

    def test_factory_generates_valid_coordinates(self):
        """Test that factory generates valid Coordinate instances."""
        for _ in range(50):
            coord = CoordinateFactory.build()

            assert isinstance(coord, Coordinate)

            # Verify X coordinate is in valid range for Italy
            if coord.x is not None:
                x_val = float(coord.x)
                assert 6.0 <= x_val <= 18.0

            # Verify Y coordinate is in valid range for Italy
            if coord.y is not None:
                y_val = float(coord.y)
                assert 36.0 <= y_val <= 47.0

            # Verify metodo is 1-4
            if coord.metodo is not None:
                metodo_val = int(coord.metodo)
                assert 1 <= metodo_val <= 4

    def test_factory_batch_generation(self):
        """Test generating batches of valid coordinates."""
        batch = CoordinateFactory.batch(size=100)

        assert len(batch) == 100
        for coord in batch:
            assert isinstance(coord, Coordinate)


class TestAccessoFactory:
    """Tests for Accesso model factory."""

    def test_factory_generates_valid_accesso(self):
        """Test that factory generates valid Accesso instances."""
        for _ in range(30):
            accesso = AccessoFactory.build()

            assert isinstance(accesso, Accesso)

            # Verify codcom is valid Belfiore code format
            if accesso.codcom is not None:
                assert len(accesso.codcom) == 4
                assert accesso.codcom[0].isupper()
                assert accesso.codcom[1:].isdigit()

            # Verify progr_civico is numeric
            if accesso.progr_civico is not None:
                assert accesso.progr_civico.isdigit()

    def test_accesso_with_coordinates(self):
        """Test that Accesso can have nested Coordinate."""
        accesso = AccessoFactory.build()

        if accesso.coordinate is not None:
            assert isinstance(accesso.coordinate, Coordinate)


class TestRichiestaOperazioneFactory:
    """Tests for RichiestaOperazione model factory."""

    def test_factory_generates_valid_richiesta(self):
        """Test that factory generates valid RichiestaOperazione instances."""
        for _ in range(20):
            richiesta_op = RichiestaOperazioneFactory.build()

            assert isinstance(richiesta_op, RichiestaOperazione)

    def test_richiesta_has_nested_structure(self):
        """Test that RichiestaOperazione has proper nested structure."""
        richiesta_op = RichiestaOperazioneFactory.build()

        if richiesta_op.richiesta is not None:
            assert isinstance(richiesta_op.richiesta, Richiesta)

            if richiesta_op.richiesta.accesso is not None:
                assert isinstance(richiesta_op.richiesta.accesso, Accesso)

    def test_can_serialize_to_dict(self):
        """Test that generated models can be serialized."""
        richiesta_op = RichiestaOperazioneFactory.build()

        data = richiesta_op.model_dump()
        assert isinstance(data, dict)


class TestRispostaOperazioneFactory:
    """Tests for RispostaOperazione model factory."""

    def test_factory_generates_valid_risposta(self):
        """Test that factory generates valid RispostaOperazione instances."""
        for _ in range(20):
            risposta = RispostaOperazioneFactory.build()

            assert isinstance(risposta, RispostaOperazione)

            # Verify esito is valid
            if risposta.esito is not None:
                assert risposta.esito in ["OK", "KO", "WARNING"]

    def test_risposta_can_have_dati(self):
        """Test that RispostaOperazione can have dati list."""
        risposta = RispostaOperazioneFactory.build()

        if risposta.dati is not None:
            assert isinstance(risposta.dati, list)


class TestSecurityFactory:
    """Tests for Security model factory."""

    def test_factory_generates_valid_security(self):
        """Test that factory generates valid Security instances."""
        for _ in range(20):
            security = SecurityFactory.build()

            assert isinstance(security, Security)

            # Verify bearer_auth looks like a JWT
            if security.bearer_auth is not None:
                assert security.bearer_auth.startswith("eyJ")


class TestDatiFactory:
    """Tests for Dati model factory."""

    def test_factory_generates_valid_dati(self):
        """Test that factory generates valid Dati instances."""
        for _ in range(30):
            dati = DatiFactory.build()

            assert isinstance(dati, Dati)

            # Verify codcom is valid Belfiore code format
            if dati.codcom is not None:
                assert len(dati.codcom) == 4
                assert dati.codcom[0].isupper()
                assert dati.codcom[1:].isdigit()

            # Verify coordinates are in valid range
            if dati.coordinata_x_comune is not None:
                x_val = float(dati.coordinata_x_comune)
                assert 6.0 <= x_val <= 18.0

            if dati.coordinata_y_comune is not None:
                y_val = float(dati.coordinata_y_comune)
                assert 36.0 <= y_val <= 47.0


class TestFactoryIntegration:
    """Integration tests for factories."""

    def test_complete_request_flow(self):
        """Test creating a complete request with all nested objects."""
        # Create coordinate
        coord = CoordinateFactory.build()
        assert coord is not None

        # Create accesso with coordinate
        accesso = Accesso(
            codcom="H501",  # Rome
            progr_civico="12345",
            coordinate=coord,
        )
        assert accesso.coordinate is not None

        # Create richiesta
        richiesta = Richiesta(accesso=accesso)
        assert richiesta.accesso is not None

        # Create full request
        richiesta_op = RichiestaOperazione(richiesta=richiesta)
        assert richiesta_op.richiesta is not None

        # Serialize and verify
        data = richiesta_op.model_dump()
        assert "richiesta" in data or data.get("richiesta") is not None

    def test_complete_response_flow(self):
        """Test creating a complete response."""
        # Create dati
        dati = DatiFactory.build()
        assert dati is not None

        # Create full response
        risposta = RispostaOperazione(
            id_richiesta="test-123",
            esito="OK",
            messaggio="Operazione completata",
            dati=[dati],
        )

        assert risposta.esito == "OK"
        assert len(risposta.dati) == 1

        # Serialize and verify
        data = risposta.model_dump()
        assert data["esito"] == "OK"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
