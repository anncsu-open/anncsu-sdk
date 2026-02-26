# SDK Coordinate

SDK per l'API ANNCSU Aggiornamento Coordinate degli Accessi.

Questa API richiede header ModI aggiuntivi (pattern INTEGRITY_REST_02 e AUDIT_REST_02).

> **Nota sulla terminologia**: L'identificatore di un accesso (civico) è chiamato `prognazacc` (progressivo nazionale accesso) nell'API PA Consultazione e `progr_civico` nell'API Coordinate. **Rappresentano lo stesso valore** - l'identificatore progressivo nazionale univoco di un punto di accesso.

## Installazione

```bash
pip install anncsu
# oppure
uv add anncsu
```

## Quick Start con ModI Headers

L'API Coordinate richiede header ModI. Usa la dependency injection per configurare l'hook.

```python
from anncsu.common.hooks import SDKHooks, register_modi_hook
from anncsu.common.modi import ModIConfig, AuditContext
from anncsu.coordinate import AnncsuCoordinate
from anncsu.coordinate.models import Security

# 1. Carica la chiave privata (stessa usata per PDND)
with open("/path/to/private_key.pem", "rb") as f:
    private_key = f.read()

# 2. Configura ModI
modi_config = ModIConfig(
    private_key=private_key,
    kid="your-pdnd-kid",
    issuer="your-client-id",
    audience="https://modipa-val.agenziaentrate.it/govway/rest/in/AE/ANNCSU/v1",
)

audit_context = AuditContext(
    user_id="batch-user-001",
    user_location="server-01",
    loa="SPID_L2",
)

# 3. Crea hooks con ModI
hooks = SDKHooks()
register_modi_hook(hooks, config=modi_config, audit_context=audit_context)

# 4. Inietta hooks nell'SDK
sdk = AnncsuCoordinate(
    security=Security(bearer_auth="your-access-token"),
    server_url="https://modipa-val.agenziaentrate.it/govway/rest/in/AE/ANNCSU/v1",
    hooks=hooks,  # <-- Dependency Injection
)

# 5. Usa SDK - gli header ModI vengono aggiunti automaticamente
result = sdk.json_post.gestionecoordinate(
    richiesta_operazione=request_data
)
```

## Header ModI Generati Automaticamente

Quando l'hook ModI è registrato, tutte le richieste POST/PUT/PATCH includeranno automaticamente:

| Header | Pattern | Descrizione |
|--------|---------|-------------|
| `Digest` | RFC 3230 | Hash SHA-256 del body HTTP: `SHA-256=<base64>` |
| `Agid-JWT-Signature` | INTEGRITY_REST_02 | JWT con digest nel claim `signed_headers` |
| `Agid-JWT-TrackingEvidence` | AUDIT_REST_02 | JWT con claim di audit (`userID`, `userLocation`, `LoA`) |

### Struttura Agid-JWT-Signature

```json
// Header
{
  "alg": "RS256",
  "typ": "JWT",
  "kid": "your-pdnd-kid"
}

// Payload
{
  "iss": "your-client-id",
  "aud": "https://modipa-val.agenziaentrate.it/...",
  "iat": 1706284800,
  "nbf": 1706284800,
  "exp": 1706285100,
  "jti": "unique-uuid",
  "signed_headers": [
    {"digest": "SHA-256=abc123..."},
    {"content-type": "application/json"}
  ]
}
```

### Struttura Agid-JWT-TrackingEvidence

```json
// Payload
{
  "iss": "your-client-id",
  "aud": "https://modipa-val.agenziaentrate.it/...",
  "iat": 1706284800,
  "nbf": 1706284800,
  "exp": 1706285100,
  "jti": "unique-uuid",
  "userID": "batch-user-001",
  "userLocation": "server-01",
  "LoA": "SPID_L2"
}
```

## Dependency Injection Pattern

L'SDK usa il pattern **Dependency Injection** tramite il Protocol `HooksProvider`:

```python
from anncsu.common.hooks import HooksProvider, SDKHooks

# SDKHooks implementa HooksProvider
hooks: HooksProvider = SDKHooks()

# Verifica a runtime
assert isinstance(hooks, HooksProvider)

# Inietta nell'SDK
sdk = AnncsuCoordinate(
    security=...,
    hooks=hooks,  # Optional[HooksProvider]
)
```

