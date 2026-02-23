# Security and Authentication

The ANNCSU SDK uses PDND (Piattaforma Digitale Nazionale Dati) voucher-based authentication for all API requests. This document explains how to configure and use authentication across all ANNCSU API specifications.

## Overview

All ANNCSU APIs share the same authentication mechanism:
- **Type**: HTTP Bearer Token
- **Format**: PDND Voucher (typically JWT)
- **Header**: `Authorization: Bearer <token>`
- **Common**: Same `Security` class works for all ANNCSU APIs

## Quick Start

```python
from anncsu.pa import AnncsuConsultazione
from anncsu.common import Security

# Create security configuration with your PDND voucher
security = Security(bearer="your-pdnd-voucher-token")

# Initialize SDK with security
sdk = AnncsuConsultazione(security=security)

# Make authenticated requests
response = sdk.queryparam.esiste_odonimo_get_query_param(
    codcom="H501",
    denom="VklBIFJPTUE="
)
```

## Security Class

The `Security` class is located in the common module and is shared across all ANNCSU API SDKs:

```python
from anncsu.common import Security

# With bearer token (authenticated)
security = Security(bearer="your-pdnd-voucher-token")

# Without bearer token (if supported by endpoint)
security = Security()
```

### Attributes

**`bearer: str | None`**
- PDND voucher token for Bearer authentication
- Included in Authorization header as `Bearer <token>`
- `None` for anonymous/unauthenticated requests (if supported)

**`validate_expiration: bool`** (default: `True`)
- When `True`, validates that the token is not expired on initialization
- Raises `TokenExpiredError` if the token has expired
- Set to `False` to skip validation (not recommended)

### Token Expiration Validation

The `Security` class automatically validates token expiration when initialized. This prevents confusing API errors (like 404) when using an expired token:

```python
from anncsu.common import Security, TokenExpiredError

try:
    security = Security(bearer=access_token)
except TokenExpiredError as e:
    print(f"Token expired at {e.expired_at}")
    print(f"Current time: {e.current_time}")
    # Refresh the token and retry
```

### Checking Expiration Manually

```python
from anncsu.common import Security

security = Security(bearer=access_token)

# Check if token is expired
if security.is_expired():
    print("Token needs refresh!")

# Get seconds until expiration
ttl = security.time_until_expiration()
if ttl is not None:
    if ttl < 0:
        print(f"Token expired {abs(ttl)} seconds ago")
    elif ttl < 60:
        print(f"Token expires in {ttl} seconds - refresh soon!")
    else:
        print(f"Token valid for {ttl} seconds")
```

### Skipping Expiration Validation

In some cases (e.g., testing), you may want to skip validation:

```python
# Not recommended for production use
security = Security(bearer=expired_token, validate_expiration=False)
```

## PDND Voucher Format

PDND vouchers are typically JWT (JSON Web Token) format:

```
eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCIsImtpZCI6InBkbmQta2V5LTEyMyJ9.
eyJpc3MiOiJodHRwczovL2F1dGgucGRuZC5pdGFsaWEuaXQiLCJzdWIiOiJjb211bmUt
ZGktcm9tYSIsImF1ZCI6Imh0dHBzOi8vYXBpLmFuY3N1Lmdvdi5pdCIsImV4cCI6MTcz
NjYwMDAwMCwiaWF0IjoxNzM2NTEzNjAwLCJzY29wZSI6ImFuY3N1LmNvbnN1bHRhemlv
bmUgYW5jc3UuYWdnaW9ybmFtZW50byJ9.
ABC123signature456DEF789
```

### JWT Structure

PDND vouchers have three parts separated by dots:
1. **Header**: Algorithm and token type
2. **Payload**: Claims (issuer, subject, audience, expiration, etc.)
3. **Signature**: Cryptographic signature

## Generating Client Assertions

The SDK includes a built-in module for generating PDND client assertions (JWT tokens). This allows you to create the JWT needed to obtain a PDND voucher programmatically.

### Basic Usage

```python
from anncsu.common import ClientAssertionConfig, create_client_assertion

# With private key as bytes
config = ClientAssertionConfig(
    kid="your-key-id",
    issuer="your-client-id",
    subject="your-client-id",
    audience="https://auth.interop.pagopa.it/token.oauth2",
    purpose_id="your-purpose-id",
    private_key=b"-----BEGIN RSA PRIVATE KEY-----\n...",
)
token = create_client_assertion(config)
```

### With Key File Path

```python
from pathlib import Path
from anncsu.common import ClientAssertionConfig, create_client_assertion

config = ClientAssertionConfig(
    kid="your-key-id",
    issuer="your-client-id",
    subject="your-client-id",
    audience="https://auth.interop.pagopa.it/token.oauth2",
    purpose_id="your-purpose-id",
    key_path=Path("./private_key.pem"),
)
token = create_client_assertion(config)
```

### From Environment Variables (.env file)

The SDK supports loading configuration from environment variables or a `.env` file using `ClientAssertionSettings`:

```python
from anncsu.common.config import ClientAssertionSettings
from anncsu.common import create_client_assertion

# Loads configuration from environment variables or .env file
settings = ClientAssertionSettings()
config = settings.to_config()
token = create_client_assertion(config)
```

#### Environment Variables

All environment variables use the `PDND_` prefix:

| Environment Variable | Required | Description |
|---------------------|----------|-------------|
| `PDND_KID` | Yes | Key ID (kid) header parameter |
| `PDND_ISSUER` | Yes | Issuer (iss) claim - your client_id |
| `PDND_SUBJECT` | Yes | Subject (sub) claim - your client_id |
| `PDND_AUDIENCE` | Yes | Audience (aud) claim - PDND token endpoint URL |
| `PDND_PURPOSE_ID_PA` | Yes | Purpose ID for PA Consultazione API |
| `PDND_PURPOSE_ID_COORDINATE` | Yes | Purpose ID for Coordinate API |
| `PDND_PURPOSE_ID_ACCESSI` | Yes* | Purpose ID for Accessi API (can be empty) |
| `PDND_PURPOSE_ID_INTERNI` | Yes* | Purpose ID for Interni API (can be empty) |
| `PDND_PURPOSE_ID_ODONIMI` | Yes* | Purpose ID for Odonimi API (can be empty) |
| `PDND_PRIVATE_KEY` | One required | RSA private key content in PEM format (string) |
| `PDND_KEY_PATH` | One required | Path to the RSA private key file |
| `PDND_ALG` | No | Algorithm (default: "RS256") |
| `PDND_TYP` | No | Token type (default: "JWT") |
| `PDND_VALIDITY_MINUTES` | No | JWT validity in minutes (default: 43200) |

#### Example .env File

