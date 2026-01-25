# Pathparam
(*pathparam*)

## Overview

Servizio con valori di input come parametro path in URI

### Available Operations

* [esiste_odonimo_get_path_param](#esiste_odonimo_get_path_param) - Ritorna un valore boolean dell'esistenza dell'odonimo in ANNCSU
* [esiste_accesso_get_path_param](#esiste_accesso_get_path_param) - Ritorna un valore boolean dell'esistenza dell'accesso in ANNCSU
* [elenco_odonimi_get_path_param](#elenco_odonimi_get_path_param) - Ritorna un elenco di odonimi presenti in ANNCSU
* [elenco_accessi_get_path_param](#elenco_accessi_get_path_param) - Ritorna un elenco di accessi presenti in ANNCSU
* [elencoodonimiprog_get_path_param](#elencoodonimiprog_get_path_param) - Ritorna un elenco di odonimi presenti in ANNCSU incluso il progressivo nazionale
* [elencoaccessiprog_get_path_param](#elencoaccessiprog_get_path_param) - Ritorna un elenco di accessi presenti in ANNCSU incluso il progressivo nazionale
* [prognazarea_get_path_param](#prognazarea_get_path_param) - Cerca in ANNCSU un odonimo per progressivo nazionale e ne ritorna i dati
* [prognazacc_get_path_param](#prognazacc_get_path_param) - Cerca in ANNCSU un accesso per progressivo nazionale accesso e ne ritorna i dati comprensivi dell'odonimo

## esiste_odonimo_get_path_param

Ritorna un valore boolean dell'esistenza dell'odonimo in ANNCSU

### Example Usage

<!-- UsageSnippet language="python" operationID="esisteOdonimoGetPathParam" method="get" path="/esisteodonimo/{codcom}/{denom}" -->
```python
from anncsu.pa import AnncsuConsultazione


with Anncsu() as a_client:

    res = a_client.pathparam.esiste_odonimo_get_path_param(codcom="H501", denom="VklBIFJPTUE=")

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

**[models.EsisteOdonimoGetPathParamResponse](../../models/esisteodonimogetpathparamresponse.md)**

### Errors

| Error Type                                               | Status Code                                              | Content Type                                             |
| -------------------------------------------------------- | -------------------------------------------------------- | -------------------------------------------------------- |
| errors.EsisteOdonimoGetPathParamBadRequestError          | 400                                                      | application/problem+json                                 |
| errors.EsisteOdonimoGetPathParamMethodNotAllowedError    | 405                                                      | application/problem+json                                 |
| errors.EsisteOdonimoGetPathParamUnprocessableEntityError | 422                                                      | application/problem+json                                 |
| errors.EsisteOdonimoGetPathParamInternalServerError      | 500                                                      | application/problem+json                                 |
| errors.APIError                                          | 4XX, 5XX                                                 | \*/\*                                                    |

## esiste_accesso_get_path_param

Ritorna un valore boolean dell'esistenza dell'accesso in ANNCSU

### Example Usage

<!-- UsageSnippet language="python" operationID="esisteAccessoGetPathParam" method="get" path="/esisteaccesso/{codcom}/{denom}/{accesso}" -->
```python
from anncsu.pa import AnncsuConsultazione


with Anncsu() as a_client:

    res = a_client.pathparam.esiste_accesso_get_path_param(codcom="H501", denom="VklBIFJPTUE=", accesso="42")

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

**[models.EsisteAccessoGetPathParamResponse](../../models/esisteaccessogetpathparamresponse.md)**

### Errors

| Error Type                                               | Status Code                                              | Content Type                                             |
| -------------------------------------------------------- | -------------------------------------------------------- | -------------------------------------------------------- |
| errors.EsisteAccessoGetPathParamBadRequestError          | 400                                                      | application/problem+json                                 |
| errors.EsisteAccessoGetPathParamMethodNotAllowedError    | 405                                                      | application/problem+json                                 |
| errors.EsisteAccessoGetPathParamUnprocessableEntityError | 422                                                      | application/problem+json                                 |
| errors.EsisteAccessoGetPathParamInternalServerError      | 500                                                      | application/problem+json                                 |
| errors.APIError                                          | 4XX, 5XX                                                 | \*/\*                                                    |

## elenco_odonimi_get_path_param

Ritorna un elenco di odonimi presenti in ANNCSU

### Example Usage

<!-- UsageSnippet language="python" operationID="elencoOdonimiGetPathParam" method="get" path="/elencoodonimi/{codcom}/{denomparz}" -->
```python
from anncsu.pa import AnncsuConsultazione


with Anncsu() as a_client:

    res = a_client.pathparam.elenco_odonimi_get_path_param(codcom="H501", denomparz="Uk9NQQ==")

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

**[models.ElencoOdonimiGetPathParamResponse](../../models/elencoodonimigetpathparamresponse.md)**

### Errors

| Error Type                                               | Status Code                                              | Content Type                                             |
| -------------------------------------------------------- | -------------------------------------------------------- | -------------------------------------------------------- |
| errors.ElencoOdonimiGetPathParamBadRequestError          | 400                                                      | application/problem+json                                 |
| errors.ElencoOdonimiGetPathParamNotFoundError            | 404                                                      | application/problem+json                                 |
| errors.ElencoOdonimiGetPathParamMethodNotAllowedError    | 405                                                      | application/problem+json                                 |
| errors.ElencoOdonimiGetPathParamUnprocessableEntityError | 422                                                      | application/problem+json                                 |
| errors.ElencoOdonimiGetPathParamInternalServerError      | 500                                                      | application/problem+json                                 |
| errors.APIError                                          | 4XX, 5XX                                                 | \*/\*                                                    |

## elenco_accessi_get_path_param

Ritorna un elenco di accessi presenti in ANNCSU

### Example Usage

<!-- UsageSnippet language="python" operationID="elencoAccessiGetPathParam" method="get" path="/elencoaccessi/{codcom}/{denom}/{accparz}" -->
```python
from anncsu.pa import AnncsuConsultazione


with Anncsu() as a_client:

    res = a_client.pathparam.elenco_accessi_get_path_param(codcom="H501", denom="VklBIFJPTUE=", accparz="42")

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

**[models.ElencoAccessiGetPathParamResponse](../../models/elencoaccessigetpathparamresponse.md)**

### Errors

| Error Type                                               | Status Code                                              | Content Type                                             |
| -------------------------------------------------------- | -------------------------------------------------------- | -------------------------------------------------------- |
| errors.ElencoAccessiGetPathParamBadRequestError          | 400                                                      | application/problem+json                                 |
| errors.ElencoAccessiGetPathParamNotFoundError            | 404                                                      | application/problem+json                                 |
| errors.ElencoAccessiGetPathParamMethodNotAllowedError    | 405                                                      | application/problem+json                                 |
| errors.ElencoAccessiGetPathParamUnprocessableEntityError | 422                                                      | application/problem+json                                 |
| errors.ElencoAccessiGetPathParamInternalServerError      | 500                                                      | application/problem+json                                 |
| errors.APIError                                          | 4XX, 5XX                                                 | \*/\*                                                    |

## elencoodonimiprog_get_path_param

Ritorna un elenco di odonimi presenti in ANNCSU incluso il progressivo nazionale

### Example Usage

<!-- UsageSnippet language="python" operationID="elencoodonimiprogGetPathParam" method="get" path="/elencoodonimiprog/{codcom}/{denomparz}" -->
```python
from anncsu.pa import AnncsuConsultazione


with Anncsu() as a_client:

    res = a_client.pathparam.elencoodonimiprog_get_path_param(codcom="H501", denomparz="Uk9NQQ==")

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

**[models.ElencoodonimiprogGetPathParamResponse](../../models/elencoodonimiproggetpathparamresponse.md)**

### Errors

| Error Type                                                   | Status Code                                                  | Content Type                                                 |
| ------------------------------------------------------------ | ------------------------------------------------------------ | ------------------------------------------------------------ |
| errors.ElencoodonimiprogGetPathParamBadRequestError          | 400                                                          | application/problem+json                                     |
| errors.ElencoodonimiprogGetPathParamNotFoundError            | 404                                                          | application/problem+json                                     |
| errors.ElencoodonimiprogGetPathParamMethodNotAllowedError    | 405                                                          | application/problem+json                                     |
| errors.ElencoodonimiprogGetPathParamUnprocessableEntityError | 422                                                          | application/problem+json                                     |
| errors.ElencoodonimiprogGetPathParamInternalServerError      | 500                                                          | application/problem+json                                     |
| errors.APIError                                              | 4XX, 5XX                                                     | \*/\*                                                        |

## elencoaccessiprog_get_path_param

Ritorna un elenco di accessi presenti in ANNCSU incluso il progressivo nazionale

### Example Usage

<!-- UsageSnippet language="python" operationID="elencoaccessiprogGetPathParam" method="get" path="/elencoaccessiprog/{prognaz}/{accparz}" -->
```python
from anncsu.pa import AnncsuConsultazione


with Anncsu() as a_client:

    res = a_client.pathparam.elencoaccessiprog_get_path_param(prognaz="919572", accparz="42")

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

**[models.ElencoaccessiprogGetPathParamResponse](../../models/elencoaccessiproggetpathparamresponse.md)**

### Errors

| Error Type                                                   | Status Code                                                  | Content Type                                                 |
| ------------------------------------------------------------ | ------------------------------------------------------------ | ------------------------------------------------------------ |
| errors.ElencoaccessiprogGetPathParamBadRequestError          | 400                                                          | application/problem+json                                     |
| errors.ElencoaccessiprogGetPathParamNotFoundError            | 404                                                          | application/problem+json                                     |
| errors.ElencoaccessiprogGetPathParamMethodNotAllowedError    | 405                                                          | application/problem+json                                     |
| errors.ElencoaccessiprogGetPathParamUnprocessableEntityError | 422                                                          | application/problem+json                                     |
| errors.ElencoaccessiprogGetPathParamInternalServerError      | 500                                                          | application/problem+json                                     |
| errors.APIError                                              | 4XX, 5XX                                                     | \*/\*                                                        |

## prognazarea_get_path_param

Cerca in ANNCSU un odonimo per progressivo nazionale e ne ritorna i dati

### Example Usage

<!-- UsageSnippet language="python" operationID="prognazareaGetPathParam" method="get" path="/prognazarea/{prognaz}" -->
```python
from anncsu.pa import AnncsuConsultazione


with Anncsu() as a_client:

    res = a_client.pathparam.prognazarea_get_path_param(prognaz="919572")

    # Handle response
    print(res)

```

### Parameters

| Parameter                                                           | Type                                                                | Required                                                            | Description                                                         | Example                                                             |
| ------------------------------------------------------------------- | ------------------------------------------------------------------- | ------------------------------------------------------------------- | ------------------------------------------------------------------- | ------------------------------------------------------------------- |
| `prognaz`                                                           | *str*                                                               | :heavy_check_mark:                                                  | Progressivo nazionale dell'odonimo                                  | 919572                                                              |
| `retries`                                                           | [Optional[utils.RetryConfig]](../../models/utils/retryconfig.md)    | :heavy_minus_sign:                                                  | Configuration to override the default retry behavior of the client. |                                                                     |

### Response

**[models.PrognazareaGetPathParamResponse](../../models/prognazareagetpathparamresponse.md)**

### Errors

| Error Type                                             | Status Code                                            | Content Type                                           |
| ------------------------------------------------------ | ------------------------------------------------------ | ------------------------------------------------------ |
| errors.PrognazareaGetPathParamBadRequestError          | 400                                                    | application/problem+json                               |
| errors.PrognazareaGetPathParamNotFoundError            | 404                                                    | application/problem+json                               |
| errors.PrognazareaGetPathParamMethodNotAllowedError    | 405                                                    | application/problem+json                               |
| errors.PrognazareaGetPathParamUnprocessableEntityError | 422                                                    | application/problem+json                               |
| errors.PrognazareaGetPathParamInternalServerError      | 500                                                    | application/problem+json                               |
| errors.APIError                                        | 4XX, 5XX                                               | \*/\*                                                  |

## prognazacc_get_path_param

Cerca in ANNCSU un accesso per progressivo nazionale accesso e ne ritorna i dati comprensivi dell'odonimo

### Example Usage

<!-- UsageSnippet language="python" operationID="prognazaccGetPathParam" method="get" path="/prognazacc/{prognazacc}" -->
```python
from anncsu.pa import AnncsuConsultazione


with Anncsu() as a_client:

    res = a_client.pathparam.prognazacc_get_path_param(prognazacc="6744962")

    # Handle response
    print(res)

```

### Parameters

| Parameter                                                           | Type                                                                | Required                                                            | Description                                                         | Example                                                             |
| ------------------------------------------------------------------- | ------------------------------------------------------------------- | ------------------------------------------------------------------- | ------------------------------------------------------------------- | ------------------------------------------------------------------- |
| `prognazacc`                                                        | *str*                                                               | :heavy_check_mark:                                                  | Progressivo nazionale dell'accesso                                  | 6744962                                                             |
| `retries`                                                           | [Optional[utils.RetryConfig]](../../models/utils/retryconfig.md)    | :heavy_minus_sign:                                                  | Configuration to override the default retry behavior of the client. |                                                                     |

### Response

**[models.PrognazaccGetPathParamResponse](../../models/prognazaccgetpathparamresponse.md)**

### Errors

| Error Type                                            | Status Code                                           | Content Type                                          |
| ----------------------------------------------------- | ----------------------------------------------------- | ----------------------------------------------------- |
| errors.PrognazaccGetPathParamBadRequestError          | 400                                                   | application/problem+json                              |
| errors.PrognazaccGetPathParamNotFoundError            | 404                                                   | application/problem+json                              |
| errors.PrognazaccGetPathParamMethodNotAllowedError    | 405                                                   | application/problem+json                              |
| errors.PrognazaccGetPathParamUnprocessableEntityError | 422                                                   | application/problem+json                              |
| errors.PrognazaccGetPathParamInternalServerError      | 500                                                   | application/problem+json                              |
| errors.APIError                                       | 4XX, 5XX                                              | \*/\*                                                 |