### Vantaggi

1. **Testabilità**: Puoi iniettare mock hooks nei test
2. **Flessibilità**: Configura hooks diversi per ambienti diversi
3. **Separazione**: La logica ModI è separata dalla logica SDK
4. **Backward compatibility**: Se non passi `hooks`, viene creato un default

## Senza Audit Context

Se non hai bisogno di AUDIT_REST_02 (tracking), puoi omettere l'audit context:

```python
hooks = SDKHooks()
register_modi_hook(hooks, config=modi_config)  # Senza audit_context

# Solo Digest e Agid-JWT-Signature verranno aggiunti
sdk = AnncsuCoordinate(
    security=Security(bearer_auth="your-token"),
    hooks=hooks,
)
```

## Autenticazione Completa

Esempio completo con autenticazione PDND e ModI:

```python
from anncsu.common.auth import PDNDAuthManager
from anncsu.common.config import ClientAssertionSettings, APIType
from anncsu.common.hooks import SDKHooks, register_modi_hook
from anncsu.common.modi import ModIConfig, AuditContext
from anncsu.coordinate import AnncsuCoordinate
from anncsu.coordinate.models import Security, RichiestaOperazione

# 1. Carica configurazione
settings = ClientAssertionSettings()

# 2. Ottieni access token per API Coordinate
auth_manager = PDNDAuthManager(
    settings=settings,
    api_type=APIType.COORDINATE,
    token_endpoint="https://auth.uat.interop.pagopa.it/token.oauth2",
)
access_token = auth_manager.get_access_token()

# 3. Carica chiave privata
with open(settings.key_path, "rb") as f:
    private_key = f.read()

# 4. Configura ModI
modi_config = ModIConfig(
    private_key=private_key,
    kid=settings.kid,
    issuer=settings.issuer,
    audience="https://modipa-val.agenziaentrate.it/govway/rest/in/AE/ANNCSU/v1",
)

audit_context = AuditContext(
    user_id=settings.modi_user_id or "default-user",
    user_location=settings.modi_user_location or "default-location",
    loa=settings.modi_loa or "SPID_L2",
)

# 5. Crea hooks
hooks = SDKHooks()
register_modi_hook(hooks, config=modi_config, audit_context=audit_context)

# 6. Crea SDK
sdk = AnncsuCoordinate(
    security=Security(bearer_auth=access_token),
    server_url="https://modipa-val.agenziaentrate.it/govway/rest/in/AE/ANNCSU/v1",
    hooks=hooks,
)

# 7. Crea richiesta
request = RichiestaOperazione(
    codcom="H501",
    progr_civico=12345,
    coord_x=12.4963655,
    coord_y=41.9027835,
    metodo="GPS",
)

# 8. Invia richiesta - header ModI aggiunti automaticamente
result = sdk.json_post.gestionecoordinate(
    richiesta_operazione=request
)
print(result)
```

## Operazioni Disponibili

### JSON POST

| Operazione | Descrizione |
|------------|-------------|
| `gestionecoordinate` | Aggiorna coordinate di un accesso |

### Status

| Operazione | Descrizione |
|------------|-------------|
| `show_status` | Verifica stato del servizio |

## Configurazione Ambiente

### File .env

```bash
# ~/.anncsu/.env

# PDND Configuration
PDND_KID=your-key-id
PDND_ISSUER=your-client-id
PDND_SUBJECT=your-client-id
PDND_AUDIENCE=https://auth.uat.interop.pagopa.it/client-assertion
PDND_KEY_PATH=/path/to/private_key.pem

# Purpose ID per Coordinate API
PDND_PURPOSE_ID_COORDINATE=your-coordinate-purpose-id

# ModI Audit Context (opzionale)
MODI_USER_ID=batch-user-001
MODI_USER_LOCATION=server-01
MODI_LOA=SPID_L2
```

## Validazione Coordinate

L'SDK fornisce un modello `ValidatedCoordinate` con validazione delle business rules ANNCSU.

### Business Rules

