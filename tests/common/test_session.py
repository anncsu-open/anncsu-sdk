# SPDX-FileCopyrightText: 2025-present Geobeyond <info@geobeyond.it>
# SPDX-License-Identifier: MIT
"""Tests for session.py with multi-API support.

All session functions require api_type parameter - no default session.json.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest


class TestGetSessionPath:
    """Tests for get_session_path function - api_type is REQUIRED."""

    def test_session_path_requires_api_type(self, tmp_path: Path) -> None:
        """Test that get_session_path raises error with api_type=None."""
        from anncsu.common.session import get_session_path

        with pytest.raises(ValueError, match="api_type.*required"):
            get_session_path(api_type=None, config_dir=tmp_path)

    def test_session_path_with_api_type_pa(self, tmp_path: Path) -> None:
        """Test session path for PA API type."""
        from anncsu.common.config import APIType
        from anncsu.common.session import get_session_path

        result = get_session_path(config_dir=tmp_path, api_type=APIType.PA)
        assert result == tmp_path / "session_pa.json"

    def test_session_path_with_api_type_coordinate(self, tmp_path: Path) -> None:
        """Test session path for COORDINATE API type."""
        from anncsu.common.config import APIType
        from anncsu.common.session import get_session_path

        result = get_session_path(config_dir=tmp_path, api_type=APIType.COORDINATE)
        assert result == tmp_path / "session_coordinate.json"

    def test_session_path_with_all_api_types(self, tmp_path: Path) -> None:
        """Test session path for all API types."""
        from anncsu.common.config import APIType
        from anncsu.common.session import get_session_path

        for api_type in APIType:
            result = get_session_path(config_dir=tmp_path, api_type=api_type)
            expected = tmp_path / f"session_{api_type.value}.json"
            assert result == expected, f"Failed for {api_type}"


class TestSaveSession:
    """Tests for save_session function - api_type is REQUIRED."""

    def test_save_session_requires_api_type(self, tmp_path: Path) -> None:
        """Test that save_session raises error with api_type=None."""
        from anncsu.common.session import Session, save_session

        session = Session(
            client_assertion="test-assertion",
            access_token="test-token",
            token_endpoint="https://test.endpoint",
        )

        with pytest.raises(ValueError, match="api_type.*required"):
            save_session(session, api_type=None, config_dir=tmp_path)

    def test_save_session_with_api_type(self, tmp_path: Path) -> None:
        """Test saving session with specific API type."""
        from anncsu.common.config import APIType
        from anncsu.common.session import Session, save_session

        session = Session(
            client_assertion="pa-assertion",
            access_token="pa-token",
            token_endpoint="https://test.endpoint",
        )
        save_session(session, config_dir=tmp_path, api_type=APIType.PA)

        session_file = tmp_path / "session_pa.json"
        assert session_file.exists()

        data = json.loads(session_file.read_text())
        assert data["client_assertion"] == "pa-assertion"

    def test_save_different_sessions_for_different_apis(self, tmp_path: Path) -> None:
        """Test that different API types save to different files."""
        from anncsu.common.config import APIType
        from anncsu.common.session import Session, save_session

        # Save PA session
        pa_session = Session(
            client_assertion="pa-assertion",
            access_token="pa-token",
            token_endpoint="https://test.endpoint",
        )
        save_session(pa_session, config_dir=tmp_path, api_type=APIType.PA)

        # Save COORDINATE session
        coord_session = Session(
            client_assertion="coord-assertion",
            access_token="coord-token",
            token_endpoint="https://test.endpoint",
        )
        save_session(coord_session, config_dir=tmp_path, api_type=APIType.COORDINATE)

        # Verify both files exist with correct content
        pa_file = tmp_path / "session_pa.json"
        coord_file = tmp_path / "session_coordinate.json"

        assert pa_file.exists()
        assert coord_file.exists()

        # Verify no generic session.json was created
        generic_file = tmp_path / "session.json"
        assert not generic_file.exists()

        pa_data = json.loads(pa_file.read_text())
        coord_data = json.loads(coord_file.read_text())

        assert pa_data["client_assertion"] == "pa-assertion"
        assert coord_data["client_assertion"] == "coord-assertion"


class TestLoadSession:
    """Tests for load_session function - api_type is REQUIRED."""

    def test_load_session_requires_api_type(self, tmp_path: Path) -> None:
        """Test that load_session raises error with api_type=None."""
        from anncsu.common.session import load_session

        with pytest.raises(ValueError, match="api_type.*required"):
            load_session(api_type=None, config_dir=tmp_path)

    def test_load_session_with_api_type(self, tmp_path: Path) -> None:
        """Test loading session with specific API type."""
        from anncsu.common.config import APIType
        from anncsu.common.session import Session, load_session, save_session

        session = Session(
            client_assertion="pa-assertion",
            access_token="pa-token",
            token_endpoint="https://test.endpoint",
        )
        save_session(session, config_dir=tmp_path, api_type=APIType.PA)

        loaded = load_session(config_dir=tmp_path, api_type=APIType.PA)
        assert loaded is not None
        assert loaded.client_assertion == "pa-assertion"

    def test_load_session_returns_none_for_missing_api_type(
        self, tmp_path: Path
    ) -> None:
        """Test that loading non-existent API session returns None."""
        from anncsu.common.config import APIType
        from anncsu.common.session import Session, load_session, save_session

        # Save PA session only
        session = Session(
            client_assertion="pa-assertion",
            access_token="pa-token",
            token_endpoint="https://test.endpoint",
        )
        save_session(session, config_dir=tmp_path, api_type=APIType.PA)

        # Try to load COORDINATE session (doesn't exist)
        loaded = load_session(config_dir=tmp_path, api_type=APIType.COORDINATE)
        assert loaded is None

    def test_load_different_sessions_for_different_apis(self, tmp_path: Path) -> None:
        """Test loading different sessions for different API types."""
        from anncsu.common.config import APIType
        from anncsu.common.session import Session, load_session, save_session

        # Save PA session
        pa_session = Session(
            client_assertion="pa-assertion",
            access_token="pa-token",
            token_endpoint="https://test.endpoint",
        )
        save_session(pa_session, config_dir=tmp_path, api_type=APIType.PA)

        # Save COORDINATE session
        coord_session = Session(
            client_assertion="coord-assertion",
            access_token="coord-token",
            token_endpoint="https://test.endpoint",
        )
        save_session(coord_session, config_dir=tmp_path, api_type=APIType.COORDINATE)

        # Load and verify each
        pa_loaded = load_session(config_dir=tmp_path, api_type=APIType.PA)
        coord_loaded = load_session(config_dir=tmp_path, api_type=APIType.COORDINATE)

        assert pa_loaded is not None
        assert coord_loaded is not None
        assert pa_loaded.client_assertion == "pa-assertion"
        assert coord_loaded.client_assertion == "coord-assertion"


class TestClearSession:
    """Tests for clear_session function - api_type is REQUIRED."""

    def test_clear_session_requires_api_type(self, tmp_path: Path) -> None:
        """Test that clear_session raises error with api_type=None."""
        from anncsu.common.session import clear_session

        with pytest.raises(ValueError, match="api_type.*required"):
            clear_session(api_type=None, config_dir=tmp_path)

    def test_clear_session_with_api_type(self, tmp_path: Path) -> None:
        """Test clearing session for specific API type."""
        from anncsu.common.config import APIType
        from anncsu.common.session import Session, clear_session, save_session

        session = Session(
            client_assertion="pa-assertion",
            access_token="pa-token",
            token_endpoint="https://test.endpoint",
        )
        save_session(session, config_dir=tmp_path, api_type=APIType.PA)

        session_file = tmp_path / "session_pa.json"
        assert session_file.exists()

        clear_session(config_dir=tmp_path, api_type=APIType.PA)
        assert not session_file.exists()

    def test_clear_session_only_clears_specific_api(self, tmp_path: Path) -> None:
        """Test that clearing one API session doesn't affect others."""
        from anncsu.common.config import APIType
        from anncsu.common.session import Session, clear_session, save_session

        # Save both sessions
        pa_session = Session(
            client_assertion="pa-assertion",
            access_token="pa-token",
            token_endpoint="https://test.endpoint",
        )
        save_session(pa_session, config_dir=tmp_path, api_type=APIType.PA)

        coord_session = Session(
            client_assertion="coord-assertion",
            access_token="coord-token",
            token_endpoint="https://test.endpoint",
        )
        save_session(coord_session, config_dir=tmp_path, api_type=APIType.COORDINATE)

        # Clear only PA
        clear_session(config_dir=tmp_path, api_type=APIType.PA)

        # PA should be gone, COORDINATE should remain
        pa_file = tmp_path / "session_pa.json"
        coord_file = tmp_path / "session_coordinate.json"

        assert not pa_file.exists()
        assert coord_file.exists()

    def test_clear_nonexistent_session_no_error(self, tmp_path: Path) -> None:
        """Test that clearing non-existent session doesn't raise error."""
        from anncsu.common.config import APIType
        from anncsu.common.session import clear_session

        # Should not raise any error
        clear_session(config_dir=tmp_path, api_type=APIType.PA)