```bash
# .env
PDND_KID=my-key-id
PDND_ISSUER=my-client-id
PDND_SUBJECT=my-client-id
PDND_AUDIENCE=https://auth.interop.pagopa.it/token.oauth2

# Purpose ID for each API type (ALL must be present, can be empty if not used)
PDND_PURPOSE_ID_PA=your-purpose-id-for-pa-consultazione
PDND_PURPOSE_ID_COORDINATE=your-purpose-id-for-coordinate-api
PDND_PURPOSE_ID_ACCESSI=
PDND_PURPOSE_ID_INTERNI=
PDND_PURPOSE_ID_ODONIMI=

PDND_KEY_PATH=./private_key.pem
# Or use PDND_PRIVATE_KEY for inline key content
```

#### Shell Environment Variables

```bash
export PDND_KID="my-key-id"
export PDND_ISSUER="my-client-id"
export PDND_SUBJECT="my-client-id"
export PDND_AUDIENCE="https://auth.interop.pagopa.it/token.oauth2"

# Purpose ID for each API type (ALL must be present, can be empty if not used)
export PDND_PURPOSE_ID_PA="your-purpose-id-for-pa-consultazione"
export PDND_PURPOSE_ID_COORDINATE="your-purpose-id-for-coordinate-api"
export PDND_PURPOSE_ID_ACCESSI=""
export PDND_PURPOSE_ID_INTERNI=""
export PDND_PURPOSE_ID_ODONIMI=""

export PDND_KEY_PATH="./private_key.pem"
```

Then in Python:

```python
from anncsu.common.config import ClientAssertionSettings
from anncsu.common import create_client_assertion

# Automatically loads from environment
settings = ClientAssertionSettings()
token = create_client_assertion(settings.to_config())
```

### Configuration Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `kid` | `str` | Yes | Key ID (kid) header parameter - identifies which key was used |
| `issuer` | `str` | Yes | Issuer (iss) claim - typically your client_id from PDND |
| `subject` | `str` | Yes | Subject (sub) claim - typically your client_id from PDND |
| `audience` | `str` | Yes | Audience (aud) claim - the PDND token endpoint URL (must be HTTPS) |
| `purpose_id` | `str` | Yes | Purpose ID for the PDND request |
| `private_key` | `bytes` | One of these | RSA private key content in PEM format |
| `key_path` | `Path` | is required | Path to the RSA private key file |
| `alg` | `str` | No | Algorithm (default: "RS256") |
| `typ` | `str` | No | Token type (default: "JWT") |
| `validity_minutes` | `int` | No | JWT validity period in minutes (default: 43200 = 30 days, max: 43200) |

### Custom Timestamps (for Testing)

```python
import datetime
from anncsu.common import ClientAssertionConfig, create_client_assertion

config = ClientAssertionConfig(
    kid="your-key-id",
    issuer="your-client-id",
    subject="your-client-id",
    audience="https://auth.interop.pagopa.it/token.oauth2",
    purpose_id="your-purpose-id",
    private_key=private_key_bytes,
    validity_minutes=60,  # 1 hour
)

# Custom issued_at and jti for deterministic testing
token = create_client_assertion(
    config,
    issued_at=datetime.datetime(2024, 1, 1, 12, 0, 0, tzinfo=datetime.UTC),
    jti="custom-jti-for-testing",
)
```

### Error Handling

```python
from anncsu.common import (
    ClientAssertionConfig,
    create_client_assertion,
    ClientAssertionError,
    KeyFileError,
    JWTGenerationError,
)

try:
    config = ClientAssertionConfig(
        kid="your-key-id",
        issuer="your-client-id",
        subject="your-client-id",
        audience="https://auth.interop.pagopa.it/token.oauth2",
        purpose_id="your-purpose-id",
        key_path=Path("./private_key.pem"),
    )
    token = create_client_assertion(config)
except KeyFileError as e:
    print(f"Error reading key file: {e}")
except JWTGenerationError as e:
    print(f"Error generating JWT: {e}")
except ClientAssertionError as e:
    print(f"Client assertion error: {e}")
```

### CLI Tool

For command-line usage, a CLI tool is also available:

```bash
python scripts/create_client_assertion.py create \
    --kid "your-key-id" \
    --issuer "your-client-id" \
    --subject "your-client-id" \
    --audience "auth.interop.pagopa.it/client-assertion" \
    --purpose-id "your-purpose-id" \
    --key-path ./private_key.pem
```

## Token Exchange (OAuth2 Client Credentials)

After generating a client assertion, exchange it for an access token using the `get_access_token` function.

### TokenConfig Parameters

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `client_id` | `str` | Yes | - | Your PDND client ID |
| `client_assertion` | `str` | Yes | - | JWT from `create_client_assertion()` |
| `token_endpoint` | `str` | Yes | - | PDND token endpoint URL (must be HTTPS) |
| `client_assertion_type` | `str` | No | `urn:ietf:params:oauth:client-assertion-type:jwt-bearer` | OAuth2 assertion type |
| `grant_type` | `str` | No | `client_credentials` | OAuth2 grant type |
| `timeout` | `float` | No | `30.0` | Request timeout in seconds |

### TokenResponse Fields

| Field | Type | Description |
|-------|------|-------------|
| `access_token` | `str` | The access token for API requests |
| `token_type` | `str` | Token type (typically "Bearer") |
| `expires_in` | `int \| None` | Token lifetime in seconds |

### Token Exchange Error Handling

```python
from anncsu.common import (
    TokenConfig,
    get_access_token,
    TokenError,
    TokenRequestError,
    TokenResponseError,
)

try:
    token_config = TokenConfig(
        client_id="your-client-id",
        client_assertion=client_assertion,
        token_endpoint="https://auth.uat.interop.pagopa.it/token.oauth2",
    )
    token_response = get_access_token(token_config)
    
except TokenRequestError as e:
    # Network/HTTP errors
    print(f"Request failed: {e}")
    print(f"Status code: {e.status_code}")
    print(f"Response body: {e.response_body}")
    
except TokenResponseError as e:
    # OAuth2 error response
    print(f"Token error: {e}")
    print(f"Error code: {e.error}")           # e.g., "invalid_grant"
    print(f"Description: {e.error_description}")
    
except TokenError as e:
    # Base exception for any token-related error
    print(f"Token error: {e}")
```

### Common Token Errors

| Error Code | Description | Solution |
|------------|-------------|----------|
| `invalid_client` | Client authentication failed | Check client_id and assertion signature |
| `invalid_grant` | Client assertion is invalid or expired | Regenerate client assertion |
| `invalid_request` | Missing or invalid parameters | Check all required parameters |
| `unauthorized_client` | Client not authorized for grant type | Contact PDND support |

### Using Custom HTTP Client

