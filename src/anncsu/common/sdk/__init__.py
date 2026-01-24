"""Base SDK infrastructure for ANNCSU API clients.

This package provides shared SDK components that are used by all ANNCSU API
implementations (pa, odonimi, accessi, coordinate, interni).

Exports:
    - BaseSDK: Base class for SDK implementations
    - SDKConfigurationProtocol: Protocol for SDK configuration
    - HttpClient, AsyncHttpClient: HTTP client protocols
    - utils: Utility functions for SDK operations
    - types: Common types (BaseModel, UNSET, etc.)
"""

from .basesdk import BaseSDK
from .httpclient import AsyncHttpClient, HttpClient, close_clients
from .protocols import SDKConfigurationProtocol

__all__ = [
    # Core SDK
    "BaseSDK",
    "SDKConfigurationProtocol",
    # HTTP clients
    "HttpClient",
    "AsyncHttpClient",
    "close_clients",
]
