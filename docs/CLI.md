# ANNCSU CLI

Command-line interface for PDND authentication and ANNCSU API interaction.

## Installation

The CLI is included with the ANNCSU SDK:

```bash
pip install anncsu-sdk
```

Or with uv:

```bash
uv add anncsu-sdk
```

## Quick Start

```bash
# 1. Initialize configuration in ~/.anncsu/.env
anncsu config init

# 2. Edit ~/.anncsu/.env with your PDND credentials
nano ~/.anncsu/.env

# 3. Validate configuration
anncsu config validate

# 4. Login (generates assertion + obtains token + saves session)
anncsu auth login

# 5. Check status (loads from ~/.anncsu/session.json)
anncsu auth status

# 6. Use token in API calls (auto-refreshes if expired)
curl -H "Authorization: Bearer $(anncsu auth token)" https://api.example.com

# 7. Update coordinates for an access point
anncsu coordinate update --codcom H501 --progr-civico 12345 --x 12.4963655 --y 41.9027835
```

## Commands

### `anncsu config` - Configuration Management

Manage PDND configuration stored in `.env` file.

#### `anncsu config init`

Generate a template `.env` file with all required variables:

```bash
anncsu config init
```

Output:
```
Created .env.template with the following variables:
- PDND_KID
- PDND_ISSUER
- PDND_SUBJECT
- PDND_AUDIENCE
- PDND_PURPOSE_ID
- PDND_KEY_PATH (or PDND_PRIVATE_KEY)
- PDND_TOKEN_ENDPOINT
```

#### `anncsu config show`

Display current configuration (with masked sensitive values):

```bash
anncsu config show
```

Output:
```
┌─────────────────────────────────────────┐
│ PDND Configuration                      │
├─────────────────────────────────────────┤
│ KID:           abc123...                │
│ Issuer:        a1b2c3d4-e5f6-...        │
│ Subject:       a1b2c3d4-e5f6-...        │
│ Audience:      https://auth.uat...      │
│ Purpose ID:    12345678-90ab-...        │
│ Key Path:      ./private_key.pem ✅     │
│ Token Endpoint: https://auth.uat...     │
│ Validity:      43200 minutes (30 days)  │
└─────────────────────────────────────────┘
```

#### `anncsu config validate`

Validate that `.env` file is correctly configured:

```bash
anncsu config validate
```

Output (success):
```
✅ Configuration valid!
   - All required fields present
   - Key file exists and is readable
   - Audience URL is valid HTTPS
```

Output (error):
```
❌ Configuration errors:
   - PDND_KID: Missing required field
   - PDND_KEY_PATH: File not found: ./private_key.pem
```

---

### `anncsu assertion` - Client Assertion Management

Generate and inspect PDND client assertions (JWT).

#### `anncsu assertion create`

Generate a new client assertion and print it:

```bash
anncsu assertion create
```

Output:
```
eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCIsImtpZCI6ImFiYzEyMyJ9.eyJpc3MiOiJhMWIyYzNkNC...
```

Options:
- `--output FILE` - Save assertion to file instead of stdout
- `--json` - Output as JSON with metadata

#### `anncsu assertion info`

Display information about the current/cached assertion:

```bash
anncsu assertion info
```

Output:
```
┌─────────────────────────────────────────┐
│ Client Assertion Info                   │
├─────────────────────────────────────────┤
│ Algorithm:   RS256                      │
│ Type:        JWT                        │
│ Key ID:      abc123...                  │
├─────────────────────────────────────────┤
│ Issuer:      a1b2c3d4-e5f6-...          │
│ Subject:     a1b2c3d4-e5f6-...          │
│ Audience:    https://auth.uat...        │
│ Purpose ID:  12345678-90ab-...          │
├─────────────────────────────────────────┤
│ Issued At:   2026-01-18 10:30:00        │
│ Expires At:  2026-02-17 10:30:00        │
│ TTL:         29 days, 23 hours          │
│ Status:      ✅ Valid                   │
└─────────────────────────────────────────┘
```

---

### `anncsu auth` - Authentication

Authenticate with PDND and manage access tokens.

#### `anncsu auth login`

Perform full authentication flow (assertion + token exchange):

```bash
anncsu auth login
```

Output:
```
✅ Login successful!

┌─────────────────────────────────────────┐
│ Client Assertion                        │
├─────────────────────────────────────────┤
│ TTL:         29 days, 23 hours          │
│ Expires:     2026-02-17 10:30:00        │
├─────────────────────────────────────────┤
│ Access Token                            │
├─────────────────────────────────────────┤
│ TTL:         600 seconds                │
│ Expires:     2026-01-18 10:40:00        │
└─────────────────────────────────────────┘
```

