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

# 4. Login for PA API (generates assertion + obtains token + saves session)
anncsu auth login --api pa

# 5. Check status
anncsu auth status --api pa

# 6. Use token in API calls (auto-refreshes if expired)
curl -H "Authorization: Bearer $(anncsu auth token --api pa)" \
  "https://modipa-val.agenziaentrate.it/govway/rest/in/AgenziaEntrate-PDND/anncsu-consultazione/v1/elencoodonimi?codcom=H501"

# 7. Update coordinates for an access point
anncsu coordinate update --codcom H501 --progr-civico 12345 --x 12.4963655 --y 41.9027835

# 8. Validate a CSV for bulk coordinate updates
anncsu coordinate bulk validate input.csv

# 9. Run a dry-run on a few records before bulk update
anncsu coordinate bulk dry-run input.csv --max-records 5
```

## Commands

### `anncsu config` - Configuration Management

Manage PDND configuration stored in `.env` file.

#### `anncsu config init`

Generate a template `.env` file with all required PDND configuration variables.
By default, creates the file at `~/.anncsu/.env`.

```bash
anncsu config init
anncsu config init --output /path/to/custom/.env
anncsu config init --force  # overwrite existing file
```

Options:
- `--output`, `-o` - Output path for .env file (default: `~/.anncsu/.env`)
- `--force`, `-f` - Overwrite existing .env file

Output:
```
Created /Users/user/.anncsu/.env

Edit the file with your PDND credentials, then run:
  anncsu config validate
```

The generated template includes:
- `PDND_KID`, `PDND_ISSUER`, `PDND_SUBJECT`, `PDND_AUDIENCE`
- `PDND_PURPOSE_ID_PA`, `PDND_PURPOSE_ID_COORDINATE`
- `PDND_PURPOSE_ID_ACCESSI`, `PDND_PURPOSE_ID_INTERNI`, `PDND_PURPOSE_ID_ODONIMI`
- `PDND_KEY_PATH`
- `PDND_VALIDITY_MINUTES` (commented, optional)

#### `anncsu config show`

Display current configuration (with masked sensitive values):

```bash
anncsu config show
anncsu config show --json
```

Options:
- `--json` - Output as JSON

Output (3 tables: PDND config, Purpose IDs, ModI):
```
┌─────────────────────────────────────────┐
│ PDND Configuration                      │
├─────────────────────────────────────────┤
│ KID:           abc123...                │
│ Issuer:        a1b2c3d4-e5f6-...        │
│ Subject:       a1b2c3d4-e5f6-...        │
│ Audience:      https://auth.uat...      │
│ Key Path:      ./private_key.pem OK     │
│ Validity:      43200 minutes (30 days)  │
└─────────────────────────────────────────┘

┌──────────────────────────────────────────┐
│ Purpose IDs per API                      │
├──────────────────────────────────────────┤
│ PA (Consultazione): 12345678...          │
│ Coordinate:         abcdef01...          │
│ Accessi:            Not set              │
│ Interni:            Not set              │
│ Odonimi:            Not set              │
└──────────────────────────────────────────┘

┌─────────────────────────────────────────┐
│ ModI Configuration                      │
├─────────────────────────────────────────┤
│ Status:        Configured               │
│ User ID:       batch-user-001           │
│ User Location: server-batch-01          │
│ LoA:           SPID_L2                  │
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

#### `anncsu config import`

Import an existing `.env` file into `~/.anncsu/.env`. Useful when migrating
from a project-local `.env` to the centralized config directory.

```bash
anncsu config import                    # import .env from current directory
anncsu config import /path/to/.env      # import from specific path
anncsu config import --force            # overwrite existing config
```

Options:
- `--force`, `-f` - Overwrite existing configuration

Output:
```
Imported /path/to/.env -> /Users/user/.anncsu/.env

Verify with:
  anncsu config show
  anncsu config validate
```

#### `anncsu config set`

Set individual configuration values in the `.env` file. By default, updates
`~/.anncsu/.env`. Values not provided are left unchanged.

```bash
anncsu config set --kid my-key-id
anncsu config set --purpose-id-pa your-purpose-id
anncsu config set --modi-user-id batch-user --modi-loa SPID_L2
anncsu config set --env-file /custom/path/.env --issuer my-client-id
```

Options:
- `--kid` - Set PDND_KID
- `--issuer` - Set PDND_ISSUER
- `--subject` - Set PDND_SUBJECT
- `--audience` - Set PDND_AUDIENCE
- `--purpose-id-pa` - Set PDND_PURPOSE_ID_PA
- `--purpose-id-coordinate` - Set PDND_PURPOSE_ID_COORDINATE
- `--purpose-id-accessi` - Set PDND_PURPOSE_ID_ACCESSI
- `--purpose-id-interni` - Set PDND_PURPOSE_ID_INTERNI
- `--purpose-id-odonimi` - Set PDND_PURPOSE_ID_ODONIMI
- `--key-path` - Set PDND_KEY_PATH
- `--modi-user-id` - Set PDND_MODI_USER_ID (for ModI audit headers)
- `--modi-user-location` - Set PDND_MODI_USER_LOCATION (for ModI audit headers)
- `--modi-loa` - Set PDND_MODI_LOA (Level of Assurance, e.g., SPID_L2)
- `--env-file` - Path to .env file (default: `~/.anncsu/.env`)

Output:
```
Updated 2 value(s) in /Users/user/.anncsu/.env
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

#### `anncsu assertion decode`

Decode and display a JWT token (without signature verification).
Accepts a token as argument or from stdin.

```bash
anncsu assertion decode eyJhbGciOiJSUzI1NiIs...
anncsu auth token | anncsu assertion decode
anncsu assertion decode eyJhbGciOiJSUzI1NiIs... --json
```

Options:
- `--json` - Output as JSON

Output:
```
┌──────────────────────────────┐
│ JWT Header                   │
├──────────────────────────────┤
│ Algorithm (alg)  RS256       │
│ Type (typ)       JWT         │
│ Key ID (kid)     abc123...   │
└──────────────────────────────┘

┌──────────────────────────────────────┐
│ JWT Payload                          │
├──────────────────────────────────────┤
│ Issuer (iss)     a1b2c3d4-e5f6-...  │
│ Subject (sub)    a1b2c3d4-e5f6-...  │
│ Audience (aud)   https://auth.uat...│
│ Purpose ID       12345678-90ab-...  │
│ Issued At (iat)  2026-01-18 10:30   │
│ Expires At (exp) 2026-02-17 10:30   │
└──────────────────────────────────────┘
```

JSON output:
```json
{
  "header": {
    "alg": "RS256",
    "typ": "JWT",
    "kid": "abc123..."
  },
  "payload": {
    "iss": "a1b2c3d4-e5f6-...",
    "sub": "a1b2c3d4-e5f6-...",
    "aud": "https://auth.uat.interop.pagopa.it/client-assertion",
    "purposeId": "12345678-90ab-...",
    "iat": 1737192600,
    "exp": 1739784600
  }
}
```

---

### `anncsu auth` - Authentication

Authenticate with PDND and manage access tokens.

#### `anncsu auth login`

Perform full authentication flow (assertion + token exchange) for a specific API type:

```bash
anncsu auth login --api pa
anncsu auth login --api coordinate
anncsu auth login --api coordinate_bulk
anncsu auth login --api pa --json
```

Options:
- `--api`, `-a` - **(required)** API type. Valid values: `pa`, `coordinate`, `coordinate_bulk`, `accessi`, `interni`, `odonimi`
- `--token-endpoint`, `-e` - PDND token endpoint URL (default: UAT)
- `--json` - Output as JSON

Output:
```
Login successful!

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

#### `anncsu auth status`

Show current authentication status for a specific API type:

```bash
anncsu auth status --api pa
anncsu auth status --api coordinate --json
```

Options:
- `--api`, `-a` - **(required)** API type
- `--token-endpoint`, `-e` - PDND token endpoint URL (default: UAT)
- `--json` - Output as JSON

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
anncsu auth refresh --api pa
anncsu auth refresh --api coordinate
```

Options:
- `--api`, `-a` - **(required)** API type
- `--token-endpoint`, `-e` - PDND token endpoint URL (default: UAT)

Output:
```
Token refreshed!
   TTL: 600 seconds
   Expires: 2026-01-18 10:50:00
```

#### `anncsu auth token`

Print the current access token (useful for piping):

```bash
anncsu auth token --api pa
anncsu auth token --api coordinate
```

Options:
- `--api`, `-a` - **(required)** API type
- `--token-endpoint`, `-e` - PDND token endpoint URL (default: UAT)

Output:
```
eyJhbGciOiJSUzI1NiIsInR5cCI6ImF0K2p3dCJ9.eyJpc3MiOiJodHRwczovL2F1dGgudWF0...
```

Usage with curl:
```bash
curl -H "Authorization: Bearer $(anncsu auth token --api pa)" \
  https://modipa-val.agenziaentrate.it/govway/rest/in/AgenziaEntrate-PDND/anncsu-consultazione/v1/esisteodonimo?codcom=H501
```

#### `anncsu auth curl`

Generate a complete cURL command with all authentication headers, ready to copy-paste.

For PA (GET) APIs, generates a cURL with Bearer token only.
For Coordinate (POST) APIs, generates a cURL with Bearer + ModI headers (Digest, Agid-JWT-Signature, Agid-JWT-TrackingEvidence).

```bash
# PA consultazione — passa i parametri di query direttamente
anncsu auth curl --api pa --codcom H501 --denom "VIA ROMA"
anncsu auth curl --api pa --endpoint elencoodonimi --codcom H501 --denomparz VIA
anncsu auth curl --api pa --endpoint prognazacc --prognazacc 0001234500001
anncsu auth curl --api pa --endpoint elencoaccessiprog --prognaz 0001234500000 --accparz 1 --production

# Coordinate (POST with ModI headers)
anncsu auth curl --api coordinate
anncsu auth curl --api coordinate --body '{"richiesta":{...}}'

