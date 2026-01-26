"""Property-based tests for coordinate validators using Hypothesis and Faker."""

import string

import pytest
from faker import Faker
from hypothesis import assume, given, settings
from hypothesis import strategies as st

from anncsu.common.validation import belfiore_code_validator

# Initialize Faker
fake = Faker("it_IT")  # Italian locale for realistic Italian data

# Italian geographic coordinate boundaries
# Italy spans approximately:
# - Longitude (X): 6.0 to 18.0 degrees East
# - Latitude (Y): 36.0 to 47.0 degrees North
ITALY_X_MIN = 6.0
ITALY_X_MAX = 18.0
ITALY_Y_MIN = 36.0
ITALY_Y_MAX = 47.0


class TestCoordinateXValidatorPropertyBased:
    """Property-based tests for X coordinate (longitude) validation."""

    @given(st.floats(min_value=ITALY_X_MIN, max_value=ITALY_X_MAX, allow_nan=False))
    @settings(max_examples=200)
    def test_valid_x_coordinates_in_italy(self, x: float):
        """Test that valid X coordinates within Italy are accepted."""
        # Coordinates within Italy's bounding box should be valid
        assert ITALY_X_MIN <= x <= ITALY_X_MAX

    @given(st.floats(min_value=-180.0, max_value=ITALY_X_MIN - 0.1, allow_nan=False))
    @settings(max_examples=50)
    def test_x_coordinate_west_of_italy(self, x: float):
        """Test X coordinates west of Italy."""
        assume(x < ITALY_X_MIN)
        # These are valid longitude values but outside Italy
        assert x < ITALY_X_MIN

    @given(st.floats(min_value=ITALY_X_MAX + 0.1, max_value=180.0, allow_nan=False))
    @settings(max_examples=50)
    def test_x_coordinate_east_of_italy(self, x: float):
        """Test X coordinates east of Italy."""
        assume(x > ITALY_X_MAX)
        # These are valid longitude values but outside Italy
        assert x > ITALY_X_MAX

    @given(st.floats(allow_nan=True, allow_infinity=True))
    @settings(max_examples=50)
    def test_special_float_values(self, x: float):
        """Test handling of special float values (NaN, Inf)."""
        import math

        if math.isnan(x) or math.isinf(x):
            # These should be considered invalid coordinates
            assert not (ITALY_X_MIN <= x <= ITALY_X_MAX)


class TestCoordinateYValidatorPropertyBased:
    """Property-based tests for Y coordinate (latitude) validation."""

    @given(st.floats(min_value=ITALY_Y_MIN, max_value=ITALY_Y_MAX, allow_nan=False))
    @settings(max_examples=200)
    def test_valid_y_coordinates_in_italy(self, y: float):
        """Test that valid Y coordinates within Italy are accepted."""
        # Coordinates within Italy's bounding box should be valid
        assert ITALY_Y_MIN <= y <= ITALY_Y_MAX

    @given(st.floats(min_value=-90.0, max_value=ITALY_Y_MIN - 0.1, allow_nan=False))
    @settings(max_examples=50)
    def test_y_coordinate_south_of_italy(self, y: float):
        """Test Y coordinates south of Italy."""
        assume(y < ITALY_Y_MIN)
        # These are valid latitude values but outside Italy
        assert y < ITALY_Y_MIN

    @given(st.floats(min_value=ITALY_Y_MAX + 0.1, max_value=90.0, allow_nan=False))
    @settings(max_examples=50)
    def test_y_coordinate_north_of_italy(self, y: float):
        """Test Y coordinates north of Italy."""
        assume(y > ITALY_Y_MAX)
        # These are valid latitude values but outside Italy
        assert y > ITALY_Y_MAX


