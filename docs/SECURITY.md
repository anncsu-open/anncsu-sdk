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

## Further Reading

- [PDND Authentication Guide](https://docs.pdnd.italia.it/docs/authentication)
- [JWT Specification (RFC 7519)](https://tools.ietf.org/html/rfc7519)
- [HTTP Bearer Authentication (RFC 6750)](https://tools.ietf.org/html/rfc6750)
- [OAuth 2.0 (RFC 6749)](https://tools.ietf.org/html/rfc6749)
