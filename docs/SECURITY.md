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
from anncsu.pa import Anncsu
from anncsu.common import Security

# Create security configuration with your PDND voucher
security = Security(bearer="your-pdnd-voucher-token")

# Initialize SDK with security
sdk = Anncsu(security=security)

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
    --audience "https://auth.interop.pagopa.it/token.oauth2" \
    --purpose-id "your-purpose-id" \
    --key-path ./private_key.pem
```

## Authentication Flow

### 1. Obtain PDND Voucher

Before using the SDK, you need to obtain a PDND voucher from the PDND platform:

1. Register your organization on PDND
2. Request access to ANNCSU APIs
3. Obtain client credentials (client ID and secret)
4. Generate a client assertion using the SDK or CLI
5. Exchange the client assertion for a voucher token

*Note: The final exchange step is outside the scope of this SDK. Refer to PDND documentation.*

### 2. Configure SDK with Security

```python
from anncsu.pa import Anncsu
from anncsu.common import Security

# Create security with your voucher
security = Security(bearer="your-voucher-token")

# Initialize SDK
sdk = Anncsu(security=security)
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

PDND vouchers have an expiration time. Handle token refresh in your application:

```python
from anncsu.pa import Anncsu
from anncsu.common import Security
import time

class TokenManager:
    def __init__(self):
        self.token = None
        self.expires_at = 0
    
    def get_token(self) -> str:
        """Get current token, refreshing if necessary."""
        if time.time() >= self.expires_at:
            self.token, self.expires_at = self.refresh_token()
        return self.token
    
    def refresh_token(self) -> tuple[str, float]:
        """Refresh PDND voucher (implement your logic)."""
        # Your token refresh logic here
        new_token = "new-pdnd-voucher"
        expires_at = time.time() + 3600  # 1 hour
        return new_token, expires_at

# Usage
token_manager = TokenManager()

# Create SDK with refreshable token
security = Security(bearer=token_manager.get_token())
sdk = Anncsu(security=security)

# For long-running applications, recreate SDK periodically
# or implement automatic refresh in your HTTP client
```

## Security Per Request

If you need different tokens for different requests:

```python
from anncsu.pa import Anncsu
from anncsu.common import Security

# SDK 1 with token A
sdk1 = Anncsu(security=Security(bearer="token-a"))

# SDK 2 with token B
sdk2 = Anncsu(security=Security(bearer="token-b"))

# Different tokens for different requests
response1 = sdk1.queryparam.esiste_odonimo_get_query_param(...)
response2 = sdk2.queryparam.esiste_odonimo_get_query_param(...)
```

## Common Across All ANNCSU APIs

The same `Security` class works for all ANNCSU API specifications:

### Consultazione API

```python
from anncsu.pa import Anncsu
from anncsu.common import Security

security = Security(bearer="your-pdnd-voucher")
sdk = Anncsu(security=security)

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
from anncsu.pa import Anncsu
from anncsu.common import Security
from anncsu.common.errors import APIError

security = Security(bearer="invalid-token")
sdk = Anncsu(security=security)

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
from anncsu.pa import Anncsu

# SDK without security (may fail for protected endpoints)
sdk = Anncsu()

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
sdk1 = Anncsu(security=security)
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
from anncsu.pa import Anncsu
from anncsu.common import Security

def test_authenticated_request():
    """Test authenticated API request."""
    # Use test token from environment
    test_token = os.getenv("TEST_PDND_VOUCHER")
    security = Security(bearer=test_token)
    sdk = Anncsu(security=security)
    
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
from dataclasses import dataclass

@dataclass
class Security:
    """Security configuration for ANNCSU API authentication.
    
    All ANNCSU APIs use PDND (Piattaforma Digitale Nazionale Dati) 
    voucher-based authentication with HTTP Bearer tokens.
    
    Attributes:
        bearer: PDND voucher token for Bearer authentication.
                This token is included in the Authorization header 
                as "Bearer <token>".
    
    Example:
        >>> security = Security(bearer="your-pdnd-voucher-token")
        >>> # Token will be used in Authorization: Bearer your-pdnd-voucher-token
    """
    
    bearer: str | None = None
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

### Token Validation Failed

**Problem**: API returns 401 Unauthorized

**Solutions**:
1. Check token format (should be valid JWT)
2. Verify token hasn't expired
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
