# Input and Output Validation

The ANNCSU SDK implements a hybrid validation approach to ensure data quality for both API requests and responses.

## Overview

### Phase 1: Input Validation (Always Enabled)
Pydantic-based validation for request inputs using Field constraints and custom validators.

### Phase 2: Response Validation (Opt-in)
OpenAPI specification-based validation for API responses, useful for development and testing.

## Phase 1: Input Validation

### Built-in Pydantic Validation

All request models inherit from Pydantic's `BaseModel`, providing automatic validation:

```python
from anncsu.pa import AnncsuConsultazione
from pydantic import ValidationError

sdk = AnncsuConsultazione()

try:
    # This will fail - codcom must be exactly 4 characters
    response = sdk.queryparam.esiste_odonimo_get_query_param(
        codcom="TOOLONG",
        denom="VklBIFJPTUE="
    )
except ValidationError as e:
    print(e.errors())
    # [{'loc': ('codcom',), 'msg': 'String should have at most 4 characters', ...}]
```

### Custom Validators

The SDK provides custom validators for ANNCSU-specific business rules:

#### Base64 Validator

Validates that strings are properly base64 encoded:

```python
from anncsu.common import base64_validator
from pydantic import Field, field_validator
from anncsu.common.types import BaseModel

class MyModel(BaseModel):
    encoded_value: str
    
    @field_validator('encoded_value')
    @classmethod
    def validate_encoding(cls, v: str) -> str:
        return base64_validator(v)

# Valid
model = MyModel(encoded_value="VklBIFJPTUE=")

# Invalid - raises ValidationError
model = MyModel(encoded_value="Not base64!")
```

#### Belfiore Code Validator

Validates Italian Belfiore municipality codes (format: 1 letter + 3 digits):

```python
from anncsu.common import belfiore_code_validator

# Valid Belfiore codes
belfiore_code_validator("H501")  # Rome
belfiore_code_validator("F205")  # Milan

# Invalid - raises ValueError
belfiore_code_validator("INVALID")  # Wrong format
belfiore_code_validator("h501")     # Lowercase not allowed
```

### Enhanced Model Example

Here's how to create models with full validation:

```python
from pydantic import Field, field_validator
from typing_extensions import Annotated
from anncsu.common.types import BaseModel
from anncsu.common import base64_validator, belfiore_code_validator

class ValidatedRequest(BaseModel):
    codcom: Annotated[
        str,
        Field(
            min_length=4,
            max_length=4,
            pattern=r"^[A-Z]\d{3}$",
            description="Codice Belfiore del comune",
            examples=["H501"]
        )
    ]
    
    denom: Annotated[
        str,
        Field(
            min_length=1,
            description="Denominazione base64 encoded",
            examples=["VklBIFJPTUE="]
        )
    ]
    
    @field_validator("codcom")
    @classmethod
    def validate_belfiore(cls, v: str) -> str:
        return belfiore_code_validator(v)
    
    @field_validator("denom")
    @classmethod
    def validate_base64(cls, v: str) -> str:
        return base64_validator(v)
```

## Phase 2: Response Validation

Response validation is **optional** and primarily intended for development and testing.

### Prerequisites

Response validation requires additional dependencies (included in dev dependencies):
- `openapi-pydantic>=0.4.1`
- `pyyaml>=6.0.0`

These are automatically installed with:
```bash
uv sync --dev
```

### Enabling Response Validation

```python
from pathlib import Path
from anncsu.pa import AnncsuConsultazione

# Enable response validation
# For development/validation environment:
sdk = AnncsuConsultazione(
    validate_responses=True,
    openapi_spec_path=Path("oas/dev/Specifica API - ANNCSU – Consultazione per le PA.yaml")
)

# For production environment:
# sdk = AnncsuConsultazione(
#     validate_responses=True,
#     openapi_spec_path=Path("oas/prod/Specifica API - ANNCSU – Consultazione per le PA.yaml")
# )

# Now all API responses will be validated against the OpenAPI spec
response = sdk.queryparam.esiste_odonimo_get_query_param(
    codcom="H501",
    denom="VklBIFJPTUE="
)
```

### What Gets Validated

Response validation checks:

1. **Status Code**: Response status matches one defined in the spec
2. **Content-Type**: Response content type matches expected type
3. **Response Schema**: Response body structure matches the schema
4. **Required Fields**: All required fields are present

### Validation Errors

If validation fails, you'll get detailed error information:

```python
from anncsu.common.errors import ResponseValidationError

try:
    response = sdk.queryparam.esiste_odonimo_get_query_param(
        codcom="H501",
        denom="VklBIFJPTUE="
    )
except ResponseValidationError as e:
    print(f"Validation failed: {e}")
    print(f"Errors: {e.errors}")
```

### Using ResponseValidator Directly

For more control, use the `ResponseValidator` class directly:

