# SDK Odonimi

SDK per l'API ANNCSU Aggiornamento Odonimi.

Questa API implementa operazioni CRUD (Create / Replace / Sopprimi) su un singolo **odonimo** (via, piazza, ecc.) e richiede header ModI aggiuntivi (pattern INTEGRITY_REST_02 e AUDIT_REST_02).

> **Nota su `tipo_operazione`**: il campo `tipo_operazione` è un enum esplicito (a differenza di Accessi dove `operazione_civico` è una semplice stringa). Discrimina l'operazione richiesta:
>
> - `I` — Inserimento di un nuovo odonimo
> - `R` — Replace/aggiornamento di un odonimo esistente
> - `S` — Soppressione (logical delete) di un odonimo esistente

> **Nota sui sotto-oggetti**: a differenza di Accessi (che ha solo `coordinate` come sotto-oggetto), Odonimi ha due oggetti annidati con regole condizionali:
>
> - `provvedimento` — `data`, `protocollo`, `flag_delibera` (con regola: `flag_delibera ∈ {0,1}` → `data` + `protocollo` obbligatori)
> - `aut_prefettura` — `data_pref`, `protocollo_pref` (mutex: entrambi presenti o entrambi assenti)

## Installazione

```bash
pip install anncsu
# oppure
uv add anncsu
```

## Quick Start con ModI Headers

L'API Odonimi richiede header ModI. Usa la dependency injection per configurare l'hook.

```python
from anncsu.odonimi import AnncsuOdonimi
from anncsu.odonimi.models import Security
from anncsu.odonimi.models.richiestaoperazione import Richiesta, RichiestaOperazione
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
    audience=(
        "https://modipa-val.agenziaentrate.it/govway/rest/in/"
        "AgenziaEntrate-PDND/anncsu-aggiornamento-odonimi/v1"
    ),
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
sdk = AnncsuOdonimi(
    security=Security(bearer_auth="your-access-token"),
    server_url=(
        "https://modipa-val.agenziaentrate.it/govway/rest/in/"
        "AgenziaEntrate-PDND/anncsu-aggiornamento-odonimi/v1"
    ),
    hooks=hooks,
)

# 5. Crea una richiesta INSERT (tipo_operazione='I')
richiesta = RichiestaOperazione(
    richiesta=Richiesta(
        codcom="A062",
        tipo_operazione="I",
        dug="VIA",
        denom_delibera="DELLE ORCHIDEE",
    )
)

# 6. Invia richiesta - gli header ModI vengono aggiunti automaticamente
result = sdk.anncsu.gestione_anncsu_odonimi_pdnd(richiesta=richiesta.richiesta)
print(result.esito, result.messaggio, result.id_richiesta)
```

## Header ModI Generati Automaticamente

Quando l'hook ModI è registrato, tutte le richieste POST verso `/odonimi` includeranno automaticamente:

| Header | Pattern | Descrizione |
|--------|---------|-------------|
| `Digest` | RFC 3230 | Hash SHA-256 del body HTTP: `SHA-256=<base64>` |
| `Agid-JWT-Signature` | INTEGRITY_REST_02 | JWT con digest nel claim `signed_headers` |
| `Agid-JWT-TrackingEvidence` | AUDIT_REST_02 | JWT con claim di audit (`userID`, `userLocation`, `LoA`) |