| X | Y | metodo | Z | Valido? |
|---|---|--------|---|---------|
| - | - | - | - | ✅ (nessuna coordinata) |
| - | - | ✅ | * | ❌ metodo senza coordinate |
| ✅ | - | * | * | ❌ X richiede Y |
| - | ✅ | * | * | ❌ Y richiede X |
| ✅ | ✅ | - | * | ❌ metodo obbligatorio |
| ✅ | ✅ | 0,5,... | * | ❌ metodo fuori range (1-4) |
| ✅ | ✅ | 1-4 | * | ✅ |
| - | - | - | ✅ | ❌ Z richiede X e Y |

### Range Coordinate Italia

- **X (longitude)**: 6.0 ≤ x ≤ 18.0
- **Y (latitude)**: 36.0 ≤ y ≤ 47.0

### Uso del Modello Validato

```python
from pydantic import ValidationError
from anncsu.coordinate.models.validated import ValidatedCoordinate

# Valido - nessuna coordinata
coord = ValidatedCoordinate()

# Valido - coordinate con metodo
coord = ValidatedCoordinate.model_validate({
    "x": "12.4963655",
    "y": "41.9027835",
    "metodo": "4",
})

# Con quota
coord = ValidatedCoordinate.model_validate({
    "x": "12.4963655",
    "y": "41.9027835",
    "z": "21",
    "metodo": "4",
})

# Invalido - coordinate senza metodo
try:
    coord = ValidatedCoordinate.model_validate({
        "x": "12.4963655",
        "y": "41.9027835",
    })
except ValidationError as e:
    print(f"Errore: {e}")
```

### Errori di Validazione

```python
from anncsu.coordinate.errors.coordinate_validation import (
    CoordinateValidationError,  # Base class
    MetodoRequiredError,        # metodo mancante con X/Y
    MetodoNotAllowedError,      # metodo presente senza X/Y
    MetodoOutOfRangeError,      # metodo non tra 1-4
    CoordinateDependencyError,  # X senza Y o viceversa
    CoordinateRangeError,       # coordinate fuori range Italia
    QuotaNotAllowedError,       # Z senza X/Y
)

# Catch specifico
try:
    coord = ValidatedCoordinate.model_validate({"x": "12.0", "y": "41.0"})
except ValidationError as e:
    cause = e.errors()[0]["ctx"]["error"]
    if isinstance(cause, MetodoRequiredError):
        print(f"Metodo richiesto per coordinate X={cause.x}, Y={cause.y}")
    elif isinstance(cause, CoordinateRangeError):
        print(f"Coordinata {cause.coordinate_name} fuori range: {cause.value}")

# Catch generico
try:
    coord = ValidatedCoordinate.model_validate({"metodo": "1"})
except ValidationError as e:
    cause = e.errors()[0]["ctx"]["error"]
    if isinstance(cause, CoordinateValidationError):
        print(f"Errore validazione: {cause}")
```

### Valori metodo

| Valore | Descrizione |
|--------|-------------|
| `1` | GPS |
| `2` | Cartografia |
| `3` | Indirizzo |
| `4` | Altro |

## Gestione Errori

```python
from anncsu.coordinate.errors import APIError, RispostaErrore
from anncsu.common.hooks import ModIHookError

try:
    result = sdk.json_post.gestionecoordinate(
        richiesta_operazione=request
    )
except ModIHookError as e:
    # Errore nella generazione degli header ModI
    print(f"ModI Error: {e.message}")
    if e.cause:
        print(f"Causa: {e.cause}")
except RispostaErrore as e:
    # Errore dall'API (RFC 7807)
    print(f"API Error: {e.title}")
    print(f"Detail: {e.detail}")
    print(f"Status: {e.status}")
except APIError as e:
    # Errore HTTP generico
    print(f"HTTP Error: {e.status_code}")
```

### Errori Comuni

| Errore | Causa | Soluzione |
|--------|-------|-----------|
| `ModIHookError` | Chiave privata invalida | Verifica formato PEM della chiave |
| `InteroperabilityInvalidRequest` | Header ModI mancanti o invalidi | Verifica configurazione ModI |
| `401 Unauthorized` | Token scaduto | Rigenera access token |
| `400 Bad Request` | Digest non corrisponde | Bug nell'hook - segnala issue |