Options:
- `--token-endpoint URL` - Override token endpoint from .env
- `--quiet` - Suppress output, only show errors

#### `anncsu auth status`

Show current authentication status:

```bash
anncsu auth status
```

Output (authenticated):
```
┌─────────────────────────────────────────┐
│ Authentication Status                   │
├─────────────────────────────────────────┤
│ Client Assertion                        │
│   Status:    ✅ Valid                   │
│   TTL:       29 days, 23 hours          │
│   Expires:   2026-02-17 10:30:00        │
├─────────────────────────────────────────┤
│ Access Token                            │
│   Status:    ✅ Valid                   │
│   TTL:       542 seconds                │
│   Expires:   2026-01-18 10:39:02        │
└─────────────────────────────────────────┘
```

Output (not authenticated):
```
❌ Not authenticated. Run 'anncsu auth login' first.
```

#### `anncsu auth refresh`

Force refresh of the access token:

```bash
anncsu auth refresh
```

Output:
```
✅ Token refreshed!
   TTL: 600 seconds
   Expires: 2026-01-18 10:50:00
```

#### `anncsu auth token`

Print the current access token (useful for piping):

```bash
anncsu auth token
```

Output:
```
eyJhbGciOiJSUzI1NiIsInR5cCI6ImF0K2p3dCJ9.eyJpc3MiOiJodHRwczovL2F1dGgudWF0...
```

Usage with curl:
```bash
curl -H "Authorization: Bearer $(anncsu auth token)" \
  https://modipa-val.agenziaentrate.it/govway/rest/in/AgenziaEntrate-PDND/anncsu-consultazione/v1/esisteodonimo?codcom=H501
```

---

### `anncsu coordinate` - Coordinate Management

Manage geographic coordinates for access points (civici) in ANNCSU.

#### `anncsu coordinate update`

Update coordinates for an access point (civico):

```bash
anncsu coordinate update --codcom H501 --progr-civico 12345 --x 12.4963655 --y 41.9027835 --metodo 4
```

Output:
```
Operation successful! ID: abc123-def456

┌─────────────────────────────────────────┐
│ Field              │ Value              │
├─────────────────────────────────────────┤
│ ID Richiesta       │ abc123-def456      │
│ Esito              │ OK                 │
│ Messaggio          │ Operazione eseguita│
│ Dati Restituiti    │ 1                  │
└─────────────────────────────────────────┘
```

Options:
- `--codcom, -c` - Codice comune (Belfiore code, e.g. H501 for Roma) **[required]**
- `--progr-civico, -p` - Progressivo civico (access progressive number) **[required]**
- `--x` - Coordinata X (longitude). Valid range for Italy: 6.0-18.0
- `--y` - Coordinata Y (latitude). Valid range for Italy: 36.0-47.0
- `--z` - Quota (altitude in meters)
- `--metodo, -m` - Metodo di rilevazione (1-4)
- `--token-endpoint, -e` - PDND token endpoint URL
- `--server-url, -s` - API server URL (defaults to validation environment)
- `--validation/--production` - Use validation (UAT) or production environment
- `--no-verify-ssl` - Disable SSL certificate verification (use with caution)
- `--json` - Output as JSON

Example with JSON output:
```bash
anncsu coordinate update --codcom H501 --progr-civico 12345 --x 12.4963655 --y 41.9027835 --json
```

Output:
```json
{
  "success": true,
  "id_richiesta": "abc123-def456",
  "esito": "OK",
  "messaggio": "Operazione eseguita con successo",
  "dati_count": 1
}
```

#### `anncsu coordinate status`

Check the status of the Coordinate API service:

```bash
anncsu coordinate status
```

Output:
```
Coordinate API Status - Validation (UAT)

┌─────────────────────────────────────────┐
│ Property           │ Value              │
├─────────────────────────────────────────┤
│ Status             │ OK                 │
│ Server             │ https://modipa-val…│
│ Response           │ OK                 │
└─────────────────────────────────────────┘
```

Options:
- `--token-endpoint, -e` - PDND token endpoint URL
- `--server-url, -s` - API server URL
- `--validation/--production` - Use validation (UAT) or production environment
- `--no-verify-ssl` - Disable SSL certificate verification
- `--json` - Output as JSON

Example checking production environment:
```bash
anncsu coordinate status --production
```