# Headers only (for scripting)
anncsu auth curl --api pa --codcom H501 --denom "VIA ROMA" --headers-only

# JSON output
anncsu auth curl --api pa --codcom H501 --denom "VIA ROMA" --json

# Copy to clipboard (macOS)
anncsu auth curl --api pa --codcom H501 --denom "VIA ROMA" | pbcopy
```

I parametri `--denom` e `--denomparz` accettano testo in chiaro e vengono automaticamente codificati in base64 dal CLI.
Non serve codificare manualmente: basta passare il nome della strada e la cURL generata conterrà il valore base64 corretto.

Options:
- `--api`, `-a` - **(required)** API type (`pa`, `coordinate`, etc.)
- `--endpoint`, `-p` - PA endpoint to query (default: `esisteodonimo`). Only for `--api pa`.
- `--validation/--production` - Environment (default: `--validation`)
- `--body`, `-b` - JSON body for POST (coordinate). Uses sample if omitted
- `--headers-only` - Output only `-H` flags
- `--json` - Output as structured JSON (`CurlOutput` model)
- `--token-endpoint`, `-e` - PDND token endpoint URL (default: UAT)

Query parameter options (solo `--api pa`):
- `--codcom` - Codice Belfiore del comune (es. `H501`)
- `--denom` - Denominazione esatta dell'odonimo (testo, auto base64)
- `--denomparz` - Denominazione parziale dell'odonimo (testo, auto base64)
- `--accesso` - Valore civico (+esponente/specificita) o metrico
- `--accparz` - Valore parziale del civico o metrico
- `--prognaz` - Progressivo nazionale dell'odonimo
- `--prognazacc` - Progressivo nazionale dell'accesso

Available PA endpoints (`--endpoint`):

| Endpoint | Path | Required Params | Description |
|---|---|---|---|
| `esisteodonimo` | `/esisteodonimo` | `--codcom`, `--denom` (auto base64) | Verifica esistenza odonimo |
| `esisteaccesso` | `/esisteaccesso` | `--codcom`, `--denom` (auto base64), `--accesso` | Verifica esistenza accesso |
| `elencoodonimi` | `/elencoodonimi` | `--codcom`, `--denomparz` (auto base64) | Elenco odonimi |
| `elencoaccessi` | `/elencoaccessi` | `--codcom`, `--denom` (auto base64), `--accparz` | Elenco accessi |
| `elencoodonimiprog` | `/elencoodonimiprog` | `--codcom`, `--denomparz` (auto base64) | Elenco odonimi con progressivo nazionale |
| `elencoaccessiprog` | `/elencoaccessiprog` | `--prognaz`, `--accparz` | Elenco accessi con progressivo nazionale |
| `prognazarea` | `/prognazarea` | `--prognaz` | Dati odonimo per progressivo nazionale |
| `prognazacc` | `/prognazacc` | `--prognazacc` | Dati accesso per progressivo nazionale accesso |

Output (PA GET):
```bash
# anncsu auth curl --api pa --codcom H501 --denom "VIA ROMA"
curl -X GET \
  "https://modipa-val.agenziaentrate.it/govway/rest/in/AgenziaEntrate-PDND/anncsu-consultazione/v1/esisteodonimo?codcom=H501&denom=VklBIFJPTUE%3D" \
  -H "Authorization: Bearer eyJ..."
```

Output (Coordinate POST):
```bash
curl -X POST \
  "https://modipa-val.agenziaentrate.it/govway/rest/in/AgenziaEntrate-PDND/anncsu-aggiornamento-coordinate/v1/gestionecoordinate" \
  -H "Authorization: Bearer eyJ..." \
  -H "Content-Type: application/json" \
  -H "Digest: SHA-256=..." \
  -H "Agid-JWT-Signature: eyJ..." \
  -H "Agid-JWT-TrackingEvidence: eyJ..." \
  -d '{"richiesta":{"accesso":{"codcom":"H501",...}}}'
```

JSON output (`--json`):
```json
{
  "curl_command": "curl -X GET ...",
  "headers": {
    "Authorization": "Bearer eyJ..."
  },
  "server_url": "https://modipa-val.agenziaentrate.it/.../esisteodonimo?codcom=H501&denom=VklBIFJPTUE%3D",
  "method": "GET",
  "body": null,
  "api_type": "pa",
  "environment": "validation",
  "token_ttl": 600,
  "warnings": ["denom: \"VIA ROMA\" -> base64: VklBIFJPTUE="]
}
```

> **Note**: ModI headers (Agid-JWT-Signature) are valid for ~5 minutes. The Digest header is computed from the body, so if you modify the body the cURL will be invalid.

> **Note**: Se non vengono passati tutti i parametri richiesti per l'endpoint, il CLI stampa un warning con i parametri mancanti. La cURL viene comunque generata con i parametri forniti.

#### `anncsu auth logout`

Clear cached tokens for a specific API type (end session):

```bash
anncsu auth logout --api pa
anncsu auth logout --api coordinate
anncsu auth logout --api coordinate_bulk
```

Options:
- `--api`, `-a` - API type for authentication. Valid values: `pa`, `coordinate`, `coordinate_bulk`, `accessi`, `interni`, `odonimi`
- `--token-endpoint`, `-e` - PDND token endpoint URL (default: UAT)

Output:
```
Logout successful. Session cleared.
```

> **Note**: This clears local state only. The tokens may still be valid on the server until they expire.

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
- `--raw` - Print raw API response to stderr

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
- `--raw` - Print raw API response to stderr

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
- `--raw` - Print raw API responses to stderr (one per API call: lookup, test update, restore)

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

**Safety skip on legacy NULL `metodo`**: a dry-run **guarantees zero changes** in production. If the target record has an original `metodo` that is not one of the valid OAS values (`"1"`, `"2"`, `"3"`, `"4"`) — typically legacy data imported before the validation rule was enforced — the restore step would fail (ANNCSU error 130, *"Il metodo deve essere obbligatorio e compreso tra 1 e 4"*) and the test update would remain committed permanently.

To preserve the dry-run guarantee, the CLI **skips** such records **before any API write call**:

- No `gestionecoordinate` request is sent.
- A warning is printed (or, with `--json`, a structured payload with `"skipped": true` and `"skip_reason": "original_metodo_null_or_invalid"`).
- Exit code is `0` (the dry-run completed as designed, the record was simply not testable).

JSON output when a record is skipped:

```json
{
  "success": true,
  "original_coordinates": {
    "prognazacc": "5256880",
    "codcom": "H501",
    "civico": "1",
    "coord_x": null,
    "coord_y": null,
    "quota": null,
    "metodo": null
  },
  "test_update": null,
  "restore": null,
  "restore_failed": false,
  "skipped": true,
  "skip_reason": "original_metodo_null_or_invalid",
  "error_message": null
}
```

> **Removed in this release**: the prior fallback that injected Roma Colosseo coordinates (`X=12.4922309`, `Y=41.8902102`, `metodo=4`) when the access had no original coordinates. That fallback violated the "dry-run = zero changes" guarantee because the eventual restore to `metodo=NULL` could not succeed. Skip is now the only behaviour.

**Warning Handling (legacy)**: if a restore fails for any *other* reason (e.g. transient network error during the round-trip on a record that did pass the safety check), the command will still display original values for manual recovery — same as before.

---

#### `anncsu coordinate duckdb-batch-update`

Batch update coordinates from a DuckDB table for small municipalities that don't have access to the bulk coordinate API endpoint. Reads geocoded data from a DuckDB source table, updates coordinates one-by-one via the ANNCSU API, and stores all results in a `batch_update_results` table for auditing.

Supports resumable multi-day execution with `--resume` to respect the daily limit of 4,000 records per municipality.

```bash
# First run (day 1): process up to 4000 records
# --production auto-selects the production token endpoint.
anncsu coordinate duckdb-batch-update \
  --db ~/Downloads/anncsu_anagni/A269.duckdb \
  --source-table deoverlapped_geocoded_anncsu_prepared \
  --codcom A269 \
  --production \
  --max-records 4000

# Day 2: resume with same run ID
anncsu coordinate duckdb-batch-update \
  --db ~/Downloads/anncsu_anagni/A269.duckdb \
  --source-table deoverlapped_geocoded_anncsu_prepared \
  --codcom A269 \
  --production \
  --max-records 4000 \
  --resume 20260319_140554

# Day 3: finish remaining records (no --max-records needed)
anncsu coordinate duckdb-batch-update \
  --db ~/Downloads/anncsu_anagni/A269.duckdb \
  --source-table deoverlapped_geocoded_anncsu_prepared \
  --codcom A269 \
  --production \
  --resume 20260319_140554
```

**Options:**

| Option | Description | Default |
|--------|-------------|---------|
| `--db`, `-d` | Path to DuckDB file (required) | — |
| `--codcom`, `-c` | Codice comune / Belfiore code (required) | — |
| `--source-table`, `-t` | Source table name | `deoverlapped_geocoded_anncsu` |
| `--max-records`, `-m` | Max records to process (0 = all) | `0` |
| `--resume` | Resume a previous run by its Run ID | — |
| `--token-endpoint`, `-e` | PDND token endpoint URL | UAT endpoint |
| `--server-url`, `-s` | API server URL (auto-detected) | — |
| `--validation/--production` | Environment selection | `--validation` |
| `--no-verify-ssl` | Disable SSL verification | `false` |
| `--json` | Output as JSON | `false` |

**Source table requirements:**

The source table must have coordinate columns as `VARCHAR` with length ≤ 12 for `x`/`y` and ≤ 7 for `z`. If the coordinates are stored as `FLOAT`/`DOUBLE`, create a `_prepared` table first:

```sql
CREATE TABLE deoverlapped_geocoded_anncsu_prepared AS
SELECT
    PROGRESSIVO_ACCESSO::INTEGER as PROGRESSIVO_ACCESSO,
    CIVICO::INTEGER as CIVICO,
    CODICE_COMUNE,
    CAST(ROUND(COORD_X_COMUNE, 6) AS VARCHAR) as COORD_X_COMUNE,
    CAST(ROUND(COORD_Y_COMUNE, 6) AS VARCHAR) as COORD_Y_COMUNE,
    CASE WHEN QUOTA IS NOT NULL THEN CAST(ROUND(QUOTA, 1) AS VARCHAR) ELSE NULL END as QUOTA,
    CAST(METODO AS VARCHAR) as METODO
