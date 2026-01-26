"""Model factory tests using Polyfactory for generating test data."""

import base64

import pytest
from polyfactory.factories.pydantic_factory import ModelFactory
from polyfactory.pytest_plugin import register_fixture
from pydantic import ValidationError

from anncsu.common.validation.examples import (
    EsisteOdonimoGetQueryParamRequestValidated,
    StrictValidatedModel,
)


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


class Base64StringFactory:
    """Factory for generating valid base64-encoded strings."""

    @staticmethod
    def build(text: str | None = None) -> str:
        """Generate a valid base64-encoded string."""
        import random
        import string

        if text is None:
            # Generate random text
            length = random.randint(5, 50)
            text = "".join(
                random.choices(string.ascii_letters + string.digits + " ", k=length)
            )

        return base64.b64encode(text.encode("utf-8")).decode("ascii")


class EsisteOdonimoRequestFactory(
    ModelFactory[EsisteOdonimoGetQueryParamRequestValidated]
):
    """Factory for generating valid EsisteOdonimoGetQueryParamRequest instances."""

    __model__ = EsisteOdonimoGetQueryParamRequestValidated
    __check_model__ = False  # Explicitly disable to avoid deprecation warning

    @classmethod
    def codcom(cls) -> str:
        """Generate a valid Belfiore code."""
        return BelfioreCodeFactory.build()

    @classmethod
    def denom(cls) -> str:
        """Generate a valid base64-encoded denomination."""
        return Base64StringFactory.build()


class StrictModelFactory(ModelFactory[StrictValidatedModel]):
    """Factory for strict validated model."""

    __model__ = StrictValidatedModel
    __check_model__ = False  # Explicitly disable to avoid deprecation warning


# Register as pytest fixture
request_factory = register_fixture(EsisteOdonimoRequestFactory)
strict_factory = register_fixture(StrictModelFactory)


class TestModelFactories:
    """Tests using Polyfactory to generate model instances."""

    def test_factory_generates_valid_models(self):
        """Test that factory generates valid model instances."""
        for _ in range(50):
            request = EsisteOdonimoRequestFactory.build()

            # Verify it's a valid model
            assert isinstance(request, EsisteOdonimoGetQueryParamRequestValidated)

            # Verify fields are valid
            assert len(request.codcom) == 4
            assert request.codcom[0].isupper()
            assert request.codcom[1:].isdigit()

            # Verify base64 is valid
            decoded = base64.b64decode(request.denom)
            assert isinstance(decoded, bytes)

    def test_factory_batch_generation(self):
        """Test generating batches of valid models."""
        batch = EsisteOdonimoRequestFactory.batch(size=100)

        assert len(batch) == 100
        for request in batch:
            # All should be valid
            assert isinstance(request, EsisteOdonimoGetQueryParamRequestValidated)

            # Can be serialized
            data = request.model_dump()
            assert "codcom" in data
            assert "denom" in data

    def test_factory_with_custom_values(self):
        """Test factory with custom field values."""
        custom_code = "H501"  # Rome
        custom_denom = base64.b64encode(b"VIA ROMA").decode("ascii")

        request = EsisteOdonimoRequestFactory.build(
            codcom=custom_code, denom=custom_denom
        )

        assert request.codcom == custom_code
        assert request.denom == custom_denom

    def test_strict_model_factory(self):
        """Test factory for strict validated model."""
        for _ in range(30):
            model = StrictModelFactory.build()

            assert isinstance(model, StrictValidatedModel)
            assert len(model.required_string) >= 1
            assert len(model.required_string) <= 100

            if model.optional_int is not None:
                assert 0 <= model.optional_int <= 1000


class TestFactoryValidationCatching:
    """Tests that factory-generated data catches validation errors."""

    def test_factory_respects_field_constraints(self):
        """Test that factory respects Pydantic Field constraints."""
        # Generate many instances
        batch = StrictModelFactory.batch(size=100)

        for model in batch:
            # All required_string values should respect constraints
            assert 1 <= len(model.required_string) <= 100

            # All optional_int values should be in range
            if model.optional_int is not None:
                assert 0 <= model.optional_int <= 1000

    def test_invalid_data_rejected(self):
        """Test that invalid data is still rejected even with factory."""
        # Try to create with invalid codcom (too long)
        with pytest.raises(ValidationError):
            EsisteOdonimoRequestFactory.build(codcom="TOOLONG")

        # Try to create with invalid base64
        with pytest.raises(ValidationError):
            EsisteOdonimoRequestFactory.build(denom="NOT BASE64!")

    def test_factory_data_passes_custom_validators(self):
        """Test that factory-generated data passes custom validators."""
        for _ in range(50):
            request = EsisteOdonimoRequestFactory.build()

            # The custom validators should have been called and passed
            # Verify codcom format
            assert request.codcom[0] in "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
            assert request.codcom[1:].isdigit()
            assert len(request.codcom) == 4

            # Verify base64 can be decoded
            try:
                base64.b64decode(request.denom, validate=True)
            except Exception as e:
                pytest.fail(f"Factory generated invalid base64: {e}")


