<!-- Start SDK Example Usage [usage] -->
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