## CLI Dry-Run

Il comando `dry-run` permette di testare il ciclo completo di aggiornamento coordinate senza modifiche permanenti.

### Modalità di Utilizzo

Il dry-run supporta due modalità di utilizzo:

1. **Modalità Diretta** (`--prognazacc`): Usa direttamente il progressivo nazionale accesso se già noto
2. **Modalità Ricerca** (`--codcom` + `--denom`): Cerca prima l'odonimo e poi l'accesso

### Sintassi

**Modalità Diretta** (salta la ricerca):

```bash
# Usa direttamente il prognazacc
anncsu coordinate dry-run --prognazacc 5256880
anncsu coordinate dry-run -p 5256880
```

**Modalità Ricerca** (cerca odonimo e accesso):

```bash
# Cerca per codice comune e denominazione
anncsu coordinate dry-run --codcom H501 --denom VklBIFJPTUE=
anncsu coordinate dry-run --codcom H501 --denom VklBIFJPTUE= --accparz 10
```

### Parametri

| Parametro | Alias | Descrizione | Modalità |
|-----------|-------|-------------|----------|
| `--prognazacc` | `-p` | Progressivo nazionale accesso | Diretta |
| `--codcom` | `-c` | Codice comune (Belfiore) | Ricerca |
| `--denom` | `-d` | Denominazione odonimo (Base64) | Ricerca |
| `--accparz` | `-a` | Progressivo accesso parziale (opzionale) | Ricerca |
| `--json` | | Output in formato JSON | Entrambe |
| `--no-verify-ssl` | | Disabilita verifica SSL | Entrambe |

**Note:**
- `--prognazacc` è mutuamente esclusivo con `--codcom`/`--denom`
- Se usi `--codcom` devi specificare anche `--denom` (e viceversa)

### Flusso Operativo

**Modalità Diretta** (`--prognazacc`):
1. **Query accesso**: Recupera i dettagli dell'accesso tramite prognazacc
2. **Salvataggio originale**: Memorizza le coordinate originali
3. **Test update**: Esegue un aggiornamento di test
4. **Restore**: Ripristina le coordinate originali

**Modalità Ricerca** (`--codcom` + `--denom`):
1. **Ricerca odonimo**: Trova il progressivo nazionale dell'odonimo
2. **Ricerca accesso**: Trova il primo accesso (civico) disponibile
3. **Salvataggio originale**: Memorizza le coordinate originali
4. **Test update**: Esegue un aggiornamento di test
5. **Restore**: Ripristina le coordinate originali

### Gestione Accessi Senza Coordinate

Quando un accesso non ha coordinate esistenti (X, Y e metodo sono vuoti), il dry-run utilizza coordinate di test temporanee:

| Campo | Valore Test | Descrizione |
|-------|-------------|-------------|
| X | `12.4922309` | Longitudine area Roma Colosseo |
| Y | `41.8902102` | Latitudine area Roma Colosseo |
| Z | `None` | Quota non specificata |
| metodo | `4` | Altro metodo di rilevazione |

Dopo il test, il comando ripristina lo stato originale (senza coordinate).

**Nota**: Se l'API non consente di ripristinare un accesso senza coordinate valide, il restore potrebbe fallire. In questo caso vengono mostrati i valori originali per il ripristino manuale.

### Output Esempio

**Modalità Diretta** (`--prognazacc 5256880`):

```
Step 1: Querying access point with prognazacc=5256880...
Found access point: prognazacc=5256880
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
┏━━━━━━━━━━━━━┳━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃ Step        ┃ Status ┃ Details                  ┃
┡━━━━━━━━━━━━━╇━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━━━━━┩
│ Search      │ OK     │ Found prognazacc=5256880 │
│ Test Update │ OK     │ Operazione completata    │
│ Restore     │ OK     │ Operazione completata    │
└─────────────┴────────┴──────────────────────────┘
```

**Modalità Ricerca** (`--codcom H501 --denom VklBIFJPTUE=`):