FROM deoverlapped_geocoded_anncsu
WHERE CODICE_COMUNE = 'A269'
AND PROGRESSIVO_ACCESSO IS NOT NULL
AND COORD_X_COMUNE IS NOT NULL
AND COORD_Y_COMUNE IS NOT NULL;
```

The command will reject the source table if any coordinate exceeds the maxLength limits.

**Resume behavior:**

- `--resume RUN_ID` skips records already succeeded (esito='0') for that run
- Failed records are retried on resume
- The same `run_id` is reused across all days for consistent auditing
- When all records are complete, exits with code 0 and a confirmation message

**JSON output (`--json`):**

```json
{
  "run_id": "20260319_140554",
  "timestamp": "2026-03-19T14:05:54",
  "total": 4000,
  "success": 3998,
  "failed": 2,
  "errors": [
    {"progr_accesso": 12345, "error": "Network error"}
  ]
}
```

**Query results in DuckDB:**

```sql
-- Summary by run
SELECT run_id, COUNT(*) as total,
       SUM(CASE WHEN esito = '0' THEN 1 ELSE 0 END) as success,
       SUM(CASE WHEN esito != '0' OR esito IS NULL THEN 1 ELSE 0 END) as failed
FROM batch_update_results
GROUP BY run_id;

-- Failed records for retry analysis
SELECT progressivo_accesso, error_detail, elapsed_ms
FROM batch_update_results
WHERE run_id = '20260319_140554' AND (esito != '0' OR esito IS NULL);
```

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

| Column | Required | Description | Max Length |
|--------|----------|-------------|-----------|
| `codcom` | Yes | Codice comune (Belfiore code). Must be the same for all rows. | - |
| `progr_civico` | Yes | Progressivo civico (access progressive number) | 15 |
| `x` | No | Coordinata X (longitude). Range: 6.0-18.0 | **12** |
| `y` | No | Coordinata Y (latitude). Range: 36.0-47.0 | **12** |
| `z` | No | Quota (altitude in meters) | **7** |
| `metodo` | No | Metodo di rilevazione (1-4) | 1 |

**Supported separators**: comma (`,`) and semicolon (`;`). The separator is auto-detected from the header.

**Validation rules**:
- Header must be present and contain all 6 columns
- If `x` is provided, `y` must also be provided (and vice versa)
- `metodo` must be in range 1-4 (when provided)
- Coordinates must be within Italy bounds (x: 6.0-18.0, y: 36.0-47.0)
- **Coordinate string length must not exceed API limits**: x max 12 chars, y max 12 chars, z max 7 chars
- Empty `x`, `y`, `z`, `metodo` is valid (clears coordinates for that access point)
- All rows must have the same `codcom`

> **Important**: The ANNCSU API enforces `maxLength` on coordinate fields (from the OAS specification). Coordinates with too many decimal places (e.g., `12.3476928612` = 14 chars) will be rejected as invalid during validation. Ensure coordinate values are truncated/rounded to fit within the maximum length before importing.

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

#### `anncsu coordinate bulk update`

Execute bulk coordinate update from a CSV file. Imports the CSV, validates
rows, then calls the Coordinate API for each valid row. Progress is tracked
in a local DuckDB database for resume capability.

```bash
anncsu coordinate bulk update input.csv
anncsu coordinate bulk update input.csv --production
anncsu coordinate bulk update input.csv --max-records 1000
anncsu coordinate bulk update input.csv --json
```

Options:
- `--max-records`, `-n` - Maximum number of valid rows to process (default: all). Useful for testing with a subset before running a full update.
- `--token-endpoint`, `-e` - PDND token endpoint URL (default: UAT)
- `--server-url`, `-s` - Custom API server URL
- `--validation/--production` - Use validation (UAT) or production environment (default: validation)
- `--no-verify-ssl` - Disable SSL certificate verification
- `--json` - Output results as JSON

Output:
```
Bulk Update
  CSV: input.csv
  Codice Comune: A062
  Total rows: 100
  Valid: 98
  Invalid: 2
  Run ID: abc123-def456
  DB: /Users/user/.anncsu/bulk/A062_abc123-def456.db

⠋ Processing: 50/98 (ok=48 err=2)

Results:
  Processed: 98
  Succeeded: 96
  Failed: 2

Timing:
  Avg: 481 ms/call
  Min: 345 ms  Max: 1637 ms
  Total: 481.2 s
  Est. 50k calls: 400.6 min
```

JSON output:
```json
{
  "run_id": "abc123-def456",
  "codcom": "A062",
  "db_path": "/Users/user/.anncsu/bulk/A062_abc123-def456.db",
  "total_rows": 100,
  "valid_rows": 98,
  "invalid_rows": 2,
  "max_records": 1000,
  "processed": 98,
  "succeeded": 96,
  "failed": 2,
  "rate_limited": false,
  "timing": {
    "total_elapsed_ms": 47218.45,
    "avg_elapsed_ms": 481.82,
    "min_elapsed_ms": 345.12,
    "max_elapsed_ms": 1637.89,
    "estimated_50k_minutes": 401.5
  }
}
```

> **Note**: `max_records` is `null` in JSON output when not specified (all valid rows are processed). The `timing` section shows per-call latency statistics and an estimate for processing 50,000 calls at the observed average rate.

If the daily rate limit (50,000 API calls) is reached, the command exits with code 1
and prints a message with the `run_id` to use for resuming:

```
Rate limit reached after 49998 calls. 2 rows remaining.
Resume with: anncsu coordinate bulk resume abc123-def456
```

#### `anncsu coordinate bulk dry-run`

Dry-run: validate a CSV and simulate updates on a limited number of records.
For each tested record, the command:
1. Looks up current coordinates via the Consultazione (PA) API
2. Updates with CSV values via the Coordinate API
3. Restores original coordinates

```bash
anncsu coordinate bulk dry-run input.csv
anncsu coordinate bulk dry-run input.csv --max-records 5
anncsu coordinate bulk dry-run input.csv --json
```

Options:
- `--max-records`, `-n` - Maximum records to test (default: 10)
- `--token-endpoint`, `-e` - PDND token endpoint URL (default: UAT)
- `--server-url`, `-s` - Custom API server URL
- `--validation/--production` - Use validation (UAT) or production environment (default: validation)
- `--no-verify-ssl` - Disable SSL certificate verification
- `--json` - Output results as JSON

Output:
```
Bulk Dry-Run
  CSV: input.csv
  Codice Comune: A062
  Valid rows: 98
  Max records to test: 10

⠋ Running dry-run...

Dry-Run Results:
┌──────────────────────┬───────┐
│ Metric               │ Value │
├──────────────────────┼───────┤
│ Total tested         │ 8     │
│ Updates succeeded    │ 8     │
│ Updates failed       │ 0     │
│ Restores succeeded   │ 8     │
│ Restores failed      │ 0     │
│ Lookup failures      │ 0     │
│ Metodo NULL skipped  │ 2     │
└──────────────────────┴───────┘
```

JSON output:
```json
{
  "run_id": "abc123-def456",
  "total_tested": 8,
  "updates_succeeded": 6,
  "updates_failed": 2,
  "restores_succeeded": 6,
  "restores_failed": 0,
  "lookup_failures": 0,
  "metodo_null_skipped": 2,
  "errors": [
    {
      "row_id": 4,
      "progr_civico": "33013415",
      "operation": "dryrun_update",
      "http_status": 400,
      "error_detail": "body.richiesta.accesso.coordinate.y: Max length is '12', found '13'"
    },
    {
      "row_id": 7,
      "progr_civico": "33013422",
      "operation": "dryrun_update",
      "http_status": 400,
      "error_detail": "body.richiesta.accesso.coordinate.x: Max length is '12', found '14'"
    },
    {
      "row_id": 12,
      "progr_civico": "33013500",
      "operation": "dryrun_skip",
      "http_status": null,
      "error_detail": "original_metodo_null_or_invalid: None"
    }
  ]
}
```

**Safety skip on legacy NULL `metodo`**: same semantics as `coordinate dry-run` — records whose original `metodo` is not in `{"1", "2", "3", "4"}` are skipped **before any API write** to preserve the "dry-run = zero changes" guarantee. Counted in the dedicated `metodo_null_skipped` field; logged in `bulk_results` with `operation = 'dryrun_skip'` and `error_detail = 'original_metodo_null_or_invalid: <value>'`, so they appear in the **Error Details** section alongside other failures (distinguishable by the `operation` column).

When there are errors, the text output also includes an **Error Details** table showing
row, progr_civico, operation, HTTP status, and error message for each failed operation.

Exits with code 1 if any restores failed (manual intervention may be needed). Skipped records do NOT cause a non-zero exit.

#### `anncsu coordinate bulk resume`

Resume an interrupted bulk update execution. Finds the DuckDB file for
the given run ID, resets any rows stuck in 'processing' state, and
continues execution from where it left off.

```bash
anncsu coordinate bulk resume abc123-def456
anncsu coordinate bulk resume abc123-def456 --json
```

Options:
- `--token-endpoint`, `-e` - PDND token endpoint URL (default: UAT)
- `--server-url`, `-s` - Custom API server URL
- `--validation/--production` - Use validation (UAT) or production environment (default: validation)
- `--no-verify-ssl` - Disable SSL certificate verification
- `--json` - Output results as JSON

Output:
```
Resuming Run
  Run ID: abc123-def456
  Codice Comune: A062
  DB: /Users/user/.anncsu/bulk/A062_abc123-def456.db

⠋ Processing: 2/2 (ok=2 err=0)

