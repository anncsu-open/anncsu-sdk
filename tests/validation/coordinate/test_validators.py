"""Tests for Coordinate API validators."""

import pytest


def coordinate_x_validator(value: str) -> str:
    """Validate X coordinate for Italy (6.0 <= x <= 18.0)."""
    if not isinstance(value, str):
        raise ValueError("X coordinate must be a string")

    try:
        x_val = float(value)
    except ValueError as e:
        raise ValueError(f"Invalid X coordinate: {value} is not a valid number") from e

    if not (6.0 <= x_val <= 18.0):
        raise ValueError(
            f"Invalid X coordinate: {value}. Must be between 6.0 and 18.0 for Italy"
        )

    return value


def coordinate_y_validator(value: str) -> str:
    """Validate Y coordinate for Italy (36.0 <= y <= 47.0)."""
    if not isinstance(value, str):
        raise ValueError("Y coordinate must be a string")

    try:
        y_val = float(value)
    except ValueError as e:
        raise ValueError(f"Invalid Y coordinate: {value} is not a valid number") from e

    if not (36.0 <= y_val <= 47.0):
        raise ValueError(
            f"Invalid Y coordinate: {value}. Must be between 36.0 and 47.0 for Italy"
        )

    return value


def metodo_validator(value: str) -> str:
    """Validate metodo (survey method, 1-4)."""
    if not isinstance(value, str):
        raise ValueError("Metodo must be a string")

    try:
        metodo_val = int(value)
    except ValueError as e:
        raise ValueError(f"Invalid metodo: {value} is not a valid integer") from e

    if not (1 <= metodo_val <= 4):
        raise ValueError(f"Invalid metodo: {value}. Must be between 1 and 4")

    return value


def belfiore_code_validator(value: str) -> str:
    """Validate Belfiore code format (letter + 3 digits)."""
    if not isinstance(value, str):
        raise ValueError("Belfiore code must be a string")

    if len(value) != 4:
        raise ValueError(
            f"Invalid Belfiore code: {value}. Must be exactly 4 characters"
        )

    if not value[0].isupper():
        raise ValueError(
            f"Invalid Belfiore code: {value}. Must start with uppercase letter"
        )

    if not value[1:].isdigit():
        raise ValueError(
            f"Invalid Belfiore code: {value}. Last 3 characters must be digits"
        )

    return value


def progr_civico_validator(value: str) -> str:
    """Validate progressive civic number (numeric string)."""
    if not isinstance(value, str):
        raise ValueError("Progressive civic number must be a string")

    if not value.isdigit():
        raise ValueError(f"Invalid progressive civic number: {value}. Must be numeric")

    if int(value) <= 0:
        raise ValueError(f"Invalid progressive civic number: {value}. Must be positive")

    return value


class TestCoordinateXValidator:
    """Tests for X coordinate validator."""

    def test_valid_x_coordinates(self):
        """Test that valid X coordinates pass validation."""
        valid_coords = [
            "6.0",
            "12.0",
            "18.0",
            "11.123456",
            "9.876543",
            "15.5",
        ]

        for coord in valid_coords:
            result = coordinate_x_validator(coord)
            assert result == coord

    def test_invalid_x_coordinates_out_of_range(self):
        """Test that X coordinates outside Italy range raise ValueError."""
        invalid_coords = [
            "5.9",  # Too west
            "18.1",  # Too east
            "0.0",
            "-5.0",
            "25.0",
        ]

        for coord in invalid_coords:
            with pytest.raises(ValueError, match="Invalid X coordinate"):
                coordinate_x_validator(coord)

    def test_invalid_x_coordinate_not_number(self):
        """Test that non-numeric X coordinates raise ValueError."""
        with pytest.raises(ValueError, match="not a valid number"):
            coordinate_x_validator("abc")

    def test_invalid_x_coordinate_type(self):
        """Test that non-string input raises ValueError."""
        with pytest.raises(ValueError, match="must be a string"):
            coordinate_x_validator(12.0)


