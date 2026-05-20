# SDK Accessi

SDK per l'API ANNCSU Aggiornamento Accessi.

Questa API implementa operazioni CRUD (Create / Replace / Sopprimi) su un singolo accesso (civico) e richiede header ModI aggiuntivi (pattern INTEGRITY_REST_02 e AUDIT_REST_02).

> **Nota sulla terminologia**: L'identificatore di un accesso è chiamato `prognazacc` nell'API PA Consultazione e `progr_civico` nell'API Accessi. **Rappresentano lo stesso valore** — l'identificatore progressivo nazionale univoco di un punto di accesso.

> **Nota su `operazione_civico`**: il campo `operazione_civico` discrimina l'operazione richiesta:
> - `I` — Inserimento di un nuovo accesso
> - `R` — Replace/aggiornamento di un accesso esistente
> - `S` — Soppressione (logical delete) di un accesso esistente

## Installazione

```bash
pip install anncsu
# oppure
uv add anncsu
```

## Quick Start con ModI Headers

L'API Accessi richiede header ModI. Usa la dependency injection per configurare l'hook.

```python
from anncsu.accessi import AnncsuAccessi
from anncsu.accessi.models import Security
from anncsu.accessi.models.richiestaoperazione import Accesso, Richiesta
from anncsu.common.hooks import SDKHooks, register_modi_hook
from anncsu.common.modi import AuditContext, ModIConfig

# 1. Carica la chiave privata (stessa usata per PDND)
with open("/path/to/private_key.pem", "rb") as f:
    private_key = f.read()

# 2. Configura ModI
modi_config = ModIConfig(
    private_key=private_key,
    kid="your-pdnd-kid",
    issuer="your-client-id",
    audience="https://modipa-val.agenziaentrate.it/govway/rest/in/AgenziaEntrate/anncsuaccessi/v1",
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
sdk = AnncsuAccessi(
    security=Security(bearer_auth="your-access-token"),
    server_url="https://modipa-val.agenziaentrate.it/govway/rest/in/AgenziaEntrate/anncsuaccessi/v1",
    hooks=hooks,
)

# 5. Crea una richiesta INSERT (operazione_civico='I')
richiesta = Richiesta(
    codcom="A062",
    progr_nazionale="2000449",
    accesso=Accesso(operazione_civico="I", numero="12"),
)

# 6. Invia richiesta - gli header ModI vengono aggiunti automaticamente
result = sdk.anncsu.gestione_anncsu_pdnd(richiesta=richiesta)
print(result.esito, result.messaggio, result.id_richiesta)
```

## Header ModI Generati Automaticamente

Quando l'hook ModI è registrato, tutte le richieste POST verso `/accessi` includeranno automaticamente:

| Header | Pattern | Descrizione |
|--------|---------|-------------|
| `Digest` | RFC 3230 | Hash SHA-256 del body HTTP: `SHA-256=<base64>` |
| `Agid-JWT-Signature` | INTEGRITY_REST_02 | JWT con digest nel claim `signed_headers` |
| `Agid-JWT-TrackingEvidence` | AUDIT_REST_02 | JWT con claim di audit (`userID`, `userLocation`, `LoA`) |

