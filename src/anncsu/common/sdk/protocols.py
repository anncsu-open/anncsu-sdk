"""Protocol definitions for SDK configuration.

This module defines protocols (interfaces) for SDK components that allow
different API implementations to share the same base SDK infrastructure.
"""

from typing import Any, Dict, Optional, Tuple, Union

from typing_extensions import Protocol, runtime_checkable

from .httpclient import AsyncHttpClient, HttpClient
from .utils import Logger


@runtime_checkable
class SDKConfigurationProtocol(Protocol):
    """Protocol defining the interface for SDK configuration.

    Each API package (pa, odonimi, accessi, etc.) will have its own
    concrete SDKConfiguration class that implements this protocol.
    """

    client: Union[HttpClient, None]
    async_client: Union[AsyncHttpClient, None]
    debug_logger: Logger
    user_agent: str
    retry_config: Any  # OptionalNullable[RetryConfig]
    timeout_ms: Optional[int]
    security: Any

    def get_server_details(self) -> Tuple[str, Dict[str, str]]:
        """Get the server URL and variables for API requests."""
        ...