```python
import httpx
from anncsu.common import TokenConfig, get_access_token

# Custom client with specific settings
custom_client = httpx.Client(
    timeout=60.0,
    verify=True,  # SSL verification
    # Add proxy, headers, etc.
)

token_config = TokenConfig(
    client_id="your-client-id",
    client_assertion=client_assertion,
    token_endpoint="https://auth.uat.interop.pagopa.it/token.oauth2",
)

# Pass custom client
token_response = get_access_token(token_config, client=custom_client)

# Don't forget to close the client when done
custom_client.close()
```

## Complete Authentication Flow

The PDND authentication flow consists of three steps, all supported by this SDK:

```
┌─────────────────────┐     ┌─────────────────────┐     ┌─────────────────────┐
│  1. Create Client   │     │  2. Exchange for    │     │  3. Use Access      │
│     Assertion       │────▶│     Access Token    │────▶│     Token           │
│     (JWT)           │     │     (OAuth2)        │     │     (API Calls)     │
└─────────────────────┘     └─────────────────────┘     └─────────────────────┘
```

### Step 1: Create Client Assertion (JWT)

Generate a signed JWT client assertion using your RSA private key:

```python
from pathlib import Path
from anncsu.common import ClientAssertionConfig, create_client_assertion

# Configure the client assertion
config = ClientAssertionConfig(
    kid="your-key-id",                                    # Key ID from PDND
    issuer="43508172-aa22-46b0-8c01-3006e745c73c",       # Your client_id
    subject="43508172-aa22-46b0-8c01-3006e745c73c",      # Your client_id
    audience="auth.uat.interop.pagopa.it/client-assertion",  # PDND audience
    purpose_id="732877af-a76b-4528-979a-e6515ff9b06b",   # Your purpose_id
    key_path=Path("./private_key.pem"),                   # Your RSA private key
)

# Generate the JWT
client_assertion = create_client_assertion(config)
print(f"Client Assertion: {client_assertion}")
```

### Step 2: Exchange for Access Token

Exchange the client assertion for an access token via the PDND token endpoint:

```python
from anncsu.common import TokenConfig, get_access_token

# Configure the token request
token_config = TokenConfig(
    client_id="43508172-aa22-46b0-8c01-3006e745c73c",           # Your client_id
    client_assertion=client_assertion,                           # JWT from step 1
    token_endpoint="https://auth.uat.interop.pagopa.it/token.oauth2",  # PDND token endpoint
)

# Exchange for access token
token_response = get_access_token(token_config)

print(f"Access Token: {token_response.access_token}")
print(f"Token Type: {token_response.token_type}")
print(f"Expires In: {token_response.expires_in} seconds")
```

### Step 3: Use Access Token for API Calls

Use the access token to authenticate API requests:

```python
from anncsu.pa import AnncsuConsultazione
from anncsu.common import Security

# Create security with the access token
security = Security(bearer=token_response.access_token)

# Initialize SDK
sdk = AnncsuConsultazione(security=security)

# Make authenticated requests
response = sdk.queryparam.esiste_odonimo_get_query_param(
    codcom="H501",
    denom="VklBIFJPTUE="
)
```

### Complete Example

Here's the full authentication workflow in one place:

```python
from pathlib import Path
from anncsu.pa import AnncsuConsultazione
from anncsu.common import (
    # Client Assertion
    ClientAssertionConfig,
    create_client_assertion,
    # Token Exchange
    TokenConfig,
    get_access_token,
    # API Authentication
    Security,
)

# Step 1: Create client assertion
assertion_config = ClientAssertionConfig(
    kid="your-key-id",
    issuer="43508172-aa22-46b0-8c01-3006e745c73c",
    subject="43508172-aa22-46b0-8c01-3006e745c73c",
    audience="auth.uat.interop.pagopa.it/client-assertion",
    purpose_id="73277faf-a76b-4528-979a-e6515ff9b06b",
    key_path=Path("./private_key.pem"),
)
client_assertion = create_client_assertion(assertion_config)

# Step 2: Exchange for access token
token_config = TokenConfig(
    client_id="43508172-aa22-46b0-8c01-3006e745c73c",
    client_assertion=client_assertion,
    token_endpoint="https://auth.uat.interop.pagopa.it/token.oauth2",
)
token_response = get_access_token(token_config)

# Step 3: Use access token for API calls
security = Security(bearer=token_response.access_token)
sdk = AnncsuConsultazione(security=security)

response = sdk.queryparam.esiste_odonimo_get_query_param(
    codcom="H501",
    denom="VklBIFJPTUE="
)
print(response)
```

### Async Version

For async applications, use `get_access_token_async`:

```python
import asyncio
from anncsu.common import TokenConfig, get_access_token_async

async def get_token():
    token_config = TokenConfig(
        client_id="your-client-id",
        client_assertion=client_assertion,
        token_endpoint="https://auth.uat.interop.pagopa.it/token.oauth2",
    )
    return await get_access_token_async(token_config)

token_response = asyncio.run(get_token())
```

## Configure SDK with Security

```python
from anncsu.pa import AnncsuConsultazione
from anncsu.common import Security

# Create security with your voucher
security = Security(bearer="your-voucher-token")

# Initialize SDK
sdk = AnncsuConsultazione(security=security)
```

### 3. Make Authenticated Requests

The SDK automatically includes the bearer token in all requests:

```python
# SDK adds: Authorization: Bearer your-voucher-token
response = sdk.queryparam.esiste_odonimo_get_query_param(
    codcom="H501",
    denom="VklBIFJPTUE="
)
```

## Token Refresh

PDND vouchers have an expiration time. Handle token refresh in your application using the built-in expiration checking:

```python
from anncsu.pa import AnncsuConsultazione
from anncsu.common import Security, TokenExpiredError

class TokenManager:
    def __init__(self, token_config, assertion_config):
        self.token_config = token_config
        self.assertion_config = assertion_config
        self.security = None
    
    def get_security(self) -> Security:
        """Get Security instance, refreshing token if necessary."""
        # Check if we need to refresh
        if self.security is None or self.security.is_expired():
            self._refresh_token()
        
        # Also check if token expires soon (within 60 seconds)
        ttl = self.security.time_until_expiration()
        if ttl is not None and ttl < 60:
            self._refresh_token()
        
        return self.security
    
    def _refresh_token(self):
        """Refresh the access token."""
        from anncsu.common import create_client_assertion, get_access_token, TokenConfig
        
        # Generate new client assertion
        client_assertion = create_client_assertion(self.assertion_config)
        
        # Exchange for new access token
        token_config = TokenConfig(
            client_id=self.token_config.client_id,
            client_assertion=client_assertion,
            token_endpoint=self.token_config.token_endpoint,
        )
        token_response = get_access_token(token_config)
        
        # Create new Security instance
        self.security = Security(bearer=token_response.access_token)

# Usage
token_manager = TokenManager(token_config, assertion_config)

# Get SDK with auto-refreshing token
sdk = AnncsuConsultazione(security=token_manager.get_security())

# For long-running applications, call get_security() before each request
# or implement automatic refresh in your HTTP client
```