Results:
  Processed: 2
  Succeeded: 2
  Failed: 0
```

JSON output:
```json
{
  "run_id": "abc123-def456",
  "codcom": "A062",
  "processed": 2,
  "succeeded": 2,
  "failed": 0,
  "rate_limited": false
}
```

Only `update` mode runs can be resumed. Attempting to resume a `dryrun` or
`validate` run will produce an error.

#### `anncsu coordinate bulk status`

Show status of a bulk execution run.

```bash
anncsu coordinate bulk status abc123-def456
anncsu coordinate bulk status abc123-def456 --json
```

Options:
- `--json` - Output results as JSON

Output:
```
Bulk Run Status

┌───────────────┬─────────────────────────┐
│ Field         │ Value                   │
├───────────────┼─────────────────────────┤
│ Run ID        │ abc123-d...             │
│ Codice Comune │ A062                    │
│ Mode          │ update                  │
│ Total rows    │ 100                     │
│ Valid         │ 98                      │
│ Invalid       │ 2                       │
│ Processed     │ 98                      │
│ Succeeded     │ 96                      │
│ Failed        │ 2                       │
│ Started       │ 2026-02-20 10:00:00     │
│ Finished      │ 2026-02-20 10:05:00     │
│ DB            │ /Users/user/.anncsu/... │
└───────────────┴─────────────────────────┘
```

JSON output:
```json
{
  "run_id": "abc123-def456",
  "codcom": "A062",
  "mode": "update",
  "total_rows": 100,
  "valid_rows": 98,
  "invalid_rows": 2,
  "processed": 98,
  "succeeded": 96,
  "failed": 2,
  "started_at": "2026-02-20 10:00:00",
  "finished_at": "2026-02-20 10:05:00"
}
```

#### `anncsu coordinate bulk report`

Export results of a bulk run as CSV or JSON.

```bash
anncsu coordinate bulk report abc123-def456
anncsu coordinate bulk report abc123-def456 --format csv
anncsu coordinate bulk report abc123-def456 --format json --output results.json
```

Options:
- `--format`, `-f` - Output format: `csv` or `json` (default: `csv`)
- `--output`, `-o` - Output file path. Defaults to stdout.

CSV output includes the following columns:
`codcom`, `progr_civico`, `input_x`, `input_y`, `input_z`, `input_metodo`,
`esito`, `messaggio`, `id_richiesta`, `operation`, `error_detail`, `processed_at`

JSON output includes a summary section and the full results array:
```json
{
  "summary": {
    "run_id": "abc123-def456",
    "codcom": "A062",
    "mode": "update",
    "total_rows": 100,
    "valid_rows": 98,
    "invalid_rows": 2,
    "processed": 98,
    "succeeded": 96,
    "failed": 2,
    "started_at": "2026-02-20 10:00:00",
    "finished_at": "2026-02-20 10:05:00"
  },
  "results": [
    {
      "codcom": "A062",
      "progr_civico": "1370588",
      "input_x": "13.1022",
      "input_y": "41.8848",
      "input_z": "150",
      "input_metodo": "3",
      "esito": "0",
      "messaggio": "OK",
      "id_richiesta": "5144",
      "operation": "update",
      "error_detail": null,
      "processed_at": "2026-02-20 10:00:01"
    }
  ]
}
```

**Filtering results**: The `report` command exports all results. To filter by outcome (e.g., only successes or only errors), export to CSV and filter, or use direct DuckDB queries (see [DuckDB Query Examples](#duckdb-query-examples) below).

#### `anncsu coordinate bulk list`

List all past bulk execution runs found in the local DuckDB storage.

```bash
anncsu coordinate bulk list
anncsu coordinate bulk list --json
```

Options:
- `--json` - Output results as JSON

Output:
```
Bulk Runs (3 total)

┌────────────┬────────┬────────┬───────┬────┬─────┬─────────────────────┬─────────────┐
│ Run ID     │ Codcom │ Mode   │ Total │ OK │ Err │ Started             │ Status      │
├────────────┼────────┼────────┼───────┼────┼─────┼─────────────────────┼─────────────┤
│ abc123-d...│ A062   │ update │ 100   │ 96 │ 2   │ 2026-02-20 10:00:00 │ done        │
│ def456-g...│ H501   │ dryrun │ 50    │ 10 │ 0   │ 2026-02-19 14:00:00 │ done        │
│ ghi789-j...│ A062   │ update │ 200   │ 100│ 0   │ 2026-02-18 09:00:00 │ in progress │
└────────────┴────────┴────────┴───────┴────┴─────┴─────────────────────┴─────────────┘
```

JSON output:
```json
[
  {
    "run_id": "abc123-def456",
    "codcom": "A062",
    "mode": "update",
    "started_at": "2026-02-20 10:00:00",
    "finished_at": "2026-02-20 10:05:00",
    "total_rows": 100,
    "processed": 98,
    "succeeded": 96,
    "failed": 2,
    "db_file": "/Users/user/.anncsu/bulk/A062_abc123-def456.db"
  }
]
```

#### `anncsu coordinate bulk clean`

Remove old bulk DuckDB files from local storage.

```bash
anncsu coordinate bulk clean --older-than 30
anncsu coordinate bulk clean --older-than 30 --dry-run
anncsu coordinate bulk clean --dry-run
anncsu coordinate bulk clean --older-than 7 --json
```

Options:
- `--older-than` - Remove DB files older than N days
- `--dry-run` - Show what would be deleted without actually deleting
- `--json` - Output results as JSON

At least `--older-than` or `--dry-run` must be provided.
When only `--dry-run` is used (without `--older-than`), all DB files are shown.

Output:
```
  Would remove: A062_abc123-def456.db (45.2 KB)
  Would remove: H501_def789-ghi012.db (12.8 KB)

2 file(s) would be removed.
```

JSON output:
```json
{
  "dry_run": true,
  "removed": 0,
  "would_remove": 2,
  "files": [
    {
      "file": "/Users/user/.anncsu/bulk/A062_abc123-def456.db",
      "size_bytes": 46285
    }
  ]
}
```

#### DuckDB Persistence

Bulk operations use DuckDB as a local persistence layer for tracking execution state.
This enables resume after interruption, progress tracking, and report generation.

- **DB location**: `~/.anncsu/bulk/{codcom}_{run_id}.db`
- **Chunking**: Rows are internally divided in chunks of 50,000 via a generated `chunk_id` column
- **Rate limiting**: 50,000 API calls/day tracked in the database
- **Tables**: `bulk_input` (rows + validation), `bulk_results` (API responses), `bulk_runs` (execution metadata), `dryrun_originals` (saved coordinates for restore)

#### DuckDB Schema

```
bulk_input                          bulk_results
├── row_id (PK)                     ├── result_id (PK, auto)
├── run_id                          ├── row_id → bulk_input.row_id
├── codcom                          ├── run_id → bulk_runs.run_id
├── progr_civico                    ├── operation (update/dryrun_update/dryrun_restore)
├── x, y, z, metodo                ├── esito ("0" = success)
├── status (valid/invalid/done/     ├── messaggio
│          processing/error)        ├── id_richiesta
├── validation_error                ├── api_response_json
├── imported_at                     ├── http_status
└── chunk_id (generated)            ├── error_detail
                                    ├── elapsed_ms
bulk_runs                           └── processed_at
├── run_id (PK)
├── codcom                          dryrun_originals
├── csv_path, db_path               ├── row_id (PK)
├── mode (update/dryrun/validate)   ├── run_id
├── started_at, finished_at         ├── progr_civico, codcom
├── total_rows, valid_rows          ├── original_x, original_y
├── invalid_rows                    ├── original_z, original_metodo
├── processed, succeeded, failed    └── saved_at
└── daily_api_calls
```

#### DuckDB Query Examples

You can query DuckDB files directly using the `duckdb` CLI for advanced filtering and analysis that goes beyond the `bulk report` command.

```bash
# Open a bulk run database
duckdb ~/.anncsu/bulk/H501_abc123-def456.db
```

**Find the run ID** (if you don't know it):

```sql
SELECT run_id, codcom, mode, total_rows, succeeded, failed, started_at
FROM bulk_runs;
```

**Records with esito OK (successful updates)**:

```sql
SELECT
    bi.codcom,
    bi.progr_civico,
    bi.x, bi.y, bi.z, bi.metodo,
    br.esito,
    br.messaggio,
    br.id_richiesta,
    br.elapsed_ms
FROM bulk_input bi
JOIN bulk_results br ON bi.row_id = br.row_id AND bi.run_id = br.run_id
WHERE bi.run_id = '<run_id>'
  AND br.esito = '0'
ORDER BY bi.row_id;
```

**Records with errors (esito != 0 or API exceptions)**:

```sql
SELECT
    bi.row_id,
    bi.progr_civico,
    br.esito,
    br.messaggio,
    br.http_status,
    br.error_detail
FROM bulk_input bi
JOIN bulk_results br ON bi.row_id = br.row_id AND bi.run_id = br.run_id
WHERE bi.run_id = '<run_id>'
  AND (br.esito IS NULL OR br.esito != '0')
ORDER BY bi.row_id;
```

**Validation errors (rows rejected before API call)**:

```sql
SELECT row_id, progr_civico, x, y, z, metodo, validation_error
FROM bulk_input
WHERE run_id = '<run_id>' AND status = 'invalid'
ORDER BY row_id;
```

**Timing statistics**:

```sql
SELECT
    COUNT(*) AS total_calls,
    ROUND(AVG(elapsed_ms), 1) AS avg_ms,
    ROUND(MIN(elapsed_ms), 1) AS min_ms,
    ROUND(MAX(elapsed_ms), 1) AS max_ms,
    ROUND(SUM(elapsed_ms) / 1000, 1) AS total_seconds,
    ROUND(AVG(elapsed_ms) * 50000 / 60000, 1) AS estimated_50k_minutes
