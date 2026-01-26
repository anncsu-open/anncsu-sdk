# anncsu-sdk
ANNCSU Software Development Kit for API consumption

Developer-friendly & type-safe Python SDK specifically catered to leverage *anncsu* API.

<div align="left">
    <a href="https://www.speakeasy.com/?utm_source=anncsu&utm_campaign=python"><img src="https://custom-icon-badges.demolab.com/badge/-Built%20By%20Speakeasy-212015?style=for-the-badge&logoColor=FBE331&logo=speakeasy&labelColor=545454" /></a>
    <a href="https://opensource.org/licenses/MIT">
        <img src="https://img.shields.io/badge/License-MIT-blue.svg" style="width: 100px; height: 28px;" />
    </a>
</div>


<br /><br />
> [!IMPORTANT]
> This SDK is not yet ready for production use. To complete setup please follow the steps outlined in your [workspace](https://app.speakeasy.com/org/geobeyond-zd1/anncsu). Delete this section before > publishing to a package manager.

<!-- Start Summary [summary] -->
## Summary

ANNCSU REST API: API dei servizi REST di ANNCSU su PDND
<!-- End Summary [summary] -->

<!-- Start Table of Contents [toc] -->
## Table of Contents
<!-- $toc-max-depth=2 -->
* [anncsu](#anncsu)
  * [SDK Installation](#sdk-installation)
  * [IDE Support](#ide-support)
  * [SDK Example Usage](#sdk-example-usage)
  * [Security and Authentication](#security-and-authentication)
  * [Available Resources and Operations](#available-resources-and-operations)
  * [Retries](#retries)
  * [Error Handling](#error-handling)
  * [Server Selection](#server-selection)
  * [Custom HTTP Client](#custom-http-client)
  * [Resource Management](#resource-management)
  * [Debugging](#debugging)
  * [Architecture](#architecture)
  * [Command Line Interface](#command-line-interface)
* [Development](#development)
  * [Maturity](#maturity)
  * [Contributions](#contributions)

<!-- End Table of Contents [toc] -->

<!-- Start SDK Installation [installation] -->
## SDK Installation

> [!TIP]
> To finish publishing your SDK to PyPI you must [run your first generation action](https://www.speakeasy.com/docs/github-setup#step-by-step-guide).


> [!NOTE]
> **Python version upgrade policy**
>
> Once a Python version reaches its [official end of life date](https://devguide.python.org/versions/), a 3-month grace period is provided for users to upgrade. Following this grace period, the minimum python version supported in the SDK will be updated.

The SDK can be installed with either *pip* or *poetry* package managers.

### PIP

*PIP* is the default package installer for Python, enabling easy installation and management of packages from PyPI via the command line.

```bash
pip install git+<UNSET>.git
```

### Poetry

*Poetry* is a modern tool that simplifies dependency management and package publishing by using a single `pyproject.toml` file to handle project metadata and dependencies.

```bash
poetry add git+<UNSET>.git
```

### Shell and script usage with `uv`

You can use this SDK in a Python shell with [uv](https://docs.astral.sh/uv/) and the `uvx` command that comes with it like so:

```shell
uvx --from anncsu.pa python
```

It's also possible to write a standalone Python script without needing to set up a whole project like so:

```python
#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.9"
# dependencies = [
#     "anncsu",
# ]
# ///

from anncsu.pa import AnncsuConsultazione

sdk = AnncsuConsultazione(
  # SDK arguments
)

# Rest of script here...
```

Once that is saved to a file, you can run it with `uv run script.py` where
`script.py` can be replaced with the actual file name.
<!-- End SDK Installation [installation] -->

<!-- Start IDE Support [idesupport] -->
## IDE Support

### PyCharm

Generally, the SDK will work well with most IDEs out of the box. However, when using PyCharm, you can enjoy much better integration with Pydantic by installing an additional plugin.

- [PyCharm Pydantic Plugin](https://docs.pydantic.dev/latest/integrations/pycharm/)
<!-- End IDE Support [idesupport] -->

<!-- Start SDK Example Usage [usage] -->
## SDK Example Usage

### Example

```python
# Synchronous Example
from anncsu.pa import AnncsuConsultazione


with Anncsu() as a_client:

    res = a_client.queryparam.esiste_odonimo_get_query_param(codcom="H501", denom="VklBIFJPTUE=")

    # Handle response
    print(res)
```

</br>

The same SDK client can also be used to make asychronous requests by importing asyncio.
```python
# Asynchronous Example
from anncsu.pa import AnncsuConsultazione
import asyncio

async def main():

    async with Anncsu() as a_client:

        res = await a_client.queryparam.esiste_odonimo_get_query_param_async(codcom="H501", denom="VklBIFJPTUE=")

        # Handle response
        print(res)

asyncio.run(main())
```
<!-- End SDK Example Usage [usage] -->

<!-- Start Security and Authentication [security] -->
## Security and Authentication

All ANNCSU APIs use PDND (Piattaforma Digitale Nazionale Dati) voucher-based authentication with HTTP Bearer tokens.

### Complete Authentication Flow

The SDK supports the complete PDND authentication flow:

```
┌─────────────────────┐     ┌─────────────────────┐     ┌─────────────────────┐
│  1. Create Client   │     │  2. Exchange for    │     │  3. Use Access      │
│     Assertion       │────▶│     Access Token    │────▶│     Token           │
│     (JWT)           │     │     (OAuth2)        │     │     (API Calls)     │
└─────────────────────┘     └─────────────────────┘     └─────────────────────┘
```

```python
from pathlib import Path
from anncsu.pa import AnncsuConsultazione
from anncsu.common import (
    # Step 1: Client Assertion
    ClientAssertionConfig,
    create_client_assertion,
    # Step 2: Token Exchange
    TokenConfig,
    get_access_token,
    # Step 3: API Authentication
    Security,
)

# Step 1: Create client assertion (JWT)
assertion_config = ClientAssertionConfig(
    kid="your-key-id",
    issuer="your-client-id",
    subject="your-client-id",
    audience="auth.uat.interop.pagopa.it/client-assertion",
    purpose_id="your-purpose-id",
    key_path=Path("./private_key.pem"),
)
client_assertion = create_client_assertion(assertion_config)

# Step 2: Exchange for access token
token_config = TokenConfig(
    client_id="your-client-id",
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
```

### Basic Authentication (with existing token)

If you already have an access token:

```python
from anncsu.pa import AnncsuConsultazione
from anncsu.common import Security

security = Security(bearer="your-access-token")
sdk = AnncsuConsultazione(security=security)

response = sdk.queryparam.esiste_odonimo_get_query_param(
    codcom="H501",
    denom="VklBIFJPTUE="
)
```

### Token Expiration Validation

The `Security` class automatically validates token expiration when initialized. If the token is expired, it raises `TokenExpiredError` instead of letting the API return a confusing 404 error:

```python
from anncsu.common import Security, TokenExpiredError

try:
    security = Security(bearer=token_response.access_token)
except TokenExpiredError as e:
    print(f"Token expired at {e.expired_at}, current time: {e.current_time}")
    # Obtain a new access token...
    token_response = get_access_token(token_config)
    security = Security(bearer=token_response.access_token)
```

You can also check expiration manually:

```python
# Check if token is expired
if security.is_expired():
    print("Token needs refresh!")

# Get seconds until expiration (negative if already expired)
ttl = security.time_until_expiration()
if ttl and ttl < 60:
    print(f"Token expires in {ttl} seconds, consider refreshing")
```

To skip validation (not recommended):

```python
security = Security(bearer=expired_token, validate_expiration=False)
```

### Key Features

- **Complete Auth Flow**: Generate assertions, exchange for tokens, authenticate API calls
- **PDND Voucher**: Full PDND (Piattaforma Digitale Nazionale Dati) authentication support
- **Bearer Token**: JWT format tokens in Authorization header
- **Sync & Async**: Both `get_access_token` and `get_access_token_async` available
- **Error Handling**: Dedicated exceptions for token errors (`TokenRequestError`, `TokenResponseError`)
- **Type-Safe**: Full type hints with modern Python syntax

### Loading Configuration from Environment Variables

The SDK supports loading configuration from environment variables or a `.env` file:

```python
from anncsu.common.config import ClientAssertionSettings
from anncsu.common import create_client_assertion, TokenConfig, get_access_token, Security
from anncsu.pa import AnncsuConsultazione

# Automatically loads from environment variables or .env file
settings = ClientAssertionSettings()
client_assertion = create_client_assertion(settings.to_config())

# Exchange for access token
token_response = get_access_token(TokenConfig(
    client_id=settings.issuer,
    client_assertion=client_assertion,
    token_endpoint="https://auth.uat.interop.pagopa.it/token.oauth2",
))

# Use with SDK
sdk = AnncsuConsultazione(security=Security(bearer=token_response.access_token))
```

#### Required Environment Variables (prefix: `PDND_`)

| Variable | Description |
|----------|-------------|
| `PDND_KID` | Key ID (kid) header parameter |
| `PDND_ISSUER` | Issuer claim - your client_id |
| `PDND_SUBJECT` | Subject claim - your client_id |
| `PDND_AUDIENCE` | Audience claim - must end with `/client-assertion` |
| `PDND_PURPOSE_ID_PA` | Purpose ID for PA Consultazione API |
| `PDND_PURPOSE_ID_COORDINATE` | Purpose ID for Coordinate API |
| `PDND_PURPOSE_ID_ACCESSI` | Purpose ID for Accessi API (can be empty) |
| `PDND_PURPOSE_ID_INTERNI` | Purpose ID for Interni API (can be empty) |
| `PDND_PURPOSE_ID_ODONIMI` | Purpose ID for Odonimi API (can be empty) |
| `PDND_PRIVATE_KEY` | Private key content (or use `PDND_KEY_PATH`) |
| `PDND_KEY_PATH` | Path to private key file (or use `PDND_PRIVATE_KEY`) |

#### Example .env file

```bash
PDND_KID=my-key-id
PDND_ISSUER=my-client-id
PDND_SUBJECT=my-client-id
PDND_AUDIENCE=auth.uat.interop.pagopa.it/client-assertion

# Purpose ID for each API type (ALL must be present, can be empty if not used)
PDND_PURPOSE_ID_PA=your-purpose-id-for-pa-consultazione
PDND_PURPOSE_ID_COORDINATE=your-purpose-id-for-coordinate-api
PDND_PURPOSE_ID_ACCESSI=
PDND_PURPOSE_ID_INTERNI=
PDND_PURPOSE_ID_ODONIMI=

PDND_KEY_PATH=./private_key.pem
```

### Documentation

For comprehensive security documentation including:
- Complete authentication flow (3 steps)
- Token exchange parameters and error handling
- Client assertion generation
- Token refresh strategies
- Best practices and security checklist
- Testing with security

See [docs/SECURITY.md](docs/SECURITY.md)

<!-- End Security and Authentication [security] -->

<!-- Start Available Resources and Operations [operations] -->
## Available Resources and Operations

<details open>
<summary>Available methods</summary>


### [json_post](docs/sdks/jsonpost/README.md)

* [esiste_odonimo_post](docs/sdks/jsonpost/README.md#esiste_odonimo_post) - Ritorna un valore boolean dell'esistenza dell'odonimo in ANNCSU
* [esiste_accesso_post](docs/sdks/jsonpost/README.md#esiste_accesso_post) - Ritorna un valore boolean dell'esistenza dell'accesso in ANNCSU
* [elenco_odonimi_post](docs/sdks/jsonpost/README.md#elenco_odonimi_post) - Ritorna un elenco di odonimi presenti in ANNCSU
* [elenco_accessi_post](docs/sdks/jsonpost/README.md#elenco_accessi_post) - Ritorna un elenco di accessi presenti in ANNCSU
* [elencoodonimiprog_post](docs/sdks/jsonpost/README.md#elencoodonimiprog_post) - Ritorna un elenco di odonimi presenti in ANNCSU incluso il progressivo nazionale
* [elencoaccessiprog_post](docs/sdks/jsonpost/README.md#elencoaccessiprog_post) - Ritorna un elenco di accessi presenti in ANNCSU incluso il progressivo nazionale
* [prognazarea_post](docs/sdks/jsonpost/README.md#prognazarea_post) - Cerca in ANNCSU un odonimo per progressivo nazionale e ne ritorna i dati
* [prognazacc_post](docs/sdks/jsonpost/README.md#prognazacc_post) - Cerca in ANNCSU un accesso per progressivo nazionale accesso e ne ritorna i dati comprensivi dell'odonimo

### [pathparam](docs/sdks/pathparam/README.md)

* [esiste_odonimo_get_path_param](docs/sdks/pathparam/README.md#esiste_odonimo_get_path_param) - Ritorna un valore boolean dell'esistenza dell'odonimo in ANNCSU
* [esiste_accesso_get_path_param](docs/sdks/pathparam/README.md#esiste_accesso_get_path_param) - Ritorna un valore boolean dell'esistenza dell'accesso in ANNCSU
* [elenco_odonimi_get_path_param](docs/sdks/pathparam/README.md#elenco_odonimi_get_path_param) - Ritorna un elenco di odonimi presenti in ANNCSU
* [elenco_accessi_get_path_param](docs/sdks/pathparam/README.md#elenco_accessi_get_path_param) - Ritorna un elenco di accessi presenti in ANNCSU
* [elencoodonimiprog_get_path_param](docs/sdks/pathparam/README.md#elencoodonimiprog_get_path_param) - Ritorna un elenco di odonimi presenti in ANNCSU incluso il progressivo nazionale
* [elencoaccessiprog_get_path_param](docs/sdks/pathparam/README.md#elencoaccessiprog_get_path_param) - Ritorna un elenco di accessi presenti in ANNCSU incluso il progressivo nazionale
* [prognazarea_get_path_param](docs/sdks/pathparam/README.md#prognazarea_get_path_param) - Cerca in ANNCSU un odonimo per progressivo nazionale e ne ritorna i dati
* [prognazacc_get_path_param](docs/sdks/pathparam/README.md#prognazacc_get_path_param) - Cerca in ANNCSU un accesso per progressivo nazionale accesso e ne ritorna i dati comprensivi dell'odonimo

### [queryparam](docs/sdks/queryparam/README.md)

* [esiste_odonimo_get_query_param](docs/sdks/queryparam/README.md#esiste_odonimo_get_query_param) - Ritorna un valore boolean dell'esistenza dell'odonimo in ANNCSU
* [esiste_accesso_get_query_param](docs/sdks/queryparam/README.md#esiste_accesso_get_query_param) - Ritorna un valore boolean dell'esistenza dell'accesso in ANNCSU
* [elenco_odonimi_get_query_param](docs/sdks/queryparam/README.md#elenco_odonimi_get_query_param) - Ritorna un elenco di odonimi presenti in ANNCSU
* [elenco_accessi_get_query_param](docs/sdks/queryparam/README.md#elenco_accessi_get_query_param) - Ritorna un elenco di accessi presenti in ANNCSU
* [elencoodonimiprog_get_query_param](docs/sdks/queryparam/README.md#elencoodonimiprog_get_query_param) - Ritorna un elenco di odonimi presenti in ANNCSU incluso il progressivo nazionale
* [elencoaccessiprog_get_query_param](docs/sdks/queryparam/README.md#elencoaccessiprog_get_query_param) - Ritorna un elenco di accessi presenti in ANNCSU incluso il progressivo nazionale
* [prognazarea_get_query_param](docs/sdks/queryparam/README.md#prognazarea_get_query_param) - Cerca in ANNCSU un odonimo per progressivo nazionale e ne ritorna i dati
* [prognazacc_get_query_param](docs/sdks/queryparam/README.md#prognazacc_get_query_param) - Cerca in ANNCSU un accesso per progressivo nazionale accesso e ne ritorna i dati comprensivi dell'odonimo

### [status](docs/sdks/status/README.md)

* [show_status](docs/sdks/status/README.md#show_status) - Ritorna lo stato dell'applicazione.

</details>
<!-- End Available Resources and Operations [operations] -->

<!-- Start Retries [retries] -->
## Retries

Some of the endpoints in this SDK support retries. If you use the SDK without any configuration, it will fall back to the default retry strategy provided by the API. However, the default retry strategy can be overridden on a per-operation basis, or across the entire SDK.

To change the default retry strategy for a single API call, simply provide a `RetryConfig` object to the call:
```python
from anncsu.pa import AnncsuConsultazione
from anncsu.common.utils import BackoffStrategy, RetryConfig


with Anncsu() as a_client:

    res = a_client.queryparam.esiste_odonimo_get_query_param(codcom="H501", denom="VklBIFJPTUE=",
        RetryConfig("backoff", BackoffStrategy(1, 50, 1.1, 100), False))

    # Handle response
    print(res)

```

If you'd like to override the default retry strategy for all operations that support retries, you can use the `retry_config` optional parameter when initializing the SDK:
```python
from anncsu.pa import AnncsuConsultazione
from anncsu.common.utils import BackoffStrategy, RetryConfig


with Anncsu(
    retry_config=RetryConfig("backoff", BackoffStrategy(1, 50, 1.1, 100), False),
) as a_client:

    res = a_client.queryparam.esiste_odonimo_get_query_param(codcom="H501", denom="VklBIFJPTUE=")

    # Handle response
    print(res)

```
<!-- End Retries [retries] -->

<!-- Start Error Handling [errors] -->
## Error Handling

[`AnncsuError`](./src/anncsu/errors/anncsuerror.py) is the base class for all HTTP error responses. It has the following properties:

| Property           | Type             | Description                                                                             |
| ------------------ | ---------------- | --------------------------------------------------------------------------------------- |
| `err.message`      | `str`            | Error message                                                                           |
| `err.status_code`  | `int`            | HTTP response status code eg `404`                                                      |
| `err.headers`      | `httpx.Headers`  | HTTP response headers                                                                   |
| `err.body`         | `str`            | HTTP body. Can be empty string if no body is returned.                                  |
| `err.raw_response` | `httpx.Response` | Raw HTTP response                                                                       |
| `err.data`         |                  | Optional. Some errors may contain structured data. [See Error Classes](#error-classes). |

### Example
```python
from anncsu.pa import AnncsuConsultazione, errors


with Anncsu() as a_client:
    res = None
    try:

        res = a_client.queryparam.esiste_odonimo_get_query_param(codcom="H501", denom="VklBIFJPTUE=")

        # Handle response
        print(res)


    except errors.AnncsuError as e:
        # The base class for HTTP error responses
        print(e.message)
        print(e.status_code)
        print(e.body)
        print(e.headers)
        print(e.raw_response)

        # Depending on the method different errors may be thrown
        if isinstance(e, errors.EsisteOdonimoGetQueryParamBadRequestError):
            print(e.data.title)  # Optional[str]
            print(e.data.detail)  # Optional[str]
```

### Error Classes
**Primary error:**
* [`AnncsuError`](./src/anncsu/errors/anncsuerror.py): The base class for HTTP error responses.

<details><summary>Less common errors (120)</summary>

<br />

**Network errors:**
* [`httpx.RequestError`](https://www.python-httpx.org/exceptions/#httpx.RequestError): Base class for request errors.
    * [`httpx.ConnectError`](https://www.python-httpx.org/exceptions/#httpx.ConnectError): HTTP client was unable to make a request to a server.
    * [`httpx.TimeoutException`](https://www.python-httpx.org/exceptions/#httpx.TimeoutException): HTTP request timed out.


**Inherit from [`AnncsuError`](./src/anncsu/errors/anncsuerror.py)**:
* [`EsisteOdonimoGetQueryParamBadRequestError`](./src/anncsu/errors/esisteodonimogetqueryparambadrequesterror.py): Bad Request. Status code `400`. Applicable to 1 of 25 methods.*
* [`EsisteAccessoGetQueryParamBadRequestError`](./src/anncsu/errors/esisteaccessogetqueryparambadrequesterror.py): Bad Request. Status code `400`. Applicable to 1 of 25 methods.*
* [`ElencoOdonimiGetQueryParamBadRequestError`](./src/anncsu/errors/elencoodonimigetqueryparambadrequesterror.py): Bad Request. Status code `400`. Applicable to 1 of 25 methods.*
* [`ElencoAccessiGetQueryParamBadRequestError`](./src/anncsu/errors/elencoaccessigetqueryparambadrequesterror.py): Bad Request. Status code `400`. Applicable to 1 of 25 methods.*
* [`ElencoodonimiprogGetQueryParamBadRequestError`](./src/anncsu/errors/elencoodonimiproggetqueryparambadrequesterror.py): Bad Request. Status code `400`. Applicable to 1 of 25 methods.*
* [`ElencoaccessiprogGetQueryParamBadRequestError`](./src/anncsu/errors/elencoaccessiproggetqueryparambadrequesterror.py): Bad Request. Status code `400`. Applicable to 1 of 25 methods.*
* [`PrognazareaGetQueryParamBadRequestError`](./src/anncsu/errors/prognazareagetqueryparambadrequesterror.py): Bad Request. Status code `400`. Applicable to 1 of 25 methods.*
* [`PrognazaccGetQueryParamBadRequestError`](./src/anncsu/errors/prognazaccgetqueryparambadrequesterror.py): Bad Request. Status code `400`. Applicable to 1 of 25 methods.*
* [`EsisteOdonimoPostBadRequestError`](./src/anncsu/errors/esisteodonimopostbadrequesterror.py): Bad Request. Status code `400`. Applicable to 1 of 25 methods.*
* [`EsisteAccessoPostBadRequestError`](./src/anncsu/errors/esisteaccessopostbadrequesterror.py): Bad Request. Status code `400`. Applicable to 1 of 25 methods.*
* [`ElencoOdonimiPostBadRequestError`](./src/anncsu/errors/elencoodonimipostbadrequesterror.py): Bad Request. Status code `400`. Applicable to 1 of 25 methods.*
* [`ElencoAccessiPostBadRequestError`](./src/anncsu/errors/elencoaccessipostbadrequesterror.py): Bad Request. Status code `400`. Applicable to 1 of 25 methods.*
* [`ElencoodonimiprogPostBadRequestError`](./src/anncsu/errors/elencoodonimiprogpostbadrequesterror.py): Bad Request. Status code `400`. Applicable to 1 of 25 methods.*
* [`ElencoaccessiprogPostBadRequestError`](./src/anncsu/errors/elencoaccessiprogpostbadrequesterror.py): Bad Request. Status code `400`. Applicable to 1 of 25 methods.*
* [`PrognazareaPostBadRequestError`](./src/anncsu/errors/prognazareapostbadrequesterror.py): Bad Request. Status code `400`. Applicable to 1 of 25 methods.*
* [`PrognazaccPostBadRequestError`](./src/anncsu/errors/prognazaccpostbadrequesterror.py): Bad Request. Status code `400`. Applicable to 1 of 25 methods.*
* [`EsisteOdonimoGetPathParamBadRequestError`](./src/anncsu/errors/esisteodonimogetpathparambadrequesterror.py): Bad Request. Status code `400`. Applicable to 1 of 25 methods.*
* [`EsisteAccessoGetPathParamBadRequestError`](./src/anncsu/errors/esisteaccessogetpathparambadrequesterror.py): Bad Request. Status code `400`. Applicable to 1 of 25 methods.*
* [`ElencoOdonimiGetPathParamBadRequestError`](./src/anncsu/errors/elencoodonimigetpathparambadrequesterror.py): Bad Request. Status code `400`. Applicable to 1 of 25 methods.*
* [`ElencoAccessiGetPathParamBadRequestError`](./src/anncsu/errors/elencoaccessigetpathparambadrequesterror.py): Bad Request. Status code `400`. Applicable to 1 of 25 methods.*
* [`ElencoodonimiprogGetPathParamBadRequestError`](./src/anncsu/errors/elencoodonimiproggetpathparambadrequesterror.py): Bad Request. Status code `400`. Applicable to 1 of 25 methods.*
* [`ElencoaccessiprogGetPathParamBadRequestError`](./src/anncsu/errors/elencoaccessiproggetpathparambadrequesterror.py): Bad Request. Status code `400`. Applicable to 1 of 25 methods.*
* [`PrognazareaGetPathParamBadRequestError`](./src/anncsu/errors/prognazareagetpathparambadrequesterror.py): Bad Request. Status code `400`. Applicable to 1 of 25 methods.*
* [`PrognazaccGetPathParamBadRequestError`](./src/anncsu/errors/prognazaccgetpathparambadrequesterror.py): Bad Request. Status code `400`. Applicable to 1 of 25 methods.*
* [`ElencoOdonimiGetQueryParamNotFoundError`](./src/anncsu/errors/elencoodonimigetqueryparamnotfounderror.py): Not found. Status code `404`. Applicable to 1 of 25 methods.*
* [`ElencoAccessiGetQueryParamNotFoundError`](./src/anncsu/errors/elencoaccessigetqueryparamnotfounderror.py): Not found. Status code `404`. Applicable to 1 of 25 methods.*
* [`ElencoodonimiprogGetQueryParamNotFoundError`](./src/anncsu/errors/elencoodonimiproggetqueryparamnotfounderror.py): Not found. Status code `404`. Applicable to 1 of 25 methods.*
* [`ElencoaccessiprogGetQueryParamNotFoundError`](./src/anncsu/errors/elencoaccessiproggetqueryparamnotfounderror.py): Not found. Status code `404`. Applicable to 1 of 25 methods.*
* [`PrognazareaGetQueryParamNotFoundError`](./src/anncsu/errors/prognazareagetqueryparamnotfounderror.py): Not found. Status code `404`. Applicable to 1 of 25 methods.*
* [`PrognazaccGetQueryParamNotFoundError`](./src/anncsu/errors/prognazaccgetqueryparamnotfounderror.py): Not found. Status code `404`. Applicable to 1 of 25 methods.*
* [`ElencoOdonimiPostNotFoundError`](./src/anncsu/errors/elencoodonimipostnotfounderror.py): Not found. Status code `404`. Applicable to 1 of 25 methods.*
* [`ElencoAccessiPostNotFoundError`](./src/anncsu/errors/elencoaccessipostnotfounderror.py): Not found. Status code `404`. Applicable to 1 of 25 methods.*
* [`ElencoodonimiprogPostNotFoundError`](./src/anncsu/errors/elencoodonimiprogpostnotfounderror.py): Not found. Status code `404`. Applicable to 1 of 25 methods.*
* [`ElencoaccessiprogPostNotFoundError`](./src/anncsu/errors/elencoaccessiprogpostnotfounderror.py): Not found. Status code `404`. Applicable to 1 of 25 methods.*
* [`PrognazareaPostNotFoundError`](./src/anncsu/errors/prognazareapostnotfounderror.py): Not found. Status code `404`. Applicable to 1 of 25 methods.*
* [`PrognazaccPostNotFoundError`](./src/anncsu/errors/prognazaccpostnotfounderror.py): Not found. Status code `404`. Applicable to 1 of 25 methods.*
* [`ElencoOdonimiGetPathParamNotFoundError`](./src/anncsu/errors/elencoodonimigetpathparamnotfounderror.py): Not found. Status code `404`. Applicable to 1 of 25 methods.*
* [`ElencoAccessiGetPathParamNotFoundError`](./src/anncsu/errors/elencoaccessigetpathparamnotfounderror.py): Not found. Status code `404`. Applicable to 1 of 25 methods.*
* [`ElencoodonimiprogGetPathParamNotFoundError`](./src/anncsu/errors/elencoodonimiproggetpathparamnotfounderror.py): Not found. Status code `404`. Applicable to 1 of 25 methods.*
* [`ElencoaccessiprogGetPathParamNotFoundError`](./src/anncsu/errors/elencoaccessiproggetpathparamnotfounderror.py): Not found. Status code `404`. Applicable to 1 of 25 methods.*
* [`PrognazareaGetPathParamNotFoundError`](./src/anncsu/errors/prognazareagetpathparamnotfounderror.py): Not found. Status code `404`. Applicable to 1 of 25 methods.*
* [`PrognazaccGetPathParamNotFoundError`](./src/anncsu/errors/prognazaccgetpathparamnotfounderror.py): Not found. Status code `404`. Applicable to 1 of 25 methods.*
* [`EsisteOdonimoGetQueryParamMethodNotAllowedError`](./src/anncsu/errors/esisteodonimogetqueryparammethodnotallowederror.py): Method Not Allowed. Status code `405`. Applicable to 1 of 25 methods.*
* [`EsisteAccessoGetQueryParamMethodNotAllowedError`](./src/anncsu/errors/esisteaccessogetqueryparammethodnotallowederror.py): Method Not Allowed. Status code `405`. Applicable to 1 of 25 methods.*
* [`ElencoOdonimiGetQueryParamMethodNotAllowedError`](./src/anncsu/errors/elencoodonimigetqueryparammethodnotallowederror.py): Method Not Allowed. Status code `405`. Applicable to 1 of 25 methods.*
* [`ElencoAccessiGetQueryParamMethodNotAllowedError`](./src/anncsu/errors/elencoaccessigetqueryparammethodnotallowederror.py): Method Not Allowed. Status code `405`. Applicable to 1 of 25 methods.*
* [`ElencoodonimiprogGetQueryParamMethodNotAllowedError`](./src/anncsu/errors/elencoodonimiproggetqueryparammethodnotallowederror.py): Method Not Allowed. Status code `405`. Applicable to 1 of 25 methods.*
* [`ElencoaccessiprogGetQueryParamMethodNotAllowedError`](./src/anncsu/errors/elencoaccessiproggetqueryparammethodnotallowederror.py): Method Not Allowed. Status code `405`. Applicable to 1 of 25 methods.*
* [`PrognazareaGetQueryParamMethodNotAllowedError`](./src/anncsu/errors/prognazareagetqueryparammethodnotallowederror.py): Method Not Allowed. Status code `405`. Applicable to 1 of 25 methods.*
* [`PrognazaccGetQueryParamMethodNotAllowedError`](./src/anncsu/errors/prognazaccgetqueryparammethodnotallowederror.py): Method Not Allowed. Status code `405`. Applicable to 1 of 25 methods.*
* [`EsisteOdonimoPostMethodNotAllowedError`](./src/anncsu/errors/esisteodonimopostmethodnotallowederror.py): Method Not Allowed. Status code `405`. Applicable to 1 of 25 methods.*
* [`EsisteAccessoPostMethodNotAllowedError`](./src/anncsu/errors/esisteaccessopostmethodnotallowederror.py): Method Not Allowed. Status code `405`. Applicable to 1 of 25 methods.*
* [`ElencoOdonimiPostMethodNotAllowedError`](./src/anncsu/errors/elencoodonimipostmethodnotallowederror.py): Method Not Allowed. Status code `405`. Applicable to 1 of 25 methods.*
* [`ElencoAccessiPostMethodNotAllowedError`](./src/anncsu/errors/elencoaccessipostmethodnotallowederror.py): Method Not Allowed. Status code `405`. Applicable to 1 of 25 methods.*
* [`ElencoodonimiprogPostMethodNotAllowedError`](./src/anncsu/errors/elencoodonimiprogpostmethodnotallowederror.py): Method Not Allowed. Status code `405`. Applicable to 1 of 25 methods.*
* [`ElencoaccessiprogPostMethodNotAllowedError`](./src/anncsu/errors/elencoaccessiprogpostmethodnotallowederror.py): Method Not Allowed. Status code `405`. Applicable to 1 of 25 methods.*
* [`PrognazareaPostMethodNotAllowedError`](./src/anncsu/errors/prognazareapostmethodnotallowederror.py): Method Not Allowed. Status code `405`. Applicable to 1 of 25 methods.*
* [`PrognazaccPostMethodNotAllowedError`](./src/anncsu/errors/prognazaccpostmethodnotallowederror.py): Method Not Allowed. Status code `405`. Applicable to 1 of 25 methods.*
* [`EsisteOdonimoGetPathParamMethodNotAllowedError`](./src/anncsu/errors/esisteodonimogetpathparammethodnotallowederror.py): Method Not Allowed. Status code `405`. Applicable to 1 of 25 methods.*
* [`EsisteAccessoGetPathParamMethodNotAllowedError`](./src/anncsu/errors/esisteaccessogetpathparammethodnotallowederror.py): Method Not Allowed. Status code `405`. Applicable to 1 of 25 methods.*
* [`ElencoOdonimiGetPathParamMethodNotAllowedError`](./src/anncsu/errors/elencoodonimigetpathparammethodnotallowederror.py): Method Not Allowed. Status code `405`. Applicable to 1 of 25 methods.*
* [`ElencoAccessiGetPathParamMethodNotAllowedError`](./src/anncsu/errors/elencoaccessigetpathparammethodnotallowederror.py): Method Not Allowed. Status code `405`. Applicable to 1 of 25 methods.*
* [`ElencoodonimiprogGetPathParamMethodNotAllowedError`](./src/anncsu/errors/elencoodonimiproggetpathparammethodnotallowederror.py): Method Not Allowed. Status code `405`. Applicable to 1 of 25 methods.*
* [`ElencoaccessiprogGetPathParamMethodNotAllowedError`](./src/anncsu/errors/elencoaccessiproggetpathparammethodnotallowederror.py): Method Not Allowed. Status code `405`. Applicable to 1 of 25 methods.*
* [`PrognazareaGetPathParamMethodNotAllowedError`](./src/anncsu/errors/prognazareagetpathparammethodnotallowederror.py): Method Not Allowed. Status code `405`. Applicable to 1 of 25 methods.*
* [`PrognazaccGetPathParamMethodNotAllowedError`](./src/anncsu/errors/prognazaccgetpathparammethodnotallowederror.py): Method Not Allowed. Status code `405`. Applicable to 1 of 25 methods.*
* [`EsisteOdonimoGetQueryParamUnprocessableEntityError`](./src/anncsu/errors/esisteodonimogetqueryparamunprocessableentityerror.py): Unprocessable Entity - error in json. Status code `422`. Applicable to 1 of 25 methods.*
* [`EsisteAccessoGetQueryParamUnprocessableEntityError`](./src/anncsu/errors/esisteaccessogetqueryparamunprocessableentityerror.py): Unprocessable Entity - error in json. Status code `422`. Applicable to 1 of 25 methods.*
* [`ElencoOdonimiGetQueryParamUnprocessableEntityError`](./src/anncsu/errors/elencoodonimigetqueryparamunprocessableentityerror.py): Unprocessable Entity - error in json. Status code `422`. Applicable to 1 of 25 methods.*
* [`ElencoAccessiGetQueryParamUnprocessableEntityError`](./src/anncsu/errors/elencoaccessigetqueryparamunprocessableentityerror.py): Unprocessable Entity - error in json. Status code `422`. Applicable to 1 of 25 methods.*
* [`ElencoodonimiprogGetQueryParamUnprocessableEntityError`](./src/anncsu/errors/elencoodonimiproggetqueryparamunprocessableentityerror.py): Unprocessable Entity - error in json. Status code `422`. Applicable to 1 of 25 methods.*
* [`ElencoaccessiprogGetQueryParamUnprocessableEntityError`](./src/anncsu/errors/elencoaccessiproggetqueryparamunprocessableentityerror.py): Unprocessable Entity - error in json. Status code `422`. Applicable to 1 of 25 methods.*
* [`PrognazareaGetQueryParamUnprocessableEntityError`](./src/anncsu/errors/prognazareagetqueryparamunprocessableentityerror.py): Unprocessable Entity - error in json. Status code `422`. Applicable to 1 of 25 methods.*
* [`PrognazaccGetQueryParamUnprocessableEntityError`](./src/anncsu/errors/prognazaccgetqueryparamunprocessableentityerror.py): Unprocessable Entity - error in json. Status code `422`. Applicable to 1 of 25 methods.*
* [`EsisteOdonimoPostUnprocessableEntityError`](./src/anncsu/errors/esisteodonimopostunprocessableentityerror.py): Unprocessable Entity - error in json. Status code `422`. Applicable to 1 of 25 methods.*
* [`EsisteAccessoPostUnprocessableEntityError`](./src/anncsu/errors/esisteaccessopostunprocessableentityerror.py): Unprocessable Entity - error in json. Status code `422`. Applicable to 1 of 25 methods.*
* [`ElencoOdonimiPostUnprocessableEntityError`](./src/anncsu/errors/elencoodonimipostunprocessableentityerror.py): Unprocessable Entity - error in json. Status code `422`. Applicable to 1 of 25 methods.*
* [`ElencoAccessiPostUnprocessableEntityError`](./src/anncsu/errors/elencoaccessipostunprocessableentityerror.py): Unprocessable Entity - error in json. Status code `422`. Applicable to 1 of 25 methods.*
* [`ElencoodonimiprogPostUnprocessableEntityError`](./src/anncsu/errors/elencoodonimiprogpostunprocessableentityerror.py): Unprocessable Entity - error in json. Status code `422`. Applicable to 1 of 25 methods.*
* [`ElencoaccessiprogPostUnprocessableEntityError`](./src/anncsu/errors/elencoaccessiprogpostunprocessableentityerror.py): Unprocessable Entity - error in json. Status code `422`. Applicable to 1 of 25 methods.*
* [`PrognazareaPostUnprocessableEntityError`](./src/anncsu/errors/prognazareapostunprocessableentityerror.py): Unprocessable Entity - error in json. Status code `422`. Applicable to 1 of 25 methods.*
* [`PrognazaccPostUnprocessableEntityError`](./src/anncsu/errors/prognazaccpostunprocessableentityerror.py): Unprocessable Entity - error in json. Status code `422`. Applicable to 1 of 25 methods.*
* [`EsisteOdonimoGetPathParamUnprocessableEntityError`](./src/anncsu/errors/esisteodonimogetpathparamunprocessableentityerror.py): Unprocessable Entity - error in json. Status code `422`. Applicable to 1 of 25 methods.*
* [`EsisteAccessoGetPathParamUnprocessableEntityError`](./src/anncsu/errors/esisteaccessogetpathparamunprocessableentityerror.py): Unprocessable Entity - error in json. Status code `422`. Applicable to 1 of 25 methods.*
* [`ElencoOdonimiGetPathParamUnprocessableEntityError`](./src/anncsu/errors/elencoodonimigetpathparamunprocessableentityerror.py): Unprocessable Entity - error in json. Status code `422`. Applicable to 1 of 25 methods.*
* [`ElencoAccessiGetPathParamUnprocessableEntityError`](./src/anncsu/errors/elencoaccessigetpathparamunprocessableentityerror.py): Unprocessable Entity - error in json. Status code `422`. Applicable to 1 of 25 methods.*
* [`ElencoodonimiprogGetPathParamUnprocessableEntityError`](./src/anncsu/errors/elencoodonimiproggetpathparamunprocessableentityerror.py): Unprocessable Entity - error in json. Status code `422`. Applicable to 1 of 25 methods.*
* [`ElencoaccessiprogGetPathParamUnprocessableEntityError`](./src/anncsu/errors/elencoaccessiproggetpathparamunprocessableentityerror.py): Unprocessable Entity - error in json. Status code `422`. Applicable to 1 of 25 methods.*
* [`PrognazareaGetPathParamUnprocessableEntityError`](./src/anncsu/errors/prognazareagetpathparamunprocessableentityerror.py): Unprocessable Entity - error in json. Status code `422`. Applicable to 1 of 25 methods.*
* [`PrognazaccGetPathParamUnprocessableEntityError`](./src/anncsu/errors/prognazaccgetpathparamunprocessableentityerror.py): Unprocessable Entity - error in json. Status code `422`. Applicable to 1 of 25 methods.*
* [`EsisteOdonimoGetQueryParamInternalServerError`](./src/anncsu/errors/esisteodonimogetqueryparaminternalservererror.py): Internal Server Error. Status code `500`. Applicable to 1 of 25 methods.*
* [`EsisteAccessoGetQueryParamInternalServerError`](./src/anncsu/errors/esisteaccessogetqueryparaminternalservererror.py): Internal Server Error. Status code `500`. Applicable to 1 of 25 methods.*
* [`ElencoOdonimiGetQueryParamInternalServerError`](./src/anncsu/errors/elencoodonimigetqueryparaminternalservererror.py): Internal Server Error. Status code `500`. Applicable to 1 of 25 methods.*
* [`ElencoAccessiGetQueryParamInternalServerError`](./src/anncsu/errors/elencoaccessigetqueryparaminternalservererror.py): Internal Server Error. Status code `500`. Applicable to 1 of 25 methods.*
* [`ElencoodonimiprogGetQueryParamInternalServerError`](./src/anncsu/errors/elencoodonimiproggetqueryparaminternalservererror.py): Internal Server Error. Status code `500`. Applicable to 1 of 25 methods.*
* [`ElencoaccessiprogGetQueryParamInternalServerError`](./src/anncsu/errors/elencoaccessiproggetqueryparaminternalservererror.py): Internal Server Error. Status code `500`. Applicable to 1 of 25 methods.*
* [`PrognazareaGetQueryParamInternalServerError`](./src/anncsu/errors/prognazareagetqueryparaminternalservererror.py): Internal Server Error. Status code `500`. Applicable to 1 of 25 methods.*
* [`PrognazaccGetQueryParamInternalServerError`](./src/anncsu/errors/prognazaccgetqueryparaminternalservererror.py): Internal Server Error. Status code `500`. Applicable to 1 of 25 methods.*
* [`EsisteOdonimoPostInternalServerError`](./src/anncsu/errors/esisteodonimopostinternalservererror.py): Internal Server Error. Status code `500`. Applicable to 1 of 25 methods.*
* [`EsisteAccessoPostInternalServerError`](./src/anncsu/errors/esisteaccessopostinternalservererror.py): Internal Server Error. Status code `500`. Applicable to 1 of 25 methods.*
* [`ElencoOdonimiPostInternalServerError`](./src/anncsu/errors/elencoodonimipostinternalservererror.py): Internal Server Error. Status code `500`. Applicable to 1 of 25 methods.*
* [`ElencoAccessiPostInternalServerError`](./src/anncsu/errors/elencoaccessipostinternalservererror.py): Internal Server Error. Status code `500`. Applicable to 1 of 25 methods.*
* [`ElencoodonimiprogPostInternalServerError`](./src/anncsu/errors/elencoodonimiprogpostinternalservererror.py): Internal Server Error. Status code `500`. Applicable to 1 of 25 methods.*
* [`ElencoaccessiprogPostInternalServerError`](./src/anncsu/errors/elencoaccessiprogpostinternalservererror.py): Internal Server Error. Status code `500`. Applicable to 1 of 25 methods.*
* [`PrognazareaPostInternalServerError`](./src/anncsu/errors/prognazareapostinternalservererror.py): Internal Server Error. Status code `500`. Applicable to 1 of 25 methods.*
* [`PrognazaccPostInternalServerError`](./src/anncsu/errors/prognazaccpostinternalservererror.py): Internal Server Error. Status code `500`. Applicable to 1 of 25 methods.*
* [`EsisteOdonimoGetPathParamInternalServerError`](./src/anncsu/errors/esisteodonimogetpathparaminternalservererror.py): Internal Server Error. Status code `500`. Applicable to 1 of 25 methods.*
* [`EsisteAccessoGetPathParamInternalServerError`](./src/anncsu/errors/esisteaccessogetpathparaminternalservererror.py): Internal Server Error. Status code `500`. Applicable to 1 of 25 methods.*
* [`ElencoOdonimiGetPathParamInternalServerError`](./src/anncsu/errors/elencoodonimigetpathparaminternalservererror.py): Internal Server Error. Status code `500`. Applicable to 1 of 25 methods.*
* [`ElencoAccessiGetPathParamInternalServerError`](./src/anncsu/errors/elencoaccessigetpathparaminternalservererror.py): Internal Server Error. Status code `500`. Applicable to 1 of 25 methods.*
* [`ElencoodonimiprogGetPathParamInternalServerError`](./src/anncsu/errors/elencoodonimiproggetpathparaminternalservererror.py): Internal Server Error. Status code `500`. Applicable to 1 of 25 methods.*
* [`ElencoaccessiprogGetPathParamInternalServerError`](./src/anncsu/errors/elencoaccessiproggetpathparaminternalservererror.py): Internal Server Error. Status code `500`. Applicable to 1 of 25 methods.*
* [`PrognazareaGetPathParamInternalServerError`](./src/anncsu/errors/prognazareagetpathparaminternalservererror.py): Internal Server Error. Status code `500`. Applicable to 1 of 25 methods.*
* [`PrognazaccGetPathParamInternalServerError`](./src/anncsu/errors/prognazaccgetpathparaminternalservererror.py): Internal Server Error. Status code `500`. Applicable to 1 of 25 methods.*
* [`ServiceUnavailableError`](./src/anncsu/errors/serviceunavailableerror.py): Il server non è disponibile. Status code `503`. Applicable to 1 of 25 methods.*
* [`ResponseValidationError`](./src/anncsu/errors/responsevalidationerror.py): Type mismatch between the response data and the expected Pydantic model. Provides access to the Pydantic validation error via the `cause` attribute.

</details>

\* Check [the method documentation](#available-resources-and-operations) to see if the error is applicable.
<!-- End Error Handling [errors] -->

<!-- Start Server Selection [server] -->
## Server Selection

### Override Server URL Per-Client

The default server can be overridden globally by passing a URL to the `server_url: str` optional parameter when initializing the SDK client instance. For example:
```python
from anncsu.pa import AnncsuConsultazione


with Anncsu(
    server_url="https://modipa.agenziaentrate.gov.it/govway/rest/in/AgenziaEntrate-PDND/anncsu-consultazione/v1",
) as a_client:

    res = a_client.queryparam.esiste_odonimo_get_query_param(codcom="H501", denom="VklBIFJPTUE=")

    # Handle response
    print(res)

```

### UAT Environment Configuration

When working with the UAT (User Acceptance Testing) environment, you may need to configure a different server URL and handle SSL certificate issues.

#### Basic UAT Configuration

```python
from anncsu.pa import AnncsuConsultazione
from anncsu.common import Security

sdk = AnncsuConsultazione(
    security=Security(bearer_auth=token_response.access_token),
    server_url="https://modipa-uat.agenziaentrate.gov.it/govway/rest/in/AgenziaEntrate-PDND/anncsu-consultazione/v1",
)
```

#### Disabling SSL Verification (UAT Only)

The UAT environment may use certificates that are not trusted by your system's certificate store. To bypass SSL verification **for testing purposes only**:

```python
import httpx
from anncsu.pa import AnncsuConsultazione
from anncsu.common import Security

# Create HTTP client with SSL verification disabled
client = httpx.Client(verify=False)

sdk = AnncsuConsultazione(
    security=Security(bearer_auth=token_response.access_token),
    server_url="https://modipa-uat.agenziaentrate.gov.it/govway/rest/in/AgenziaEntrate-PDND/anncsu-consultazione/v1",
    client=client,
)

# Make API calls
response = sdk.queryparam.esiste_odonimo_get_query_param(
    codcom="H501",
    denom="VklBIFJPTUE="
)
```

For async operations, also configure the async client:

```python
import httpx
from anncsu.pa import AnncsuConsultazione
from anncsu.common import Security

client = httpx.Client(verify=False)
async_client = httpx.AsyncClient(verify=False)

sdk = AnncsuConsultazione(
    security=Security(bearer_auth=token_response.access_token),
    server_url="https://modipa-uat.agenziaentrate.gov.it/govway/rest/in/AgenziaEntrate-PDND/anncsu-consultazione/v1",
    client=client,
    async_client=async_client,
)
```

> **Warning**: Never disable SSL verification in production! This should only be used for UAT/testing environments where the server uses self-signed or untrusted certificates.

#### Complete UAT Example

Here's a complete example for UAT environment with PDND authentication:

```python
import httpx
from pathlib import Path
from anncsu.pa import AnncsuConsultazione
from anncsu.common import (
    ClientAssertionConfig,
    create_client_assertion,
    TokenConfig,
    get_access_token,
    Security,
)

# Step 1: Create client assertion for UAT
assertion_config = ClientAssertionConfig(
    kid="your-key-id",
    issuer="your-client-id",
    subject="your-client-id",
    audience="auth.uat.interop.pagopa.it/client-assertion",  # UAT audience
    purpose_id="your-purpose-id",
    key_path=Path("./private_key.pem"),
)
client_assertion = create_client_assertion(assertion_config)

# Step 2: Exchange for access token (UAT token endpoint)
token_config = TokenConfig(
    client_id="your-client-id",
    client_assertion=client_assertion,
    token_endpoint="https://auth.uat.interop.pagopa.it/token.oauth2",  # UAT endpoint
)
token_response = get_access_token(token_config)

# Step 3: Create SDK with UAT configuration
client = httpx.Client(verify=False)  # Only for UAT!

sdk = AnncsuConsultazione(
    security=Security(bearer_auth=token_response.access_token),
    server_url="https://modipa-uat.agenziaentrate.gov.it/govway/rest/in/AgenziaEntrate-PDND/anncsu-consultazione/v1",
    client=client,
)

# Step 4: Make API calls
response = sdk.queryparam.esiste_odonimo_get_query_param(
    codcom="H501",
    denom="VklBIFJPTUE="
)
print(response)
```
<!-- End Server Selection [server] -->

<!-- Start Custom HTTP Client [http-client] -->
## Custom HTTP Client

The Python SDK makes API calls using the [httpx](https://www.python-httpx.org/) HTTP library.  In order to provide a convenient way to configure timeouts, cookies, proxies, custom headers, and other low-level configuration, you can initialize the SDK client with your own HTTP client instance.
Depending on whether you are using the sync or async version of the SDK, you can pass an instance of `HttpClient` or `AsyncHttpClient` respectively, which are Protocol's ensuring that the client has the necessary methods to make API calls.
This allows you to wrap the client with your own custom logic, such as adding custom headers, logging, or error handling, or you can just pass an instance of `httpx.Client` or `httpx.AsyncClient` directly.

For example, you could specify a header for every request that this sdk makes as follows:
```python
from anncsu.pa import AnncsuConsultazione
import httpx

http_client = httpx.Client(headers={"x-custom-header": "someValue"})
s = AnncsuConsultazione(client=http_client)
```

or you could wrap the client with your own custom logic:
```python
from anncsu.pa import AnncsuConsultazione
from anncsu.pa.httpclient import AsyncHttpClient
import httpx

class CustomClient(AsyncHttpClient):
    client: AsyncHttpClient

    def __init__(self, client: AsyncHttpClient):
        self.client = client

    async def send(
        self,
        request: httpx.Request,
        *,
        stream: bool = False,
        auth: Union[
            httpx._types.AuthTypes, httpx._client.UseClientDefault, None
        ] = httpx.USE_CLIENT_DEFAULT,
        follow_redirects: Union[
            bool, httpx._client.UseClientDefault
        ] = httpx.USE_CLIENT_DEFAULT,
    ) -> httpx.Response:
        request.headers["Client-Level-Header"] = "added by client"

        return await self.client.send(
            request, stream=stream, auth=auth, follow_redirects=follow_redirects
        )

    def build_request(
        self,
        method: str,
        url: httpx._types.URLTypes,
        *,
        content: Optional[httpx._types.RequestContent] = None,
        data: Optional[httpx._types.RequestData] = None,
        files: Optional[httpx._types.RequestFiles] = None,
        json: Optional[Any] = None,
        params: Optional[httpx._types.QueryParamTypes] = None,
        headers: Optional[httpx._types.HeaderTypes] = None,
        cookies: Optional[httpx._types.CookieTypes] = None,
        timeout: Union[
            httpx._types.TimeoutTypes, httpx._client.UseClientDefault
        ] = httpx.USE_CLIENT_DEFAULT,
        extensions: Optional[httpx._types.RequestExtensions] = None,
    ) -> httpx.Request:
        return self.client.build_request(
            method,
            url,
            content=content,
            data=data,
            files=files,
            json=json,
            params=params,
            headers=headers,
            cookies=cookies,
            timeout=timeout,
            extensions=extensions,
        )

s = AnncsuConsultazione(async_client=CustomClient(httpx.AsyncClient()))
```
<!-- End Custom HTTP Client [http-client] -->

<!-- Start Resource Management [resource-management] -->
## Resource Management

The `Anncsu` class implements the context manager protocol and registers a finalizer function to close the underlying sync and async HTTPX clients it uses under the hood. This will close HTTP connections, release memory and free up other resources held by the SDK. In short-lived Python programs and notebooks that make a few SDK method calls, resource management may not be a concern. However, in longer-lived programs, it is beneficial to create a single SDK instance via a [context manager][context-manager] and reuse it across the application.

[context-manager]: https://docs.python.org/3/reference/datamodel.html#context-managers

```python
from anncsu.pa import AnncsuConsultazione
def main():

    with Anncsu() as a_client:
        # Rest of application here...


# Or when using async:
async def amain():

    async with Anncsu() as a_client:
        # Rest of application here...
```
<!-- End Resource Management [resource-management] -->

<!-- Start Debugging [debug] -->
## Debugging

You can setup your SDK to emit debug logs for SDK requests and responses.

You can pass your own logger class directly into your SDK.
```python
from anncsu.pa import AnncsuConsultazione
import logging

logging.basicConfig(level=logging.DEBUG)
s = AnncsuConsultazione(debug_logger=logging.getLogger("anncsu"))
```

You can also enable a default debug logger by setting an environment variable `ANNCSU_DEBUG` to true.
<!-- End Debugging [debug] -->

<!-- Placeholder for Future Speakeasy SDK Sections -->

<!-- Start Architecture [architecture] -->
## Architecture

This SDK follows a modular architecture designed to support multiple ANNCSU API specifications:

### Package Structure

```
anncsu/
├── common/          # Shared infrastructure (utilities, types, HTTP client, base errors)
└── pa/              # API-specific: Consultazione per le PA
    ├── models/      # Request/response models
    ├── errors/      # Operation-specific errors
    └── sdk.py       # Main SDK class
```

### Shared Components (`anncsu.common`)

The `anncsu.common` package contains shared primitives used across all ANNCSU API clients:

- **Types**: Base models and type definitions (`BaseModel`, `OptionalNullable`, `UNSET`)
- **Utilities**: 16 utility modules for HTTP operations, serialization, retry logic, etc.
- **HTTP Infrastructure**: HTTP client wrappers, base SDK class, configuration
- **Hooks**: Before/after request hooks for customization
- **Base Errors**: Generic error classes (`AnncsuBaseError`, `APIError`, `NoResponseError`)

### Using Shared Components

When using advanced features like retry configuration, import from `anncsu.common`:

```python
from anncsu.pa import AnncsuConsultazione
from anncsu.common.utils import BackoffStrategy, RetryConfig  # Shared utilities
```

For regular SDK usage, you only need to import from `anncsu.pa`:

```python
from anncsu.pa import AnncsuConsultazione  # All you need for basic usage
```

### Multiple API Support

This architecture allows adding new ANNCSU API specifications (e.g., aggiornamento_accessi, coordinate, interni, odonimi) as separate packages under the `anncsu` namespace, all sharing the same infrastructure.

For more details, see [Refactoring Documentation](./docs/refactoring/REFACTORING_SUMMARY.md).
<!-- End Architecture [architecture] -->

<!-- Start Command Line Interface [cli] -->
## Command Line Interface

The SDK includes a command-line interface (`anncsu`) for managing PDND authentication and performing common operations without writing code.

### Quick Start

```bash
# Configure PDND credentials
anncsu config set --kid YOUR_KEY_ID --issuer YOUR_CLIENT_ID

# Login and obtain access token
anncsu auth login

# Check authentication status
anncsu auth status
```

### Key Features

- **Authentication Management**: Generate client assertions, obtain and refresh access tokens
- **Configuration**: Manage PDND credentials via CLI or environment variables
- **Standalone Utilities**: Create assertions independently for integration with other tools

### Documentation

For complete CLI documentation including all commands, options, and examples, see **[docs/CLI.md](docs/CLI.md)**.
<!-- End Command Line Interface [cli] -->

# Development

## Maturity

This SDK is in beta, and there may be breaking changes between versions without a major version update. Therefore, we recommend pinning usage
to a specific package version. This way, you can install the same version each time without breaking changes unless you are intentionally
looking for the latest version.

## Contributions

While we value open-source contributions to this SDK, this library is generated programmatically. Any manual changes added to internal files will be overwritten on the next generation.
We look forward to hearing your feedback. Feel free to open a PR or an issue with a proof of concept and we'll do our best to include it in a future release.

### SDK Created by [Speakeasy](https://www.speakeasy.com/?utm_source=anncsu&utm_campaign=python)


## Validate the specifications

### Development/Validation Environment
```shell
spectral lint oas/dev/Specifica\ API\ -\ ANNCSU\ –\ Consultazione\ per\ le\ PA.yaml --ruleset oas/.spectral.yaml
```

> [!NOTE]
> Production environment specification will be available in `oas/prod/` when provided by Agenzia delle Entrate.
