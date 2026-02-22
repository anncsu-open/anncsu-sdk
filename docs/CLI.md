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

# 8. Validate a CSV for bulk coordinate updates
anncsu coordinate bulk validate input.csv
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

> **Terminology Note**: The identifier for an access point is called `prognazacc` (progressivo nazionale accesso) in the PA Consultazione API and `progr_civico` in the Coordinate API. **They represent the same value** - the unique national progressive identifier for an access point (civico). When using the CLI:
> - `--prognazacc` option in `dry-run` command accepts this identifier
> - `--progr-civico` option in `update` command accepts this same identifier
> - The `bulk` command CSV uses `progr_civico` as the column name

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

**Two Modes of Operation:**

1. **Direct mode (`--prognazacc`)**: Use the progressivo nazionale accesso directly.
   Skips the odonimo search step - faster if you already know the prognazacc.

2. **Search mode (`--codcom` + `--denom`)**: Search for odonimo then access point.
   Use this when you only know the municipality code and street name.

```bash
# Direct mode - use prognazacc directly (faster)
anncsu coordinate dry-run --prognazacc 5256880

# Search mode - search by municipality and street
anncsu coordinate dry-run --codcom H501 --denom VklBIFJPTUE=
```

The command performs these steps:
1. **Search/Lookup** - Find an access point (direct lookup or search via consultazione API)
2. **Test Update** - Update the coordinates (using same values)
3. **Restore** - Immediately restore the original coordinates

**Output (direct mode with `--prognazacc`):**
```
Step 1: Looking up access point prognazacc=5256880...

  Found: VIA ROMA
  Progressivo nazionale odonimo: 907156

Found access point: prognazacc=5256880
  Civico: 1
  Coord X: 12.4922309
  Coord Y: 41.8902102
  Quota: 0
  Metodo: 4

Step 2: Performing test update...

Test update completed: OK (esito=0)

Step 3: Restoring original coordinates...

Restore completed: OK (esito=0)

Dry-run Summary:

┌─────────────────────────────────────────────────────────────┐
│ Step         │ Status │ Details                             │
├─────────────────────────────────────────────────────────────┤
│ Search       │ OK     │ Found prognazacc=5256880            │
│ Test Update  │ OK     │ 0                                   │
│ Restore      │ OK     │ 0                                   │
└─────────────────────────────────────────────────────────────┘
```

**Output (search mode with `--codcom` + `--denom`):**
```
Step 1: Searching for odonimo and access point...

  Found odonimo: VIA ROMA
  Progressivo nazionale: 907156

Found access point: prognazacc=5256880
  Civico: 1
  Coord X: 12.4922309
  Coord Y: 41.8902102
  Quota: 0
  Metodo: 4

Step 2: Performing test update...

Test update completed: OK (esito=0)

Step 3: Restoring original coordinates...

Restore completed: OK (esito=0)

Dry-run Summary:

┌─────────────────────────────────────────────────────────────┐
│ Step         │ Status │ Details                             │
├─────────────────────────────────────────────────────────────┤
│ Search       │ OK     │ Found prognazacc=5256880            │
│ Test Update  │ OK     │ 0                                   │
│ Restore      │ OK     │ 0                                   │
└─────────────────────────────────────────────────────────────┘
```

Options:
- `--prognazacc, -p` - Progressivo nazionale accesso (alternative to --codcom/--denom)
- `--codcom, -c` - Codice comune (Belfiore code, e.g. H501 for Roma). Required with --denom.
- `--denom, -d` - Denominazione esatta dell'odonimo - base64 encoded. Required with --codcom.
- `--accparz, -a` - Valore anche parziale del civico. Used with --codcom/--denom.
- `--token-endpoint, -e` - PDND token endpoint URL
- `--server-url, -s` - API server URL (defaults to validation environment)
- `--validation/--production` - Use validation (UAT) or production environment
- `--no-verify-ssl` - Disable SSL certificate verification (use with caution)
- `--json` - Output as JSON

> **Note**: You must provide either `--prognazacc` OR both `--codcom` and `--denom`.
> If `--prognazacc` is provided, `--codcom` and `--denom` are ignored.

**Examples:**

Direct mode - use prognazacc directly (faster):
```bash
anncsu coordinate dry-run --prognazacc 5256880
```

Search mode - search by municipality and street:
```bash
anncsu coordinate dry-run --codcom H501 --denom VklBIFJPTUE=
```

Search mode with specific civico number:
```bash
anncsu coordinate dry-run --codcom H501 --denom VklBIFJPTUE= --accparz 10
```

JSON output (works with both modes):
```bash
anncsu coordinate dry-run --prognazacc 5256880 --json
anncsu coordinate dry-run --codcom H501 --denom VklBIFJPTUE= --json
```