FROM bulk_results
WHERE run_id = '<run_id>';
```

**Timing distribution (percentiles)**:

```sql
SELECT
    ROUND(PERCENTILE_CONT(0.50) WITHIN GROUP (ORDER BY elapsed_ms), 1) AS p50_ms,
    ROUND(PERCENTILE_CONT(0.90) WITHIN GROUP (ORDER BY elapsed_ms), 1) AS p90_ms,
    ROUND(PERCENTILE_CONT(0.95) WITHIN GROUP (ORDER BY elapsed_ms), 1) AS p95_ms,
    ROUND(PERCENTILE_CONT(0.99) WITHIN GROUP (ORDER BY elapsed_ms), 1) AS p99_ms
FROM bulk_results
WHERE run_id = '<run_id>' AND elapsed_ms IS NOT NULL;
```

**Export only successes to CSV**:

```sql
COPY (
    SELECT bi.codcom, bi.progr_civico, bi.x, bi.y, bi.z, bi.metodo,
           br.id_richiesta, br.elapsed_ms
    FROM bulk_input bi
    JOIN bulk_results br ON bi.row_id = br.row_id AND bi.run_id = br.run_id
    WHERE bi.run_id = '<run_id>' AND br.esito = '0'
    ORDER BY bi.row_id
) TO '/tmp/successful_updates.csv' (HEADER, DELIMITER ',');
```

**Row status summary**:

```sql
SELECT status, COUNT(*) AS count
FROM bulk_input
WHERE run_id = '<run_id>'
GROUP BY status
ORDER BY count DESC;
```

#### Commands That Use ModI (Bulk)

| Command | ModI Headers |
|---------|-------------|
| `anncsu coordinate bulk validate` | No - local validation only |
| `anncsu coordinate bulk update` | Yes - POST requests with payload |
| `anncsu coordinate bulk dry-run` | Yes - POST requests (update + restore) |
| `anncsu coordinate bulk resume` | Yes - POST requests with payload |
| `anncsu coordinate bulk status` | No - local DB query |
| `anncsu coordinate bulk report` | No - local DB query |
| `anncsu coordinate bulk list` | No - local DB query |
| `anncsu coordinate bulk clean` | No - local file operations |

---

### `anncsu pa` - PA Consultazione (Read-Only Queries)

Read-only commands for querying ANNCSU data: search streets, lookup access points, list civici.
These commands use the `APIType.PA` authentication and the consultazione API.

#### `anncsu pa odonimo`

Search streets (odonimi) in a municipality by partial name.

```bash
# Search streets in Scanno (I501)
anncsu pa odonimo --codcom I501 --denom "VklBIFJPTUE="

# Production environment (--production auto-selects the production token endpoint)
anncsu pa odonimo --codcom I501 --denom "VklBIFJPTUE=" --production

# JSON output
anncsu pa odonimo --codcom I501 --denom "VklBIFJPTUE=" --json
```

**Options:**

| Option | Required | Description |
|--------|----------|-------------|
| `--codcom`, `-c` | Yes | Codice Belfiore del comune (e.g. I501 for Scanno) |
| `--denom`, `-d` | Yes | Denominazione parziale dell'odonimo - base64 encoded |
| `--validation/--production` | No | Environment (default: validation) |
| `--token-endpoint`, `-e` | No | PDND token endpoint URL |
| `--server-url`, `-s` | No | API server URL (overrides environment default) |
| `--no-verify-ssl` | No | Disable SSL verification |
| `--json` | No | Output as JSON |
| `--raw` | No | Print raw API response to stderr |

**Output columns:** Prog. Naz., DUG, Denominazione Ufficiale, Denominazione Locale, Lingua 1, Lingua 2

#### `anncsu pa accesso`

Lookup a single access point by its national progressive number. Returns complete detail including street info, civic number, coordinates, and survey method.

```bash
# Lookup access point
anncsu pa accesso --prognazacc 28586543

# Production with JSON output
anncsu pa accesso --prognazacc 28586543 --production --json

# See raw API response on stderr
anncsu pa accesso --prognazacc 28586543 --raw
```

**Options:**

| Option | Required | Description |
|--------|----------|-------------|
| `--prognazacc`, `-p` | Yes | Progressivo nazionale dell'accesso |
| `--validation/--production` | No | Environment (default: validation) |
| `--token-endpoint`, `-e` | No | PDND token endpoint URL |
| `--server-url`, `-s` | No | API server URL (overrides environment default) |
| `--no-verify-ssl` | No | Disable SSL verification |
| `--json` | No | Output as JSON |
| `--raw` | No | Print raw API response to stderr |

**Output fields:** Prog. Naz. Odonimo, DUG, Denominazione Ufficiale, Denominazione Locale, Lingua 1, Lingua 2, Prog. Naz. Accesso, Civico, Esponente, Specificita, Metrico, Coord X, Coord Y, Quota, Metodo

**Note:** The `denomuff` field is now correctly populated via Pydantic alias mapping (`duf` → `denomuff`). See Issue #12.

**JSON output example:**

```json
[
  {
    "prognaz": "1222543",
    "dug": "LARGO",
    "denomuff": "CHIAFFREDO BERGIA",
    "denomloc": "",
    "denomlingua1": "",
    "denomlingua2": "",
    "prognazacc": "28586543",
    "civico": "1",
    "esp": "",
    "specif": "",
    "metrico": "",
    "coordX": "13,8808002",
    "coordY": "41,9030991",
    "quota": "0",
    "metodo": "4"
  }
]
```

#### `anncsu pa accessi`

List access points (civici) for a street. First searches for the street by municipality code and partial name, then lists all access points.

```bash
# List all access points for a street
anncsu pa accessi --codcom I501 --denom "VklBIFJPTUE="

# Filter by partial civic number
anncsu pa accessi --codcom I501 --denom "VklBIFJPTUE=" --accparz "1"

# Production with JSON output
anncsu pa accessi --codcom I501 --denom "VklBIFJPTUE=" --production --json
```

**Options:**

| Option | Required | Description |
|--------|----------|-------------|
| `--codcom`, `-c` | Yes | Codice Belfiore del comune |
| `--denom`, `-d` | Yes | Denominazione parziale dell'odonimo - base64 encoded |
| `--accparz`, `-a` | No | Valore parziale del civico (default: "1") |
| `--validation/--production` | No | Environment (default: validation) |
| `--token-endpoint`, `-e` | No | PDND token endpoint URL |
| `--server-url`, `-s` | No | API server URL (overrides environment default) |
| `--no-verify-ssl` | No | Disable SSL verification |
| `--json` | No | Output as JSON |
| `--raw` | No | Print raw API responses to stderr (odonimo + accessi) |

**Output columns:** Prog. Naz. Acc., Civico, Esp., Specif., Metrico, Coord X, Coord Y, Quota, Metodo

**JSON output example:**

```json
{
  "odonimo": {
    "prognaz": "12345",
    "dug": "VIA",
    "denomuff": "ROMA",
    "denomloc": "",
    "denomlingua1": "",
    "denomlingua2": ""
  },
  "accessi": [
    {
      "prognazacc": "28586543",
      "civico": "1",
      "esp": "",
      "specif": "",
      "metrico": "",
      "coordX": "13.8808",
      "coordY": "41.9031",
      "quota": "",
      "metodo": "4"
    }
  ]
}
```

---

### `anncsu accesso` - Accesso CRUD

CRUD operations on ANNCSU access points (civici). Three sub-commands map 1:1 to the `operazione_civico` field of the POST `/accessi` endpoint:

| Sub-command | `operazione_civico` | Purpose |
|---|---|---|
| `insert` | `I` | Create a new accesso |
| `update` | `R` | Replace/update an existing accesso |
| `delete` | `S` | Soppressione (logical delete) |

Plus `status` for the GET `/status` health check.

> **ModI headers required**: All write operations (`insert`/`update`/`delete`) require `Agid-JWT-Signature` (INTEGRITY_REST_02) and `Agid-JWT-TrackingEvidence` (AUDIT_REST_02). They are added automatically by the ModI pre-request hook when `PDND_MODI_*` variables are configured. See the [ModI Headers](#modi-headers-coordinate-api) section below.

> **Validation rules**: Inputs are pre-validated by `ValidatedAccesso` before the API call. Common rules:
> - `operazione_civico` must be `I`, `R`, or `S`
> - `progr_civico` is required for `R` and `S`, optional for `I`
> - `numero` and `metrico` are mutually exclusive: exactly one is required for `I`/`R`
> - For `S`, fields like `numero`, `metrico`, `esponente`, `specificita`, `sezione_censimento`, `isolato`, `coordinate` are not allowed (and not exposed in the `delete` signature)

#### `anncsu accesso insert`

Insert a new accesso (`operazione_civico='I'`). Exactly one of `--numero` or `--metrico` must be provided.

```bash
# Civico-numbered accesso
anncsu accesso insert --codcom A062 --prognaz 2000449 --numero 12

# With esponente and coordinates
anncsu accesso insert --codcom A062 --prognaz 2000449 \
    --numero 12 --esponente A --sezione-censimento 9 \
    --coord-x 13.1022000 --coord-y 41.8847600 --metodo 3