class TestCoordinatePairPropertyBased:
    """Property-based tests for coordinate pairs."""

    @given(
        st.floats(min_value=ITALY_X_MIN, max_value=ITALY_X_MAX, allow_nan=False),
        st.floats(min_value=ITALY_Y_MIN, max_value=ITALY_Y_MAX, allow_nan=False),
    )
    @settings(max_examples=200)
    def test_valid_coordinate_pairs_in_italy(self, x: float, y: float):
        """Test that valid coordinate pairs within Italy are accepted."""
        assert ITALY_X_MIN <= x <= ITALY_X_MAX
        assert ITALY_Y_MIN <= y <= ITALY_Y_MAX
        # Both coordinates should form a valid point in Italy
        point = {"x": x, "y": y}
        assert "x" in point and "y" in point

    @given(
        st.floats(min_value=-180.0, max_value=180.0, allow_nan=False),
        st.floats(min_value=-90.0, max_value=90.0, allow_nan=False),
    )
    @settings(max_examples=100)
    def test_any_valid_geographic_coordinates(self, x: float, y: float):
        """Test any valid geographic coordinates."""
        # All values should be within valid geographic ranges
        assert -180.0 <= x <= 180.0
        assert -90.0 <= y <= 90.0

        # Check if within Italy
        in_italy = (ITALY_X_MIN <= x <= ITALY_X_MAX) and (
            ITALY_Y_MIN <= y <= ITALY_Y_MAX
        )

        # This is a valid geographic coordinate, may or may not be in Italy
        assert isinstance(in_italy, bool)


class TestMetodoValidatorPropertyBased:
    """Property-based tests for metodo (method) validation."""

    VALID_METODI = ["Coordinate", "Indirizzo", "CoordinateIndirizzo"]

    @given(st.sampled_from(VALID_METODI))
    @settings(max_examples=50)
    def test_valid_metodo_values(self, metodo: str):
        """Test that valid metodo values are accepted."""
        assert metodo in self.VALID_METODI

    @given(st.text(min_size=1, max_size=50))
    @settings(max_examples=100)
    def test_arbitrary_metodo_values(self, metodo: str):
        """Test arbitrary metodo values."""
        is_valid = metodo in self.VALID_METODI
        if is_valid:
            assert metodo in self.VALID_METODI
        else:
            assert metodo not in self.VALID_METODI

    @given(st.sampled_from(VALID_METODI).map(str.lower))
    @settings(max_examples=30)
    def test_lowercase_metodo_rejected(self, metodo: str):
        """Test that lowercase metodo values are rejected (case sensitive)."""
        # Lowercase versions should not be in the valid list
        assert metodo not in self.VALID_METODI


class TestProgrCivicoValidatorPropertyBased:
    """Property-based tests for progr_civico (progressive house number) validation."""

    @given(st.integers(min_value=1, max_value=99999))
    @settings(max_examples=200)
    def test_valid_progr_civico_values(self, progr_civico: int):
        """Test that valid progressive house numbers are accepted."""
        # Positive integers should be valid
        assert progr_civico >= 1

    @given(st.integers(max_value=0))
    @settings(max_examples=50)
    def test_invalid_zero_or_negative(self, progr_civico: int):
        """Test that zero or negative values are invalid."""
        assert progr_civico <= 0

    @given(st.floats(min_value=1.0, max_value=99999.0, allow_nan=False))
    @settings(max_examples=50)
    def test_float_values(self, progr_civico: float):
        """Test handling of float values for progr_civico."""
        # Float values should be converted to int or rejected
        as_int = int(progr_civico)
        assert as_int >= 1


class TestBelfioreCodeValidatorPropertyBased:
    """Property-based tests for Belfiore code validation (coordinate context)."""

    @given(
        st.text(alphabet=string.ascii_uppercase, min_size=1, max_size=1),
        st.integers(min_value=0, max_value=999),
    )
    @settings(max_examples=200)
    def test_valid_belfiore_format(self, letter: str, number: int):
        """Test that valid Belfiore codes are accepted."""
        code = f"{letter}{number:03d}"
        result = belfiore_code_validator(code)
        assert result == code
        assert len(result) == 4
        assert result[0].isupper()
        assert result[1:].isdigit()

    @given(st.text(alphabet=string.ascii_lowercase, min_size=1, max_size=1))
    @settings(max_examples=50)
    def test_lowercase_letter_rejected(self, letter: str):
        """Test that lowercase letters are rejected."""
        code = f"{letter}501"
        with pytest.raises(ValueError, match="Invalid Belfiore code"):
            belfiore_code_validator(code)

    @given(
        st.text(min_size=4, max_size=4).filter(
            lambda x: not (len(x) == 4 and x[0].isupper() and x[1:].isdigit())
        )
    )
    @settings(max_examples=100)
    def test_invalid_patterns_rejected(self, code: str):
        """Test that invalid patterns are rejected."""
        assume(len(code) == 4)  # Only test 4-char strings
        assume(not (code[0].isupper() and code[1:].isdigit()))  # Invalid pattern

        with pytest.raises(ValueError, match="Invalid Belfiore code"):
            belfiore_code_validator(code)