JSON output (direct mode - `codcom` may be `null`):
```json
{
  "success": true,
  "original_coordinates": {
    "prognazacc": "5256880",
    "codcom": null,
    "civico": "1",
    "coord_x": "12.4922309",
    "coord_y": "41.8902102",
    "quota": "0",
    "metodo": "4"
  },
  "test_update": {
    "success": true,
    "id_richiesta": "REQ-123",
    "esito": "0",
    "messaggio": "OK",
    "dati_count": 0
  },
  "restore": {
    "success": true,
    "id_richiesta": "REQ-456",
    "esito": "0",
    "messaggio": "OK",
    "dati_count": 0
  },
  "restore_failed": false,
  "error_message": null
}
```

JSON output (search mode - `codcom` is populated):
```json
{
  "success": true,
  "original_coordinates": {
    "prognazacc": "5256880",
    "codcom": "H501",
    "civico": "1",
    "coord_x": "12.4922309",
    "coord_y": "41.8902102",
    "quota": "0",
    "metodo": "4"
  },
  "test_update": {
    "success": true,
    "id_richiesta": "REQ-123",
    "esito": "0",
    "messaggio": "OK",
    "dati_count": 0
  },
  "restore": {
    "success": true,
    "id_richiesta": "REQ-456",
    "esito": "0",
    "messaggio": "OK",
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

**Handling Access Points Without Coordinates**: When an access point has no existing coordinates (X, Y, and metodo are all empty), the dry-run uses temporary test coordinates for the update test:

| Field | Test Value | Description |
|-------|------------|-------------|
| X | `12.4922309` | Longitude (Roma Colosseo area) |
| Y | `41.8902102` | Latitude (Roma Colosseo area) |
| Z | `null` | Altitude not specified |
| metodo | `4` | "Altro" (other method) |

After the test update, the command restores the original empty state. A note is displayed when test coordinates are used:

```
Note: Access has no coordinates. Using test coordinates (will be cleared after test).
```

**Note**: If the API does not allow restoring an access point without valid coordinates, the restore operation may fail. In this case, manual intervention may be needed.

---

### `anncsu coordinate bulk` - Bulk Coordinate Operations

Bulk coordinate operations with CSV input and DuckDB local persistence.
Supports large-scale coordinate updates with validation, execution tracking,
dry-run simulation, and resumable operations.

#### `anncsu coordinate bulk validate`

Validate a CSV file for bulk coordinate updates without making any API calls.
Checks header format, required columns, and validates each row against
ANNCSU business rules using Pydantic models.

```bash
anncsu coordinate bulk validate input.csv
```

Output:
```
CSV Validation Report

  File: input.csv
  Codice Comune: A062
  Total rows: 100
  Valid: 98
  Invalid: 2

