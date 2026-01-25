"""Property-based tests for validators using Hypothesis and Faker."""

import base64
import string

import pytest
from faker import Faker
from hypothesis import assume, given, settings
from hypothesis import strategies as st

from anncsu.common.validation import base64_validator, belfiore_code_validator

# Initialize Faker
fake = Faker("it_IT")  # Italian locale for realistic Italian data


class TestBase64ValidatorPropertyBased:
    """Property-based tests for base64_validator."""

    @given(st.binary())
    @settings(max_examples=100)
    def test_any_bytes_can_be_base64_encoded(self, data: bytes):
        """Test that any bytes can be encoded to valid base64."""
        encoded = base64.b64encode(data).decode("ascii")
        # Should not raise
        result = base64_validator(encoded)
        assert result == encoded

    @given(st.text(alphabet=string.ascii_letters + string.digits + "+/=", min_size=4))
    @settings(max_examples=100)
    def test_valid_base64_alphabet_accepts(self, text: str):
        """Test that strings with valid base64 alphabet are handled correctly."""
        # Pad to make it valid base64 length
        padded = text + "=" * ((4 - len(text) % 4) % 4)

        try:
            # Try to decode - if it works, validator should accept it
            base64.b64decode(padded, validate=True)
            result = base64_validator(padded)
            assert result == padded
        except Exception:
            # If decode fails, validator should reject it
            with pytest.raises(ValueError, match="Invalid base64"):
                base64_validator(padded)

    @given(
        st.text(
            alphabet=string.printable.replace("+", "")
            .replace("/", "")
            .replace("=", ""),
            min_size=1,
        ).filter(
            lambda x: not all(c in string.ascii_letters + string.digits for c in x)
        )
    )
    @settings(max_examples=50)
    def test_invalid_characters_rejected(self, text: str):
        """Test that strings with invalid base64 characters are rejected."""
        with pytest.raises(ValueError, match="Invalid base64"):
            base64_validator(text)

    @given(st.text(min_size=1, max_size=200))
    @settings(max_examples=100)
    def test_round_trip_encoding(self, text: str):
        """Test that encoding and validating text works correctly."""
        encoded = base64.b64encode(text.encode("utf-8")).decode("ascii")
        result = base64_validator(encoded)
        assert result == encoded

        # Verify we can decode it back
        decoded = base64.b64decode(result).decode("utf-8")
        assert decoded == text


class TestBelfioreCodeValidatorPropertyBased:
    """Property-based tests for belfiore_code_validator."""

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
        st.integers(min_value=0, max_value=9999).filter(lambda x: x < 1000 or x > 9999)
    )
    @settings(max_examples=50)
    def test_wrong_length_rejected(self, number: int):
        """Test that wrong length codes are rejected."""
        if number < 10:
            code = f"A{number}"  # Too short
        elif number >= 10 and number < 100:
            code = f"A{number}"  # Too short
        else:
            code = f"A{number}"  # Too long

        # Only test if not exactly 3 digits after letter
        if len(code) != 4:
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

    @given(st.text(alphabet=string.ascii_uppercase, min_size=2))
    @settings(max_examples=50)
    def test_multiple_letters_rejected(self, letters: str):
        """Test that codes with multiple letters are rejected."""
        code = f"{letters}01"
        with pytest.raises(ValueError, match="Invalid Belfiore code"):
            belfiore_code_validator(code)


class TestValidatorsWithFaker:
    """Tests using Faker to generate realistic Italian data."""

    def test_realistic_italian_street_names_base64(self):
        """Test base64 encoding of realistic Italian street names."""
        for _ in range(50):
            street = fake.street_name()
            encoded = base64.b64encode(street.encode("utf-8")).decode("ascii")

            # Should validate successfully
            result = base64_validator(encoded)
            assert result == encoded

            # Should decode back correctly
            decoded = base64.b64decode(result).decode("utf-8")
            assert decoded == street

    def test_realistic_city_names_base64(self):
        """Test base64 encoding of realistic Italian city names."""
        for _ in range(50):
            city = fake.city()
            encoded = base64.b64encode(city.encode("utf-8")).decode("ascii")

            result = base64_validator(encoded)
            assert result == encoded

    def test_realistic_addresses_base64(self):
        """Test base64 encoding of realistic Italian addresses."""
        for _ in range(30):
            address = fake.address()
            encoded = base64.b64encode(address.encode("utf-8")).decode("ascii")

            result = base64_validator(encoded)
            assert result == encoded

    def test_special_characters_in_italian_text(self):
        """Test base64 encoding with Italian special characters."""
        italian_texts = [
            "Via Torino",
            "Piazza San Marco",
            "Corso Vittorio Emanuele II",
            "Viale della Repubblica",
            "Via Nazionale",
            "Circonvallazione Clodia",
        ]

        for text in italian_texts:
            encoded = base64.b64encode(text.encode("utf-8")).decode("ascii")
            result = base64_validator(encoded)
            assert result == encoded

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


class TestEdgeCases:
    """Test edge cases discovered through property-based testing."""

    def test_empty_string_base64(self):
        """Test that empty string is valid base64 (encodes to empty)."""
        # Empty string encoded is empty string
        result = base64_validator("")
        assert result == ""

    def test_padding_variations(self):
        """Test base64 strings with different padding."""
        test_cases = [
            "YQ==",  # 2 padding chars
            "YWI=",  # 1 padding char
            "YWJj",  # No padding
        ]

        for encoded in test_cases:
            result = base64_validator(encoded)
            assert result == encoded

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

    def test_unicode_in_base64(self):
        """Test base64 encoding of Unicode characters."""
        unicode_strings = [
            "Café",
            "Müller",
            "日本語",
            "Привет",
            "مرحبا",
            "🏠🚗",  # Emojis
        ]

        for text in unicode_strings:
            encoded = base64.b64encode(text.encode("utf-8")).decode("ascii")
            result = base64_validator(encoded)
            assert result == encoded

            # Verify round-trip
            decoded = base64.b64decode(result).decode("utf-8")
            assert decoded == text


class TestCombinedScenarios:
    """Test realistic combined scenarios."""

    def test_realistic_api_request_data(self):
        """Test validation with realistic API request data."""
        for _ in range(20):
            # Generate realistic Italian street name
            street_name = f"Via {fake.last_name()}"
            encoded_street = base64.b64encode(street_name.encode("utf-8")).decode(
                "ascii"
            )

            # Generate realistic Belfiore code pattern
            letter = fake.random_uppercase_letter()
            number = fake.random_int(min=0, max=999)
            belfiore_code = f"{letter}{number:03d}"

            # Both should validate
            validated_street = base64_validator(encoded_street)
            validated_code = belfiore_code_validator(belfiore_code)

            assert validated_street == encoded_street
            assert validated_code == belfiore_code