```
Step 1: Searching for odonimo and access point...
  Found odonimo: VIA ROMA
  Progressivo nazionale: 12345

Found access point: prognazacc=5256880
  Civico: 1
  Coord X: N/A
  Coord Y: N/A
  Quota: N/A
  Metodo: N/A

Note: Access has no coordinates. Using test coordinates (will be cleared after test).

Step 2: Performing test update...
Test update completed: esito=OK

Step 3: Restoring original coordinates...
Restore completed: esito=OK

Dry-run Summary:
┏━━━━━━━━━━━━━┳━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃ Step        ┃ Status ┃ Details                  ┃
┡━━━━━━━━━━━━━╇━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━━━━━┩
│ Search      │ OK     │ Found prognazacc=5256880 │
│ Test Update │ OK     │ Operazione completata    │
│ Restore     │ OK     │ Operazione completata    │
└─────────────┴────────┴──────────────────────────┘
```

### Output JSON

**Modalità Diretta** (`--prognazacc`):

```bash
anncsu coordinate dry-run --prognazacc 5256880 --json
```

```json
{
  "success": true,
  "original_coordinates": {
    "prognazacc": "5256880",
    "codcom": null,
    "civico": "1",
    "coord_x": "12.4963655",
    "coord_y": "41.9027835",
    "quota": "21",
    "metodo": "4"
  },
  "test_update": {
    "success": true,
    "id_richiesta": "186817",
    "esito": "OK",
    "messaggio": "Operazione completata",
    "dati_count": 1
  },
  "restore": {
    "success": true,
    "id_richiesta": "186818",
    "esito": "OK",
    "messaggio": "Operazione completata",
    "dati_count": 1
  },
  "restore_failed": false,
  "error_message": null
}
```

**Modalità Ricerca** (`--codcom` + `--denom`):

```bash
anncsu coordinate dry-run --codcom H501 --denom VklBIFJPTUE= --json
```

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
  "test_update": {
    "success": true,
    "id_richiesta": "186817",
    "esito": "OK",
    "messaggio": "Operazione completata",
    "dati_count": 1
  },
  "restore": {
    "success": true,
    "id_richiesta": "186818",
    "esito": "OK",
    "messaggio": "Operazione completata",
    "dati_count": 1
  },
  "restore_failed": false,
  "error_message": null
}
```

### Gestione Errori Restore

Se il restore fallisce, viene mostrato un warning con i valori originali:

```
WARNING: Restore failed: [error message]

Original coordinates to restore manually:
  prognazacc: 5256880
  codcom: H501
  coord_x: 12.4963655
  coord_y: 41.9027835
  quota: 21
  metodo: 4
```

## Operazioni Bulk

L'SDK fornisce componenti per operazioni coordinate di massa: importazione CSV, validazione, esecuzione API, dry-run e reportistica. Tutti i dati vengono persistiti in DuckDB locale per consentire resume, tracking e analisi post-esecuzione.

### Architettura

```
CSV → BulkImporter → BulkDB → BulkExecutor → API
                        ↓            ↓
                   DuckDB file   BulkReporter → CSV/JSON
```

I moduli principali sono in `anncsu.coordinate.bulk`:

| Modulo | Classe/Funzione | Descrizione |
|--------|----------------|-------------|
| `db.py` | `BulkDB` | Wrapper DuckDB: schema, query, stato righe |
| `db.py` | `RowStatus` | Enum stati: `PENDING`, `VALID`, `INVALID`, `PROCESSING`, `DONE`, `ERROR` |
| `importer.py` | `import_csv()` | Importa CSV → DuckDB con validazione SQL |
| `executor.py` | `BulkExecutor` | Esegue chiamate API per righe valide |
| `executor.py` | `BulkExecutorResult` | Risultato con statistiche e timing |
| `dryrun.py` | `BulkDryRunner` | Dry-run: lookup → update → restore |
| `reporter.py` | `BulkReporter` | Genera report CSV/JSON dai risultati |

### Esempio: Importazione e Validazione

```python
from anncsu.coordinate.bulk.db import BulkDB
from anncsu.coordinate.bulk.importer import import_csv

# Apri database persistente
with BulkDB("/path/to/output.db") as db:
    result = import_csv(db=db, csv_path="/path/to/input.csv", mode="update")

    print(f"Run ID: {result.run_id}")
    print(f"Codice Comune: {result.codcom}")
    print(f"Totale: {result.total_rows}")
    print(f"Valide: {result.valid_rows}")
    print(f"Invalide: {result.invalid_rows}")