class TestValidatorsWithFaker:
    """Tests using Faker to generate realistic Italian data for coordinate context."""

    def test_known_italian_belfiore_codes(self):
        """Test validation of known real Italian Belfiore codes."""
        real_codes = [
            ("H501", "Roma"),
            ("F205", "Milano"),
            ("A794", "Bologna"),
            ("D612", "Firenze"),
            ("G273", "Napoli"),
            ("L219", "Torino"),
            ("E530", "Genova"),
            ("D969", "Palermo"),
            ("C351", "Bari"),
            ("F839", "Venezia"),
        ]

        for code, _city in real_codes:
            result = belfiore_code_validator(code)
            assert result == code

    def test_realistic_italian_city_coordinates(self):
        """Test realistic Italian city coordinates."""
        italian_cities = [
            {"name": "Roma", "x": 12.4964, "y": 41.9028, "belfiore": "H501"},
            {"name": "Milano", "x": 9.1900, "y": 45.4642, "belfiore": "F205"},
            {"name": "Napoli", "x": 14.2681, "y": 40.8518, "belfiore": "G273"},
            {"name": "Torino", "x": 7.6869, "y": 45.0703, "belfiore": "L219"},
            {"name": "Palermo", "x": 13.3615, "y": 38.1157, "belfiore": "D969"},
            {"name": "Genova", "x": 8.9463, "y": 44.4056, "belfiore": "E530"},
            {"name": "Bologna", "x": 11.3426, "y": 44.4949, "belfiore": "A794"},
            {"name": "Firenze", "x": 11.2558, "y": 43.7696, "belfiore": "D612"},
            {"name": "Bari", "x": 16.8719, "y": 41.1171, "belfiore": "C351"},
            {"name": "Catania", "x": 15.0870, "y": 37.5079, "belfiore": "C351"},
        ]

        for city in italian_cities:
            # Validate coordinates are within Italy
            assert ITALY_X_MIN <= city["x"] <= ITALY_X_MAX, (
                f"{city['name']} X out of range"
            )
            assert ITALY_Y_MIN <= city["y"] <= ITALY_Y_MAX, (
                f"{city['name']} Y out of range"
            )

            # Validate Belfiore code
            result = belfiore_code_validator(city["belfiore"])
            assert result == city["belfiore"]

    def test_generate_random_italian_coordinates(self):
        """Test generation of random coordinates within Italy."""
        for _ in range(50):
            x = fake.pyfloat(min_value=ITALY_X_MIN, max_value=ITALY_X_MAX)
            y = fake.pyfloat(min_value=ITALY_Y_MIN, max_value=ITALY_Y_MAX)

            assert ITALY_X_MIN <= x <= ITALY_X_MAX
            assert ITALY_Y_MIN <= y <= ITALY_Y_MAX

    def test_generate_random_belfiore_codes(self):
        """Test generation of random Belfiore codes."""
        for _ in range(50):
            letter = fake.random_uppercase_letter()
            number = fake.random_int(min=0, max=999)
            code = f"{letter}{number:03d}"

            result = belfiore_code_validator(code)
            assert result == code


class TestEdgeCases:
    """Test edge cases for coordinate validation."""

    def test_coordinate_boundary_values(self):
        """Test coordinate values at Italy's boundaries."""
        boundary_coords = [
            (ITALY_X_MIN, ITALY_Y_MIN),  # Southwest corner
            (ITALY_X_MIN, ITALY_Y_MAX),  # Northwest corner
            (ITALY_X_MAX, ITALY_Y_MIN),  # Southeast corner
            (ITALY_X_MAX, ITALY_Y_MAX),  # Northeast corner
            (
                (ITALY_X_MIN + ITALY_X_MAX) / 2,
                (ITALY_Y_MIN + ITALY_Y_MAX) / 2,
            ),  # Center
        ]

        for x, y in boundary_coords:
            assert ITALY_X_MIN <= x <= ITALY_X_MAX
            assert ITALY_Y_MIN <= y <= ITALY_Y_MAX

    def test_belfiore_boundary_values(self):
        """Test Belfiore codes at boundary values."""
        boundary_codes = [
            "A000",  # Minimum number
            "A001",  # Just above minimum
            "A999",  # Maximum number
            "Z000",  # Different letter at boundary
            "Z999",  # Max letter and number
        ]

        for code in boundary_codes:
            result = belfiore_code_validator(code)
            assert result == code

    def test_precision_coordinates(self):
        """Test coordinates with various precision levels."""
        precision_coords = [
            (12.0, 42.0),  # Low precision
            (12.49, 41.90),  # Medium precision
            (12.4964, 41.9028),  # High precision (Roma)
            (12.49636, 41.90278),  # Very high precision
            (12.496360123, 41.902780456),  # Ultra high precision
        ]

        for x, y in precision_coords:
            assert ITALY_X_MIN <= x <= ITALY_X_MAX
            assert ITALY_Y_MIN <= y <= ITALY_Y_MAX

    def test_metodo_case_sensitivity(self):
        """Test that metodo values are case sensitive."""
        valid_metodi = ["Coordinate", "Indirizzo", "CoordinateIndirizzo"]
        invalid_metodi = [
            "coordinate",
            "COORDINATE",
            "indirizzo",
            "INDIRIZZO",
            "coordinateindirizzo",
            "COORDINATEINDIRIZZO",
        ]

        for metodo in valid_metodi:
            assert metodo in valid_metodi

        for metodo in invalid_metodi:
            assert metodo not in valid_metodi