# Metrico (non-civico-numbered) accesso
anncsu accesso insert --codcom A062 --prognaz 2000449 --metrico 300
```

Options:
- `--codcom, -c` - Codice comune (Belfiore code) **[required]**
- `--prognaz, -p` - Progressivo nazionale dell'odonimo **[required]**
- `--numero, -n` - Numero civico (mutually exclusive with `--metrico`)
- `--metrico, -M` - Metrico (mutually exclusive with `--numero`)
- `--esponente` - Esponente (e.g. `A`, `BIS`)
- `--specificita` - Specificita (e.g. `ROSSO`)
- `--sezione-censimento` - Sezione di censimento
- `--isolato` - Codice isolato (facoltativo)
- `--codice-civico-comunale` - Codifica comunale dell'accesso
- `--coord-x` / `--coord-y` / `--coord-z` - Coordinate (longitudine, latitudine, quota)
- `--metodo, -m` - Metodo di rilevazione (1-4)
- `--data-valid-amm` - Data inizio validità amministrativa (formato `dd/MM/yyyy`)
- `--token-endpoint, -e` - PDND token endpoint URL
- `--server-url, -s` - API server URL (auto-discovered from voucher if omitted)
- `--validation/--production` - Use validation (UAT) or production environment
- `--no-verify-ssl` - Disable SSL certificate verification
- `--json` - Output as JSON
- `--raw` - Print raw API response to stderr

JSON output:
```json
{
  "success": true,
  "operazione_civico": "I",
  "id_richiesta": "5144",
  "esito": "0",
  "messaggio": "OK",
  "dati_count": 1
}
```

#### `anncsu accesso update`

Update/replace an existing accesso (`operazione_civico='R'`). Requires `--progr-civico` to identify the target. Exactly one of `--numero` or `--metrico` must be provided.

```bash
# Replace coordinates of an existing accesso
anncsu accesso update --codcom A062 --prognaz 2000449 \
    --progr-civico 1370588 --numero 12 \
    --coord-x 13.1022001 --coord-y 41.8847601 --metodo 3
```

Options (additional to `insert` ones):
- `--progr-civico, -P` - Progressivo civico of the accesso to update **[required]**

JSON output:
```json
{
  "success": true,
  "operazione_civico": "R",
  "id_richiesta": "5145",
  "esito": "0",
  "messaggio": "OK",
  "dati_count": 1
}
```

#### `anncsu accesso delete`

Soppressione (logical delete) of an accesso (`operazione_civico='S'`).

```bash
# Minimal delete (data_valid_amm defaults to today)
anncsu accesso delete --codcom A062 --prognaz 2000449 --progr-civico 1370588

# With explicit end-of-validity date
anncsu accesso delete --codcom A062 --prognaz 2000449 \
    --progr-civico 1370588 --data-valid-amm 31/12/2025
```

Options:
- `--codcom, -c` - Codice comune **[required]**
- `--prognaz, -p` - Progressivo nazionale dell'odonimo **[required]**
- `--progr-civico, -P` - Progressivo civico of the accesso to delete **[required]**
- `--data-valid-amm` - Data **fine** validità amministrativa (formato `dd/MM/yyyy`). Defaults to today if omitted.
- `--token-endpoint, -e` / `--server-url, -s` / `--validation/--production` / `--no-verify-ssl` / `--json` / `--raw` - same as `insert`

> **Note**: `delete` does NOT accept `--numero`, `--metrico`, `--esponente`, `--specificita`, `--sezione-censimento`, `--isolato`, `--coord-*`, or `--metodo` — Typer rejects them at parse time as unknown options because they have no meaning for a deletion.

JSON output:
```json
{
  "success": true,
  "operazione_civico": "S",
  "id_richiesta": "5146",
  "esito": "0",
  "messaggio": "OK",
  "dati_count": 0
}
```

#### `anncsu accesso status`

Check the status of the Accessi API service:

```bash
anncsu accesso status
anncsu accesso status --production
anncsu accesso status --json
```

Output:
```
Accessi API Status — Validation (UAT)

┌─────────────────────────────────────────┐
│ Field        │ Value                    │
├─────────────────────────────────────────┤
│ Status       │ OK (OK)                  │
│ Environment  │ validation               │
│ Server URL   │ https://modipa-val…      │
└─────────────────────────────────────────┘
```

JSON output:
```json
{
  "available": true,
  "status": "OK",
  "server_url": "https://modipa-val.agenziaentrate.it/govway/rest/in/AgenziaEntrate/anncsuaccessi/v1",
  "environment": "validation"
}
```

#### `anncsu accesso *` — `--dry-run` flag

All three write commands (`insert`, `update`, `delete`) accept `--dry-run` to execute a test cycle that automatically rolls back, useful for verifying authentication, ModI configuration, and end-to-end connectivity without persisting changes.

**Rollback flow per operation**:

| Command | Test op | Rollback | Caveats |
|---|---|---|---|
| `insert --dry-run` | `I` (insert) | `S` on the assigned `progr_civico` | ✅ Clean: the temporary accesso is fully removed |
| `update --dry-run` | `R` with new values | `R` with original values (read via PA API) | ⚠️ Pre-check: aborts if originals have null fields (legacy data); see below |
| `delete --dry-run` | `S` (soppressione) | `I` rebuilt from original values | ⚠️ Re-inserted accesso has a **new `progr_civico`** (ANNCSU assigns it autonomously — cannot be forced to the old one) |

**Crash safety**: before the rollback API call, a JSON file is written to `~/.anncsu/dryrun_pending.json` containing all data needed to manually clean up if the CLI crashes between test op and rollback.

**Pre-check for `update --dry-run`** (legacy ANNCSU data):
The CLI fetches the original accesso fields via PA API before issuing any write. If a required field (currently `metodo`) is null on the originals — common for legacy data uploaded before validation rules were tightened — the dry-run **aborts before any write**, with a clear error message. This guarantees that an `update --dry-run` is never partially destructive.

Examples:

```bash
# Insert dry-run — creates an accesso, then immediately deletes it
anncsu accesso insert --codcom A062 --prognaz 2000449 --numero 12 --dry-run

# Update dry-run — applies new coordinates, then restores originals
anncsu accesso update --codcom A062 --prognaz 2000449 \
    --progr-civico 1370588 --numero 12 \
    --coord-x 13.10 --coord-y 41.88 --metodo 3 --dry-run

# Delete dry-run — soppresses, then re-inserts with original data
anncsu accesso delete --codcom A062 --prognaz 2000449 \
    --progr-civico 1370588 --dry-run
```

JSON output of `--dry-run` (any command):

```json
{
  "success": true,
  "operazione_civico": "I",
  "test_op": {
    "success": true,
    "operazione_civico": "I",
    "id_richiesta": "REQ-001",
    "esito": "0",
    "messaggio": "OK",
    "dati_count": 1
  },
  "rollback": {
    "success": true,
    "operazione_civico": "S",
    "id_richiesta": "REQ-002",
    "esito": "0",
    "messaggio": "OK",
    "dati_count": 0
  },
  "rollback_failed": false,
  "rollback_progr_civico_changed": false,
  "pending_log_path": "/Users/me/.anncsu/dryrun_pending.json",
  "error_message": null
}
```

For `delete --dry-run` specifically, `rollback_progr_civico_changed` will be `true` when ANNCSU assigns a different `progr_civico` to the re-inserted accesso (always, in practice, since the spec does not allow forcing the old identifier).

##### Recovery from a pending log

If the CLI crashes between the test op and the rollback, the file `~/.anncsu/dryrun_pending.json` is left behind containing every detail needed for manual cleanup. Example content for a crashed `insert --dry-run`:

```json
{
  "timestamp": "2026-05-19T10:34:21.123456+00:00",
  "operazione": "S",
  "payload": {
    "codcom": "A062",
    "progr_nazionale": "2000449",
    "progr_civico": "9999999",
    "originating_test_op": "I"
  },
  "note": "Insert dry-run pending rollback. If you see this file, the CLI crashed between insert and delete — manually run `anncsu accesso delete --codcom A062 --prognaz 2000449 --progr-civico 9999999`.",
  "pid": 12345
}
```

The `note` field always contains the exact command to run for cleanup. Possible scenarios per dry-run type:

| Operation | What was done | Manual cleanup command |
|---|---|---|
| `insert --dry-run` crashed after I | An accesso was created but not deleted | `anncsu accesso delete --codcom X --prognaz Y --progr-civico <from payload>` |
| `update --dry-run` crashed after first R | New values are live; originals saved in payload | `anncsu accesso update --codcom X --prognaz Y --progr-civico Z --numero <original> --metodo <original> ...` |
| `delete --dry-run` crashed after S | Accesso is deleted, re-insert never happened | `anncsu accesso insert --codcom X --prognaz Y --numero <original> --metodo <original> ...` (note: the new accesso will have a different progr_civico) |

After resolving the issue, **delete the pending file** manually so it doesn't shadow future dry-runs:

```bash
rm ~/.anncsu/dryrun_pending.json
```

There is no automatic recovery command yet — the design intentionally keeps recovery a manual, deliberate operation to avoid hidden state mutations.

#### `anncsu accesso update/delete` — `--auto-resolve` flag

`update` and `delete` both require `--progr-civico` to identify the target accesso. As an alternative, pass `--auto-resolve` together with `--civico` to have the CLI look up the `progr_civico` automatically via PA API.

```bash
# Delete via auto-resolve (no need to know progr_civico in advance)
anncsu accesso delete --codcom A062 --prognaz 2000449 \
    --auto-resolve --civico 12

# Update via auto-resolve
anncsu accesso update --codcom A062 --prognaz 2000449 \
    --auto-resolve --civico 12 --metodo 3
```

Errors:
- `--auto-resolve` without `--civico` → error (lookup needs the civico number)
- PA lookup returns 0 matches → error (no accesso found)
- PA lookup returns >1 matches → error (ambiguous, specify `--progr-civico` directly)

The default (without `--auto-resolve`) remains `--progr-civico` explicit — safer for scripting and CI/CD, where you typically already know the identifier.

---

### `anncsu odonimo` - Odonimo CRUD

CRUD operations on ANNCSU street names (odonimi). Three sub-commands map 1:1 to the `tipo_operazione` field of the POST `/odonimi` endpoint:

| Sub-command | `tipo_operazione` | Purpose |
|---|---|---|
| `insert` | `I` | Create a new odonimo |
| `update` | `R` | Replace/update an existing odonimo |
| `delete` | `S` | Soppressione (logical delete) |

Plus `status` for the GET `/status` health check.

> **ModI headers required**: All write operations require `Agid-JWT-Signature` (INTEGRITY_REST_02) and `Agid-JWT-TrackingEvidence` (AUDIT_REST_02). They are added automatically by the ModI pre-request hook when `PDND_MODI_*` variables are configured.

> **Validation rules**: Inputs are pre-validated by `ValidatedOdonimo` before the API call. Common rules:
>
> - `tipo_operazione` must be `I`, `R`, or `S` (enum)
> - `codcom` is required for every operation
> - `progr_nazionale` is required for `R`/`S` (assigned by ANNCSU for `I`)
> - `dug` is required for `I`/`R`, **not allowed for `S`**
> - If `provvedimento.flag_delibera ∈ {0, 1}`, `provvedimento.data` and `provvedimento.protocollo` are required
> - `aut_prefettura.data_pref` ↔ `aut_prefettura.protocollo_pref` are mutually required (both or neither)
> - maxLength enforced on every string field (per OAS spec; e.g. `denom_localita` has the OAS quirk `maxLength: 151` preserved as-is)

#### `anncsu odonimo insert`

Insert a new odonimo (`tipo_operazione='I'`). `--codcom` and `--dug` are required; `--prognaz` is assigned by ANNCSU.

```bash
# Minimal insert
anncsu odonimo insert --codcom A062 --dug VIA --denom-delibera "DELLE ORCHIDEE"