class TestCoordinateYValidator:
    """Tests for Y coordinate validator."""

    def test_valid_y_coordinates(self):
        """Test that valid Y coordinates pass validation."""
        valid_coords = [
            "36.0",
            "41.9",  # Rome latitude
            "47.0",
            "45.4667",  # Milan latitude
            "40.8518",  # Naples latitude
        ]

        for coord in valid_coords:
            result = coordinate_y_validator(coord)
            assert result == coord

    def test_invalid_y_coordinates_out_of_range(self):
        """Test that Y coordinates outside Italy range raise ValueError."""
        invalid_coords = [
            "35.9",  # Too south
            "47.1",  # Too north
            "0.0",
            "-40.0",
            "60.0",
        ]

        for coord in invalid_coords:
            with pytest.raises(ValueError, match="Invalid Y coordinate"):
                coordinate_y_validator(coord)

    def test_invalid_y_coordinate_not_number(self):
        """Test that non-numeric Y coordinates raise ValueError."""
        with pytest.raises(ValueError, match="not a valid number"):
            coordinate_y_validator("xyz")

    def test_invalid_y_coordinate_type(self):
        """Test that non-string input raises ValueError."""
        with pytest.raises(ValueError, match="must be a string"):
            coordinate_y_validator(41.9)


class TestMetodoValidator:
    """Tests for metodo (survey method) validator."""

    def test_valid_metodo_values(self):
        """Test that valid metodo values pass validation."""
        valid_metodos = ["1", "2", "3", "4"]

        for metodo in valid_metodos:
            result = metodo_validator(metodo)
            assert result == metodo

    def test_invalid_metodo_out_of_range(self):
        """Test that metodo values outside 1-4 range raise ValueError."""
        invalid_metodos = ["0", "5", "-1", "10"]

        for metodo in invalid_metodos:
            with pytest.raises(ValueError, match="Invalid metodo"):
                metodo_validator(metodo)

    def test_invalid_metodo_not_integer(self):
        """Test that non-integer metodo raises ValueError."""
        with pytest.raises(ValueError, match="not a valid integer"):
            metodo_validator("1.5")

        with pytest.raises(ValueError, match="not a valid integer"):
            metodo_validator("abc")

    def test_invalid_metodo_type(self):
        """Test that non-string input raises ValueError."""
        with pytest.raises(ValueError, match="must be a string"):
            metodo_validator(1)


class TestBelfioreCodeValidator:
    """Tests for Belfiore code validator."""

    def test_valid_belfiore_codes(self):
        """Test that valid Belfiore codes pass validation."""
        valid_codes = [
            "H501",  # Rome
            "F205",  # Milan
            "A794",  # Bologna
            "G273",  # Naples (Napoli)
            "L219",  # Turin (Torino)
            "Z999",
        ]

        for code in valid_codes:
            result = belfiore_code_validator(code)
            assert result == code

    def test_invalid_belfiore_codes_format(self):
        """Test that invalid Belfiore codes raise ValueError."""
        invalid_codes = [
            "h501",  # Lowercase letter
            "H50",  # Too short
            "H5011",  # Too long
            "1501",  # Starts with digit
            "HH01",  # Two letters
            "H5O1",  # Letter instead of digit
            "",  # Empty
            "H 50",  # Space
        ]

        for code in invalid_codes:
            with pytest.raises(ValueError, match="Invalid Belfiore code"):
                belfiore_code_validator(code)

    def test_invalid_belfiore_code_type(self):
        """Test that non-string input raises ValueError."""
        with pytest.raises(ValueError, match="must be a string"):
            belfiore_code_validator(501)


class TestProgrCivicoValidator:
    """Tests for progressive civic number validator."""

    def test_valid_progr_civico(self):
        """Test that valid progressive civic numbers pass validation."""
        valid_numbers = [
            "1",
            "12345",
            "99999",
            "100",
        ]

        for num in valid_numbers:
            result = progr_civico_validator(num)
            assert result == num

    def test_invalid_progr_civico_not_numeric(self):
        """Test that non-numeric values raise ValueError."""
        invalid_numbers = [
            "abc",
            "12a",
            "1.5",
            "",
        ]

        for num in invalid_numbers:
            with pytest.raises(ValueError, match="Must be numeric"):
                progr_civico_validator(num)

    def test_invalid_progr_civico_zero(self):
        """Test that zero raises ValueError."""
        with pytest.raises(ValueError, match="Must be positive"):
            progr_civico_validator("0")

    def test_invalid_progr_civico_type(self):
        """Test that non-string input raises ValueError."""
        with pytest.raises(ValueError, match="must be a string"):
            progr_civico_validator(12345)