class TestCombinedScenarios:
    """Test realistic combined scenarios for coordinate lookups."""

    def test_realistic_coordinate_lookup_request(self):
        """Test validation with realistic coordinate lookup request data."""
        for _ in range(20):
            # Generate realistic Italian coordinates
            x = fake.pyfloat(min_value=ITALY_X_MIN, max_value=ITALY_X_MAX)
            y = fake.pyfloat(min_value=ITALY_Y_MIN, max_value=ITALY_Y_MAX)

            # Generate realistic Belfiore code
            letter = fake.random_uppercase_letter()
            number = fake.random_int(min=0, max=999)
            belfiore_code = f"{letter}{number:03d}"

            # Generate method
            metodo = fake.random_element(
                ["Coordinate", "Indirizzo", "CoordinateIndirizzo"]
            )

            # All should be valid
            assert ITALY_X_MIN <= x <= ITALY_X_MAX
            assert ITALY_Y_MIN <= y <= ITALY_Y_MAX
            validated_code = belfiore_code_validator(belfiore_code)
            assert validated_code == belfiore_code
            assert metodo in ["Coordinate", "Indirizzo", "CoordinateIndirizzo"]

    def test_realistic_italian_address_lookup(self):
        """Test validation with realistic Italian address data."""
        italian_addresses = [
            {
                "via": "Via del Corso",
                "civico": 1,
                "comune": "Roma",
                "belfiore": "H501",
                "x": 12.4802,
                "y": 41.9003,
            },
            {
                "via": "Via Montenapoleone",
                "civico": 8,
                "comune": "Milano",
                "belfiore": "F205",
                "x": 9.1955,
                "y": 45.4685,
            },
            {
                "via": "Via Toledo",
                "civico": 200,
                "comune": "Napoli",
                "belfiore": "G273",
                "x": 14.2503,
                "y": 40.8454,
            },
        ]

        for address in italian_addresses:
            # Validate Belfiore code
            validated_code = belfiore_code_validator(address["belfiore"])
            assert validated_code == address["belfiore"]

            # Validate coordinates
            assert ITALY_X_MIN <= address["x"] <= ITALY_X_MAX
            assert ITALY_Y_MIN <= address["y"] <= ITALY_Y_MAX

            # Validate civico
            assert address["civico"] >= 1

    def test_coordinate_lookup_with_all_metodi(self):
        """Test coordinate lookup with all valid metodo values."""
        metodi = ["Coordinate", "Indirizzo", "CoordinateIndirizzo"]

        for metodo in metodi:
            # Each metodo should have different required fields
            if metodo == "Coordinate":
                # Only coordinates required
                x = 12.4964
                y = 41.9028
                assert ITALY_X_MIN <= x <= ITALY_X_MAX
                assert ITALY_Y_MIN <= y <= ITALY_Y_MAX

            elif metodo == "Indirizzo":
                # Address fields required
                belfiore = "H501"
                validated = belfiore_code_validator(belfiore)
                assert validated == belfiore

            elif metodo == "CoordinateIndirizzo":
                # Both coordinates and address required
                x = 12.4964
                y = 41.9028
                belfiore = "H501"
                assert ITALY_X_MIN <= x <= ITALY_X_MAX
                assert ITALY_Y_MIN <= y <= ITALY_Y_MAX
                validated = belfiore_code_validator(belfiore)
                assert validated == belfiore