# With provvedimento (flag_delibera=1 requires data + protocollo)
anncsu odonimo insert --codcom A062 --dug VIA --denom-delibera "DEI TIGLI" \
    --provv-data 10/10/2023 --provv-protocollo "1234567/abc" \
    --provv-flag-delibera 1

# Full insert with aut_prefettura + multilingua
anncsu odonimo insert --codcom A062 --dug VIA \
    --denom-delibera "DELLE ORCHIDEE" \
    --denom-in-lingua-1 "STRASSE DER ORCHIDEEN" \
    --denom-localita "CASAL PALOCCO" \
    --provv-data 10/10/2023 --provv-protocollo "1234/abc" \
    --provv-flag-delibera 1 \
    --prefettura-data 11/10/2023 \
    --prefettura-protocollo "Prot.Gen.1234567" \
    --data-valid-amm 08/10/2024
```

Options:

- `--codcom, -c` - Codice comune (Belfiore code, e.g. `A062`) **[required]**
- `--dug` - DUG (e.g. `VIA`, `PIAZZA`, `STRADA`) **[required for I/R]**
- `--denom-delibera` - Denominazione delibera (uppercase applied server-side)
- `--denom-in-lingua-1` / `--denom-in-lingua-2` - Odonimo in lingua (per comuni bi/tri-lingua)
- `--denom-localita` - Denominazione località (uppercase applied)
- `--codice-comunale` - Codifica comunale dell'odonimo (no uppercase)
- `--provv-data` - Data del provvedimento (formato `dd/MM/yyyy`)
- `--provv-protocollo` - Protocollo del provvedimento (max 70 char, no uppercase)
- `--provv-flag-delibera` - Flag delibera (`0`-`4`); `0` and `1` make `--provv-data` + `--provv-protocollo` required
- `--prefettura-data` - Data prefettura (required if `--prefettura-protocollo`)
- `--prefettura-protocollo` - Protocollo prefettura (required if `--prefettura-data`)
- `--data-valid-amm` - Data validità amministrativa (formato `dd/MM/yyyy`)
- `--token-endpoint, -e` - PDND token endpoint URL
- `--server-url, -s` - API server URL (auto-discovered from voucher if omitted)
- `--validation/--production` - Use validation (UAT) or production environment
- `--no-verify-ssl` - Disable SSL certificate verification
- `--json` - Output as JSON
- `--raw` - Print raw API response to stderr
- `--dry-run` - I + S rollback (see `--dry-run` section below)

JSON output:

```json
{
  "success": true,
  "tipo_operazione": "I",
  "id_richiesta": "5145",
  "esito": "0",
  "messaggio": "OK",
  "dati_count": 1
}
```

#### `anncsu odonimo update`

Update/replace an existing odonimo (`tipo_operazione='R'`). Requires `--prognaz` (or `--auto-resolve` + `--denom`) and `--dug`.

```bash
# Replace denomination of an existing odonimo
anncsu odonimo update --codcom A062 --prognaz 2000449 \
    --dug VIA --denom-delibera "DEI TIGLI"

# Update with auto-resolve (lookup prognaz via PA from base64 denom)
anncsu odonimo update --codcom A062 \
    --auto-resolve --denom "VklBIERFTEwgT1JDSElERUU=" \
    --dug VIA --denom-delibera "DEI TIGLI NUOVI"
```

Options:

- All `insert` options (except `--prognaz` is required, not assigned)
- `--prognaz, -p` - Progressivo nazionale dell'odonimo (required unless `--auto-resolve`)
- `--auto-resolve` - Resolve `--prognaz` via PA from `--codcom` + `--denom` (see `--auto-resolve` section)
- `--denom` - Base64-encoded denomination used with `--auto-resolve`

#### `anncsu odonimo delete`

Soppressione (logical delete) of an odonimo (`tipo_operazione='S'`).

```bash
# Minimal delete (data_valid_amm defaults to today)
anncsu odonimo delete --codcom A062 --prognaz 2000449

# With explicit end-of-validity date
anncsu odonimo delete --codcom A062 --prognaz 2000449 \
    --data-valid-amm 31/12/2025

# Delete via auto-resolve
anncsu odonimo delete --codcom A062 \
    --auto-resolve --denom "VklBIERFTEwgT1JDSElERUU="
```

Options:

- `--codcom, -c` - Codice comune **[required]**
- `--prognaz, -p` - Progressivo nazionale (required unless `--auto-resolve`)
- `--auto-resolve` / `--denom` - Same as `update`
- `--data-valid-amm` - Data **fine** validità amministrativa (formato `dd/MM/yyyy`)
- Other shared options (`--token-endpoint`, `--server-url`, `--validation/--production`, `--no-verify-ssl`, `--json`, `--raw`, `--dry-run`)

> **Note**: `delete` does NOT accept `--dug`, `--denom-*`, `--codice-comunale`, `--provv-*`, or `--prefettura-*` — Typer rejects them at parse time as unknown options because they have no meaning for a soppressione.

> **Note on the S response shape**: the server response for a soppressione **does not** carry `esito` (it is `null`). The CLI infers success from the presence of `data_FINE` and `data_fine_valid_amm` in the `dati` payload — those mark the closure timestamp of the odonimo. When the CLI shows `Operation 'S' successful!`, this is the path that was taken. The behaviour is identical between the real `delete` and `delete --dry-run` since both call the same `_build_result` helper.

#### `anncsu odonimo status`

Check the status of the Odonimi API service:

```bash
anncsu odonimo status
anncsu odonimo status --production
anncsu odonimo status --json
```

#### `anncsu odonimo *` — `--dry-run` flag

All three write commands accept `--dry-run` to execute a full CRUD cycle on a **fictitious odonimo** (generated automatically) so real data is never touched.

Unlike `accesso --dry-run` (which operates on an existing accesso via test+restore), `odonimo --dry-run` **always creates and deletes a temporary odonimo** with a recognizable `TEST SDK <timestamp>-<uuid>` denomination.

| Command | Cycle | API calls |
|---|---|---|
| `insert --dry-run` | I (user data) → S (rollback) | 2 |
| `update --dry-run` | I (fake denom) → R (user data on fake) → S (cleanup) | 3 |
| `delete --dry-run` | I (fake denom) → S (immediate) | 2 |

**Fictitious odonimo details**:

- `denom_delibera = "TEST SDK <YYYYMMDDHHMMSS>-<short-uuid>"`
- `dug = "VIA"` (fixed)
- `codcom` = whichever value the user passes
- Easily identifiable in audit logs for manual cleanup if a crash occurs

**Crash safety**: before any rollback API call, a JSON file is written to `~/.anncsu/dryrun_pending.json` with all data needed for manual cleanup if the CLI crashes between steps.

**For `update --dry-run`**: `--prognaz` and `--auto-resolve` are ignored (a warning is printed) because the R is always applied to the fake odonimo generated by the preceding I.

Examples:

```bash
# Insert dry-run — creates the odonimo with user data, then deletes it
anncsu odonimo insert --codcom A062 --dug VIA \
    --denom-delibera "DELLE ORCHIDEE" --dry-run

# Update dry-run — fake I → user R on fake → cleanup S
anncsu odonimo update --codcom A062 --dug VIA \
    --denom-delibera "DEI TIGLI" --dry-run

# Delete dry-run — fake I → immediate S (smoke-test del flusso S)
anncsu odonimo delete --codcom A062 --dry-run
```

JSON output of `--dry-run` (delete example):

```json
{
  "success": true,
  "tipo_operazione": "S",
  "fake_denom": "TEST SDK 20260524150301-3f8a1b2c",
  "fake_prognaz": "9999999",
  "test_op": {
    "success": true,
    "tipo_operazione": "I",
    "id_richiesta": "REQ-I",
    "esito": "0",
    "messaggio": "OK",
    "dati_count": 1
  },
  "update_op": null,
  "rollback": {
    "success": true,
    "tipo_operazione": "S",
    "id_richiesta": "REQ-S",
    "esito": null,
    "messaggio": null,
    "dati_count": 1
  },
  "rollback_failed": false,
  "pending_log_path": "/Users/me/.anncsu/dryrun_pending.json",
  "error_message": null
}
```

> **Note on `esito` for S operations**: the server response for S (delete/cleanup) does **not** carry `esito` (it is `null`). Success is detected by the presence of `data_FINE` / `data_fine_valid_amm` in the `dati` payload, which mark the closure timestamp of the odonimo. The CLI maps this into `"success": true` even though `esito` stays `null` — this is by design.

For `update --dry-run`, the `update_op` field is populated (R step), and `tipo_operazione` is `"R"`.

##### Recovery from a pending log

If the CLI crashes between the I step and the rollback S, `~/.anncsu/dryrun_pending.json` contains:

```json
{
  "timestamp": "2026-05-24T15:03:01.123456+00:00",
  "tipo_operazione": "I_then_S",
  "payload": {
    "codcom": "A062",
    "fake_prognaz": "9999999",
    "fake_denom": "TEST SDK 20260524150301-3f8a1b2c"
  },
  "note": "Created an odonimo via I; about to delete via S to roll back. If the CLI crashed before deletion, run `anncsu odonimo delete --codcom A062 --prognaz 9999999` manually.",
  "pid": 12345
}
```

Manual cleanup:

```bash
anncsu odonimo delete --codcom A062 --prognaz 9999999
rm ~/.anncsu/dryrun_pending.json
```

#### `anncsu odonimo update/delete` — `--auto-resolve` flag

`update` and `delete` both require `--prognaz` to identify the target odonimo. As an alternative, pass `--auto-resolve` together with `--denom` (base64-encoded denomination) to have the CLI look up the `prognaz` automatically via PA API.

```bash
# Encode denomination to base64 (full street name including dug)
echo -n "VIA DELLE ORCHIDEE" | base64
# VklBIERFTExFIE9SQ0hJREVF

