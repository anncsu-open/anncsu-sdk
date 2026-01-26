# SDK PA Consultazione

SDK per l'API ANNCSU Consultazione per le PA.

## Installazione

```bash
pip install anncsu
# oppure
uv add anncsu
```

## Quick Start

```python
from anncsu.pa import AnncsuConsultazione
from anncsu.pa.models import Security

sdk = AnncsuConsultazione(
    security=Security(bearer_auth="your-access-token"),
    server_url="https://modipa-val.agenziaentrate.it/govway/rest/in/AE/anncsu-consultazione-pa/v1",
)

# Verifica esistenza odonimo
res = sdk.queryparam.esiste_odonimo_get_query_param(
    codcom="H501",
    denom="VklBIFJPTUE=",  # "VIA ROMA" in base64
)
print(res)
```

## Autenticazione

L'SDK richiede un access token PDND valido. Per ottenere il token, usa `PDNDAuthManager`:

```python
from anncsu.common.auth import PDNDAuthManager
from anncsu.common.config import ClientAssertionSettings, APIType

# Carica configurazione da .env
settings = ClientAssertionSettings()

# Crea auth manager per PA API
auth_manager = PDNDAuthManager(
    settings=settings,
    api_type=APIType.PA,
    token_endpoint="https://auth.uat.interop.pagopa.it/token.oauth2",
)

# Ottieni token
access_token = auth_manager.get_access_token()

# Usa con SDK
sdk = AnncsuConsultazione(
    security=Security(bearer_auth=access_token),
)
```

## Operazioni Disponibili

### Verifica Esistenza

| Operazione | Metodo | Descrizione |
|------------|--------|-------------|
| `esiste_odonimo` | GET/POST | Verifica se un odonimo esiste in un comune |
| `esiste_accesso` | GET/POST | Verifica se un accesso esiste |

### Elenchi

| Operazione | Metodo | Descrizione |
|------------|--------|-------------|
| `elenco_odonimi` | GET/POST | Lista odonimi di un comune |
| `elenco_odonimi_prog` | GET/POST | Lista odonimi con progressivo nazionale |
| `elenco_accessi` | GET/POST | Lista accessi per odonimo |
| `elenco_accessi_prog` | GET/POST | Lista accessi con progressivo nazionale |

### Progressivi Nazionali

| Operazione | Metodo | Descrizione |
|------------|--------|-------------|
| `prog_naz_acc` | GET/POST | Ottieni progressivo nazionale accesso |
| `prog_naz_area` | GET/POST | Ottieni progressivo nazionale area |

## Modalità di Invocazione

L'SDK supporta tre modalità di invocazione per ogni operazione:

### 1. Query Parameters (GET)

```python
res = sdk.queryparam.esiste_odonimo_get_query_param(
    codcom="H501",
    denom="VklBIFJPTUE=",
)
```

### 2. Path Parameters (GET)

```python
res = sdk.pathparam.esiste_odonimo_get_path_param(
    codcom="H501",
    denom="VklBIFJPTUE=",
)
```

### 3. JSON POST

```python
res = sdk.jsonpost.esiste_odonimo_post(
    codcom="H501",
    denom="VklBIFJPTUE=",
)
```

## Formato Parametri

### Codice Comune (codcom)

Codice Belfiore a 4 caratteri. Esempi:
- `H501` = Roma
- `F205` = Milano
- `L219` = Torino

### Denominazione (denom)

Denominazione strada in **Base64**. Formato: `DUG + spazio + DENOMUFF`

```python
import base64

# Codifica
street = "VIA ROMA"
denom = base64.b64encode(street.encode()).decode()  # "VklBIFJPTUE="

# Decodifica
decoded = base64.b64decode(denom).decode()  # "VIA ROMA"
```

## Esempio Completo

```python
import base64
from anncsu.pa import AnncsuConsultazione
from anncsu.pa.models import Security
from anncsu.common.auth import PDNDAuthManager
from anncsu.common.config import ClientAssertionSettings, APIType

# 1. Configura autenticazione
settings = ClientAssertionSettings()
auth_manager = PDNDAuthManager(
    settings=settings,
    api_type=APIType.PA,
    token_endpoint="https://auth.uat.interop.pagopa.it/token.oauth2",
)

# 2. Ottieni access token
access_token = auth_manager.get_access_token()

# 3. Crea SDK
sdk = AnncsuConsultazione(
    security=Security(bearer_auth=access_token),
    server_url="https://modipa-val.agenziaentrate.it/govway/rest/in/AE/anncsu-consultazione-pa/v1",
)

# 4. Verifica esistenza odonimo
codcom = "H501"  # Roma
street = "VIA ROMA"
denom = base64.b64encode(street.encode()).decode()

result = sdk.queryparam.esiste_odonimo_get_query_param(
    codcom=codcom,
    denom=denom,
)

if result.res == "OK":
    print(f"Odonimo '{street}' esiste nel comune {codcom}")
    print(f"Dati: {result.data}")
else:
    print(f"Odonimo non trovato")

# 5. Elenco accessi per l'odonimo
accessi = sdk.queryparam.elenco_accessi_get_query_param(
    codcom=codcom,
    denom=denom,
)

for accesso in accessi.data:
    print(f"Civico: {accesso.civico}, Coordinate: ({accesso.coord_x}, {accesso.coord_y})")
```

## Gestione Errori

```python
from anncsu.pa.errors import APIError, RispostaErrore

try:
    result = sdk.queryparam.esiste_odonimo_get_query_param(
        codcom="XXXX",  # Codice invalido
        denom="dGVzdA==",
    )
except RispostaErrore as e:
    print(f"Errore API: {e.title}")
    print(f"Dettaglio: {e.detail}")
    print(f"Status: {e.status}")
except APIError as e:
    print(f"Errore HTTP: {e.status_code}")
    print(f"Body: {e.body}")
```

## Async Support

```python
import asyncio
from anncsu.pa import AnncsuConsultazione
from anncsu.pa.models import Security

async def main():
    async with AnncsuConsultazione(
        security=Security(bearer_auth="your-token"),
    ) as sdk:
        result = await sdk.queryparam.esiste_odonimo_get_query_param_async(
            codcom="H501",
            denom="VklBIFJPTUE=",
        )
        print(result)

asyncio.run(main())
```

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

# Purpose ID per PA API
PDND_PURPOSE_ID_PA=your-pa-purpose-id
```

## Riferimenti

- [OpenAPI Specification](../oas/dev/)
- [CLI Documentation](./CLI.md)
- [Security Documentation](./SECURITY.md)