La struttura dei JWT è identica a quella documentata in [SDK Coordinate](./sdk-coordinate.md#struttura-agid-jwt-signature).

## Dependency Injection Pattern

L'SDK Accessi usa lo stesso pattern Dependency Injection tramite `HooksProvider` documentato in [SDK Coordinate](./sdk-coordinate.md#dependency-injection-pattern):

```python
from anncsu.accessi import AnncsuAccessi
from anncsu.common.hooks import HooksProvider, SDKHooks

hooks: HooksProvider = SDKHooks()

sdk = AnncsuAccessi(
    security=...,
    hooks=hooks,  # Optional[HooksProvider]
)
```

## Senza Audit Context

Se non hai bisogno di AUDIT_REST_02 (tracking), puoi omettere l'audit context:

```python
hooks = SDKHooks()
register_modi_hook(hooks, config=modi_config)  # Senza audit_context

# Solo Digest e Agid-JWT-Signature verranno aggiunti
sdk = AnncsuAccessi(security=Security(bearer_auth="your-token"), hooks=hooks)
```

## Autenticazione Completa

Esempio completo con autenticazione PDND e ModI:

```python
from anncsu.accessi import AnncsuAccessi
from anncsu.accessi.models import Security
from anncsu.accessi.models.richiestaoperazione import Accesso, Coordinate, Richiesta
from anncsu.common.auth import PDNDAuthManager
from anncsu.common.config import APIType, ClientAssertionSettings
from anncsu.common.hooks import SDKHooks, register_modi_hook
from anncsu.common.modi import AuditContext, ModIConfig

# 1. Carica configurazione
settings = ClientAssertionSettings()

# 2. Ottieni access token per API Accessi
auth_manager = PDNDAuthManager(
    settings=settings,
    api_type=APIType.ACCESSI,
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
    audience="https://modipa-val.agenziaentrate.it/govway/rest/in/AgenziaEntrate/anncsuaccessi/v1",
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
sdk = AnncsuAccessi(
    security=Security(bearer_auth=access_token),
    server_url="https://modipa-val.agenziaentrate.it/govway/rest/in/AgenziaEntrate/anncsuaccessi/v1",
    hooks=hooks,
)

# 7. Crea richiesta INSERT con coordinate
richiesta = Richiesta(
    codcom="A062",
    progr_nazionale="2000449",
    accesso=Accesso(
        operazione_civico="I",
        numero="12",
        esponente="A",
        coordinate=Coordinate(
            x="13.1022000",
            y="41.8847600",
            metodo="3",
        ),
    ),
)

# 8. Invia richiesta - header ModI aggiunti automaticamente
result = sdk.anncsu.gestione_anncsu_pdnd(richiesta=richiesta)
print(f"Esito: {result.esito}, ID: {result.id_richiesta}")
```

## Operazioni Disponibili

### Anncsu (POST `/accessi`)

| Metodo | Descrizione |
|--------|-------------|
| `gestione_anncsu_pdnd` | Esegue un'operazione I/R/S sull'accesso |

L'operazione effettiva è determinata dal campo `Accesso.operazione_civico` nella richiesta:

| `operazione_civico` | Operazione | Campi obbligatori |
|---|---|---|
| `I` | Inserimento | `numero` XOR `metrico` (e uno dei due deve essere valorizzato) |
| `R` | Replace/aggiornamento | `progr_civico` + `numero` XOR `metrico` |
| `S` | Soppressione | `progr_civico` |

### Status (GET `/status`)

| Metodo | Descrizione |
|--------|-------------|
| `show_status` | Verifica stato del servizio |

## Validazione Accesso

L'SDK fornisce un modello `ValidatedAccesso` con validazione delle business rules ANNCSU. Va sempre usato prima della chiamata API per intercettare errori a livello locale.

### Business Rules

Le regole sono applicate in ordine in un singolo `@model_validator(mode="after")`:

1. `operazione_civico` ∈ {`I`, `R`, `S`} — altrimenti `OperazioneCivicoError`
2. **maxLength** per ogni campo (OAS): `progr_civico ≤ 15`, `codice_civico_comunale ≤ 30`, `numero ≤ 5`, `esponente ≤ 15`, `specificita ≤ 5`, `metrico ≤ 6`, `sezione_censimento ≤ 13`, `isolato ≤ 4`
3. **Per `S`**: i campi `numero`, `metrico`, `esponente`, `specificita`, `sezione_censimento`, `isolato`, `coordinate` non devono essere valorizzati — altrimenti `FieldNotAllowedForDeleteError`
4. **Per `R` / `S`**: `progr_civico` obbligatorio — altrimenti `ProgrCivicoRequiredError`
5. **Per `I` / `R`**: esattamente uno tra `numero` e `metrico` (XOR strict) — altrimenti `NumeroMetricoMutexError`
6. **Coordinate**, se presenti, vengono ri-validate via `ValidatedCoordinate` (range Italia, X/Y dependency, `metodo` 1-4, `maxLength` X/Y/Z)

### Uso del Modello Validato

```python
from anncsu.accessi.models.validated import ValidatedAccesso

# Valido - INSERT civico
accesso = ValidatedAccesso(
    operazione_civico="I",
    numero="12",
    esponente="A",
)

# Valido - INSERT metrico
accesso = ValidatedAccesso(
    operazione_civico="I",
    metrico="300",
)

# Valido - REPLACE
accesso = ValidatedAccesso(
    operazione_civico="R",
    progr_civico="1370588",
    numero="12",
    coordinate={
        "x": "13.1022000",
        "y": "41.8847600",
        "metodo": "3",
    },
)

# Valido - DELETE (minimal)
accesso = ValidatedAccesso(
    operazione_civico="S",
    progr_civico="1370588",
)
```

### Errori di Validazione

```python
from pydantic import ValidationError

from anncsu.accessi.errors.accesso_validation import (
    AccessoValidationError,        # Base class
    OperazioneCivicoError,         # operazione_civico mancante o non in {I, R, S}
    ProgrCivicoRequiredError,      # progr_civico mancante per R o S
    NumeroMetricoMutexError,       # both/neither numero+metrico per I/R
    FieldNotAllowedForDeleteError, # campo non valorizzabile per S
    AccessoMaxLengthError,         # campo eccede maxLength
)

# Catch specifico
try:
    accesso = ValidatedAccesso(operazione_civico="I")
except ValidationError as e:
    cause = e.errors()[0]["ctx"]["error"]
    if isinstance(cause, NumeroMetricoMutexError):
        print(f"Servono uno tra numero e metrico per I/R")
    elif isinstance(cause, OperazioneCivicoError):
        print(f"Operazione invalida: {cause.value}")

# Catch generico (intercetta tutti gli errori di validazione)
try:
    accesso = ValidatedAccesso(operazione_civico="X")
except ValidationError as e:
    cause = e.errors()[0]["ctx"]["error"]
    if isinstance(cause, AccessoValidationError):
        print(f"Errore validazione accesso: {cause}")
```

### Pipeline: Validazione + Chiamata API

Pattern consigliato per usare `ValidatedAccesso` prima della chiamata SDK:

```python
from pydantic import ValidationError

from anncsu.accessi.errors.accesso_validation import AccessoValidationError
from anncsu.accessi.models.richiestaoperazione import Accesso, Richiesta
from anncsu.accessi.models.validated import ValidatedAccesso

# 1. Costruisci con Accesso (modello generato da Speakeasy)
accesso = Accesso(
    operazione_civico="R",
    progr_civico="1370588",
    numero="12",
)

# 2. Valida con ValidatedAccesso (intercetta errori locali)
try:
    ValidatedAccesso.model_validate(accesso.model_dump(exclude_unset=True))
except ValidationError as e:
    print(f"Validazione fallita: {e.errors()[0]['ctx']['error']}")
    raise

# 3. Costruisci richiesta e invia
richiesta = Richiesta(codcom="A062", progr_nazionale="2000449", accesso=accesso)
result = sdk.anncsu.gestione_anncsu_pdnd(richiesta=richiesta)
```

Questo pattern è quello usato internamente dalla CLI `anncsu accesso` — vedi `_send_one_op` in `cli/commands/accesso.py`.

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

# Purpose ID per Accessi API
PDND_PURPOSE_ID_ACCESSI=your-accessi-purpose-id

# ModI Audit Context (opzionale ma raccomandato in produzione)
MODI_USER_ID=batch-user-001
MODI_USER_LOCATION=server-01
MODI_LOA=SPID_L2
```

## Gestione Errori

```python
from anncsu.accessi.errors import APIError, RispostaErrore
from anncsu.common.hooks import ModIHookError

try:
    result = sdk.anncsu.gestione_anncsu_pdnd(richiesta=richiesta)
except ModIHookError as e:
    # Errore nella generazione degli header ModI
    print(f"ModI Error: {e.message}")
except RispostaErrore as e:
    # Errore dall'API (RFC 7807)
    print(f"API Error code: {e.codice}, msg: {e.messaggio}")
except APIError as e:
    # Errore HTTP generico
    print(f"HTTP Error: {e.status_code}")
```

### Errori Comuni

| Errore | Causa | Soluzione |
|--------|-------|-----------|
| `ModIHookError` | Chiave privata invalida | Verifica formato PEM della chiave |
| `RispostaErrore` (codice 23) | Validazione lato API | Verifica payload, confronta con `ValidatedAccesso` |
| `RispostaErrore` (codice 130) | `metodo` obbligatorio mancante | Valorizza `Coordinate.metodo` (1-4) |
| `401 Unauthorized` | Token scaduto | Rigenera access token via `PDNDAuthManager` |
| `400 Bad Request` (Digest) | Digest non corrisponde | Bug nell'hook ModI — segnala issue |

## CLI Dry-Run

La CLI fornisce il flag `--dry-run` sui comandi `insert`, `update`, `delete` per testare il ciclo completo senza modifiche permanenti. Per dettagli vedi la sezione [`anncsu accesso *` — `--dry-run` flag](./CLI.md#anncsu-accesso----dry-run-flag) nel documento CLI.

In sintesi:
- `insert --dry-run`: I → S (rollback pulito)
- `update --dry-run`: lookup originali → R nuovi → R originali (con pre-check su dati legacy)
- `delete --dry-run`: lookup originali → S → I (con nuovo `progr_civico` assegnato da ANNCSU)

Tutti i dry-run scrivono un pending log in `~/.anncsu/dryrun_pending.json` prima del rollback, per consentire recovery manuale in caso di crash.

## Testing

### Mock degli Hooks

```python
from unittest.mock import MagicMock

from anncsu.accessi import AnncsuAccessi
from anncsu.accessi.models import Security
from anncsu.common.hooks import HooksProvider

mock_hooks = MagicMock(spec=HooksProvider)

sdk = AnncsuAccessi(
    security=Security(bearer_auth="test-token"),
    hooks=mock_hooks,
)
```

### Mock dell'SDK Completo

Pattern usato nei test della CLI per simulare risposte API:

```python
from unittest.mock import MagicMock, patch

with patch("anncsu.cli.commands.accesso.AnncsuAccessi") as mock_sdk_cls:
    sdk = MagicMock()
    response = MagicMock()
    response.esito = "0"
    response.id_richiesta = "REQ-123"
    response.messaggio = "OK"
    response.dati = [MagicMock(progr_civico="9999999")]
    sdk.anncsu.gestione_anncsu_pdnd.return_value = response
    mock_sdk_cls.return_value = sdk

    # ... esegui la CLI o il codice sotto test
```

### Test con Chiave RSA Generata Runtime

```python
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa

key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
test_key = key.private_bytes(
    encoding=serialization.Encoding.PEM,
    format=serialization.PrivateFormat.TraditionalOpenSSL,
    encryption_algorithm=serialization.NoEncryption(),
)

modi_config = ModIConfig(
    private_key=test_key,
    kid="test-kid",
    issuer="test-issuer",
    audience="https://test.example.com",
)
```

## Riferimenti

- [OpenAPI Specification](../oas/dev/Specifica%20API%20-%20ANNCSU%20-%20Aggiornamento%20accessi.yaml)
- [CLI Documentation](./CLI.md) — comandi `anncsu accesso` (insert/update/delete/status) con esempi
- [SDK Coordinate](./sdk-coordinate.md) — pattern di riferimento (ModI hooks, dependency injection)
- [SDK PA Consultazione](./sdk-pa.md) — lookup `progr_civico` via PA API (usato da `--auto-resolve`)
- [Security Documentation](./SECURITY.md)
- [ModI Guidelines](https://docs.pagopa.it/interoperabilita-1/manuale-operativo/modelli-di-interoperabilita)