### Simple Token Refresh with Expiration Check

For simpler use cases, use the built-in expiration validation:

```python
from anncsu.common import Security, TokenExpiredError

def get_authenticated_sdk(access_token):
    """Get SDK, handling expired tokens."""
    try:
        security = Security(bearer=access_token)
        return Anncsu(security=security)
    except TokenExpiredError:
        # Token expired - refresh and retry
        new_token = refresh_your_token()  # Your refresh logic
        security = Security(bearer=new_token)
        return Anncsu(security=security)
```

## Security Per Request

If you need different tokens for different requests:

```python
from anncsu.pa import AnncsuConsultazione
from anncsu.common import Security

# SDK 1 with token A
sdk1 = AnncsuConsultazione(security=Security(bearer="token-a"))

# SDK 2 with token B
sdk2 = AnncsuConsultazione(security=Security(bearer="token-b"))

# Different tokens for different requests
response1 = sdk1.queryparam.esiste_odonimo_get_query_param(...)
response2 = sdk2.queryparam.esiste_odonimo_get_query_param(...)
```

## Common Across All ANNCSU APIs

The same `Security` class works for all ANNCSU API specifications:

### Consultazione API

```python
from anncsu.pa import AnncsuConsultazione
from anncsu.common import Security

security = Security(bearer="your-pdnd-voucher")
sdk = AnncsuConsultazione(security=security)

# Query operations
response = sdk.queryparam.esiste_odonimo_get_query_param(
    codcom="H501",
    denom="VklBIFJPTUE="
)
```

### Aggiornamento APIs

```python
# Same Security class for:
# - Aggiornamento odonimi
# - Aggiornamento accessi
# - Aggiornamento coordinate
# - Aggiornamento interni

security = Security(bearer="your-pdnd-voucher")
# Use with respective SDK classes
```

## Error Handling

### Authentication Errors

Handle authentication failures gracefully:

```python
from anncsu.pa import AnncsuConsultazione
from anncsu.common import Security
from anncsu.common.errors import APIError

security = Security(bearer="invalid-token")
sdk = AnncsuConsultazione(security=security)

try:
    response = sdk.queryparam.esiste_odonimo_get_query_param(
        codcom="H501",
        denom="VklBIFJPTUE="
    )
except APIError as e:
    if e.status_code == 401:
        print("Authentication failed - token invalid or expired")
        # Implement token refresh logic
    elif e.status_code == 403:
        print("Forbidden - insufficient permissions")
    else:
        print(f"API error: {e}")
```

### Missing Token

```python
from anncsu.pa import AnncsuConsultazione

# SDK without security (may fail for protected endpoints)
sdk = AnncsuConsultazione()

try:
    response = sdk.queryparam.esiste_odonimo_get_query_param(
        codcom="H501",
        denom="VklBIFJPTUE="
    )
except APIError as e:
    if e.status_code == 401:
        print("Authentication required")
```

## Best Practices

### ✅ DO

**Secure Token Storage**
```python
import os
from anncsu.common import Security

# Load token from environment variable
token = os.getenv("PDND_VOUCHER_TOKEN")
security = Security(bearer=token)
```

**Token Refresh**
```python
# Implement automatic token refresh
# before expiration
```

**Error Handling**
```python
# Always handle 401/403 errors
try:
    response = sdk.queryparam.esiste_odonimo_get_query_param(...)
except APIError as e:
    if e.status_code in (401, 403):
        # Handle auth errors
        pass
```

**Reuse Security Instance**
```python
# Reuse the same Security instance
# for multiple SDK instances
security = Security(bearer=token)
sdk1 = AnncsuConsultazione(security=security)
sdk2 = AnotherANNCSUSDK(security=security)
```

### ❌ DON'T

**Hard-code Tokens**
```python
# BAD: Don't hard-code tokens
security = Security(bearer="eyJhbGci...")
```

**Log Tokens**
```python
# BAD: Don't log bearer tokens
print(f"Using token: {security.bearer}")  # DON'T DO THIS
```

**Ignore Expiration**
```python
# BAD: Don't use expired tokens
# Implement proper refresh logic
```

**Share Tokens**
```python
# BAD: Don't share tokens between different organizations
# Each organization should have its own PDND voucher
```

## Testing

### Unit Tests

Mock security in your tests:

```python
import pytest
from unittest.mock import Mock
from anncsu.common import Security

def test_with_security():
    """Test SDK with security."""
    security = Security(bearer="test-token")
    # Your test logic
    assert security.bearer == "test-token"

def test_without_security():
    """Test SDK without security."""
    security = Security()
    assert security.bearer is None
```

### Integration Tests

Use test tokens in integration tests:

```python
import os
from anncsu.pa import AnncsuConsultazione
from anncsu.common import Security

def test_authenticated_request():
    """Test authenticated API request."""
    # Use test token from environment
    test_token = os.getenv("TEST_PDND_VOUCHER")
    security = Security(bearer=test_token)
    sdk = AnncsuConsultazione(security=security)
    
    response = sdk.queryparam.esiste_odonimo_get_query_param(
        codcom="H501",
        denom="VklBIFJPTUE="
    )
    
    assert response.status_code == 200
```

### Test Coverage

The SDK includes comprehensive security tests:

```bash
# Run security tests
uv run pytest tests/common/test_security.py -v

# 27 tests covering:
# - Initialization scenarios
# - Bearer token formats (JWT, simple, special chars)
# - Authorization header generation
# - Edge cases (Unicode, whitespace, very long tokens)
# - PDND voucher integration
# - Token refresh scenarios
# - Cross-API reusability
```

## Security Configuration Reference

### Security Class

```python
from pydantic import BaseModel

class Security(BaseModel):
    """Security configuration for ANNCSU API authentication.
    
    All ANNCSU APIs use PDND (Piattaforma Digitale Nazionale Dati) 
    voucher-based authentication with HTTP Bearer tokens.
    
    Attributes:
        bearer: PDND voucher token for Bearer authentication.
                This token is included in the Authorization header 
                as "Bearer <token>".
        validate_expiration: If True (default), validates that the token
                            is not expired when the Security object is created.
    
    Raises:
        TokenExpiredError: If validate_expiration is True and the token has expired.
    
    Methods:
        is_expired() -> bool: Check if the token is expired.
        time_until_expiration() -> int | None: Get seconds until expiration.
    
    Example:
        >>> security = Security(bearer="your-pdnd-voucher-token")
        >>> # Token will be used in Authorization: Bearer your-pdnd-voucher-token
        >>> 
        >>> # Check expiration
        >>> if security.is_expired():
        ...     print("Token needs refresh!")
        >>> 
        >>> # Get time until expiration
        >>> ttl = security.time_until_expiration()
        >>> if ttl and ttl < 60:
        ...     print(f"Token expires in {ttl} seconds")
    """
    
    bearer: str | None = None
    validate_expiration: bool = True  # Excluded from serialization
```

