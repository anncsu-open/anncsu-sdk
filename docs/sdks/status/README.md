# Status
(*status*)

## Overview

### Available Operations

* [show_status](#show_status) - Ritorna lo stato dell'applicazione.

## show_status

Ritorna lo stato dell'applicazione. A scopo
di test, su base randomica puo' ritornare
un errore.


### Example Usage

<!-- UsageSnippet language="python" operationID="show_status" method="get" path="/status" -->
```python
from anncsu.pa import AnncsuConsultazione


with Anncsu() as a_client:

    res = a_client.status.show_status()

    # Handle response
    print(res)

```

### Parameters

| Parameter                                                           | Type                                                                | Required                                                            | Description                                                         |
| ------------------------------------------------------------------- | ------------------------------------------------------------------- | ------------------------------------------------------------------- | ------------------------------------------------------------------- |
| `retries`                                                           | [Optional[utils.RetryConfig]](../../models/utils/retryconfig.md)    | :heavy_minus_sign:                                                  | Configuration to override the default retry behavior of the client. |

### Response

**[models.ShowStatusResponse](../../models/showstatusresponse.md)**

### Errors

| Error Type                     | Status Code                    | Content Type                   |
| ------------------------------ | ------------------------------ | ------------------------------ |
| errors.ServiceUnavailableError | 503                            | application/problem+json       |
| errors.APIError                | 4XX, 5XX                       | \*/\*                          |
