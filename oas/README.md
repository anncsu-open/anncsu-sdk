# OpenAPI Specifications

This directory contains the OpenAPI specifications for different ANNCSU API environments.

## Directory Structure

```
oas/
├── dev/                  # Development/Validation environment specifications
│   └── Specifica API - ANNCSU – Consultazione per le PA.yaml
├── prod/                 # Production environment specifications (when available)
│   └── (to be added by Agenzia delle Entrate)
└── .spectral.yaml        # Spectral linting rules
```

## Environment Specifications

### Development/Validation Environment (`dev/`)

Contains the OpenAPI specification for the PDND validation/test environment:
- **Base URL**: `https://modipa-val.agenziaentrate.it/govway/rest/in/AgenziaEntrate-PDND/anncsu-consultazione/v1`
- **Purpose**: Testing and integration with validation PDND tokens
- **SSL Certificates**: May use internal/self-signed certificates

**Usage in SDK**:
```python
from anncsu.pa import AnncsuConsultazione
from anncsu.common import Security

security = Security(bearer="your-validation-pdnd-token")
sdk = AnncsuConsultazione(
    security=security,
    server_url="https://modipa-val.agenziaentrate.it/govway/rest/in/AgenziaEntrate-PDND/anncsu-consultazione/v1"
)
```

### Production Environment (`prod/`)

**Status**: Not yet available

Will contain the OpenAPI specification for the production environment:
- **Base URL**: `https://modipa.agenziaentrate.gov.it/govway/rest/in/AgenziaEntrate-PDND/anncsu-consultazione/v1` (default)
- **Purpose**: Production API calls with production PDND tokens
- **SSL Certificates**: Publicly trusted certificates

**When available, usage in SDK**:
```python
from anncsu.pa import AnncsuConsultazione
from anncsu.common import Security

security = Security(bearer="your-production-pdnd-token")
# SDK uses production URL by default, or specify explicitly:
sdk = AnncsuConsultazione(
    security=security,
    server_url="https://modipa.agenziaentrate.gov.it/govway/rest/in/AgenziaEntrate-PDND/anncsu-consultazione/v1"
)
```

## Validating Specifications

### Validate Development Specification

```bash
spectral lint oas/dev/Specifica\ API\ -\ ANNCSU\ –\ Consultazione\ per\ le\ PA.yaml --ruleset oas/.spectral.yaml
```

### Validate Production Specification (when available)

```bash
spectral lint oas/prod/Specifica\ API\ -\ ANNCSU\ –\ Consultazione\ per\ le\ PA.yaml --ruleset oas/.spectral.yaml
```

## Key Differences Between Environments

| Aspect | Development/Validation | Production |
|--------|----------------------|------------|
| **Base URL** | `modipa-val.agenziaentrate.it` | `modipa.agenziaentrate.gov.it` |
| **PDND Tokens** | Validation-specific tokens | Production tokens |
| **Token `aud` field** | Points to validation URL | Points to production URL |
| **SSL Certificates** | May be internal/self-signed | Publicly trusted |
| **Purpose** | Testing, integration | Live production use |
| **Availability** | ✅ Available | ⏳ Pending |

## Using Specifications in Code

### Response Validation

You can validate API responses against the OpenAPI spec:

```python
from pathlib import Path
from anncsu.pa import AnncsuConsultazione

# For dev/validation environment:
sdk = AnncsuConsultazione(
    validate_responses=True,
    openapi_spec_path=Path("oas/dev/Specifica API - ANNCSU – Consultazione per le PA.yaml")
)

# For production (when available):
# sdk = AnncsuConsultazione(
#     validate_responses=True,
#     openapi_spec_path=Path("oas/prod/Specifica API - ANNCSU – Consultazione per le PA.yaml")
# )
```

### Direct Validator Usage

```python
from pathlib import Path
from anncsu.common import ResponseValidator

# Choose appropriate environment:
validator = ResponseValidator(
    Path("oas/dev/Specifica API - ANNCSU – Consultazione per le PA.yaml")
)

# Validate responses
is_valid, errors = validator.validate_response(
    response=api_response,
    operation_id="esisteOdonimoGetQueryParam",
    status_code=200
)
```

## Speakeasy Code Generation

The Speakeasy workflow (`.speakeasy/workflow.yaml`) is configured to use the development specification:

```yaml
sources:
    ANNCSU REST API:
        inputs:
            - location: ../oas/dev/Specifica API - ANNCSU – Consultazione per le PA.yaml
```

When production spec becomes available, update the workflow to use it or create separate targets for each environment.

## Important Notes

1. **Token-Environment Matching**: Always ensure your PDND token's `aud` (audience) field matches the environment you're connecting to
2. **SSL Certificates**: Development/validation environment may require custom CA certificates or SSL verification disabled for testing
3. **Specification Updates**: Keep specifications in sync with API provider updates
4. **Environment Isolation**: Never use validation tokens in production or vice versa

## Getting Production Specifications

Contact Agenzia delle Entrate or PDND support to obtain:
- Production OpenAPI specification
- Production PDND tokens
- Production CA certificate bundle (if needed)
- Production environment documentation

## Related Documentation

- [Main README](../README.md) - SDK usage and examples
- [Security Documentation](../docs/SECURITY.md) - PDND authentication details
- [Validation Documentation](../docs/VALIDATION.md) - Response validation guide
- [Conversation Log](../../ANNCSU/CONVERSATION_LOG.md) - Development history

---

*Last Updated: 2025-11-12*
*Environment Support: Development/Validation ✅ | Production ⏳*