### Usage Examples

**Basic Authentication**
```python
from anncsu.common import Security

security = Security(bearer="your-token")
```

**No Authentication (if supported)**
```python
security = Security()  # bearer=None
```

**With Environment Variable**
```python
import os

security = Security(bearer=os.getenv("PDND_VOUCHER"))
```

**With Token Refresh**
```python
class RefreshableToken:
    def __str__(self):
        return self.get_current_token()
    
    def get_current_token(self):
        # Your refresh logic
        return "current-token"

security = Security(bearer=str(RefreshableToken()))
```

## PDND Resources

- [PDND Official Documentation](https://docs.pdnd.italia.it/)
- [ANNCSU API Portal](https://www.agenziaentrate.gov.it/)
- PDND Support: Contact PDND for voucher-related issues

## Troubleshooting

### Token Expired Error on Initialization

**Problem**: `TokenExpiredError` raised when creating `Security` object

**Solutions**:
```python
from anncsu.common import Security, TokenExpiredError

try:
    security = Security(bearer=access_token)
except TokenExpiredError as e:
    print(f"Token expired at {e.expired_at}, current time: {e.current_time}")
    # Refresh the token
    new_token = get_access_token(token_config)
    security = Security(bearer=new_token.access_token)
```

### Token Validation Failed

**Problem**: API returns 401 Unauthorized

**Solutions**:
1. Check token format (should be valid JWT)
2. Verify token hasn't expired using `security.is_expired()`
3. Ensure correct PDND environment (production/test)
4. Verify API access permissions

### Invalid Bearer Format

**Problem**: API rejects bearer token format

**Solution**: Ensure token is passed correctly
```python
# Correct
security = Security(bearer="your-token")

# Incorrect - don't include "Bearer " prefix
security = Security(bearer="Bearer your-token")  # Wrong!
```

### Token Refresh Issues

**Problem**: Token expires during long-running operations

**Solution**: Implement automatic refresh
```python
import time

class TokenRefresher:
    def __init__(self, refresh_callback):
        self.refresh_callback = refresh_callback
        self.token = None
        self.expires_at = 0
    
    def get_token(self):
        if time.time() >= self.expires_at - 60:  # Refresh 1 min early
            self.token, self.expires_at = self.refresh_callback()
        return self.token

refresher = TokenRefresher(your_refresh_function)
security = Security(bearer=refresher.get_token())
```

## Security Checklist

Before deploying to production:

- [ ] Tokens stored securely (environment variables, secrets manager)
- [ ] Token refresh implemented
- [ ] Authentication errors handled (401, 403)
- [ ] Tokens not logged or exposed
- [ ] Test environment separated from production
- [ ] Token expiration monitored
- [ ] Backup authentication method (if available)

## Additional Security Considerations

### Transport Security

All ANNCSU APIs use HTTPS. The SDK enforces secure connections:
- TLS 1.2 or higher
- Certificate validation enabled
- No support for insecure HTTP

### Token Scope

PDND vouchers include scopes that define API access permissions:
- `anncsu.consultazione` - Read operations
- `anncsu.aggiornamento` - Write operations

Ensure your token has appropriate scopes for the operations you need.

### Token Lifecycle

1. **Obtain**: Request from PDND with client credentials
2. **Use**: Include in API requests via Security class
3. **Refresh**: Before expiration (typically 1 hour)
4. **Revoke**: When no longer needed or compromised

## ModI Headers for Coordinate API

Certain ANNCSU APIs (like Coordinate) require additional ModI (Modello di Interoperabilità) security headers beyond the bearer token:

- **Digest**: SHA-256 hash of the request body (RFC 3230)
- **Agid-JWT-Signature**: JWT containing integrity proof (INTEGRITY_REST_02)
- **Agid-JWT-TrackingEvidence**: JWT containing audit information (AUDIT_REST_02)

### ModI Pre-Request Hook

The SDK provides a `ModIPreRequestHook` that automatically injects these headers into HTTP requests. The key advantage is that the hook calculates the digest from the **actual serialized body bytes**, ensuring consistency.

#### Basic Usage

```python
from anncsu.common.hooks import register_modi_hook
from anncsu.common.hooks.sdkhooks import SDKHooks
from anncsu.common.modi import ModIConfig, AuditContext

# Configure ModI
config = ModIConfig(
    private_key=key_bytes,          # RSA key for ModI signing (from Client e-service portachiavi)
    kid="your-modi-signing-kid",    # KID of the ModI signing key (from Client e-service portachiavi)
    issuer="your-client-id",        # Same as PDND_ISSUER
    audience="https://modipa-val.agenziaentrate.it/govway/rest/in/AgenziaEntrate-PDND/anncsu-coordinate/v1",
)

# Optional: Audit context for tracking
audit = AuditContext(
    user_id="batch-user-001",       # User identifier
    user_location="server-batch-01", # Location/workstation
    loa="SPID_L2",                  # Level of Assurance
)

# Register hook with SDK
hooks = SDKHooks()
register_modi_hook(hooks, config=config, audit_context=audit)
```

#### What the Hook Does

1. **Intercepts POST/PUT/PATCH requests** after Speakeasy serializes the body
2. **Computes SHA-256 digest** from the exact request bytes (`request.content`)
3. **Generates Agid-JWT-Signature** with the digest in the `signed_headers` claim
4. **Generates Agid-JWT-TrackingEvidence** (if audit context provided)
5. **Injects all headers** and returns the modified request

#### Headers Generated

| Header | Description | Always Present |
|--------|-------------|----------------|
| `Digest` | `SHA-256=<base64-hash>` of request body | Yes |
| `Agid-JWT-Signature` | JWT with integrity proof | Yes |
| `Agid-JWT-TrackingEvidence` | JWT with audit info | Only if audit context |

#### Key Design Decisions

1. **Key usage depends on PDND portal configuration**: See [PDND Key Architecture](#pdnd-key-architecture-voucher-key-vs-modi-signing-key) below for details on how keys are configured in the PDND portal and how they map to SDK configuration.

2. **Digest from actual bytes**: The digest is computed from `request.content` (serialized bytes), not from a Python dictionary. This ensures the digest matches exactly what the server receives.

3. **Skip conditions**: The hook automatically skips:
   - GET/DELETE/HEAD/OPTIONS requests (no body)
   - Requests without a body
   - Requests with empty body

### Configuration Classes

#### ModIConfig

```python
from dataclasses import dataclass

@dataclass
class ModIConfig:
    """Configuration for ModI header generation."""
    private_key: bytes      # RSA private key (PEM format) - ModI signing key from Client e-service portachiavi
    kid: str                # Key ID of the ModI signing key (PDND_MODI_KID)
    issuer: str             # Client ID (same as PDND_ISSUER)
    audience: str           # API base URL (NOT token endpoint)
    alg: str = "RS256"      # JWT algorithm
    validity_seconds: int = 300  # JWT validity (5 minutes)
```

> **Important**: The `kid` and `private_key` in ModIConfig should be a **dedicated ModI signing key** from the Client e-service portachiavi, distinct from the voucher key used for `client_assertion`. See [PDND Key Architecture](#pdnd-key-architecture-voucher-key-vs-modi-signing-key) for details.

#### AuditContext

```python
from dataclasses import dataclass

@dataclass
class AuditContext:
    """Audit context for AUDIT_REST_02 pattern."""
    user_id: str        # User identifier in consumer's domain
    user_location: str  # Workstation/system identifier
    loa: str            # Level of Assurance (e.g., "SPID_L2", "CIE_L3")
```

### Creating ModIConfig from Settings

Use the helper function to create ModIConfig from your existing `ClientAssertionSettings`:

```python
from anncsu.common.config import ClientAssertionSettings
from anncsu.common.modi import create_modi_config_from_settings

# Load settings from .env (must include PDND_MODI_KID and PDND_MODI_PRIVATE_KEY)
settings = ClientAssertionSettings()

# Create ModI config (uses the dedicated ModI signing key when configured)
modi_config = create_modi_config_from_settings(
    settings,
    api_audience="https://modipa-val.agenziaentrate.it/govway/rest/in/AgenziaEntrate-PDND/anncsu-coordinate/v1"
)
```

### Environment Variables for ModI

Add these to your `.env` file:

```bash
# ModI Signing Key (REQUIRED for Coordinate API write operations)
# Both keys live in the same Client e-service portachiavi on PDND
# Using a separate key from PDND_KID / PDND_PRIVATE_KEY is recommended (GovWay enforces this)
PDND_MODI_KID=your-modi-signing-key-id
PDND_MODI_PRIVATE_KEY="-----BEGIN PRIVATE KEY-----
...e-service private key...
-----END PRIVATE KEY-----"

# ModI Audit Context (optional, for AUDIT_REST_02)
PDND_MODI_USER_ID=batch-user-001
PDND_MODI_USER_LOCATION=server-batch-01
PDND_MODI_LOA=SPID_L2
```

### Error Handling

```python
from anncsu.common.hooks import ModIHookError

# The hook returns ModIHookError instead of raising exceptions
# This follows the Speakeasy hook pattern

# Example error scenarios:
# - Invalid private key
# - JWT signing failure
# - Configuration issues

# Check if result is an error
result = hook.before_request(ctx, request)
if isinstance(result, ModIHookError):
    print(f"ModI error: {result}")
    print(f"Cause: {result.cause}")
```

### JWT Claims Structure

#### Agid-JWT-Signature Claims

```json
{
  "iss": "your-client-id",
  "aud": "https://api.example.com",
  "iat": 1706300000,
  "nbf": 1706300000,
  "exp": 1706300300,
  "jti": "550e8400-e29b-41d4-a716-446655440000",
  "signed_headers": [
    {"digest": "SHA-256=X48E9qOokqqrvdts8nOJRJN3OWDUoyWxBf7kbu9DBPE="},
    {"content-type": "application/json"}
  ]
}
```

#### Agid-JWT-TrackingEvidence Claims

```json
{
  "iss": "your-client-id",
  "aud": "https://api.example.com",
  "iat": 1706300000,
  "nbf": 1706300000,
  "exp": 1706300300,
  "jti": "550e8400-e29b-41d4-a716-446655440001",
  "userID": "batch-user-001",
  "userLocation": "server-batch-01",
  "LoA": "SPID_L2"
}
```

### ModI Resources

- [AgID Linee Guida ModI](https://www.agid.gov.it/it/infrastrutture/sistema-pubblico-connettivita/il-nuovo-modello-interoperabilita)
- [INTEGRITY_REST_02 Pattern](https://docs.italia.it/italia/piano-triennale-ict/lg-modellointeroperabilita-docs/)
- [AUDIT_REST_02 Pattern](https://docs.italia.it/italia/piano-triennale-ict/lg-modellointeroperabilita-docs/)
- [Forum Italia - ANNCSU Discussion](https://forum.italia.it/t/risposta-anncsu-aggiornamento-coordinate/45507)

## PDND Key Architecture: Voucher Key vs ModI Signing Key

### Understanding the PDND Key Model

On the PDND portal, each **Client e-service** (fruitore) has a **portachiavi** (key ring) where multiple RSA public keys can be uploaded. Each key gets its own `kid` (Key ID). The corresponding private keys remain with the fruitore.

The same Client e-service can use **different keys** for different purposes:

| Purpose | Key | Used For |
|---------|-----|----------|
| **Voucher key** | `PDND_KID` + `PDND_PRIVATE_KEY` | Signing the `client_assertion` JWT to obtain the access token (voucher) from PDND |
| **ModI signing key** | `PDND_MODI_KID` + `PDND_MODI_PRIVATE_KEY` | Signing `Agid-JWT-Signature` and `Agid-JWT-TrackingEvidence` headers (message security) |

**Both keys belong to the same Client e-service.** There is no "Client API Interop" involved in our flow. (The "Client API Interop" is a separate client type used only to access PDND's own management APIs programmatically — the API equivalent of the PDND web console.)

The official PDND documentation ([Voucher Bearer con informazioni aggiuntive](https://developer.pagopa.it/pdnd-interoperabilita/guides/manuale-operativo-pdnd-interoperabilita/tutorial/tutorial-per-il-fruitore/come-richiedere-un-voucher-bearer-per-le-api-di-un-erogatore-con-informazioni-aggiuntive)) states:

> *"la chiave privata che firma e il kid della pubblica corrispondente depositata su PDND Interoperabilità **non devono necessariamente essere gli stessi** con i quali si firma la client assertion"*

Translation: The private key that signs [the ModI JWS] and the kid of the corresponding public key deposited on PDND **don't necessarily have to be the same** as those used to sign the client assertion.

In practice, the GovWay gateway ([API PDND](https://govway.org/documentazione/console/profiloModIPA/messaggio/passiPreliminari/apiPDND.html)) enforces this separation strictly for production environments, requiring different keys for the voucher and for ModI message security patterns.

### Why Two Keys Are Needed

When an erogatore's gateway (e.g., GovWay/SOGEI) receives a request with ModI headers, it:

1. Reads the `kid` from the `Agid-JWT-Signature` JWT header
2. Downloads the corresponding public key from PDND via `GET /keys/{kid}`
3. Verifies the JWT signature with that public key

If the `kid` in the ModI JWT points to a key that was intended only for voucher authentication, the signature verification may fail with `InteroperabilityInvalidRequest` (400).

### Client Types in the PDND Portal (Clarification)

On the PDND portal (`selfcare.interop.pagopa.it`), under **Fruizione**, there are two client types. Only the first is relevant for our SDK:

| Client Type | Portal Location | Purpose | Relevance to SDK |
|-------------|-----------------|---------|-------------------|
| **Client e-service** | Fruizione → I tuoi client e-service | Consume e-services (obtain vouchers, sign ModI headers) | **This is what we use** — both keys live here |
| **Client API Interop** | Fruizione → I tuoi client API Interop | Access PDND's own management APIs programmatically | **Not used** by this SDK |

Source: [Client, portachiavi e materiale crittografico - Manuale Operativo PDND](https://developer.pagopa.it/pdnd-interoperabilita/guides/pdnd-manuale-operativo/manuale-operativo/client-e-materiale-crittografico)

### How Keys Map to SDK Operations

```
┌─────────────────────────────────────────────────────────────────────┐
│          PDND Client e-service — Key Ring (portachiavi)             │
│                                                                     │
│   Key A (PDND_KID)              Key B (PDND_MODI_KID)              │
│   ├─ Purpose: voucher           ├─ Purpose: ModI signing           │
│   ├─ Signs: client_assertion    ├─ Signs: Agid-JWT-Signature       │
│   └─ Sent to: auth.*.pagopa.it  │         Agid-JWT-TrackingEvidence│
│                                  └─ Sent to: erogatore API         │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  Step 1: Get Voucher (Access Token)                                 │
│  ┌──────────────────────────────────────────────────────┐           │
│  │  client_assertion (JWT)                              │           │
│  │  Signed with: PDND_KID + PDND_PRIVATE_KEY            │           │
│  │  Keys from:   Client e-service portachiavi (Key A)   │           │
│  │  Sent to:     auth.interop.pagopa.it/token.oauth2    │           │
│  └──────────────────────────────────────────────────────┘           │
│                          │                                          │
│                          ▼                                          │
│                   Access Token (voucher)                             │
│                          │                                          │
│  Step 2: Call API with ModI Headers                                 │
│  ┌──────────────────────────────────────────────────────┐           │
│  │  HTTP POST with headers:                             │           │
│  │  - Authorization: Bearer <voucher>                   │           │
│  │  - Digest: SHA-256=...                               │           │
│  │  - Agid-JWT-Signature (JWT)                          │           │
│  │    Signed with: PDND_MODI_KID + PDND_MODI_PRIVATE_KEY│           │
│  │    Keys from:   Client e-service portachiavi (Key B) │           │
│  │  - Agid-JWT-TrackingEvidence (JWT)                   │           │
│  │    Signed with: PDND_MODI_KID + PDND_MODI_PRIVATE_KEY│           │
│  │    Keys from:   Client e-service portachiavi (Key B) │           │
│  │  Sent to:     modipa.agenziaentrate.gov.it/...       │           │
│  └──────────────────────────────────────────────────────┘           │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

### SDK Environment Variables

The `.env` file should contain **two separate keypairs** from the same Client e-service portachiavi:

```bash
# ══════════════════════════════════════════════════════════════════
# KEY A: Voucher Key (client_assertion signing)
# Source: PDND Portal → Fruizione → I tuoi client e-service → Chiavi pubbliche
# Used for: client_assertion JWT to obtain voucher (access token)
# ══════════════════════════════════════════════════════════════════
PDND_KID=your-voucher-key-id
PDND_ISSUER=your-client-id
PDND_SUBJECT=your-client-id
PDND_AUDIENCE=auth.interop.pagopa.it/client-assertion
PDND_PRIVATE_KEY="-----BEGIN PRIVATE KEY-----
...voucher private key (for client_assertion)...
-----END PRIVATE KEY-----"

# ══════════════════════════════════════════════════════════════════
# KEY B: ModI Signing Key (message security headers)
# Source: PDND Portal → Fruizione → I tuoi client e-service → Chiavi pubbliche
# Used for: Agid-JWT-Signature and Agid-JWT-TrackingEvidence headers
# Can be the same key as Key A (PDND allows it) but GovWay requires different keys
# ══════════════════════════════════════════════════════════════════
PDND_MODI_KID=your-modi-signing-key-id
PDND_MODI_PRIVATE_KEY="-----BEGIN PRIVATE KEY-----
...modi signing private key (for ModI headers)...
-----END PRIVATE KEY-----"

# ═��════════════════════════════════════════════════════════════════
# Purpose IDs (from PDND Portal → Fruizione → Le tue finalità)
# ══════════════════════════════════════════════════════════════════
PDND_PURPOSE_ID_PA=...
PDND_PURPOSE_ID_COORDINATE=...
PDND_PURPOSE_ID_COORDINATE_BULK=...

# ══════════════════════════════════════════════════════════════════
# ModI Audit Context (optional, for AUDIT_REST_02)
# ══════════════════════════════════════════════════════════════════
PDND_MODI_USER_ID=batch-user-001
PDND_MODI_USER_LOCATION=server-batch-01
PDND_MODI_LOA=SPID_L2
```

### PDND Portal Configuration Checklist

To correctly configure a PDND consumer (fruitore), follow these steps on the portal:

1. **Generate two RSA keypairs** (using OpenSSL or similar):
   ```bash
   # Keypair A: for voucher (client_assertion)
   openssl genpkey -algorithm RSA -out voucher-private.pem -pkeyopt rsa_keygen_bits:2048
   openssl rsa -in voucher-private.pem -pubout -out voucher-public.pem

   # Keypair B: for ModI signing (message security)
   openssl genpkey -algorithm RSA -out modi-signing-private.pem -pkeyopt rsa_keygen_bits:2048
   openssl rsa -in modi-signing-private.pem -pubout -out modi-signing-public.pem
   ```

2. **Upload both public keys to the same Client e-service**:
   - Go to: Fruizione → I tuoi client e-service → [your client] → Chiavi pubbliche → Aggiungi
   - Upload `voucher-public.pem` → note the assigned `kid` → this becomes `PDND_KID`
   - Upload `modi-signing-public.pem` → note the assigned `kid` → this becomes `PDND_MODI_KID`
   - Keep both private keys secure → `PDND_PRIVATE_KEY` and `PDND_MODI_PRIVATE_KEY`

3. **Associate Client e-service to Purpose**:
   - Go to: Fruizione → Le tue finalità → [your purpose]
   - Associate the client e-service to the purpose

> **Note**: PDND allows using the same key for both purposes. However, the GovWay gateway enforces key separation in production, so using two distinct keys is strongly recommended.

### Common Errors from Key Misconfiguration

| Error | Cause | Solution |
|-------|-------|----------|
| `InteroperabilityInvalidRequest` (400) | ModI JWT signed with voucher key instead of dedicated ModI signing key, or kid not recognized | Use `PDND_MODI_KID`/`PDND_MODI_PRIVATE_KEY` for ModI headers |
| `015-0008 - Unable to generate a token` | client_assertion signed with wrong key or audience mismatch | Verify `PDND_KID`/`PDND_PRIVATE_KEY` match a key in the Client e-service portachiavi |
| `403 Insufficient token claims` | Voucher does not have the correct purpose for the e-service | Verify the purpose ID and that the client e-service is associated to the purpose |

### References

- [Voucher Bearer con informazioni aggiuntive - Manuale Operativo PDND](https://developer.pagopa.it/pdnd-interoperabilita/guides/manuale-operativo-pdnd-interoperabilita/tutorial/tutorial-per-il-fruitore/come-richiedere-un-voucher-bearer-per-le-api-di-un-erogatore-con-informazioni-aggiuntive) — keys for ModI signing vs client_assertion don't need to be the same
- [API PDND - GovWay Documentation](https://govway.org/documentazione/console/profiloModIPA/messaggio/passiPreliminari/apiPDND.html) — GovWay enforces key separation for message security patterns
- [Client, portachiavi e materiale crittografico - Manuale Operativo PDND](https://developer.pagopa.it/pdnd-interoperabilita/guides/pdnd-manuale-operativo/manuale-operativo/client-e-materiale-crittografico) — client types and key management
- [Utilizzare i voucher - Manuale Operativo PDND](https://developer.pagopa.it/pdnd-interoperabilita/guides/pdnd-manuale-operativo/manuale-operativo/utilizzare-i-voucher) — voucher request flow

## GovWay URL Discrepancies: OAS vs Production

> **The real URL of an e-service is ALWAYS determined by the `aud` claim in the PDND voucher, NEVER from the OAS specs.** OAS files may contain outdated, incorrect, or generic URLs.

### Domain Differences by Environment

| Environment | Domain | SSL Certificate CN |
|-------------|--------|--------------------|
| **Validation (UAT)** | `modipa-val.agenziaentrate.it` | `modipa-val.agenziaentrate.it` |
| **Production** | `modipa.agenziaentrate.gov.it` | `modipa.agenziaentrate.gov.it` |

**Warning**: Production uses `.gov.it`, NOT `.it`. Using `.it` causes SSL errors and `InteroperabilityInvalidRequest` (400) because the JWT `aud` claim doesn't match what GovWay expects.

### E-Service Path Differences by Environment

| E-Service | UAT Path | Production Path | Different? |
|-----------|----------|-----------------|------------|
| Consultazione PA | `anncsu-consultazione/v1` | `anncsu-consultazione-comune/v1` | **YES** |
| Agg. Coordinate | `anncsu-aggiornamento-coordinate/v1` | `anncsu-aggiornamento-coordinate/v1` | No |
| Agg. Coord. Bulk | `anncsu-aggiornamento-coordinate-grandi-comuni/v1` | `anncsu-aggiornamento-coordinate-grandi-comuni/v1` | No |

### OAS Spec vs Real URL Discrepancies

| Source | Domain | Subject | Path |
|--------|--------|---------|------|
| OAS Consultazione | `.gov.it` | `AgenziaEntrate-PDND` | `anncsu-consultazione/v1` |
| PDND Voucher (prod) | `.gov.it` | `AgenziaEntrate-PDND` | **`anncsu-consultazione-comune/v1`** |
| OAS Coordinate | `.it` | `AgenziaEntrate` | `anncsuaccessi/v1` |
| PDND Voucher (prod) | `.gov.it` | `AgenziaEntrate-PDND` | `anncsu-aggiornamento-coordinate/v1` |
| OAS Coord. Massivo | `.it` | `AgenziaEntrate` | `anncsuaccessi/v1` |
| PDND Voucher (prod) | `.gov.it` | `AgenziaEntrate-PDND` | `anncsu-aggiornamento-coordinate-grandi-comuni/v1` |

### How to Discover the Correct URL

Decode the PDND voucher for the target e-service and read the `aud` claim:

```bash
TOKEN=$(anncsu auth token --api pa --token-endpoint https://auth.interop.pagopa.it/token.oauth2 2>/dev/null)
anncsu assertion decode "$TOKEN" --json | python3 -c "import sys,json; print(json.load(sys.stdin)['payload']['aud'])"
```

### Automatic URL Correction (Auto-Discovery)

Since Session 49, the SDK auto-corrects hardcoded server URLs by comparing them against the `aud` claim in the PDND voucher. This eliminates the need to manually update `SERVERS` dicts when GovWay paths or domains change.

**How it works:**

1. The CLI obtains a PDND voucher (access token) via `PDNDAuthManager.get_access_token()`
2. `extract_voucher_audience()` extracts the `aud` claim from the voucher JWT
3. If `aud` differs from the hardcoded `server_url`, the SDK:
   - Replaces `server_url` with the voucher `aud`
   - Updates `modi_audience` (for ModI JWT signing) accordingly
   - Prints a warning to stderr:
     ```
     URL auto-corrected: Hardcoded URL differs from PDND voucher audience.
       Configured: https://modipa.agenziaentrate.it/govway/rest/in/...
       Voucher aud: https://modipa.agenziaentrate.gov.it/govway/rest/in/...
       Using voucher audience as server URL.
     ```

**Affected functions:**
- `_get_sdk()` in `coordinate.py` — for coordinate update, status, dry-run
- `_get_consult_sdk()` in `coordinate.py` — for consultazione PA
- Bulk operations inherit the behavior via `_get_coord_sdk()` and `_get_consult_sdk_lazy()`

**Backward compatible:** If the voucher cannot be decoded or lacks an `aud` claim, the hardcoded URL is used as fallback.

## Further Reading

- [PDND Authentication Guide](https://docs.pdnd.italia.it/docs/authentication)
- [JWT Specification (RFC 7519)](https://tools.ietf.org/html/rfc7519)
- [HTTP Bearer Authentication (RFC 6750)](https://tools.ietf.org/html/rfc6750)
- [OAuth 2.0 (RFC 6749)](https://tools.ietf.org/html/rfc6749)
- [HTTP Digest Header (RFC 3230)](https://tools.ietf.org/html/rfc3230)