```

`import_csv()` ritorna un `CSVImportResult` con:
- `run_id` — identificatore univoco del run (UUID)
- `codcom` — codice Belfiore estratto dal CSV
- `total_rows`, `valid_rows`, `invalid_rows` — contatori

### Esempio: Esecuzione Bulk Update

```python
from anncsu.coordinate.bulk.db import BulkDB
from anncsu.coordinate.bulk.importer import import_csv
from anncsu.coordinate.bulk.executor import BulkExecutor, RateLimitReached

with BulkDB("/path/to/output.db") as db:
    result = import_csv(db=db, csv_path="input.csv", mode="update")

    # Crea SDK autenticato (vedi sezione Autenticazione Completa)
    sdk = create_authenticated_sdk()

    executor = BulkExecutor(
        db=db,
        run_id=result.run_id,
        sdk=sdk,
        max_records=1000,  # Limita a 1000 righe (None = tutte)
        on_progress=lambda p, t, s, f: print(f"{p}/{t} ok={s} err={f}"),
    )

    try:
        exec_result = executor.execute()

        print(f"Processati: {exec_result.processed}")
        print(f"Successi: {exec_result.succeeded}")
        print(f"Falliti: {exec_result.failed}")
        print(f"Media: {exec_result.avg_elapsed_ms:.0f} ms/call")
        print(f"Stima 50k: {exec_result.estimated_50k_minutes:.1f} min")

    except RateLimitReached as e:
        print(f"Rate limit dopo {e.processed} chiamate, {e.remaining} rimanenti")
        print(f"Riprendi con run_id: {e.run_id}")

    db.finish_run(result.run_id)
```

`BulkExecutorResult` contiene:

| Campo | Tipo | Descrizione |
|-------|------|-------------|
| `processed` | `int` | Righe processate |
| `succeeded` | `int` | Esito OK |
| `failed` | `int` | Esito errore |
| `run_id` | `str` | ID del run |
| `total_elapsed_ms` | `float` | Tempo totale in ms |
| `avg_elapsed_ms` | `float` | Media ms per chiamata |
| `min_elapsed_ms` | `float` | Chiamata più veloce |
| `max_elapsed_ms` | `float` | Chiamata più lenta |
| `estimated_50k_minutes` | `float` | Stima minuti per 50k chiamate |

### Esempio: Resume Esecuzione Interrotta

```python
with BulkDB("/path/to/existing.db") as db:
    executor = BulkExecutor(db=db, run_id="abc123-...", sdk=sdk)
    exec_result = executor.execute(resume=True)  # Resetta righe "processing" → "valid"
```

### Esempio: Report e Analisi Errori

```python
from anncsu.coordinate.bulk.reporter import BulkReporter, ReportFormat

with BulkDB("/path/to/output.db") as db:
    reporter = BulkReporter(db=db, run_id="abc123-...")

    # Sommario
    summary = reporter.get_summary()
    print(f"{summary.succeeded}/{summary.total_rows} successi")

    # Errori API (esito != '0')
    for error in reporter.get_errors():
        print(f"  {error['progr_civico']}: {error['error_detail']}")

    # Errori di validazione (righe invalide)
    for err in reporter.get_validation_errors():
        print(f"  Riga {err['row_id']}: {err['validation_error']}")

    # Export CSV
    with open("results.csv", "w") as f:
        reporter.export_results(f, fmt=ReportFormat.CSV)

    # Export JSON
    with open("results.json", "w") as f:
        reporter.export_results(f, fmt=ReportFormat.JSON)
```

### DuckDB: Query Dirette

Per analisi avanzate, si può interrogare direttamente il file DuckDB. I file sono in `~/.anncsu/bulk/{codcom}_{run_id}.db`.

```bash
duckdb ~/.anncsu/bulk/H501_abc123-def456.db
```

**Record con esito OK**:

```sql
SELECT
    bi.codcom, bi.progr_civico,
    bi.x, bi.y, bi.z, bi.metodo,
    br.id_richiesta, br.elapsed_ms