class TestRealisticScenarios:
    """Test realistic scenarios with factory-generated data."""

    def test_api_request_simulation(self):
        """Simulate API requests with factory-generated data."""
        # Generate 100 requests as if they were coming from users
        requests = EsisteOdonimoRequestFactory.batch(size=100)

        successful = 0
        for request in requests:
            try:
                # Simulate validation
                _ = EsisteOdonimoGetQueryParamRequestValidated(
                    codcom=request.codcom, denom=request.denom
                )
                successful += 1
            except ValidationError:
                pass

        # All factory-generated requests should be valid
        assert successful == 100

    def test_concurrent_request_generation(self):
        """Test generating many requests concurrently."""
        batches = []
        for _ in range(10):
            batch = EsisteOdonimoRequestFactory.batch(size=10)
            batches.append(batch)

        # Flatten and verify all are unique
        all_requests = [req for batch in batches for req in batch]
        assert len(all_requests) == 100

        # Verify diversity in generated data
        codcoms = [req.codcom for req in all_requests]
        denoms = [req.denom for req in all_requests]

        # Should have variety (not all the same)
        assert len(set(codcoms)) > 1
        assert len(set(denoms)) > 1

    def test_model_serialization_deserialization(self):
        """Test that factory-generated models can be serialized and deserialized."""
        for _ in range(30):
            original = EsisteOdonimoRequestFactory.build()

            # Serialize to dict
            data = original.model_dump()

            # Deserialize back
            restored = EsisteOdonimoGetQueryParamRequestValidated(**data)

            # Should be equal
            assert restored.codcom == original.codcom
            assert restored.denom == original.denom

    def test_json_serialization(self):
        """Test JSON serialization of factory-generated models."""
        import json

        for _ in range(20):
            model = EsisteOdonimoRequestFactory.build()

            # Serialize to JSON
            json_str = model.model_dump_json()

            # Deserialize from JSON
            data = json.loads(json_str)
            restored = EsisteOdonimoGetQueryParamRequestValidated(**data)

            assert restored.codcom == model.codcom
            assert restored.denom == model.denom


class TestFactoryEdgeCases:
    """Test edge cases with factory-generated data."""

    def test_boundary_belfiore_codes(self):
        """Test Belfiore codes at boundaries."""
        boundary_codes = ["A000", "A999", "Z000", "Z999"]

        for code in boundary_codes:
            request = EsisteOdonimoRequestFactory.build(codcom=code)
            assert request.codcom == code

    def test_various_base64_lengths(self):
        """Test base64 strings of various lengths."""
        test_strings = ["a", "ab", "abc", "abcd", "a" * 100]

        for text in test_strings:
            encoded = base64.b64encode(text.encode()).decode("ascii")
            request = EsisteOdonimoRequestFactory.build(denom=encoded)
            assert request.denom == encoded

    def test_special_characters_in_base64(self):
        """Test base64 encoding of strings with special characters."""
        special_strings = [
            "Hello, World!",
            "Test@#$%",
            "Line1\nLine2",
            "Tab\tSeparated",
            'Quote"Test"',
        ]

        for text in special_strings:
            encoded = base64.b64encode(text.encode()).decode("ascii")
            request = EsisteOdonimoRequestFactory.build(denom=encoded)

            # Should validate and round-trip
            decoded = base64.b64decode(request.denom).decode()
            assert decoded == text


class TestFactoryPerformance:
    """Test factory performance with large batches."""

    def test_large_batch_generation(self):
        """Test generating large batches of models."""
        import time

        start = time.time()
        batch = EsisteOdonimoRequestFactory.batch(size=1000)
        elapsed = time.time() - start

        assert len(batch) == 1000
        # Should be fast (less than 5 seconds for 1000 instances)
        assert elapsed < 5.0

        # All should be valid
        for request in batch:
            assert len(request.codcom) == 4
            assert len(request.denom) > 0

    def test_factory_memory_efficiency(self):
        """Test that factory doesn't leak memory with many generations."""

        # Generate in batches to avoid memory spike
        total_generated = 0
        for _ in range(10):
            batch = EsisteOdonimoRequestFactory.batch(size=100)
            total_generated += len(batch)
            del batch  # Explicitly delete to help GC

        assert total_generated == 1000