```python
from pathlib import Path
from anncsu.common import ResponseValidator
import httpx

# Initialize validator
# Choose appropriate environment spec:
validator = ResponseValidator(
    Path("oas/dev/Specifica API - ANNCSU – Consultazione per le PA.yaml")  # or oas/prod/...
)

# Validate a response
response = httpx.get("https://api.example.com/endpoint")
is_valid, errors = validator.validate_response(
    response=response,
    operation_id="esisteOdonimoGetQueryParam"
)

if not is_valid:
    print(f"Validation errors: {errors}")
```

## Configuration

### SDKConfiguration Options

```python
from pathlib import Path
from anncsu.pa import AnncsuConsultazione

sdk = AnncsuConsultazione(
    # Phase 2: Response validation (opt-in, default: False)
    validate_responses=False,
    
    # Path to OpenAPI spec for validation
    openapi_spec_path=None,  # or Path("path/to/spec.yaml")
)
```

## Best Practices

### Development

✅ **DO** enable response validation during development:
```python
sdk = AnncsuConsultazione(
    validate_responses=True,
    openapi_spec_path=Path("oas/spec.yaml")
)
```

✅ **DO** use custom validators for business logic:
```python
@field_validator('field_name')
@classmethod
def validate_field(cls, v):
    return custom_validator(v)
```

✅ **DO** add Field constraints to catch errors early:
```python
field: Annotated[str, Field(min_length=1, max_length=100)]
```

### Production

❌ **DON'T** enable response validation in production (performance overhead)
```python
sdk = AnncsuConsultazione()  # validation_responses defaults to False
```

✅ **DO** rely on input validation (always enabled, minimal overhead)

✅ **DO** handle ValidationError exceptions:
```python
from pydantic import ValidationError

try:
    sdk.queryparam.esiste_odonimo_get_query_param(...)
except ValidationError as e:
    # Handle invalid input
    logger.error(f"Invalid request: {e}")
```

## Testing

### Running Validation Tests

```bash
# Run all validation tests
uv run pytest tests/validation/ -v

# Run with coverage
uv run pytest tests/validation/ --cov=anncsu.common.validation --cov-report=term-missing
```

### Writing Validation Tests

Example test for custom validators:

```python
import pytest
from pydantic import ValidationError
from anncsu.common import belfiore_code_validator

def test_valid_belfiore_code():
    """Test that valid Belfiore codes pass validation."""
    assert belfiore_code_validator("H501") == "H501"

def test_invalid_belfiore_code():
    """Test that invalid Belfiore codes raise ValueError."""
    with pytest.raises(ValueError, match="Invalid Belfiore code"):
        belfiore_code_validator("INVALID")
```

## OpenAPI Specification Support

The response validator supports:
- OpenAPI 3.0.x (via `openapi-pydantic.v3.v3_0`)
- OpenAPI 3.1.x (via `openapi-pydantic.v3.v3_1`)

The version is automatically detected from the spec file.

## Performance Considerations

### Input Validation
- **Overhead**: Minimal (~microseconds per request)
- **When**: Always runs, cannot be disabled
- **Impact**: Negligible for production use

### Response Validation
- **Overhead**: Moderate (~milliseconds per response)
- **When**: Only when `validate_responses=True`
- **Impact**: Suitable for dev/test, not recommended for production

## Troubleshooting

### Missing Dependencies Error

**Error**:
```
ImportError: Response validation requires openapi-pydantic and pyyaml
```

**Solution**:
```bash
uv sync --dev
```

### Validation Not Working

**Check**:
1. Is `validate_responses=True`?
2. Is `openapi_spec_path` set correctly?
3. Are dev dependencies installed?

### False Positive Validation Errors

Response validation is optimized for OpenAPI 3.1.x. If you encounter issues with 3.0.x specs, please report them.

## API Reference

### Validators

**`base64_validator(v: str) -> str`**
- Validates base64 encoding
- Raises `ValueError` if invalid

**`belfiore_code_validator(v: str) -> str`**
- Validates Belfiore code format (1 letter + 3 digits)
- Raises `ValueError` if invalid

### Classes

**`ValidationConfig`**
```python
@dataclass
class ValidationConfig:
    enabled: bool = False
    openapi_spec_path: Path | None = None
    strict: bool = True
```

**`ResponseValidator`**
```python
class ResponseValidator:
    def __init__(self, spec_path: Path):
        """Initialize validator with OpenAPI spec."""
    
    def validate_response(
        self,
        response: httpx.Response,
        operation_id: str,
    ) -> tuple[bool, list[str]]:
        """
        Validate response against spec.
        
        Returns:
            (is_valid, errors) tuple
        """
```

## Further Reading

- [Pydantic Validators Documentation](https://docs.pydantic.dev/latest/concepts/validators/)
- [OpenAPI Specification](https://spec.openapis.org/oas/v3.0.3)
- [openapi-pydantic Library](https://github.com/kuimono/openapi-pydantic)
