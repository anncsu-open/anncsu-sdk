# SPDX-FileCopyrightText: 2025-present Geobeyond <info@geobeyond.it>
# SPDX-License-Identifier: MIT
"""Session persistence for PDND authentication.

This module provides functions to save and load authentication session data
to/from JSON files in the user's config directory (~/.anncsu/).

Each API has its own session file to support different purpose_id tokens:
- ~/.anncsu/session_pa.json - Session for PA Consultazione API
- ~/.anncsu/session_coordinate.json - Session for Coordinate API
- ~/.anncsu/session_accessi.json - Session for Accessi API
- ~/.anncsu/session_interni.json - Session for Interni API
- ~/.anncsu/session_odonimi.json - Session for Odonimi API

The session stores:
- client_assertion: The JWT client assertion token (with API-specific purpose_id)
- access_token: The access token obtained from PDND
- token_endpoint: The token endpoint URL used for authentication

Example usage:
    >>> from anncsu.common.config import APIType
    >>> from anncsu.common.session import Session, save_session, load_session
    >>>
    >>> # Save a session for PA API
    >>> session = Session(
    ...     client_assertion="eyJ...",
    ...     access_token="eyJ...",
    ...     token_endpoint="https://auth.uat.interop.pagopa.it/token.oauth2",
    ... )
    >>> save_session(session, api_type=APIType.PA)
    >>>
    >>> # Load a session for PA API
    >>> loaded = load_session(api_type=APIType.PA)
    >>> if loaded:
    ...     print(f"Token endpoint: {loaded.token_endpoint}")
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import TYPE_CHECKING

from pydantic import BaseModel, ValidationError

if TYPE_CHECKING:
    from anncsu.common.config import APIType

# Default config directory name
CONFIG_DIR_NAME = ".anncsu"


class Session(BaseModel):
    """Session data for PDND authentication.

    Attributes:
        client_assertion: The JWT client assertion token (may be None if not yet generated).
        access_token: The access token from PDND (may be None if not yet obtained).
        token_endpoint: The PDND token endpoint URL.
    """

    client_assertion: str | None = None
    access_token: str | None = None
    token_endpoint: str


def get_config_dir() -> Path:
    """Get the default config directory path.

    Returns:
        Path to ~/.anncsu/
    """
    return Path.home() / CONFIG_DIR_NAME


def get_session_path(
    api_type: "APIType",
    config_dir: Path | None = None,
) -> Path:
    """Get the path to the session file for a specific API.

    Args:
        api_type: The API type (REQUIRED). Determines the session file name.
        config_dir: Optional custom config directory. Defaults to ~/.anncsu/

    Returns:
        Path to the session file: session_{api_type.value}.json

    Raises:
        ValueError: If api_type is None.
    """
    if api_type is None:
        raise ValueError(
            "api_type is required. Each API requires its own session file "
            "because each uses a different purpose_id for authentication."
        )

    if config_dir is None:
        config_dir = get_config_dir()

    return config_dir / f"session_{api_type.value}.json"


def save_session(
    session: Session,
    api_type: "APIType",
    config_dir: Path | None = None,
) -> None:
    """Save session data to file for a specific API.

    Creates the config directory if it doesn't exist.

    Args:
        session: Session data to save.
        api_type: The API type (REQUIRED). Determines the session file name.
        config_dir: Optional custom config directory. Defaults to ~/.anncsu/

    Raises:
        ValueError: If api_type is None.
    """
    if api_type is None:
        raise ValueError(
            "api_type is required. Each API requires its own session file "
            "because each uses a different purpose_id for authentication."
        )

    if config_dir is None:
        config_dir = get_config_dir()

    # Create directory if needed
    config_dir.mkdir(parents=True, exist_ok=True)

    session_path = get_session_path(api_type=api_type, config_dir=config_dir)
    session_path.write_text(session.model_dump_json(indent=2))


def load_session(
    api_type: "APIType",
    config_dir: Path | None = None,
) -> Session | None:
    """Load session data from file for a specific API.

    Args:
        api_type: The API type (REQUIRED). Determines the session file name.
        config_dir: Optional custom config directory. Defaults to ~/.anncsu/

    Returns:
        Session data if file exists and is valid, None otherwise.

    Raises:
        ValueError: If api_type is None.
    """
    if api_type is None:
        raise ValueError(
            "api_type is required. Each API requires its own session file "
            "because each uses a different purpose_id for authentication."
        )

    if config_dir is None:
        config_dir = get_config_dir()

    session_path = get_session_path(api_type=api_type, config_dir=config_dir)

    if not session_path.exists():
        return None

    try:
        data = json.loads(session_path.read_text())
        return Session.model_validate(data)
    except (json.JSONDecodeError, ValidationError):
        return None


def clear_session(
    api_type: "APIType",
    config_dir: Path | None = None,
) -> None:
    """Clear (delete) the session file for a specific API.

    Args:
        api_type: The API type (REQUIRED). Determines the session file name.
        config_dir: Optional custom config directory. Defaults to ~/.anncsu/

    Raises:
        ValueError: If api_type is None.
    """
    if api_type is None:
        raise ValueError(
            "api_type is required. Each API requires its own session file "
            "because each uses a different purpose_id for authentication."
        )

    if config_dir is None:
        config_dir = get_config_dir()

    session_path = get_session_path(api_type=api_type, config_dir=config_dir)

    if session_path.exists():
        session_path.unlink()


__all__ = [
    "Session",
    "get_config_dir",
    "get_session_path",
    "save_session",
    "load_session",
    "clear_session",
]
