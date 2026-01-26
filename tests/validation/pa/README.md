# Validation Tests

This directory contains tests for the SDK validation features.

## Overview

The ANNCSU SDK implements a hybrid validation approach:

- **Phase 1 (Input Validation)**: Pydantic Field constraints and custom validators
- **Phase 2 (Response Validation)**: Optional OpenAPI specification validation

## Test Structure

```
tests/validation/
├── __init__.py
├── README.md (this file)
├── ADVANCED_TESTING.md              # Advanced testing strategies guide
├── test_validators.py               # Basic validator tests (11 tests)
├── test_validators_property.py      # Property-based tests (19 tests)
├── test_model_factories.py          # Factory-based tests (16 tests)
└── test_response_validator.py       # Response validation tests (12 tests)
```

## Test Statistics

**Total Tests:** 58 validation tests
- Basic unit tests: 23 tests
- Property-based tests (Hypothesis): 19 tests
- Factory-based tests (Polyfactory): 16 tests

**Execution Time:** ~10 seconds
**Examples Generated:** 700+ property checks, 1500+ factory instances

## Running Tests

### Run all validation tests
```bash
uv run pytest tests/validation/ -v
```

### Run specific test file
```bash
uv run pytest tests/validation/test_validators.py -v
uv run pytest tests/validation/test_response_validator.py -v
```

### Run with coverage
```bash
uv run pytest tests/validation/ --cov=anncsu.common.validation --cov-report=term-missing
```

## Advanced Testing

This test suite uses advanced testing techniques:

- **Property-Based Testing (Hypothesis)**: Generates hundreds of random inputs to find edge cases
- **Realistic Data (Faker)**: Tests with realistic Italian street names, cities, and Belfiore codes
- **Model Factories (Polyfactory)**: Generates complete valid model instances for integration testing

See [ADVANCED_TESTING.md](ADVANCED_TESTING.md) for detailed information.

## Test Coverage

### test_validators.py (11 tests)

**TestBase64Validator (3 tests)**
- Valid base64 strings
- Invalid base64 strings
- Non-string inputs

**TestBelfioreCodeValidator (3 tests)**
- Valid Belfiore codes (H501, F205, etc.)
- Invalid Belfiore codes (wrong format, length)
- Non-string inputs

**TestValidatorsIntegration (5 tests)**
- Validators in Pydantic models
- Invalid Belfiore code in model
- Invalid base64 in model
- Field constraints enforcement
- Error message validation

### test_response_validator.py (12 tests)

**TestValidationConfig (2 tests)**
- Default configuration
- Custom configuration

**TestResponseValidator (9 tests)**
- Validator initialization
- Missing spec file handling
- Dependency requirements
- Operation finding
- Successful response validation
- Invalid operation ID
- Wrong status code
- Wrong content type
- Invalid JSON

**TestResponseValidatorIntegration (2 tests)**
- SDKConfiguration validation parameters
- Validation disabled by default

### test_validators_property.py (19 tests)

**TestBase64ValidatorPropertyBased (4 tests)**
- Any bytes can be base64 encoded (100 examples)
- Valid base64 alphabet handling (100 examples)
- Invalid characters rejected (50 examples)
- Round-trip encoding (100 examples)

**TestBelfioreCodeValidatorPropertyBased (5 tests)**
- Valid Belfiore format (200 examples)
- Lowercase letters rejected (50 examples)
- Wrong length rejected (50 examples)
- Invalid patterns rejected (100 examples)
- Multiple letters rejected (50 examples)

**TestValidatorsWithFaker (5 tests)**
- Realistic Italian street names (50 each)
- Realistic Italian city names (50 each)
- Realistic Italian addresses (30 each)
- Special characters in Italian text
- Known Italian Belfiore codes (10 major cities)

**TestEdgeCases (4 tests)**
- Empty string base64
- Padding variations
- Belfiore boundary values
- Unicode in base64 (Japanese, Arabic, emojis, etc.)

**TestCombinedScenarios (1 test)**
- Realistic API request data (20 scenarios)

### test_model_factories.py (16 tests)

**TestModelFactories (4 tests)**
- Factory generates valid models (50 instances)
- Batch generation (100 instances)
- Custom field values
- Strict model factory (30 instances)

**TestFactoryValidationCatching (3 tests)**
- Factory respects Field constraints (100 instances)
- Invalid data rejected
- Custom validators compatibility (50 instances)

**TestRealisticScenarios (4 tests)**
- API request simulation (100 requests)
- Concurrent generation (100 instances)
- Serialization/deserialization (30 examples)
- JSON serialization (20 examples)

**TestFactoryEdgeCases (3 tests)**
- Boundary Belfiore codes
- Various base64 lengths
- Special characters in base64

**TestFactoryPerformance (2 tests)**
- Large batch generation (1000 instances)
- Memory efficiency (1000 instances)

## Dependencies

The validation tests require:
- `openapi-pydantic>=0.4.1` - For parsing OpenAPI specs
- `pyyaml>=6.0.0` - For loading YAML spec files

These are included in the `dev` dependency group.

## Test Data

Tests use the actual OpenAPI specification:
```
oas/Specifica API - ANNCSU – Consultazione per le PA.yaml
```

## CI Integration

These tests run automatically in CI as part of the main test suite:
```yaml
- name: Run tests
  run: uv run pytest tests/ -v --cov=anncsu
```

The CI installs dev dependencies which include `openapi-pydantic` and `pyyaml`.

## Adding New Validation Tests

When adding new validators:

1. Create the validator in `src/anncsu/common/validation/validators.py`
2. Add unit tests in `test_validators.py`
3. Add integration tests showing usage in Pydantic models
4. Update this README

When extending response validation:

1. Add features to `src/anncsu/common/validation/response_validator.py`
2. Add tests in `test_response_validator.py`
3. Update this README