# Update via auto-resolve
anncsu odonimo update --codcom A062 \
    --auto-resolve --denom "VklBIERFTExFIE9SQ0hJREVF" \
    --dug VIA --denom-delibera "DEI TIGLI"

# Delete via auto-resolve
anncsu odonimo delete --codcom A062 \
    --auto-resolve --denom "VklBIERFTExFIE9SQ0hJREVF"
```

Errors:

- `--auto-resolve` without `--denom` → error (lookup needs the base64 denomination)
- PA lookup returns 0 matches → error (no odonimo found)
- PA lookup returns >1 matches → error (ambiguous, specify `--prognaz` directly)
- If both `--prognaz` and `--auto-resolve` are provided → `--prognaz` is ignored with a warning

The default (without `--auto-resolve`) remains `--prognaz` explicit — safer for scripting and CI/CD where you typically already know the identifier.

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

## API Environments and GovWay Paths

The ANNCSU APIs are exposed through the GovWay gateway on two environments. Each API type has its own e-service path on GovWay, and the PDND token `aud` claim must match the e-service URL.

### Environments

| Environment | Token Endpoint | GovWay Base URL |
|-------------|---------------|-----------------|
| UAT (Validation) | `https://auth.uat.interop.pagopa.it/token.oauth2` | `https://modipa-val.agenziaentrate.it/govway/rest/in` |
| Production | `https://auth.interop.pagopa.it/token.oauth2` | `https://modipa.agenziaentrate.gov.it/govway/rest/in` |

> **Note on `--token-endpoint`**: every CLI command that supports `--validation/--production` picks the token endpoint automatically based on that flag if `--token-endpoint` is omitted. You can still pass `--token-endpoint` explicitly — the CLI then validates that it matches the selected environment and exits with an error if it does not (preventing the silent `015-0008 Unable to generate a token` failure when the two diverge).

### API Types and GovWay Paths

Each API type corresponds to a distinct PDND e-service with its own GovWay path and purpose ID:

| API Type | GovWay Path | Purpose ID Env Var | CLI Flag |
|----------|------------|-------------------|----------|
| PA Consultazione (read) | `AgenziaEntrate-PDND/anncsu-consultazione/v1` | `PDND_PURPOSE_ID_PA` | N/A (used internally for lookups) |
| Coordinate singolo (write) | `AgenziaEntrate-PDND/anncsu-aggiornamento-coordinate/v1` | `PDND_PURPOSE_ID_COORDINATE` | `--validation`/`--production` |
| Coordinate Bulk grandi comuni (write) | `AgenziaEntrate-PDND/anncsu-aggiornamento-coordinate-grandi-comuni/v1` | `PDND_PURPOSE_ID_COORDINATE_BULK` | `--validation`/`--production` |

> **Important**: The bulk coordinate API uses a **different e-service** (`anncsu-aggiornamento-coordinate-grandi-comuni`) than the single coordinate update (`anncsu-aggiornamento-coordinate`). Each requires its own purpose ID activated on the PDND portal.

### Token Caching and Sessions

The CLI caches PDND tokens per API type in separate session files under `~/.anncsu/`:

| API Type | Session File |
|----------|-------------|
| PA Consultazione | `session_pa.json` |
| Coordinate (single) | `session_coordinate.json` |
| Coordinate (bulk) | `session_coordinate_bulk.json` |

Each session file contains the JWT access token obtained with the purpose ID specific to that API. Tokens are automatically refreshed when expired.

To force re-authentication for a specific API type, delete its session file:

```bash
rm ~/.anncsu/session_coordinate_bulk.json
```

### Troubleshooting API Errors

| HTTP Status | Error | Likely Cause | Solution |
|-------------|-------|-------------|----------|
| 403 | `Insufficient token claims` | Wrong purpose ID or token cached with wrong purpose | Delete the session file for the API type and re-run |
| 404 | `Unknown API Request` | Wrong GovWay path (e-service URL mismatch) | Verify the server URL matches the e-service path |
| 400 | Validation errors (e.g., `metodo obbligatorio`) | Invalid input data | Check coordinate values and required fields |

### Verifying Token Claims

To check which e-service a cached token targets, decode the JWT payload:

```bash
# Extract and decode the access_token payload from a session file
cat ~/.anncsu/session_coordinate_bulk.json | python3 -c "
import json, sys, base64
token = json.load(sys.stdin)['access_token']
payload = token.split('.')[1]
payload += '=' * (4 - len(payload) % 4)
print(json.dumps(json.loads(base64.urlsafe_b64decode(payload)), indent=2))
" | grep aud
```

The `aud` claim should match the full GovWay URL for the API type being used.

---

## ModI Headers (Coordinate and Accessi APIs)

The Coordinate and Accessi APIs require ModI (Modello di Interoperabilità) security headers in addition to the standard bearer token. These headers implement the AGID interoperability patterns:

- **INTEGRITY_REST_02**: Integrity of REST message payload in PDND
- **AUDIT_REST_02**: Forwarding of tracked data in the Consumer domain

### Configuration

To enable ModI headers, add these environment variables to your `.env`:

| Variable | Required | Description |
|----------|----------|-------------|
| `MODI_USER_ID` | Yes* | User identifier in the consumer domain |
| `MODI_USER_LOCATION` | Yes* | Workstation/system identifier from which the request originates |
| `MODI_LOA` | Yes* | Level of Assurance in the authentication process |

*Required for POST requests on Coordinate and Accessi APIs. If not configured, ModI headers will not be sent (API calls may be rejected by GovWay).

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
| `anncsu accesso insert` | ✅ Yes - POST request with payload |
| `anncsu accesso update` | ✅ Yes - POST request with payload |
| `anncsu accesso delete` | ✅ Yes - POST request with payload |
| `anncsu accesso status` | ❌ No - GET request, no payload |
| `anncsu auth curl --api coordinate` | ✅ Yes - Generates cURL with ModI headers |
| `anncsu auth curl --api pa` | ❌ No - GET request, Bearer only |
| `anncsu auth *` (other) | ❌ No - Authentication only |
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

The CLI automatically persists authentication tokens between sessions. Each API type has its own session file under `~/.anncsu/`.

### Session Files per API Type

| API Type | Session File |
|----------|-------------|
| PA Consultazione | `~/.anncsu/session_pa.json` |
| Coordinate (single) | `~/.anncsu/session_coordinate.json` |
| Coordinate (bulk) | `~/.anncsu/session_coordinate_bulk.json` |

Each session file contains the JWT access token obtained with the purpose ID specific to that API. Tokens are automatically refreshed when expired.

### Session File Format

```json
{
  "client_assertion": "eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCIsImtpZCI6Ii4uLiJ9...",
  "access_token": "eyJhbGciOiJSUzI1NiIsInR5cCI6ImF0K2p3dCJ9...",
  "token_endpoint": "https://auth.uat.interop.pagopa.it/token.oauth2"
}
```

### How It Works

1. **Login** (`anncsu auth login --api pa`): Saves tokens to API-specific session file
2. **Status** (`anncsu auth status --api pa`): Loads and displays tokens from session
3. **Token** (`anncsu auth token --api pa`): Loads token, auto-refreshes if expired
4. **Logout** (`anncsu auth logout --api pa`): Deletes session file for that API type
5. **Coordinate commands**: Automatically manage their own session files (PA for lookups, coordinate/coordinate_bulk for writes)

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
anncsu auth login --api pa --token-endpoint https://auth.uat.interop.pagopa.it/token.oauth2

# PROD environment - creates new session (different endpoint)
anncsu auth login --api pa --token-endpoint https://auth.interop.pagopa.it/token.oauth2
```

### Clear Session

To remove cached tokens for a specific API type:

```bash
anncsu auth logout --api pa
anncsu auth logout --api coordinate
anncsu auth logout --api coordinate_bulk
```

Or delete session files directly:

```bash
rm ~/.anncsu/session_pa.json
rm ~/.anncsu/session_coordinate_bulk.json
```

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

# Login for PA Consultazione API
anncsu auth login --api pa || exit 1

# Get token for API calls
TOKEN=$(anncsu auth token --api pa)

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
    PDND_PURPOSE_ID_COORDINATE_BULK: ${{ secrets.PDND_PURPOSE_ID_COORDINATE_BULK }}
    PDND_PURPOSE_ID_ACCESSI: ${{ secrets.PDND_PURPOSE_ID_ACCESSI }}
    PDND_PURPOSE_ID_INTERNI: ""
    PDND_PURPOSE_ID_ODONIMI: ""
    PDND_PRIVATE_KEY: ${{ secrets.PDND_PRIVATE_KEY }}
    PDND_TOKEN_ENDPOINT: ${{ secrets.PDND_TOKEN_ENDPOINT }}
  run: |
    anncsu auth login --api pa
    anncsu auth status --api pa
```

---

## See Also

- [Security Documentation](./SECURITY.md) - PDND authentication details
- [SDK Usage](../README.md) - Programmatic SDK usage
- [PDNDAuthManager](./conversation_log.md#session-19) - Authentication manager internals