class TestValidatorsWithModels:
    """Integration tests for validators with Coordinate models."""

    def test_coordinate_model_with_valid_data(self):
        """Test creating Coordinate model with valid data."""
        from anncsu.coordinate.models.richiestaoperazione import Coordinate

        coord = Coordinate(
            x="12.4964",
            y="41.9028",
            z="21.0",
            metodo="1",
        )

        assert coord.x == "12.4964"
        assert coord.y == "41.9028"
        assert coord.metodo == "1"

    def test_accesso_model_with_valid_data(self):
        """Test creating Accesso model with valid data."""
        from anncsu.coordinate.models.richiestaoperazione import (
            Accesso,
            Coordinate,
        )

        coord = Coordinate(x="12.4964", y="41.9028")
        accesso = Accesso(
            codcom="H501",
            progr_civico="12345",
            coordinate=coord,
        )

        assert accesso.codcom == "H501"
        assert accesso.progr_civico == "12345"
        assert accesso.coordinate is not None

    def test_richiesta_operazione_with_valid_data(self):
        """Test creating RichiestaOperazione with valid data."""
        from anncsu.coordinate.models import RichiestaOperazione
        from anncsu.coordinate.models.richiestaoperazione import (
            Accesso,
            Coordinate,
            Richiesta,
        )

        coord = Coordinate(x="12.4964", y="41.9028", metodo="2")
        accesso = Accesso(codcom="H501", progr_civico="12345", coordinate=coord)
        richiesta = Richiesta(accesso=accesso)
        richiesta_op = RichiestaOperazione(richiesta=richiesta)

        assert richiesta_op.richiesta is not None
        assert richiesta_op.richiesta.accesso is not None
        assert richiesta_op.richiesta.accesso.codcom == "H501"

    def test_risposta_operazione_with_valid_data(self):
        """Test creating RispostaOperazione with valid data."""
        from anncsu.coordinate.models import RispostaOperazione
        from anncsu.coordinate.models.rispostaoperazione import Dati

        dati = Dati(
            codcom="H501",
            progr_civico="12345",
            numero="10",
            coordinata_x_comune="12.4964",
            coordinata_y_comune="41.9028",
        )

        risposta = RispostaOperazione(
            id_richiesta="req-123",
            esito="OK",
            messaggio="Operazione completata con successo",
            dati=[dati],
        )

        assert risposta.esito == "OK"
        assert len(risposta.dati) == 1
        assert risposta.dati[0].codcom == "H501"


class TestItalianCityCoordinates:
    """Tests with real Italian city coordinates."""

    # Real coordinates of major Italian cities
    ITALIAN_CITIES = {
        "Rome": {"x": "12.4964", "y": "41.9028", "codcom": "H501"},
        "Milan": {"x": "9.1900", "y": "45.4642", "codcom": "F205"},
        "Naples": {"x": "14.2681", "y": "40.8518", "codcom": "F839"},
        "Turin": {"x": "7.6869", "y": "45.0703", "codcom": "L219"},
        "Florence": {"x": "11.2558", "y": "43.7696", "codcom": "D612"},
        "Bologna": {"x": "11.3426", "y": "44.4949", "codcom": "A944"},
        "Venice": {"x": "12.3155", "y": "45.4408", "codcom": "L736"},
        "Palermo": {"x": "13.3615", "y": "38.1157", "codcom": "G273"},
    }

    def test_validate_real_city_coordinates(self):
        """Test that real Italian city coordinates pass validation."""
        for city, data in self.ITALIAN_CITIES.items():
            # Validate X coordinate
            result_x = coordinate_x_validator(data["x"])
            assert result_x == data["x"], f"Failed for {city} X coordinate"

            # Validate Y coordinate
            result_y = coordinate_y_validator(data["y"])
            assert result_y == data["y"], f"Failed for {city} Y coordinate"

            # Validate Belfiore code
            result_code = belfiore_code_validator(data["codcom"])
            assert result_code == data["codcom"], f"Failed for {city} Belfiore code"

    def test_create_models_with_real_city_data(self):
        """Test creating models with real Italian city data."""
        from anncsu.coordinate.models.richiestaoperazione import (
            Accesso,
            Coordinate,
        )

        for _city, data in self.ITALIAN_CITIES.items():
            coord = Coordinate(x=data["x"], y=data["y"])
            accesso = Accesso(codcom=data["codcom"], coordinate=coord)

            assert accesso.codcom == data["codcom"]
            assert accesso.coordinate.x == data["x"]
            assert accesso.coordinate.y == data["y"]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