Example with JSON output:
```bash
anncsu coordinate status --json
```

Output:
```json
{
  "available": true,
  "status": "OK",
  "server_url": "https://modipa-val.agenziaentrate.it/govway/rest/in/AgenziaEntrate/anncsuaccessi/v1",
  "environment": "validation"
}
```

#### `anncsu coordinate dry-run`

Perform a test coordinate update cycle: search for an access point, update coordinates, then immediately restore the original values. This is useful for testing that authentication and configuration are correct without permanently altering data.

```bash
anncsu coordinate dry-run --codcom H501 --denom VklBIFJPTUE=
```

The command performs these steps:
1. **Search** - Find an access point using the consultazione API
2. **Test Update** - Update the coordinates (using same values)
3. **Restore** - Immediately restore the original coordinates

Output:
```
Step 1: Searching for access point...

Found access point: prognazacc=123456789
  Civico: 1
  Coord X: 12.4963655
  Coord Y: 41.9027835
  Quota: 21
  Metodo: 4

Step 2: Performing test update...

Test update completed: esito=OK

Step 3: Restoring original coordinates...

Restore completed: esito=OK

Dry-run Summary:

┌─────────────────────────────────────────────────────────────┐
│ Step         │ Status │ Details                             │
├─────────────────────────────────────────────────────────────┤
│ Search       │ OK     │ Found prognazacc=123456789          │
│ Test Update  │ OK     │ Operazione completata               │
│ Restore      │ OK     │ Operazione completata               │
└─────────────────────────────────────────────────────────────┘
```

Options:
- `--codcom, -c` - Codice comune (Belfiore code, e.g. H501 for Roma) **[required]**
- `--denom, -d` - Denominazione esatta dell'odonimo - base64 encoded **[required]**
- `--accparz, -a` - Valore anche parziale del civico (default: '1')
- `--token-endpoint, -e` - PDND token endpoint URL
- `--server-url, -s` - API server URL (defaults to validation environment)
- `--validation/--production` - Use validation (UAT) or production environment
- `--no-verify-ssl` - Disable SSL certificate verification (use with caution)
- `--json` - Output as JSON

Example with specific civico number:
```bash
anncsu coordinate dry-run --codcom H501 --denom VklBIFJPTUE= --accparz 10
```

Example with JSON output:
```bash
anncsu coordinate dry-run --codcom H501 --denom VklBIFJPTUE= --json
```

Output:
```json
{
  "success": true,
  "original_coordinates": {
    "prognazacc": "123456789",
    "codcom": "H501",
    "civico": "1",
    "coord_x": "12.4963655",
    "coord_y": "41.9027835",
    "quota": "21",
    "metodo": "4"
  },
  "test_update": {
    "success": true,
    "id_richiesta": "REQ-123",
    "esito": "OK",
    "messaggio": "Operazione completata",
    "dati_count": 0
  },
  "restore": {
    "success": true,
    "id_richiesta": "REQ-456",
    "esito": "OK",
    "messaggio": "Operazione completata",
    "dati_count": 0
  },
  "restore_failed": false,
  "error_message": null
}
```

**Warning Handling**: If the restore operation fails, the command will display a warning with the original coordinate values so they can be manually restored:

```
WARNING: Restore failed: <error message>

Original coordinates to restore manually:
  prognazacc: 123456789
  codcom: H501
  coord_x: 12.4963655
  coord_y: 41.9027835
  quota: 21
  metodo: 4
```

---

## Environment Variables

The CLI reads configuration from environment variables (with `PDND_` prefix) or a `.env` file:

| Variable | Required | Description |
|----------|----------|-------------|
| `PDND_KID` | Yes | Key ID (kid) header parameter |
| `PDND_ISSUER` | Yes | Issuer (iss) claim - your client_id |
| `PDND_SUBJECT` | Yes | Subject (sub) claim - your client_id |
| `PDND_AUDIENCE` | Yes | Audience (aud) - PDND client-assertion endpoint |
| `PDND_PURPOSE_ID` | Yes | Purpose ID for the PDND request |
| `PDND_KEY_PATH` | One required | Path to RSA private key file |
| `PDND_PRIVATE_KEY` | One required | RSA private key content (alternative to KEY_PATH) |
| `PDND_TOKEN_ENDPOINT` | Yes | PDND token endpoint URL |
| `PDND_ALG` | No | Algorithm (default: RS256) |
| `PDND_TYP` | No | Token type (default: JWT) |
| `PDND_VALIDITY_MINUTES` | No | Assertion validity in minutes (default: 43200 = 30 days) |

