# JSONPost
(*json_post*)

## Overview

Servizio con valori di input in file JSON sottomesso POST

### Available Operations

* [esiste_odonimo_post](#esiste_odonimo_post) - Ritorna un valore boolean dell'esistenza dell'odonimo in ANNCSU
* [esiste_accesso_post](#esiste_accesso_post) - Ritorna un valore boolean dell'esistenza dell'accesso in ANNCSU
* [elenco_odonimi_post](#elenco_odonimi_post) - Ritorna un elenco di odonimi presenti in ANNCSU
* [elenco_accessi_post](#elenco_accessi_post) - Ritorna un elenco di accessi presenti in ANNCSU
* [elencoodonimiprog_post](#elencoodonimiprog_post) - Ritorna un elenco di odonimi presenti in ANNCSU incluso il progressivo nazionale
* [elencoaccessiprog_post](#elencoaccessiprog_post) - Ritorna un elenco di accessi presenti in ANNCSU incluso il progressivo nazionale
* [prognazarea_post](#prognazarea_post) - Cerca in ANNCSU un odonimo per progressivo nazionale e ne ritorna i dati
* [prognazacc_post](#prognazacc_post) - Cerca in ANNCSU un accesso per progressivo nazionale accesso e ne ritorna i dati comprensivi dell'odonimo

## esiste_odonimo_post

Ritorna un valore boolean dell'esistenza dell'odonimo in ANNCSU

### Example Usage

<!-- UsageSnippet language="python" operationID="esisteOdonimoPost" method="post" path="/esisteodonimo" -->
```python
from anncsu.pa import AnncsuConsultazione


with Anncsu() as a_client:

    res = a_client.json_post.esiste_odonimo_post(req="esisteodonimo", codcom="H501", denom="VIA ROMA")

    # Handle response
    print(res)

```

### Parameters

| Parameter                                                           | Type                                                                | Required                                                            | Description                                                         | Example                                                             |
| ------------------------------------------------------------------- | ------------------------------------------------------------------- | ------------------------------------------------------------------- | ------------------------------------------------------------------- | ------------------------------------------------------------------- |
| `req`                                                               | *Optional[str]*                                                     | :heavy_minus_sign:                                                  | N/A                                                                 | esisteodonimo                                                       |
| `codcom`                                                            | *Optional[str]*                                                     | :heavy_minus_sign:                                                  | N/A                                                                 | H501                                                                |
| `denom`                                                             | *Optional[str]*                                                     | :heavy_minus_sign:                                                  | N/A                                                                 | VIA ROMA                                                            |
| `retries`                                                           | [Optional[utils.RetryConfig]](../../models/utils/retryconfig.md)    | :heavy_minus_sign:                                                  | Configuration to override the default retry behavior of the client. |                                                                     |

### Response

**[models.EsisteOdonimoPostResponse](../../models/esisteodonimopostresponse.md)**

### Errors

| Error Type                                       | Status Code                                      | Content Type                                     |
| ------------------------------------------------ | ------------------------------------------------ | ------------------------------------------------ |
| errors.EsisteOdonimoPostBadRequestError          | 400                                              | application/problem+json                         |
| errors.EsisteOdonimoPostMethodNotAllowedError    | 405                                              | application/problem+json                         |
| errors.EsisteOdonimoPostUnprocessableEntityError | 422                                              | application/problem+json                         |
| errors.EsisteOdonimoPostInternalServerError      | 500                                              | application/problem+json                         |
| errors.APIError                                  | 4XX, 5XX                                         | \*/\*                                            |

## esiste_accesso_post

Ritorna un valore boolean dell'esistenza dell'accesso in ANNCSU

### Example Usage

<!-- UsageSnippet language="python" operationID="esisteAccessoPost" method="post" path="/esisteaccesso" -->
```python
from anncsu.pa import AnncsuConsultazione


with Anncsu() as a_client:

    res = a_client.json_post.esiste_accesso_post(req="esisteaccesso", codcom="H501", denom="VIA ROMA", accesso="42")

    # Handle response
    print(res)

```

### Parameters

| Parameter                                                           | Type                                                                | Required                                                            | Description                                                         | Example                                                             |
| ------------------------------------------------------------------- | ------------------------------------------------------------------- | ------------------------------------------------------------------- | ------------------------------------------------------------------- | ------------------------------------------------------------------- |
| `req`                                                               | *Optional[str]*                                                     | :heavy_minus_sign:                                                  | N/A                                                                 | esisteaccesso                                                       |
| `codcom`                                                            | *Optional[str]*                                                     | :heavy_minus_sign:                                                  | N/A                                                                 | H501                                                                |
| `denom`                                                             | *Optional[str]*                                                     | :heavy_minus_sign:                                                  | N/A                                                                 | VIA ROMA                                                            |
| `accesso`                                                           | *Optional[str]*                                                     | :heavy_minus_sign:                                                  | N/A                                                                 | 42                                                                  |
| `retries`                                                           | [Optional[utils.RetryConfig]](../../models/utils/retryconfig.md)    | :heavy_minus_sign:                                                  | Configuration to override the default retry behavior of the client. |                                                                     |

### Response

**[models.EsisteAccessoPostResponse](../../models/esisteaccessopostresponse.md)**

### Errors

| Error Type                                       | Status Code                                      | Content Type                                     |
| ------------------------------------------------ | ------------------------------------------------ | ------------------------------------------------ |
| errors.EsisteAccessoPostBadRequestError          | 400                                              | application/problem+json                         |
| errors.EsisteAccessoPostMethodNotAllowedError    | 405                                              | application/problem+json                         |
| errors.EsisteAccessoPostUnprocessableEntityError | 422                                              | application/problem+json                         |
| errors.EsisteAccessoPostInternalServerError      | 500                                              | application/problem+json                         |
| errors.APIError                                  | 4XX, 5XX                                         | \*/\*                                            |

## elenco_odonimi_post

Ritorna un elenco di odonimi presenti in ANNCSU

### Example Usage

<!-- UsageSnippet language="python" operationID="elencoOdonimiPost" method="post" path="/elencoodonimi" -->
```python
from anncsu.pa import AnncsuConsultazione


with Anncsu() as a_client:

    res = a_client.json_post.elenco_odonimi_post(req="elencoodonimi", codcom="H501", denomparz="ROMA")

    # Handle response
    print(res)

```

### Parameters

| Parameter                                                           | Type                                                                | Required                                                            | Description                                                         | Example                                                             |
| ------------------------------------------------------------------- | ------------------------------------------------------------------- | ------------------------------------------------------------------- | ------------------------------------------------------------------- | ------------------------------------------------------------------- |
| `req`                                                               | *Optional[str]*                                                     | :heavy_minus_sign:                                                  | N/A                                                                 | elencoodonimi                                                       |
| `codcom`                                                            | *Optional[str]*                                                     | :heavy_minus_sign:                                                  | N/A                                                                 | H501                                                                |
| `denomparz`                                                         | *Optional[str]*                                                     | :heavy_minus_sign:                                                  | N/A                                                                 | ROMA                                                                |
| `retries`                                                           | [Optional[utils.RetryConfig]](../../models/utils/retryconfig.md)    | :heavy_minus_sign:                                                  | Configuration to override the default retry behavior of the client. |                                                                     |

### Response

**[models.ElencoOdonimiPostResponse](../../models/elencoodonimipostresponse.md)**

### Errors

| Error Type                                       | Status Code                                      | Content Type                                     |
| ------------------------------------------------ | ------------------------------------------------ | ------------------------------------------------ |
| errors.ElencoOdonimiPostBadRequestError          | 400                                              | application/problem+json                         |
| errors.ElencoOdonimiPostNotFoundError            | 404                                              | application/problem+json                         |
| errors.ElencoOdonimiPostMethodNotAllowedError    | 405                                              | application/problem+json                         |
| errors.ElencoOdonimiPostUnprocessableEntityError | 422                                              | application/problem+json                         |
| errors.ElencoOdonimiPostInternalServerError      | 500                                              | application/problem+json                         |
| errors.APIError                                  | 4XX, 5XX                                         | \*/\*                                            |

## elenco_accessi_post

Ritorna un elenco di accessi presenti in ANNCSU

### Example Usage

<!-- UsageSnippet language="python" operationID="elencoAccessiPost" method="post" path="/elencoaccessi" -->
```python
from anncsu.pa import AnncsuConsultazione


with Anncsu() as a_client:

    res = a_client.json_post.elenco_accessi_post(req="elencoaccessi", codcom="H501", denom="VIA ROMA", accparz="42")

    # Handle response
    print(res)

```

### Parameters

| Parameter                                                           | Type                                                                | Required                                                            | Description                                                         | Example                                                             |
| ------------------------------------------------------------------- | ------------------------------------------------------------------- | ------------------------------------------------------------------- | ------------------------------------------------------------------- | ------------------------------------------------------------------- |
| `req`                                                               | *Optional[str]*                                                     | :heavy_minus_sign:                                                  | N/A                                                                 | elencoaccessi                                                       |
| `codcom`                                                            | *Optional[str]*                                                     | :heavy_minus_sign:                                                  | N/A                                                                 | H501                                                                |
| `denom`                                                             | *Optional[str]*                                                     | :heavy_minus_sign:                                                  | N/A                                                                 | VIA ROMA                                                            |
| `accparz`                                                           | *Optional[str]*                                                     | :heavy_minus_sign:                                                  | N/A                                                                 | 42                                                                  |
| `retries`                                                           | [Optional[utils.RetryConfig]](../../models/utils/retryconfig.md)    | :heavy_minus_sign:                                                  | Configuration to override the default retry behavior of the client. |                                                                     |

### Response

**[models.ElencoAccessiPostResponse](../../models/elencoaccessipostresponse.md)**

### Errors

| Error Type                                       | Status Code                                      | Content Type                                     |
| ------------------------------------------------ | ------------------------------------------------ | ------------------------------------------------ |
| errors.ElencoAccessiPostBadRequestError          | 400                                              | application/problem+json                         |
| errors.ElencoAccessiPostNotFoundError            | 404                                              | application/problem+json                         |
| errors.ElencoAccessiPostMethodNotAllowedError    | 405                                              | application/problem+json                         |
| errors.ElencoAccessiPostUnprocessableEntityError | 422                                              | application/problem+json                         |
| errors.ElencoAccessiPostInternalServerError      | 500                                              | application/problem+json                         |
| errors.APIError                                  | 4XX, 5XX                                         | \*/\*                                            |

## elencoodonimiprog_post

Ritorna un elenco di odonimi presenti in ANNCSU incluso il progressivo nazionale

### Example Usage

<!-- UsageSnippet language="python" operationID="elencoodonimiprogPost" method="post" path="/elencoodonimiprog" -->
```python
from anncsu.pa import AnncsuConsultazione


with Anncsu() as a_client:

    res = a_client.json_post.elencoodonimiprog_post(req="elencoodonimiprog", codcom="H501", denomparz="ROMA")

    # Handle response
    print(res)

```

### Parameters

| Parameter                                                           | Type                                                                | Required                                                            | Description                                                         | Example                                                             |
| ------------------------------------------------------------------- | ------------------------------------------------------------------- | ------------------------------------------------------------------- | ------------------------------------------------------------------- | ------------------------------------------------------------------- |
| `req`                                                               | *Optional[str]*                                                     | :heavy_minus_sign:                                                  | N/A                                                                 | elencoodonimiprog                                                   |
| `codcom`                                                            | *Optional[str]*                                                     | :heavy_minus_sign:                                                  | N/A                                                                 | H501                                                                |
| `denomparz`                                                         | *Optional[str]*                                                     | :heavy_minus_sign:                                                  | N/A                                                                 | ROMA                                                                |
| `retries`                                                           | [Optional[utils.RetryConfig]](../../models/utils/retryconfig.md)    | :heavy_minus_sign:                                                  | Configuration to override the default retry behavior of the client. |                                                                     |

### Response

**[models.ElencoodonimiprogPostResponse](../../models/elencoodonimiprogpostresponse.md)**

### Errors

| Error Type                                           | Status Code                                          | Content Type                                         |
| ---------------------------------------------------- | ---------------------------------------------------- | ---------------------------------------------------- |
| errors.ElencoodonimiprogPostBadRequestError          | 400                                                  | application/problem+json                             |
| errors.ElencoodonimiprogPostNotFoundError            | 404                                                  | application/problem+json                             |
| errors.ElencoodonimiprogPostMethodNotAllowedError    | 405                                                  | application/problem+json                             |
| errors.ElencoodonimiprogPostUnprocessableEntityError | 422                                                  | application/problem+json                             |
| errors.ElencoodonimiprogPostInternalServerError      | 500                                                  | application/problem+json                             |
| errors.APIError                                      | 4XX, 5XX                                             | \*/\*                                                |

## elencoaccessiprog_post

Ritorna un elenco di accessi presenti in ANNCSU incluso il progressivo nazionale

### Example Usage

<!-- UsageSnippet language="python" operationID="elencoaccessiprogPost" method="post" path="/elencoaccessiprog" -->
```python
from anncsu.pa import AnncsuConsultazione


with Anncsu() as a_client:

    res = a_client.json_post.elencoaccessiprog_post(req="elencoaccessiprog", prognaz="919572", accparz="42")

    # Handle response
    print(res)

```

### Parameters

| Parameter                                                           | Type                                                                | Required                                                            | Description                                                         | Example                                                             |
| ------------------------------------------------------------------- | ------------------------------------------------------------------- | ------------------------------------------------------------------- | ------------------------------------------------------------------- | ------------------------------------------------------------------- |
| `req`                                                               | *Optional[str]*                                                     | :heavy_minus_sign:                                                  | N/A                                                                 | elencoaccessiprog                                                   |
| `prognaz`                                                           | *Optional[str]*                                                     | :heavy_minus_sign:                                                  | N/A                                                                 | 919572                                                              |
| `accparz`                                                           | *Optional[str]*                                                     | :heavy_minus_sign:                                                  | N/A                                                                 | 42                                                                  |
| `retries`                                                           | [Optional[utils.RetryConfig]](../../models/utils/retryconfig.md)    | :heavy_minus_sign:                                                  | Configuration to override the default retry behavior of the client. |                                                                     |

### Response

**[models.ElencoaccessiprogPostResponse](../../models/elencoaccessiprogpostresponse.md)**

### Errors

| Error Type                                           | Status Code                                          | Content Type                                         |
| ---------------------------------------------------- | ---------------------------------------------------- | ---------------------------------------------------- |
| errors.ElencoaccessiprogPostBadRequestError          | 400                                                  | application/problem+json                             |
| errors.ElencoaccessiprogPostNotFoundError            | 404                                                  | application/problem+json                             |
| errors.ElencoaccessiprogPostMethodNotAllowedError    | 405                                                  | application/problem+json                             |
| errors.ElencoaccessiprogPostUnprocessableEntityError | 422                                                  | application/problem+json                             |
| errors.ElencoaccessiprogPostInternalServerError      | 500                                                  | application/problem+json                             |
| errors.APIError                                      | 4XX, 5XX                                             | \*/\*                                                |

## prognazarea_post

Cerca in ANNCSU un odonimo per progressivo nazionale e ne ritorna i dati

### Example Usage

<!-- UsageSnippet language="python" operationID="prognazareaPost" method="post" path="/prognazarea" -->
```python
from anncsu.pa import AnncsuConsultazione


with Anncsu() as a_client:

    res = a_client.json_post.prognazarea_post(req="prognazarea", prognaz="919572")

    # Handle response
    print(res)

```

### Parameters

| Parameter                                                           | Type                                                                | Required                                                            | Description                                                         | Example                                                             |
| ------------------------------------------------------------------- | ------------------------------------------------------------------- | ------------------------------------------------------------------- | ------------------------------------------------------------------- | ------------------------------------------------------------------- |
| `req`                                                               | *Optional[str]*                                                     | :heavy_minus_sign:                                                  | N/A                                                                 | prognazarea                                                         |
| `prognaz`                                                           | *Optional[str]*                                                     | :heavy_minus_sign:                                                  | N/A                                                                 | 919572                                                              |
| `retries`                                                           | [Optional[utils.RetryConfig]](../../models/utils/retryconfig.md)    | :heavy_minus_sign:                                                  | Configuration to override the default retry behavior of the client. |                                                                     |

### Response

**[models.PrognazareaPostResponse](../../models/prognazareapostresponse.md)**

### Errors

| Error Type                                     | Status Code                                    | Content Type                                   |
| ---------------------------------------------- | ---------------------------------------------- | ---------------------------------------------- |
| errors.PrognazareaPostBadRequestError          | 400                                            | application/problem+json                       |
| errors.PrognazareaPostNotFoundError            | 404                                            | application/problem+json                       |
| errors.PrognazareaPostMethodNotAllowedError    | 405                                            | application/problem+json                       |
| errors.PrognazareaPostUnprocessableEntityError | 422                                            | application/problem+json                       |
| errors.PrognazareaPostInternalServerError      | 500                                            | application/problem+json                       |
| errors.APIError                                | 4XX, 5XX                                       | \*/\*                                          |

## prognazacc_post

Cerca in ANNCSU un accesso per progressivo nazionale accesso e ne ritorna i dati comprensivi dell'odonimo

### Example Usage

<!-- UsageSnippet language="python" operationID="prognazaccPost" method="post" path="/prognazacc" -->
```python
from anncsu.pa import AnncsuConsultazione


with Anncsu() as a_client:

    res = a_client.json_post.prognazacc_post(req="prognazacc", prognazacc="6744962")

    # Handle response
    print(res)

```

### Parameters

| Parameter                                                           | Type                                                                | Required                                                            | Description                                                         | Example                                                             |
| ------------------------------------------------------------------- | ------------------------------------------------------------------- | ------------------------------------------------------------------- | ------------------------------------------------------------------- | ------------------------------------------------------------------- |
| `req`                                                               | *Optional[str]*                                                     | :heavy_minus_sign:                                                  | N/A                                                                 | prognazacc                                                          |
| `prognazacc`                                                        | *Optional[str]*                                                     | :heavy_minus_sign:                                                  | N/A                                                                 | 6744962                                                             |
| `retries`                                                           | [Optional[utils.RetryConfig]](../../models/utils/retryconfig.md)    | :heavy_minus_sign:                                                  | Configuration to override the default retry behavior of the client. |                                                                     |

### Response

**[models.PrognazaccPostResponse](../../models/prognazaccpostresponse.md)**

### Errors

| Error Type                                    | Status Code                                   | Content Type                                  |
| --------------------------------------------- | --------------------------------------------- | --------------------------------------------- |
| errors.PrognazaccPostBadRequestError          | 400                                           | application/problem+json                      |
| errors.PrognazaccPostNotFoundError            | 404                                           | application/problem+json                      |
| errors.PrognazaccPostMethodNotAllowedError    | 405                                           | application/problem+json                      |
| errors.PrognazaccPostUnprocessableEntityError | 422                                           | application/problem+json                      |
| errors.PrognazaccPostInternalServerError      | 500                                           | application/problem+json                      |
| errors.APIError                               | 4XX, 5XX                                      | \*/\*                                         |