La struttura dei JWT è identica a quella documentata in [SDK Coordinate](./sdk-coordinate.md#struttura-agid-jwt-signature).

## Dependency Injection Pattern

L'SDK Odonimi usa lo stesso pattern Dependency Injection tramite `HooksProvider` documentato in [SDK Coordinate](./sdk-coordinate.md#dependency-injection-pattern).

## Autenticazione Completa

Esempio end-to-end con `PDNDAuthManager`:

```python
from anncsu.common import PDNDAuthManager
from anncsu.common.auth import extract_voucher_audience
from anncsu.common.config import APIType, ClientAssertionSettings
from anncsu.common.hooks import SDKHooks, register_modi_hook
from anncsu.common.modi import AuditContext, ModIConfig
from anncsu.odonimi import AnncsuOdonimi
from anncsu.odonimi.models import Security
from anncsu.odonimi.models.richiestaoperazione import Richiesta

# 1. Carica settings da .env
settings = ClientAssertionSettings()

# 2. Crea auth manager per Odonimi
manager = PDNDAuthManager(
    api_type=APIType.ODONIMI,
    settings=settings,
    token_endpoint="https://auth.uat.interop.pagopa.it/token.oauth2",
    session_persistence=True,
)

# 3. Ottieni access token (refresh automatico)
access_token = manager.get_access_token()

# 4. Auto-discovery URL dal voucher
server_url = extract_voucher_audience(access_token)

# 5. Configura ModI hook
with open(settings.key_path, "rb") as f:
    private_key = f.read()

modi_config = ModIConfig(
    private_key=private_key,
    kid=settings.kid,
    issuer=settings.issuer,
    audience=server_url,
)
audit_context = settings.get_modi_audit_context()

hooks = SDKHooks()
register_modi_hook(hooks, config=modi_config, audit_context=audit_context)

# 6. Security provider per refresh automatico
def security_provider() -> Security:
    return Security(bearer_auth=manager.get_access_token())

# 7. Istanzia SDK
sdk = AnncsuOdonimi(
    security=security_provider,
    server_url=server_url,
    hooks=hooks,
)

# 8. Crea richiesta INSERT
richiesta = Richiesta(
    codcom="A062",
    tipo_operazione="I",
    dug="VIA",
    denom_delibera="DELLE ORCHIDEE",
    denom_localita="CASAL PALOCCO",
    provvedimento={
        "data": "10/10/2023",
        "protocollo": "1234567/abc",
        "flag_delibera": "1",
    },
    data_valid_amm="08/10/2024",
)

# 9. Invia richiesta
result = sdk.anncsu.gestione_anncsu_odonimi_pdnd(richiesta=richiesta)
print(f"Esito: {result.esito} — Richiesta: {result.id_richiesta}")
```

## Operazioni Disponibili

### Anncsu (POST `/odonimi`)

| Metodo | Descrizione |
|--------|-------------|
| `gestione_anncsu_odonimi_pdnd` | Esegue un'operazione I/R/S sull'odonimo |

L'operazione effettiva è determinata dal campo `Richiesta.tipo_operazione`:

| `tipo_operazione` | Operazione | Campi obbligatori |
|---|---|---|
| `I` | Inserimento | `codcom`, `dug` (assegnato `progr_nazionale` da ANNCSU) |
| `R` | Replace/aggiornamento | `codcom`, `progr_nazionale`, `dug` |
| `S` | Soppressione | `codcom`, `progr_nazionale` (vietato: `dug` e qualunque denominazione) |

### Status (GET `/status`)

| Metodo | Descrizione |
|--------|-------------|
| `show_status` | Verifica stato del servizio |

## Validazione Odonimo

L'SDK fornisce un modello `ValidatedOdonimo` con validazione delle business rules ANNCSU. Va sempre usato prima della chiamata API per intercettare errori a livello locale.

### Business Rules

Le regole sono applicate in ordine in un singolo `@model_validator(mode="after")`:

1. `tipo_operazione` ∈ {`I`, `R`, `S`} — altrimenti `TipoOperazioneError`
2. **maxLength** per ogni campo (OAS): `progr_nazionale ≤ 10`, `codice_comunale ≤ 30`, `dug ≤ 30`, `denom_delibera ≤ 120`, `denom_in_lingua_1/2 ≤ 150`, `denom_localita ≤ 151` (quirk OAS), `provvedimento.protocollo ≤ 70`, `aut_prefettura.protocollo_pref ≤ 70`
3. `codcom` obbligatorio sempre — altrimenti `CodcomRequiredError`
4. **Per `R` / `S`**: `progr_nazionale` obbligatorio — altrimenti `ProgrNazionaleRequiredError`
5. **Per `I` / `R`**: `dug` obbligatorio — altrimenti `DugRequiredError`
6. **Per `S`**: `dug` **vietato** — altrimenti `DugNotAllowedForDeleteError`
7. Se `provvedimento.flag_delibera ∈ {"0","1"}`: `data` + `protocollo` obbligatori — altrimenti `FlagDeliberaMissingFieldsError`
8. `aut_prefettura.data_pref` ↔ `protocollo_pref` mutex (entrambi o nessuno) — altrimenti `PrefetturaMutexError`

Le regole su `data_valid_amm` (`≤` data corrente per `I/S`, `≥` precedente per `R`) sono **delegate al server** (richiedono date arithmetic e lookup storici non disponibili lato client).

### Uso del Modello Validato

```python
from anncsu.odonimi.models.validated import ValidatedOdonimo

# Valido - INSERT minimal
odonimo = ValidatedOdonimo(
    codcom="A062",
    tipo_operazione="I",
    dug="VIA",
    denom_delibera="DELLE ORCHIDEE",
)

# Valido - REPLACE con provvedimento condizionale
odonimo = ValidatedOdonimo(
    codcom="A062",
    tipo_operazione="R",
    progr_nazionale="2000449",
    dug="VIA",
    denom_delibera="DEI TIGLI",
    provvedimento={
        "flag_delibera": "1",
        "data": "10/10/2023",
        "protocollo": "1234/abc",
    },
)

# Valido - DELETE (minimal, senza dug)
odonimo = ValidatedOdonimo(
    codcom="A062",
    tipo_operazione="S",
    progr_nazionale="2000449",
)

# Valido - INSERT con aut_prefettura (entrambi i campi)
odonimo = ValidatedOdonimo(
    codcom="A062",
    tipo_operazione="I",
    dug="VIA",
    denom_delibera="DELLA REPUBBLICA",
    aut_prefettura={
        "data_pref": "10/10/2023",
        "protocollo_pref": "Prot.Gen.1234567",
    },
)
```

### Errori di Validazione

```python
from pydantic import ValidationError

from anncsu.odonimi.errors.odonimo_validation import (
    OdonimoValidationError,         # Base class
    TipoOperazioneError,            # tipo_operazione mancante o non in {I,R,S}
    CodcomRequiredError,            # codcom mancante
    ProgrNazionaleRequiredError,    # progr_nazionale mancante per R o S
    DugRequiredError,               # dug mancante per I o R
    DugNotAllowedForDeleteError,    # dug valorizzato per S
    OdonimoMaxLengthError,          # campo eccede maxLength OAS
    FlagDeliberaMissingFieldsError, # flag_delibera 0/1 senza data+protocollo
    PrefetturaMutexError,           # data_pref ↔ protocollo_pref mutex
)

# Catch specifico
try:
    odonimo = ValidatedOdonimo(codcom="A062", tipo_operazione="S")
except ValidationError as e:
    cause = e.errors()[0]["ctx"]["error"]
    if isinstance(cause, ProgrNazionaleRequiredError):
        print(f"progr_nazionale obbligatorio per {cause.operazione}")
    elif isinstance(cause, DugRequiredError):
        print(f"dug obbligatorio per {cause.operazione}")

# Catch generico (tutti gli errori di validazione)
try:
    odonimo = ValidatedOdonimo(
        codcom="A062",
        tipo_operazione="I",
        dug="VIA",
        provvedimento={"flag_delibera": "1"},  # manca data + protocollo
    )
except ValidationError as e:
    cause = e.errors()[0]["ctx"]["error"]
    if isinstance(cause, OdonimoValidationError):
        print(f"Errore validazione odonimo: {cause}")
```

### Pipeline: Validazione + Chiamata API

Pattern consigliato per usare `ValidatedOdonimo` prima della chiamata SDK:

```python
from pydantic import ValidationError

from anncsu.odonimi.errors.odonimo_validation import OdonimoValidationError
from anncsu.odonimi.models.richiestaoperazione import Richiesta
from anncsu.odonimi.models.validated import ValidatedOdonimo

# 1. Costruisci con Richiesta (modello generato da Speakeasy)
richiesta = Richiesta(
    codcom="A062",
    tipo_operazione="R",
    progr_nazionale="2000449",
    dug="VIA",
    denom_delibera="DEI TIGLI",
)

# 2. Valida con ValidatedOdonimo (intercetta errori locali)
try:
    ValidatedOdonimo.model_validate(richiesta.model_dump(exclude_unset=True))
except ValidationError as e:
    print(f"Validazione fallita: {e.errors()[0]['ctx']['error']}")
    raise

# 3. Invia
result = sdk.anncsu.gestione_anncsu_odonimi_pdnd(richiesta=richiesta)
```

Questo pattern è quello usato internamente dalla CLI `anncsu odonimo` — vedi `_execute_operation` in `cli/commands/odonimo.py`.

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

# Purpose ID per Odonimi API
PDND_PURPOSE_ID_ODONIMI=your-odonimi-purpose-id

# ModI Audit Context (opzionale ma raccomandato in produzione)
MODI_USER_ID=batch-user-001
MODI_USER_LOCATION=server-01
MODI_LOA=SPID_L2
```

## Gestione Errori

```python
from anncsu.odonimi.errors import APIError, RispostaErrore
from anncsu.common.hooks import ModIHookError

try:
    result = sdk.anncsu.gestione_anncsu_odonimi_pdnd(richiesta=richiesta)
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
| `RispostaErrore` (codice 23) | Validazione lato API | Verifica payload, confronta con `ValidatedOdonimo` |
| `RispostaErrore` (codice 100) | Dato di riferimento inesistente (es. `codcom` ignoto) | Verifica codice Belfiore comune sul portale ANNCSU |
| `401 Unauthorized` | Token scaduto | Rigenera access token via `PDNDAuthManager` |
| `400 Bad Request` (Digest) | Digest non corrisponde | Bug nell'hook ModI — segnala issue |

## CLI Dry-Run

La CLI fornisce il flag `--dry-run` sui comandi `insert`, `update`, `delete` con un pattern diverso da Accessi: il dry-run opera sempre su una **denominazione fittizia generata** (`TEST SDK <timestamp>-<uuid>`), così i dati reali non vengono mai toccati.

In sintesi:

- `insert --dry-run`: I (dati utente) → S (rollback)
- `update --dry-run`: I (denom fittizia) → R (dati utente sul fittizio) → S (cleanup)
- `delete --dry-run`: I (denom fittizia) → S (immediato)

Per dettagli vedi la sezione [`anncsu odonimo *` — `--dry-run` flag](./CLI.md#anncsu-odonimo----dry-run-flag) nel documento CLI.

## Testing

### Mock degli Hooks

```python
from unittest.mock import MagicMock

mock_hooks = MagicMock()
mock_hooks.sdk_init.return_value = MagicMock()  # SDKConfiguration mocked
mock_hooks.before_request.return_value = MagicMock()  # request mocked

sdk = AnncsuOdonimi(security=Security(bearer_auth="test"), hooks=mock_hooks)
```

### Mock dell'SDK Completo

```python
from unittest.mock import MagicMock, patch

with patch("anncsu.cli.commands.odonimo.AnncsuOdonimi") as mock_sdk_cls:
    sdk = MagicMock()
    response = MagicMock(esito="0", messaggio="OK", id_richiesta="TEST-001")
    sdk.anncsu.gestione_anncsu_odonimi_pdnd.return_value = response
    mock_sdk_cls.return_value = sdk
    # ... esegui codice che usa AnncsuOdonimi
```

## Riferimenti

- [Specifica OAS](../oas/dev/Specifica%20API%20-%20ANNCSU%20-%20Aggiornamento%20odonimi.yaml)
- [CLI Documentation](./CLI.md#anncsu-odonimo---odonimo-crud)
- [SDK Coordinate](./sdk-coordinate.md) (struttura JWT, dependency injection)
- [SDK Accessi](./sdk-accessi.md) (gemello CRUD per accessi/civici)
- [SDK PA Consultazione](./sdk-pa.md) (per lookup `prognaz` via `--auto-resolve`)
- [SECURITY.md](../SECURITY.md) (gestione chiavi PDND)
- [ModI Guidelines AgID](https://www.agid.gov.it/sites/agid/files/2022-09/lg_modi_3.0.0_v0_94_1_1.pdf)