### Example `.env` file

```env
# PDND Configuration
PDND_KID=your-key-id
PDND_ISSUER=your-client-id
PDND_SUBJECT=your-client-id
PDND_AUDIENCE=https://auth.uat.interop.pagopa.it/client-assertion
PDND_PURPOSE_ID=your-purpose-id
PDND_KEY_PATH=./private_key.pem
PDND_TOKEN_ENDPOINT=https://auth.uat.interop.pagopa.it/token.oauth2

# Optional
PDND_VALIDITY_MINUTES=43200
```

---

## Session Persistence

The CLI automatically persists authentication tokens between sessions in `~/.anncsu/session.json`.

### Session File Location

| Platform | Path |
|----------|------|
| Linux/macOS | `~/.anncsu/session.json` |
| Windows | `%USERPROFILE%\.anncsu\session.json` |

### Session File Format

```json
{
  "client_assertion": "eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCIsImtpZCI6Ii4uLiJ9...",
  "access_token": "eyJhbGciOiJSUzI1NiIsInR5cCI6ImF0K2p3dCJ9...",
  "token_endpoint": "https://auth.uat.interop.pagopa.it/token.oauth2"
}
```

### How It Works

1. **Login** (`anncsu auth login`): Saves tokens to session file
2. **Status** (`anncsu auth status`): Loads and displays tokens from session
3. **Token** (`anncsu auth token`): Loads token, auto-refreshes if expired
4. **Logout** (`anncsu auth logout`): Deletes session file

### Automatic Token Refresh

When you run `anncsu auth token`, the CLI automatically:
- Loads the session from file
- Checks if the access token is expired or expiring soon (< 60 seconds)
- If expired, requests a new access token using the client assertion
- If the client assertion is also expired (< 1 day remaining), generates a new one
- Saves the updated session to file

### Multi-Environment Support

The session file stores the `token_endpoint` URL. If you switch between environments (e.g., UAT to PROD), the CLI will not load a session for a different endpoint, preventing accidental credential mixing.

```bash
# UAT environment - saves session with UAT endpoint
anncsu auth login --token-endpoint https://auth.uat.interop.pagopa.it/token.oauth2

# PROD environment - creates new session (different endpoint)
anncsu auth login --token-endpoint https://auth.interop.pagopa.it/token.oauth2

# Status shows only tokens for current endpoint
anncsu auth status --token-endpoint https://auth.uat.interop.pagopa.it/token.oauth2
```

### Clear Session

To remove all cached tokens:

```bash
anncsu auth logout
```

This deletes `~/.anncsu/session.json` and clears in-memory tokens.

---

## Exit Codes

| Code | Description |
|------|-------------|
| 0 | Success |
| 1 | Configuration error |
| 2 | Authentication error |
| 3 | Network error |
| 4 | Token expired |

---

## Examples

### Script Integration

```bash
#!/bin/bash
# Script that uses ANNCSU CLI for authentication

# Login and check status
anncsu auth login --quiet || exit 1

# Get token for API calls
TOKEN=$(anncsu auth token)

# Make API call
curl -s -H "Authorization: Bearer $TOKEN" \
  "https://modipa-val.agenziaentrate.it/govway/rest/in/AgenziaEntrate-PDND/anncsu-consultazione/v1/elencoodonimi?codcom=H501&denomparz=$(echo -n 'ROMA' | base64)"
```

### CI/CD Pipeline

```yaml
# GitHub Actions example
- name: ANNCSU Authentication
  env:
    PDND_KID: ${{ secrets.PDND_KID }}
    PDND_ISSUER: ${{ secrets.PDND_ISSUER }}
    PDND_SUBJECT: ${{ secrets.PDND_SUBJECT }}
    PDND_AUDIENCE: ${{ secrets.PDND_AUDIENCE }}
    PDND_PURPOSE_ID: ${{ secrets.PDND_PURPOSE_ID }}
    PDND_PRIVATE_KEY: ${{ secrets.PDND_PRIVATE_KEY }}
    PDND_TOKEN_ENDPOINT: ${{ secrets.PDND_TOKEN_ENDPOINT }}
  run: |
    anncsu auth login
    anncsu auth status
```

---

## See Also

- [Security Documentation](./SECURITY.md) - PDND authentication details
- [SDK Usage](../README.md) - Programmatic SDK usage
- [PDNDAuthManager](./conversation_log.md#session-19) - Authentication manager internals