FROM bulk_input bi
JOIN bulk_results br ON bi.row_id = br.row_id AND bi.run_id = br.run_id
WHERE bi.run_id = '<run_id>' AND br.esito = '0'
ORDER BY bi.row_id;
```

**Record con errori**:

```sql
SELECT
    bi.row_id, bi.progr_civico,
    br.esito, br.messaggio,
    br.http_status, br.error_detail
FROM bulk_input bi
JOIN bulk_results br ON bi.row_id = br.row_id AND bi.run_id = br.run_id
WHERE bi.run_id = '<run_id>'
  AND (br.esito IS NULL OR br.esito != '0')
ORDER BY bi.row_id;
```

**Errori di validazione**:

```sql
SELECT row_id, progr_civico, x, y, z, metodo, validation_error
FROM bulk_input
WHERE run_id = '<run_id>' AND status = 'invalid'
ORDER BY row_id;
```

**Statistiche timing**:

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

**Distribuzione percentili latenza**:

```sql
SELECT
    ROUND(PERCENTILE_CONT(0.50) WITHIN GROUP (ORDER BY elapsed_ms), 1) AS p50_ms,
    ROUND(PERCENTILE_CONT(0.90) WITHIN GROUP (ORDER BY elapsed_ms), 1) AS p90_ms,
    ROUND(PERCENTILE_CONT(0.95) WITHIN GROUP (ORDER BY elapsed_ms), 1) AS p95_ms,
    ROUND(PERCENTILE_CONT(0.99) WITHIN GROUP (ORDER BY elapsed_ms), 1) AS p99_ms
FROM bulk_results
WHERE run_id = '<run_id>' AND elapsed_ms IS NOT NULL;
```

**Esporta solo successi in CSV**:

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

**Riepilogo stati righe**:

```sql
SELECT status, COUNT(*) AS count
FROM bulk_input
WHERE run_id = '<run_id>'
GROUP BY status
ORDER BY count DESC;
```

### Schema DuckDB

Le 4 tabelle usate internamente:

| Tabella | Descrizione | Chiave primaria |
|---------|-------------|-----------------|
| `bulk_input` | Righe CSV importate con stato e errori validazione | `row_id` |
| `bulk_results` | Risposte API per ogni riga processata (con `elapsed_ms`) | `result_id` (auto) |
| `bulk_runs` | Metadati di esecuzione (run_id, codcom, mode, contatori) | `run_id` |
| `dryrun_originals` | Coordinate originali salvate per restore nel dry-run | `row_id` |

Colonne notevoli:
- `bulk_input.status`: stato FSM della riga (`pending` → `valid`/`invalid` → `processing` → `done`/`error`)
- `bulk_input.chunk_id`: generato automaticamente come `(row_id - 1) // 50000` per chunking interno
- `bulk_results.elapsed_ms`: latenza della singola chiamata API in millisecondi
- `bulk_results.esito`: `"0"` = successo, altro = errore (codice ANNCSU)
- `bulk_runs.daily_api_calls`: contatore per il rate limit di 50.000/giorno

## Testing

### Mock degli Hooks

```python
from unittest.mock import MagicMock
from anncsu.common.hooks import HooksProvider

# Crea mock
mock_hooks = MagicMock(spec=HooksProvider)

# Usa nei test
sdk = AnncsuCoordinate(
    security=Security(bearer_auth="test-token"),
    hooks=mock_hooks,
)
```

### Test con Chiave di Test

```python
# Genera chiave RSA di test
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa

key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
test_key = key.private_bytes(
    encoding=serialization.Encoding.PEM,
    format=serialization.PrivateFormat.TraditionalOpenSSL,
    encryption_algorithm=serialization.NoEncryption()
)

modi_config = ModIConfig(
    private_key=test_key,
    kid="test-kid",
    issuer="test-issuer",
    audience="https://test.example.com",
)
```

## Riferimenti

- [OpenAPI Specification](../oas/dev/)
- [CLI Documentation](./CLI.md) — comandi CLI con esempi, inclusa la sezione [DuckDB Query Examples](./CLI.md#duckdb-query-examples)
- [Security Documentation](./SECURITY.md)
- [ModI Guidelines](https://docs.pagopa.it/interoperabilita-1/manuale-operativo/modelli-di-interoperabilita)
