"""Base error classes for ANNCSU SDKs."""

from anncsu.common.errors.apierror import APIError
from anncsu.common.errors.audience_mismatch import AudienceMismatchError
from anncsu.common.errors.base import AnncsuBaseError
from anncsu.common.errors.digest_serialization_mismatch import (
    DigestSerializationMismatchError,
)
from anncsu.common.errors.no_response_error import NoResponseError
from anncsu.common.errors.responsevalidationerror import ResponseValidationError

# Alias for backward compatibility with generated code
AnncsuError = AnncsuBaseError

__all__ = [
    "AnncsuBaseError",
    "AnncsuError",
    "APIError",
    "AudienceMismatchError",
    "DigestSerializationMismatchError",
    "NoResponseError",
    "ResponseValidationError",
]