┌─────────────────────────────────────┐
│ Validation Errors                   │
├─────┬──────────────┬────────────────┤
│ Row │ progr_civico │ Error          │
├─────┼──────────────┼────────────────┤
│ 45  │ 1370588      │ x provided ... │
│ 78  │ 1370592      │ metodo must .. │
└─────┴──────────────┴────────────────┘
```

Options:
- `--json` - Output results as JSON

JSON output:
```bash
anncsu coordinate bulk validate input.csv --json
```

```json
{
  "total_rows": 100,
  "valid_rows": 98,
  "invalid_rows": 2,
  "codcom": "A062",
  "validation_errors": [
    {
      "row_id": 45,
      "progr_civico": "1370588",
      "validation_error": "x provided without y"
    }
  ]
}
```

#### CSV File Format

The input CSV must have a header row with the following columns:

| Column | Required | Description |
|--------|----------|-------------|
| `codcom` | Yes | Codice comune (Belfiore code). Must be the same for all rows. |
| `progr_civico` | Yes | Progressivo civico (access progressive number) |
| `x` | No | Coordinata X (longitude). Range: 6.0-18.0 |
| `y` | No | Coordinata Y (latitude). Range: 36.0-47.0 |
| `z` | No | Quota (altitude in meters) |
| `metodo` | No | Metodo di rilevazione (1-4) |

**Supported separators**: comma (`,`) and semicolon (`;`). The separator is auto-detected from the header.

**Validation rules**:
- Header must be present and contain all 6 columns
- If `x` is provided, `y` must also be provided (and vice versa)
- `metodo` must be in range 1-4 (when provided)
- Coordinates must be within Italy bounds (x: 6.0-18.0, y: 36.0-47.0)
- Empty `x`, `y`, `z`, `metodo` is valid (clears coordinates for that access point)
- All rows must have the same `codcom`

**Example CSV (comma)**:
```csv
codcom,progr_civico,x,y,z,metodo
A062,100,13.1022000,41.8847600,150,3
A062,200,14.0000000,42.0000000,,2
A062,300,,,,,
```

**Example CSV (semicolon)**:
```csv
codcom;progr_civico;x;y;z;metodo
H501;1000;12.4922;41.8902;;4
H501;2000;12.5000;41.9000;;3
```

#### Planned Bulk Commands (Not Yet Implemented)

The following commands are planned but not yet wired to the CLI.
The underlying business logic exists in the SDK modules.

| Command | Description |
|---------|-------------|
| `anncsu coordinate bulk update` | Execute bulk coordinate update from CSV |
| `anncsu coordinate bulk dry-run` | Dry-run: validate + simulate on 10 records |
| `anncsu coordinate bulk resume` | Resume an interrupted bulk execution |
| `anncsu coordinate bulk status` | Show status of current/past bulk execution |
| `anncsu coordinate bulk report` | Generate report (CSV/JSON) for a completed run |
| `anncsu coordinate bulk list` | List past bulk executions |
| `anncsu coordinate bulk clean` | Remove old DuckDB files |

#### DuckDB Persistence

Bulk operations use DuckDB as a local persistence layer for tracking execution state.
This enables resume after interruption, progress tracking, and report generation.

- **DB location**: `~/.anncsu/bulk/{codcom}_{run_id}.db`
- **Chunking**: Rows are internally divided in chunks of 50,000 via a generated `chunk_id` column
- **Rate limiting**: 50,000 API calls/day tracked in the database
- **Tables**: `bulk_input` (rows + validation), `bulk_results` (API responses), `bulk_runs` (execution metadata), `dryrun_originals` (saved coordinates for restore)

#### Commands That Use ModI (Bulk)

| Command | ModI Headers |
|---------|-------------|
| `anncsu coordinate bulk validate` | No - local validation only |
| `anncsu coordinate bulk update` | Yes - POST requests with payload |
| `anncsu coordinate bulk dry-run` | Yes - POST requests (update + restore) |
| `anncsu coordinate bulk resume` | Yes - POST requests with payload |
| `anncsu coordinate bulk status` | No - local DB query |
| `anncsu coordinate bulk report` | No - local DB query |

---

## Environment Variables

The CLI reads configuration from environment variables (with `PDND_` prefix) or a `.env` file:

### PDND Configuration

| Variable | Required | Description |
|----------|----------|-------------|
| `PDND_KID` | Yes | Key ID (kid) header parameter |
| `PDND_ISSUER` | Yes | Issuer (iss) claim - your client_id |
| `PDND_SUBJECT` | Yes | Subject (sub) claim - your client_id |
| `PDND_AUDIENCE` | Yes | Audience (aud) - PDND client-assertion endpoint |
| `PDND_PURPOSE_ID_PA` | Yes | Purpose ID for PA Consultazione API |
| `PDND_PURPOSE_ID_COORDINATE` | Yes | Purpose ID for Coordinate API |
| `PDND_PURPOSE_ID_COORDINATE_BULK` | Yes* | Purpose ID for Coordinate Bulk API (can be empty) |
| `PDND_PURPOSE_ID_ACCESSI` | Yes* | Purpose ID for Accessi API (can be empty) |
| `PDND_PURPOSE_ID_INTERNI` | Yes* | Purpose ID for Interni API (can be empty) |
| `PDND_PURPOSE_ID_ODONIMI` | Yes* | Purpose ID for Odonimi API (can be empty) |
| `PDND_KEY_PATH` | One required | Path to RSA private key file |
| `PDND_PRIVATE_KEY` | One required | RSA private key content (alternative to KEY_PATH) |
| `PDND_TOKEN_ENDPOINT` | Yes | PDND token endpoint URL |
| `PDND_ALG` | No | Algorithm (default: RS256) |
| `PDND_TYP` | No | Token type (default: JWT) |
| `PDND_VALIDITY_MINUTES` | No | Assertion validity in minutes (default: 43200 = 30 days) |

### ModI Audit Context (for Coordinate API)

| Variable | Required | Description |
|----------|----------|-------------|
| `MODI_USER_ID` | For Coordinate | User identifier in the consumer domain |
| `MODI_USER_LOCATION` | For Coordinate | Workstation/system identifier |
| `MODI_LOA` | For Coordinate | Level of Assurance (e.g., SPID_L2, CIE_L3) |

> **Note**: ModI variables are required only for Coordinate API write operations (`update`, `dry-run`). If not configured, the CLI will attempt requests without ModI headers, which will fail for APIs requiring them.

### Example `.env` file

```env
# PDND Configuration
PDND_KID=your-key-id
PDND_ISSUER=your-client-id
PDND_SUBJECT=your-client-id
PDND_AUDIENCE=https://auth.uat.interop.pagopa.it/client-assertion

