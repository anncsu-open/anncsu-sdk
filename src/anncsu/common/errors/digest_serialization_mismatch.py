"""Digest serialization mismatch error for ModI headers."""

import json
from typing import Any


class DigestSerializationMismatchError(Exception):
    """Exception raised when payload serialization order doesn't match HTTP body.

    The ModI Digest header must be computed on the exact bytes that will be
    sent as the HTTP body. Speakeasy SDK serializes JSON without sort_keys,
    preserving insertion order. If the payload keys are not in sorted order,
    the digest computed with sort_keys=True won't match the actual HTTP body.

    This error is raised when such a mismatch is detected, to prevent
    cryptographic verification failures on the server side.
    """

    def __init__(self, payload: dict[str, Any]) -> None:
        self.payload = payload

        # Show the difference
        insertion_order = json.dumps(payload, separators=(",", ":"))
        sorted_order = json.dumps(payload, separators=(",", ":"), sort_keys=True)

        self.message = (
            "ModI Digest serialization mismatch detected.\n\n"
            "The payload keys are not in sorted order, which will cause the "
            "Digest header to not match the HTTP body.\n\n"
            "Speakeasy SDK serializes JSON preserving insertion order (no sort_keys),\n"
            "but the digest was computed with sorted keys.\n\n"
            f"Insertion order: {insertion_order}\n"
            f"Sorted order:    {sorted_order}\n\n"
            "Solution: Ensure payload keys are passed in sorted order, or use\n"
            "a model that serializes with consistent key ordering."
        )
        super().__init__(self.message)

    def __str__(self) -> str:
        return self.message
