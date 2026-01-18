# SPDX-FileCopyrightText: 2025-present Geobeyond <info@geobeyond.it>
# SPDX-License-Identifier: MIT
"""Session persistence for PDND authentication.

This module provides functions to save and load authentication session data
to/from a JSON file in the user's config directory (~/.anncsu/session.json).

The session stores:
- client_assertion: The JWT client assertion token
- access_token: The access token obtained from PDND
- token_endpoint: The token endpoint URL used for authentication

Example usage:
    >>> from anncsu.common.session import Session, save_session, load_session
    >>>
    >>> # Save a session
    >>> session = Session(
    ...     client_assertion="eyJ...",
    ...     access_token="eyJ...",
    ...     token_endpoint="https://auth.uat.interop.pagopa.it/token.oauth2",
    ... )
    >>> save_session(session)
    >>>
    >>> # Load a session
    >>> loaded = load_session()
    >>> if loaded:
    ...     print(f"Token endpoint: {loaded.token_endpoint}")
"""

from __future__ import annotations

import json
from pathlib import Path

from pydantic import BaseModel, ValidationError

# Default config directory name
CONFIG_DIR_NAME = ".anncsu"
SESSION_FILE_NAME = "session.json"


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


def get_session_path(config_dir: Path | None = None) -> Path:
    """Get the path to the session file.

    Args:
        config_dir: Optional custom config directory. Defaults to ~/.anncsu/

    Returns:
        Path to the session.json file.
    """
    if config_dir is None:
        config_dir = get_config_dir()
    return config_dir / SESSION_FILE_NAME


def save_session(session: Session, config_dir: Path | None = None) -> None:
    """Save session data to file.

    Creates the config directory if it doesn't exist.

    Args:
        session: Session data to save.
        config_dir: Optional custom config directory. Defaults to ~/.anncsu/
    """
    if config_dir is None:
        config_dir = get_config_dir()

    # Create directory if needed
    config_dir.mkdir(parents=True, exist_ok=True)

    session_path = config_dir / SESSION_FILE_NAME
    session_path.write_text(session.model_dump_json(indent=2))


def load_session(config_dir: Path | None = None) -> Session | None:
    """Load session data from file.

    Args:
        config_dir: Optional custom config directory. Defaults to ~/.anncsu/

    Returns:
        Session data if file exists and is valid, None otherwise.
    """
    if config_dir is None:
        config_dir = get_config_dir()

    session_path = config_dir / SESSION_FILE_NAME

    if not session_path.exists():
        return None

    try:
        data = json.loads(session_path.read_text())
        return Session.model_validate(data)
    except (json.JSONDecodeError, ValidationError):
        return None


def clear_session(config_dir: Path | None = None) -> None:
    """Clear (delete) the session file.

    Args:
        config_dir: Optional custom config directory. Defaults to ~/.anncsu/
    """
    if config_dir is None:
        config_dir = get_config_dir()

    session_path = config_dir / SESSION_FILE_NAME

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
