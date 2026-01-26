# Queryparam
(*queryparam*)

## Overview

Servizio con valori di input come parametro query in URI

### Available Operations

* [esiste_odonimo_get_query_param](#esiste_odonimo_get_query_param) - Ritorna un valore boolean dell'esistenza dell'odonimo in ANNCSU
* [esiste_accesso_get_query_param](#esiste_accesso_get_query_param) - Ritorna un valore boolean dell'esistenza dell'accesso in ANNCSU
* [elenco_odonimi_get_query_param](#elenco_odonimi_get_query_param) - Ritorna un elenco di odonimi presenti in ANNCSU
* [elenco_accessi_get_query_param](#elenco_accessi_get_query_param) - Ritorna un elenco di accessi presenti in ANNCSU
* [elencoodonimiprog_get_query_param](#elencoodonimiprog_get_query_param) - Ritorna un elenco di odonimi presenti in ANNCSU incluso il progressivo nazionale
* [elencoaccessiprog_get_query_param](#elencoaccessiprog_get_query_param) - Ritorna un elenco di accessi presenti in ANNCSU incluso il progressivo nazionale
* [prognazarea_get_query_param](#prognazarea_get_query_param) - Cerca in ANNCSU un odonimo per progressivo nazionale e ne ritorna i dati
* [prognazacc_get_query_param](#prognazacc_get_query_param) - Cerca in ANNCSU un accesso per progressivo nazionale accesso e ne ritorna i dati comprensivi dell'odonimo

## esiste_odonimo_get_query_param

Ritorna un valore boolean dell'esistenza dell'odonimo in ANNCSU

### Example Usage

<!-- UsageSnippet language="python" operationID="esisteOdonimoGetQueryParam" method="get" path="/esisteodonimo" -->
```python
from anncsu.pa import AnncsuConsultazione


with Anncsu() as a_client:

    res = a_client.queryparam.esiste_odonimo_get_query_param(codcom="H501", denom="VklBIFJPTUE=")

    # Handle response
    print(res)

```

### Parameters

| Parameter                                                           | Type                                                                | Required                                                            | Description                                                         | Example                                                             |
| ------------------------------------------------------------------- | ------------------------------------------------------------------- | ------------------------------------------------------------------- | ------------------------------------------------------------------- | ------------------------------------------------------------------- |
| `codcom`                                                            | *str*                                                               | :heavy_check_mark:                                                  | Codice Belfiore del comune dell'odonimo                             | H501                                                                |
| `denom`                                                             | *str*                                                               | :heavy_check_mark:                                                  | Denominazione esatta dell'odonimo - base64 encoded                  | VklBIFJPTUE=                                                        |
| `retries`                                                           | [Optional[utils.RetryConfig]](../../models/utils/retryconfig.md)    | :heavy_minus_sign:                                                  | Configuration to override the default retry behavior of the client. |                                                                     |

### Response

**[models.EsisteOdonimoGetQueryParamResponse](../../models/esisteodonimogetqueryparamresponse.md)**

### Errors

| Error Type                                                | Status Code                                               | Content Type                                              |
| --------------------------------------------------------- | --------------------------------------------------------- | --------------------------------------------------------- |
| errors.EsisteOdonimoGetQueryParamBadRequestError          | 400                                                       | application/problem+json                                  |
| errors.EsisteOdonimoGetQueryParamMethodNotAllowedError    | 405                                                       | application/problem+json                                  |
| errors.EsisteOdonimoGetQueryParamUnprocessableEntityError | 422                                                       | application/problem+json                                  |
| errors.EsisteOdonimoGetQueryParamInternalServerError      | 500                                                       | application/problem+json                                  |
| errors.APIError                                           | 4XX, 5XX                                                  | \*/\*                                                     |

## esiste_accesso_get_query_param

Ritorna un valore boolean dell'esistenza dell'accesso in ANNCSU

### Example Usage

<!-- UsageSnippet language="python" operationID="esisteAccessoGetQueryParam" method="get" path="/esisteaccesso" -->
```python
from anncsu.pa import AnncsuConsultazione


with Anncsu() as a_client:

    res = a_client.queryparam.esiste_accesso_get_query_param(codcom="H501", denom="VklBIFJPTUE=", accesso="42")

    # Handle response
    print(res)

```

### Parameters

| Parameter                                                           | Type                                                                | Required                                                            | Description                                                         | Example                                                             |
| ------------------------------------------------------------------- | ------------------------------------------------------------------- | ------------------------------------------------------------------- | ------------------------------------------------------------------- | ------------------------------------------------------------------- |
| `codcom`                                                            | *str*                                                               | :heavy_check_mark:                                                  | Codice Belfiore del comune dell'odonimo                             | H501                                                                |
| `denom`                                                             | *str*                                                               | :heavy_check_mark:                                                  | Denominazione esatta dell'odonimo - base64 encoded                  | VklBIFJPTUE=                                                        |
| `accesso`                                                           | *str*                                                               | :heavy_check_mark:                                                  | valore civico(+eventuale esponente e/o specificit�) oppure metrico  | 42                                                                  |
| `retries`                                                           | [Optional[utils.RetryConfig]](../../models/utils/retryconfig.md)    | :heavy_minus_sign:                                                  | Configuration to override the default retry behavior of the client. |                                                                     |

### Response

**[models.EsisteAccessoGetQueryParamResponse](../../models/esisteaccessogetqueryparamresponse.md)**

### Errors

| Error Type                                                | Status Code                                               | Content Type                                              |
| --------------------------------------------------------- | --------------------------------------------------------- | --------------------------------------------------------- |
| errors.EsisteAccessoGetQueryParamBadRequestError          | 400                                                       | application/problem+json                                  |
| errors.EsisteAccessoGetQueryParamMethodNotAllowedError    | 405                                                       | application/problem+json                                  |
| errors.EsisteAccessoGetQueryParamUnprocessableEntityError | 422                                                       | application/problem+json                                  |
| errors.EsisteAccessoGetQueryParamInternalServerError      | 500                                                       | application/problem+json                                  |
| errors.APIError                                           | 4XX, 5XX                                                  | \*/\*                                                     |

## elenco_odonimi_get_query_param

Ritorna un elenco di odonimi presenti in ANNCSU

### Example Usage

<!-- UsageSnippet language="python" operationID="elencoOdonimiGetQueryParam" method="get" path="/elencoodonimi" -->
```python
from anncsu.pa import AnncsuConsultazione


with Anncsu() as a_client:

    res = a_client.queryparam.elenco_odonimi_get_query_param(codcom="H501", denomparz="Uk9NQQ==")

    # Handle response
    print(res)

```

### Parameters

| Parameter                                                           | Type                                                                | Required                                                            | Description                                                         | Example                                                             |
| ------------------------------------------------------------------- | ------------------------------------------------------------------- | ------------------------------------------------------------------- | ------------------------------------------------------------------- | ------------------------------------------------------------------- |
| `codcom`                                                            | *str*                                                               | :heavy_check_mark:                                                  | Codice Belfiore del comune dell'odonimo                             | H501                                                                |
| `denomparz`                                                         | *str*                                                               | :heavy_check_mark:                                                  | Denominazione anche parziale dell'odonimo - base64 encoded          | Uk9NQQ==                                                            |
| `retries`                                                           | [Optional[utils.RetryConfig]](../../models/utils/retryconfig.md)    | :heavy_minus_sign:                                                  | Configuration to override the default retry behavior of the client. |                                                                     |

### Response

**[models.ElencoOdonimiGetQueryParamResponse](../../models/elencoodonimigetqueryparamresponse.md)**

### Errors

| Error Type                                                | Status Code                                               | Content Type                                              |
| --------------------------------------------------------- | --------------------------------------------------------- | --------------------------------------------------------- |
| errors.ElencoOdonimiGetQueryParamBadRequestError          | 400                                                       | application/problem+json                                  |
| errors.ElencoOdonimiGetQueryParamNotFoundError            | 404                                                       | application/problem+json                                  |
| errors.ElencoOdonimiGetQueryParamMethodNotAllowedError    | 405                                                       | application/problem+json                                  |
| errors.ElencoOdonimiGetQueryParamUnprocessableEntityError | 422                                                       | application/problem+json                                  |
| errors.ElencoOdonimiGetQueryParamInternalServerError      | 500                                                       | application/problem+json                                  |
| errors.APIError                                           | 4XX, 5XX                                                  | \*/\*                                                     |

## elenco_accessi_get_query_param

Ritorna un elenco di accessi presenti in ANNCSU

### Example Usage

<!-- UsageSnippet language="python" operationID="elencoAccessiGetQueryParam" method="get" path="/elencoaccessi" -->
```python
from anncsu.pa import AnncsuConsultazione


with Anncsu() as a_client:

    res = a_client.queryparam.elenco_accessi_get_query_param(codcom="H501", denom="VklBIFJPTUE=", accparz="42")

    # Handle response
    print(res)

```

### Parameters

| Parameter                                                                             | Type                                                                                  | Required                                                                              | Description                                                                           | Example                                                                               |
| ------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------- |
| `codcom`                                                                              | *str*                                                                                 | :heavy_check_mark:                                                                    | Codice Belfiore del comune dell'odonimo                                               | H501                                                                                  |
| `denom`                                                                               | *str*                                                                                 | :heavy_check_mark:                                                                    | Denominazione esatta dell'odonimo - base64 encoded                                    | VklBIFJPTUE=                                                                          |
| `accparz`                                                                             | *str*                                                                                 | :heavy_check_mark:                                                                    | valore anche parziale del civico(+eventuale esponente e/o specificit�) oppure metrico | 42                                                                                    |
| `retries`                                                                             | [Optional[utils.RetryConfig]](../../models/utils/retryconfig.md)                      | :heavy_minus_sign:                                                                    | Configuration to override the default retry behavior of the client.                   |                                                                                       |

### Response

**[models.ElencoAccessiGetQueryParamResponse](../../models/elencoaccessigetqueryparamresponse.md)**

### Errors

| Error Type                                                | Status Code                                               | Content Type                                              |
| --------------------------------------------------------- | --------------------------------------------------------- | --------------------------------------------------------- |
| errors.ElencoAccessiGetQueryParamBadRequestError          | 400                                                       | application/problem+json                                  |
| errors.ElencoAccessiGetQueryParamNotFoundError            | 404                                                       | application/problem+json                                  |
| errors.ElencoAccessiGetQueryParamMethodNotAllowedError    | 405                                                       | application/problem+json                                  |
| errors.ElencoAccessiGetQueryParamUnprocessableEntityError | 422                                                       | application/problem+json                                  |
| errors.ElencoAccessiGetQueryParamInternalServerError      | 500                                                       | application/problem+json                                  |
| errors.APIError                                           | 4XX, 5XX                                                  | \*/\*                                                     |

## elencoodonimiprog_get_query_param

Ritorna un elenco di odonimi presenti in ANNCSU incluso il progressivo nazionale

### Example Usage

<!-- UsageSnippet language="python" operationID="elencoodonimiprogGetQueryParam" method="get" path="/elencoodonimiprog" -->
```python
from anncsu.pa import AnncsuConsultazione


with Anncsu() as a_client:

    res = a_client.queryparam.elencoodonimiprog_get_query_param(codcom="H501", denomparz="Uk9NQQ==")

    # Handle response
    print(res)

```

### Parameters

| Parameter                                                           | Type                                                                | Required                                                            | Description                                                         | Example                                                             |
| ------------------------------------------------------------------- | ------------------------------------------------------------------- | ------------------------------------------------------------------- | ------------------------------------------------------------------- | ------------------------------------------------------------------- |
| `codcom`                                                            | *str*                                                               | :heavy_check_mark:                                                  | Codice Belfiore del comune dell'odonimo                             | H501                                                                |
| `denomparz`                                                         | *str*                                                               | :heavy_check_mark:                                                  | Denominazione anche parziale dell'odonimo - base64 encoded          | Uk9NQQ==                                                            |
| `retries`                                                           | [Optional[utils.RetryConfig]](../../models/utils/retryconfig.md)    | :heavy_minus_sign:                                                  | Configuration to override the default retry behavior of the client. |                                                                     |

### Response

**[models.ElencoodonimiprogGetQueryParamResponse](../../models/elencoodonimiproggetqueryparamresponse.md)**

### Errors

| Error Type                                                    | Status Code                                                   | Content Type                                                  |
| ------------------------------------------------------------- | ------------------------------------------------------------- | ------------------------------------------------------------- |
| errors.ElencoodonimiprogGetQueryParamBadRequestError          | 400                                                           | application/problem+json                                      |
| errors.ElencoodonimiprogGetQueryParamNotFoundError            | 404                                                           | application/problem+json                                      |
| errors.ElencoodonimiprogGetQueryParamMethodNotAllowedError    | 405                                                           | application/problem+json                                      |
| errors.ElencoodonimiprogGetQueryParamUnprocessableEntityError | 422                                                           | application/problem+json                                      |
| errors.ElencoodonimiprogGetQueryParamInternalServerError      | 500                                                           | application/problem+json                                      |
| errors.APIError                                               | 4XX, 5XX                                                      | \*/\*                                                         |

## elencoaccessiprog_get_query_param

Ritorna un elenco di accessi presenti in ANNCSU incluso il progressivo nazionale

### Example Usage

<!-- UsageSnippet language="python" operationID="elencoaccessiprogGetQueryParam" method="get" path="/elencoaccessiprog" -->
```python
from anncsu.pa import AnncsuConsultazione


with Anncsu() as a_client:

    res = a_client.queryparam.elencoaccessiprog_get_query_param(prognaz="919572", accparz="42")

    # Handle response
    print(res)

```

### Parameters

| Parameter                                                                             | Type                                                                                  | Required                                                                              | Description                                                                           | Example                                                                               |
| ------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------- |
| `prognaz`                                                                             | *str*                                                                                 | :heavy_check_mark:                                                                    | Progressivo nazionale dell'odonimo                                                    | 919572                                                                                |
| `accparz`                                                                             | *str*                                                                                 | :heavy_check_mark:                                                                    | valore anche parziale del civico(+eventuale esponente e/o specificit�) oppure metrico | 42                                                                                    |
| `retries`                                                                             | [Optional[utils.RetryConfig]](../../models/utils/retryconfig.md)                      | :heavy_minus_sign:                                                                    | Configuration to override the default retry behavior of the client.                   |                                                                                       |

### Response

**[models.ElencoaccessiprogGetQueryParamResponse](../../models/elencoaccessiproggetqueryparamresponse.md)**

### Errors

| Error Type                                                    | Status Code                                                   | Content Type                                                  |
| ------------------------------------------------------------- | ------------------------------------------------------------- | ------------------------------------------------------------- |
| errors.ElencoaccessiprogGetQueryParamBadRequestError          | 400                                                           | application/problem+json                                      |
| errors.ElencoaccessiprogGetQueryParamNotFoundError            | 404                                                           | application/problem+json                                      |
| errors.ElencoaccessiprogGetQueryParamMethodNotAllowedError    | 405                                                           | application/problem+json                                      |
| errors.ElencoaccessiprogGetQueryParamUnprocessableEntityError | 422                                                           | application/problem+json                                      |
| errors.ElencoaccessiprogGetQueryParamInternalServerError      | 500                                                           | application/problem+json                                      |
| errors.APIError                                               | 4XX, 5XX                                                      | \*/\*                                                         |

## prognazarea_get_query_param

Cerca in ANNCSU un odonimo per progressivo nazionale e ne ritorna i dati

### Example Usage

<!-- UsageSnippet language="python" operationID="prognazareaGetQueryParam" method="get" path="/prognazarea" -->
```python
from anncsu.pa import AnncsuConsultazione


with Anncsu() as a_client:

    res = a_client.queryparam.prognazarea_get_query_param(prognaz="919572")

    # Handle response
    print(res)

```

### Parameters

| Parameter                                                           | Type                                                                | Required                                                            | Description                                                         | Example                                                             |
| ------------------------------------------------------------------- | ------------------------------------------------------------------- | ------------------------------------------------------------------- | ------------------------------------------------------------------- | ------------------------------------------------------------------- |
| `prognaz`                                                           | *str*                                                               | :heavy_check_mark:                                                  | Progressivo nazionale dell'odonimo                                  | 919572                                                              |
| `retries`                                                           | [Optional[utils.RetryConfig]](../../models/utils/retryconfig.md)    | :heavy_minus_sign:                                                  | Configuration to override the default retry behavior of the client. |                                                                     |

### Response

**[models.PrognazareaGetQueryParamResponse](../../models/prognazareagetqueryparamresponse.md)**

### Errors

| Error Type                                              | Status Code                                             | Content Type                                            |
| ------------------------------------------------------- | ------------------------------------------------------- | ------------------------------------------------------- |
| errors.PrognazareaGetQueryParamBadRequestError          | 400                                                     | application/problem+json                                |
| errors.PrognazareaGetQueryParamNotFoundError            | 404                                                     | application/problem+json                                |
| errors.PrognazareaGetQueryParamMethodNotAllowedError    | 405                                                     | application/problem+json                                |
| errors.PrognazareaGetQueryParamUnprocessableEntityError | 422                                                     | application/problem+json                                |
| errors.PrognazareaGetQueryParamInternalServerError      | 500                                                     | application/problem+json                                |
| errors.APIError                                         | 4XX, 5XX                                                | \*/\*                                                   |

## prognazacc_get_query_param

Cerca in ANNCSU un accesso per progressivo nazionale accesso e ne ritorna i dati comprensivi dell'odonimo

### Example Usage

<!-- UsageSnippet language="python" operationID="prognazaccGetQueryParam" method="get" path="/prognazacc" -->
```python
from anncsu.pa import AnncsuConsultazione


with Anncsu() as a_client:

    res = a_client.queryparam.prognazacc_get_query_param(prognazacc="6744962")

    # Handle response
    print(res)

```

### Parameters

| Parameter                                                           | Type                                                                | Required                                                            | Description                                                         | Example                                                             |
| ------------------------------------------------------------------- | ------------------------------------------------------------------- | ------------------------------------------------------------------- | ------------------------------------------------------------------- | ------------------------------------------------------------------- |
| `prognazacc`                                                        | *str*                                                               | :heavy_check_mark:                                                  | Progressivo nazionale dell'accesso                                  | 6744962                                                             |
| `retries`                                                           | [Optional[utils.RetryConfig]](../../models/utils/retryconfig.md)    | :heavy_minus_sign:                                                  | Configuration to override the default retry behavior of the client. |                                                                     |

### Response

**[models.PrognazaccGetQueryParamResponse](../../models/prognazaccgetqueryparamresponse.md)**

### Errors

| Error Type                                             | Status Code                                            | Content Type                                           |
| ------------------------------------------------------ | ------------------------------------------------------ | ------------------------------------------------------ |
| errors.PrognazaccGetQueryParamBadRequestError          | 400                                                    | application/problem+json                               |
| errors.PrognazaccGetQueryParamNotFoundError            | 404                                                    | application/problem+json                               |
| errors.PrognazaccGetQueryParamMethodNotAllowedError    | 405                                                    | application/problem+json                               |
| errors.PrognazaccGetQueryParamUnprocessableEntityError | 422                                                    | application/problem+json                               |
| errors.PrognazaccGetQueryParamInternalServerError      | 500                                                    | application/problem+json                               |
| errors.APIError                                        | 4XX, 5XX                                               | \*/\*                                                  |