# Purpose ID for each API type (ALL must be present, can be empty if not used)
PDND_PURPOSE_ID_PA=your-purpose-id-for-pa-consultazione
PDND_PURPOSE_ID_COORDINATE=your-purpose-id-for-coordinate-api
PDND_PURPOSE_ID_COORDINATE_BULK=your-purpose-id-for-bulk-api
PDND_PURPOSE_ID_ACCESSI=
PDND_PURPOSE_ID_INTERNI=
PDND_PURPOSE_ID_ODONIMI=

PDND_KEY_PATH=./private_key.pem
PDND_TOKEN_ENDPOINT=https://auth.uat.interop.pagopa.it/token.oauth2

# Optional
PDND_VALIDITY_MINUTES=43200

# ModI Audit Context (required for Coordinate API)
MODI_USER_ID=batch-user-001
MODI_USER_LOCATION=server-batch-01
MODI_LOA=SPID_L2
```

---

## ModI Headers (Coordinate API)

The Coordinate API requires ModI (Modello di Interoperabilità) security headers in addition to the standard bearer token. These headers implement the AGID interoperability patterns:

- **INTEGRITY_REST_02**: Integrity of REST message payload in PDND
- **AUDIT_REST_02**: Forwarding of tracked data in the Consumer domain

### Configuration

To enable ModI headers, add these environment variables to your `.env`:

| Variable | Required | Description |
|----------|----------|-------------|
| `MODI_USER_ID` | Yes* | User identifier in the consumer domain |
| `MODI_USER_LOCATION` | Yes* | Workstation/system identifier from which the request originates |
| `MODI_LOA` | Yes* | Level of Assurance in the authentication process |

*Required only for Coordinate API (POST requests). If not configured, ModI headers will not be sent.

### Level of Assurance (LoA) Values

| Value | Description |
|-------|-------------|
| `SPID_L1` | SPID Level 1 authentication |
| `SPID_L2` | SPID Level 2 authentication (recommended for batch operations) |
| `SPID_L3` | SPID Level 3 authentication |
| `CIE_L1` | CIE Level 1 authentication |
| `CIE_L2` | CIE Level 2 authentication |
| `CIE_L3` | CIE Level 3 authentication |

### How It Works

When ModI is configured, the CLI automatically generates two JWT headers for each POST request:

1. **`Agid-JWT-Signature`**: Contains a SHA-256 digest of the request payload, ensuring integrity
2. **`Agid-JWT-TrackingEvidence`**: Contains audit information (userID, userLocation, LoA) for traceability

These headers are signed using the same RSA private key used for PDND authentication.

### Example Configuration

```env
# ModI Audit Context
MODI_USER_ID=system-batch-processor
MODI_USER_LOCATION=datacenter-rm-01
MODI_LOA=SPID_L2
```

### Commands That Use ModI

| Command | ModI Headers |
|---------|-------------|
| `anncsu coordinate update` | ✅ Yes - POST request with payload |
| `anncsu coordinate dry-run` | ✅ Yes - Two POST requests (test + restore) |
| `anncsu coordinate bulk validate` | ❌ No - Local validation only |
| `anncsu coordinate bulk update` | ✅ Yes - POST requests with payload |
| `anncsu coordinate bulk dry-run` | ✅ Yes - POST requests (update + restore) |
| `anncsu coordinate status` | ❌ No - GET request, no payload |
| `anncsu auth *` | ❌ No - Authentication only |
| `anncsu config *` | ❌ No - Local configuration |

### Verifying ModI Configuration

To check if ModI is properly configured:

```bash
anncsu config show
```

The output will show:
```
┌─────────────────────────────────────────┐
│ ModI Configuration                      │
├─────────────────────────────────────────┤
│ User ID:       system-batch-processor   │
│ User Location: datacenter-rm-01         │
│ LoA:           SPID_L2                  │
│ Status:        ✅ Configured            │
└─────────────────────────────────────────┘
```

If ModI is not configured:
```
┌─────────────────────────────────────────┐
│ ModI Configuration                      │
├─────────────────────────────────────────┤
│ Status:        ❌ Not configured        │
│ Note:          Required for Coordinate  │
│                API write operations     │
└─────────────────────────────────────────┘
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
    PDND_PURPOSE_ID_PA: ${{ secrets.PDND_PURPOSE_ID_PA }}
    PDND_PURPOSE_ID_COORDINATE: ${{ secrets.PDND_PURPOSE_ID_COORDINATE }}
    PDND_PURPOSE_ID_ACCESSI: ""
    PDND_PURPOSE_ID_INTERNI: ""
    PDND_PURPOSE_ID_ODONIMI: ""
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
