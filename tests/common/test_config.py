# SPDX-FileCopyrightText: 2025-present Geobeyond <info@geobeyond.it>
# SPDX-License-Identifier: MIT
"""Tests for configuration settings and APIType enum."""

from __future__ import annotations

import os
from typing import TYPE_CHECKING
from unittest.mock import patch

import pytest

if TYPE_CHECKING:
    from pathlib import Path


class TestAPITypeEnum:
    """Tests for the APIType enum."""

    def test_api_type_values(self) -> None:
        """Test that all expected API types are defined."""
        from anncsu.common.config import APIType

        assert APIType.PA.value == "pa"
        assert APIType.COORDINATE.value == "coordinate"
        assert APIType.COORDINATE_BULK.value == "coordinate_bulk"
        assert APIType.ACCESSI.value == "accessi"
        assert APIType.INTERNI.value == "interni"
        assert APIType.ODONIMI.value == "odonimi"

    def test_api_type_count(self) -> None:
        """Test that we have exactly 6 API types."""
        from anncsu.common.config import APIType

        assert len(APIType) == 6

    def test_env_var_name_property(self) -> None:
        """Test that env_var_name returns correct variable names."""
        from anncsu.common.config import APIType

        assert APIType.PA.env_var_name == "PDND_PURPOSE_ID_PA"
        assert APIType.COORDINATE.env_var_name == "PDND_PURPOSE_ID_COORDINATE"
        assert APIType.COORDINATE_BULK.env_var_name == "PDND_PURPOSE_ID_COORDINATE_BULK"
        assert APIType.ACCESSI.env_var_name == "PDND_PURPOSE_ID_ACCESSI"
        assert APIType.INTERNI.env_var_name == "PDND_PURPOSE_ID_INTERNI"
        assert APIType.ODONIMI.env_var_name == "PDND_PURPOSE_ID_ODONIMI"

    def test_cli_command_property(self) -> None:
        """Test that cli_command returns the enum value."""
        from anncsu.common.config import APIType

        assert APIType.PA.cli_command == "pa"
        assert APIType.COORDINATE.cli_command == "coordinate"
        assert APIType.COORDINATE_BULK.cli_command == "coordinate bulk"
        assert APIType.ACCESSI.cli_command == "accessi"
        assert APIType.INTERNI.cli_command == "interni"
        assert APIType.ODONIMI.cli_command == "odonimi"

    def test_description_property(self) -> None:
        """Test that description returns meaningful descriptions."""
        from anncsu.common.config import APIType

        assert "Consultazione" in APIType.PA.description
        assert "Coordinate" in APIType.COORDINATE.description
        assert "Massivo" in APIType.COORDINATE_BULK.description
        assert "Accessi" in APIType.ACCESSI.description
        assert "Interni" in APIType.INTERNI.description
        assert "Odonimi" in APIType.ODONIMI.description

    def test_from_cli_command_valid(self) -> None:
        """Test that from_cli_command works for valid commands."""
        from anncsu.common.config import APIType

        assert APIType.from_cli_command("pa") == APIType.PA
        assert APIType.from_cli_command("coordinate") == APIType.COORDINATE
        assert APIType.from_cli_command("coordinate bulk") == APIType.COORDINATE_BULK
        assert APIType.from_cli_command("accessi") == APIType.ACCESSI
        assert APIType.from_cli_command("interni") == APIType.INTERNI
        assert APIType.from_cli_command("odonimi") == APIType.ODONIMI

    def test_from_cli_command_invalid(self) -> None:
        """Test that from_cli_command raises ValueError for invalid commands."""
        from anncsu.common.config import APIType

        with pytest.raises(ValueError, match="Unknown CLI command"):
            APIType.from_cli_command("invalid")

    def test_api_type_is_string_enum(self) -> None:
        """Test that APIType inherits from str for easy string operations."""
        from anncsu.common.config import APIType

        # Should be comparable to string
        assert APIType.PA == "pa"
        assert APIType.COORDINATE == "coordinate"
        # Can use .value in f-strings
        assert f"anncsu {APIType.PA.value}" == "anncsu pa"


class TestMissingPurposeIDError:
    """Tests for MissingPurposeIDError exception."""

    def test_exception_can_be_raised(self) -> None:
        """Test that MissingPurposeIDError can be raised."""
        from anncsu.common.config import MissingPurposeIDError

        with pytest.raises(MissingPurposeIDError):
            raise MissingPurposeIDError("Test message")

    def test_exception_message(self) -> None:
        """Test that exception message is preserved."""
        from anncsu.common.config import MissingPurposeIDError

        msg = "Missing PDND_PURPOSE_ID_PA"
        try:
            raise MissingPurposeIDError(msg)
        except MissingPurposeIDError as e:
            assert msg in str(e)


class TestEmptyPurposeIDError:
    """Tests for EmptyPurposeIDError exception."""

    def test_exception_can_be_raised(self) -> None:
        """Test that EmptyPurposeIDError can be raised."""
        from anncsu.common.config import EmptyPurposeIDError

        with pytest.raises(EmptyPurposeIDError):
            raise EmptyPurposeIDError("Test message")

    def test_exception_message(self) -> None:
        """Test that exception message is preserved."""
        from anncsu.common.config import EmptyPurposeIDError

        msg = "Purpose ID for PA is empty"
        try:
            raise EmptyPurposeIDError(msg)
        except EmptyPurposeIDError as e:
            assert msg in str(e)


class TestClientAssertionSettingsMultiAPI:
    """Tests for ClientAssertionSettings with multi-API purpose_id support."""

    @pytest.fixture
    def base_env_vars(self) -> dict[str, str]:
        """Fixture providing base environment variables (without purpose_id)."""
        # Use PDND_PRIVATE_KEY instead of PDND_KEY_PATH to avoid file existence check
        return {
            "PDND_KID": "test-kid",
            "PDND_ISSUER": "test-issuer",
            "PDND_SUBJECT": "test-subject",
            "PDND_AUDIENCE": "https://auth.test.example.com/client-assertion",
            "PDND_PRIVATE_KEY": "-----BEGIN RSA PRIVATE KEY-----\ntest-key-content\n-----END RSA PRIVATE KEY-----",
        }

    @pytest.fixture
    def all_purpose_ids_env(self) -> dict[str, str]:
        """Fixture providing all purpose_id environment variables."""
        return {
            "PDND_PURPOSE_ID_PA": "pa-purpose-id-123",
            "PDND_PURPOSE_ID_COORDINATE": "coordinate-purpose-id-456",
            "PDND_PURPOSE_ID_COORDINATE_BULK": "",  # Empty but present
            "PDND_PURPOSE_ID_ACCESSI": "",  # Empty but present
            "PDND_PURPOSE_ID_INTERNI": "",  # Empty but present
            "PDND_PURPOSE_ID_ODONIMI": "",  # Empty but present
        }

    @pytest.fixture
    def complete_env_vars(
        self, base_env_vars: dict[str, str], all_purpose_ids_env: dict[str, str]
    ) -> dict[str, str]:
        """Fixture providing complete environment variables."""
        return {**base_env_vars, **all_purpose_ids_env}

    def test_settings_loads_all_purpose_ids(
        self, complete_env_vars: dict[str, str]
    ) -> None:
        """Test that settings loads all purpose_id fields."""
        from anncsu.common.config import ClientAssertionSettings

        with patch.dict(os.environ, complete_env_vars, clear=True):
            settings = ClientAssertionSettings()

            assert settings.purpose_id_pa == "pa-purpose-id-123"
            assert settings.purpose_id_coordinate == "coordinate-purpose-id-456"
            assert settings.purpose_id_accessi == ""
            assert settings.purpose_id_interni == ""
            assert settings.purpose_id_odonimi == ""

    def test_settings_raises_when_purpose_id_var_missing(
        self,
        base_env_vars: dict[str, str],
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Test that settings raises MissingPurposeIDError when env vars are missing."""
        from anncsu.common.config import (
            ClientAssertionSettings,
            MissingPurposeIDError,
        )

        # Change to temp dir without .env file to avoid reading project's .env
        monkeypatch.chdir(tmp_path)

        # Only base vars, no purpose_id vars
        with patch.dict(os.environ, base_env_vars, clear=True):
            with pytest.raises(MissingPurposeIDError) as exc_info:
                ClientAssertionSettings()

            # Should mention all missing vars
            error_msg = str(exc_info.value)
            assert "PDND_PURPOSE_ID_PA" in error_msg
            assert "PDND_PURPOSE_ID_COORDINATE" in error_msg
            assert "PDND_PURPOSE_ID_COORDINATE_BULK" in error_msg
            assert "PDND_PURPOSE_ID_ACCESSI" in error_msg
            assert "PDND_PURPOSE_ID_INTERNI" in error_msg
            assert "PDND_PURPOSE_ID_ODONIMI" in error_msg

    def test_settings_raises_when_one_purpose_id_missing(
        self,
        base_env_vars: dict[str, str],
        all_purpose_ids_env: dict[str, str],
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Test that settings raises when even one purpose_id is missing."""
        from anncsu.common.config import (
            ClientAssertionSettings,
            MissingPurposeIDError,
        )

        # Change to temp dir without .env file to avoid reading project's .env
        monkeypatch.chdir(tmp_path)

        # Remove one purpose_id
        partial_purpose_ids = {
            k: v
            for k, v in all_purpose_ids_env.items()
            if k != "PDND_PURPOSE_ID_INTERNI"
        }
        env_vars = {**base_env_vars, **partial_purpose_ids}

        with patch.dict(os.environ, env_vars, clear=True):
            with pytest.raises(MissingPurposeIDError) as exc_info:
                ClientAssertionSettings()

            error_msg = str(exc_info.value)
            assert "PDND_PURPOSE_ID_INTERNI" in error_msg
            # Others should NOT be mentioned
            assert "PDND_PURPOSE_ID_PA" not in error_msg

    def test_get_purpose_id_returns_correct_value(
        self, complete_env_vars: dict[str, str]
    ) -> None:
        """Test that get_purpose_id returns the correct value for each API."""
        from anncsu.common.config import APIType, ClientAssertionSettings

        with patch.dict(os.environ, complete_env_vars, clear=True):
            settings = ClientAssertionSettings()

            assert settings.get_purpose_id(APIType.PA) == "pa-purpose-id-123"
            assert (
                settings.get_purpose_id(APIType.COORDINATE)
                == "coordinate-purpose-id-456"
            )

    def test_get_purpose_id_raises_when_empty(
        self, complete_env_vars: dict[str, str]
    ) -> None:
        """Test that get_purpose_id raises EmptyPurposeIDError for empty values."""
        from anncsu.common.config import (
            APIType,
            ClientAssertionSettings,
            EmptyPurposeIDError,
        )

        with patch.dict(os.environ, complete_env_vars, clear=True):
            settings = ClientAssertionSettings()

            # ACCESSI has empty value
            with pytest.raises(EmptyPurposeIDError) as exc_info:
                settings.get_purpose_id(APIType.ACCESSI)

            error_msg = str(exc_info.value)
            assert "PDND_PURPOSE_ID_ACCESSI" in error_msg
            assert "empty" in error_msg.lower()

    def test_to_config_with_api_type(self, complete_env_vars: dict[str, str]) -> None:
        """Test that to_config creates config with correct purpose_id for API type."""
        from anncsu.common.config import APIType, ClientAssertionSettings

        with patch.dict(os.environ, complete_env_vars, clear=True):
            settings = ClientAssertionSettings()

            config_pa = settings.to_config(APIType.PA)
            assert config_pa.purpose_id == "pa-purpose-id-123"

            config_coordinate = settings.to_config(APIType.COORDINATE)
            assert config_coordinate.purpose_id == "coordinate-purpose-id-456"

    def test_to_config_raises_for_empty_purpose_id(
        self, complete_env_vars: dict[str, str]
    ) -> None:
        """Test that to_config raises EmptyPurposeIDError for empty purpose_id."""
        from anncsu.common.config import (
            APIType,
            ClientAssertionSettings,
            EmptyPurposeIDError,
        )

        with patch.dict(os.environ, complete_env_vars, clear=True):
            settings = ClientAssertionSettings()

            with pytest.raises(EmptyPurposeIDError):
                settings.to_config(APIType.INTERNI)


class TestClientAssertionSettingsBackwardCompatibility:
    """Tests for backward compatibility of ClientAssertionSettings."""

    @pytest.fixture
    def legacy_env_vars(self) -> dict[str, str]:
        """Fixture providing legacy environment variables with single purpose_id."""
        return {
            "PDND_KID": "test-kid",
            "PDND_ISSUER": "test-issuer",
            "PDND_SUBJECT": "test-subject",
            "PDND_AUDIENCE": "https://auth.test.example.com/client-assertion",
            "PDND_PURPOSE_ID": "legacy-purpose-id",  # Old single purpose_id
            "PDND_KEY_PATH": "/tmp/test_key.pem",
        }

    def test_existing_fields_still_work(self, legacy_env_vars: dict[str, str]) -> None:
        """Test that existing settings fields still work."""
        from anncsu.common.config import ClientAssertionSettings

        # Add required new fields
        legacy_env_vars.update(
            {
                "PDND_PURPOSE_ID_PA": "pa-id",
                "PDND_PURPOSE_ID_COORDINATE": "coord-id",
                "PDND_PURPOSE_ID_COORDINATE_BULK": "",
                "PDND_PURPOSE_ID_ACCESSI": "",
                "PDND_PURPOSE_ID_INTERNI": "",
                "PDND_PURPOSE_ID_ODONIMI": "",
            }
        )

        with patch.dict(os.environ, legacy_env_vars, clear=True):
            settings = ClientAssertionSettings()

            assert settings.kid == "test-kid"
            assert settings.issuer == "test-issuer"
            assert settings.subject == "test-subject"
            assert settings.audience == "https://auth.test.example.com/client-assertion"
            assert settings.key_path == "/tmp/test_key.pem"

    def test_key_validation_still_works(self) -> None:
        """Test that key validation (private_key or key_path) still works."""
        from anncsu.common.config import ClientAssertionSettings

        env_vars = {
            "PDND_KID": "test-kid",
            "PDND_ISSUER": "test-issuer",
            "PDND_SUBJECT": "test-subject",
            "PDND_AUDIENCE": "https://auth.test.example.com/client-assertion",
            # No PDND_PRIVATE_KEY or PDND_KEY_PATH
            "PDND_PURPOSE_ID_PA": "pa-id",
            "PDND_PURPOSE_ID_COORDINATE": "coord-id",
            "PDND_PURPOSE_ID_COORDINATE_BULK": "",
            "PDND_PURPOSE_ID_ACCESSI": "",
            "PDND_PURPOSE_ID_INTERNI": "",
            "PDND_PURPOSE_ID_ODONIMI": "",
        }

        with patch.dict(os.environ, env_vars, clear=True):
            with pytest.raises(ValueError, match="PDND_PRIVATE_KEY.*PDND_KEY_PATH"):
                # Disable .env file loading to test validation
                ClientAssertionSettings(_env_file=None)


class TestClientAssertionSettingsModIFields:
    """Tests for ModI audit context fields in ClientAssertionSettings."""

    @pytest.fixture
    def base_env_vars(self, mock_private_key: "Path") -> dict[str, str]:
        """Base environment variables for settings tests."""
        return {
            "PDND_KID": "test-kid",
            "PDND_ISSUER": "test-issuer",
            "PDND_SUBJECT": "test-subject",
            "PDND_AUDIENCE": "https://auth.test.example.com/client-assertion",
            "PDND_KEY_PATH": str(mock_private_key),
            "PDND_PURPOSE_ID_PA": "pa-id",
            "PDND_PURPOSE_ID_COORDINATE": "coord-id",
            "PDND_PURPOSE_ID_COORDINATE_BULK": "",
            "PDND_PURPOSE_ID_ACCESSI": "",
            "PDND_PURPOSE_ID_INTERNI": "",
            "PDND_PURPOSE_ID_ODONIMI": "",
        }

    def test_modi_fields_are_optional(self, base_env_vars: dict[str, str]) -> None:
        """Test that ModI audit fields are optional and default to None."""
        from anncsu.common.config import ClientAssertionSettings

        with patch.dict(os.environ, base_env_vars, clear=True):
            settings = ClientAssertionSettings(_env_file=None)

        # ModI fields should default to None
        assert settings.modi_user_id is None
        assert settings.modi_user_location is None
        assert settings.modi_loa is None

    def test_modi_fields_can_be_set(self, base_env_vars: dict[str, str]) -> None:
        """Test that ModI audit fields can be set via environment variables."""
        from anncsu.common.config import ClientAssertionSettings

        env_vars = {
            **base_env_vars,
            "PDND_MODI_USER_ID": "batch-user-001",
            "PDND_MODI_USER_LOCATION": "server-batch-01",
            "PDND_MODI_LOA": "SPID_L2",
        }

        with patch.dict(os.environ, env_vars, clear=True):
            settings = ClientAssertionSettings(_env_file=None)

        assert settings.modi_user_id == "batch-user-001"
        assert settings.modi_user_location == "server-batch-01"
        assert settings.modi_loa == "SPID_L2"

    def test_has_modi_audit_context_false_when_not_set(
        self, base_env_vars: dict[str, str]
    ) -> None:
        """Test has_modi_audit_context returns False when no audit fields set."""
        from anncsu.common.config import ClientAssertionSettings

        with patch.dict(os.environ, base_env_vars, clear=True):
            settings = ClientAssertionSettings(_env_file=None)

        assert settings.has_modi_audit_context is False

    def test_has_modi_audit_context_true_when_all_set(
        self, base_env_vars: dict[str, str]
    ) -> None:
        """Test has_modi_audit_context returns True when all audit fields set."""
        from anncsu.common.config import ClientAssertionSettings

        env_vars = {
            **base_env_vars,
            "PDND_MODI_USER_ID": "batch-user",
            "PDND_MODI_USER_LOCATION": "server",
            "PDND_MODI_LOA": "SPID_L2",
        }

        with patch.dict(os.environ, env_vars, clear=True):
            settings = ClientAssertionSettings(_env_file=None)

        assert settings.has_modi_audit_context is True

    def test_has_modi_audit_context_false_when_partial(
        self, base_env_vars: dict[str, str]
    ) -> None:
        """Test has_modi_audit_context returns False when only some audit fields set."""
        from anncsu.common.config import ClientAssertionSettings

        # Only user_id set
        env_vars = {
            **base_env_vars,
            "PDND_MODI_USER_ID": "batch-user",
        }

        with patch.dict(os.environ, env_vars, clear=True):
            settings = ClientAssertionSettings(_env_file=None)

        assert settings.has_modi_audit_context is False

    def test_get_modi_audit_context_returns_audit_context(
        self, base_env_vars: dict[str, str]
    ) -> None:
        """Test get_modi_audit_context returns AuditContext when all fields set."""
        from anncsu.common.config import ClientAssertionSettings
        from anncsu.common.modi import AuditContext

        env_vars = {
            **base_env_vars,
            "PDND_MODI_USER_ID": "batch-user-001",
            "PDND_MODI_USER_LOCATION": "server-batch-01",
            "PDND_MODI_LOA": "SPID_L2",
        }

        with patch.dict(os.environ, env_vars, clear=True):
            settings = ClientAssertionSettings(_env_file=None)
            audit_context = settings.get_modi_audit_context()

        assert isinstance(audit_context, AuditContext)
        assert audit_context.user_id == "batch-user-001"
        assert audit_context.user_location == "server-batch-01"
        assert audit_context.loa == "SPID_L2"

    def test_get_modi_audit_context_returns_none_when_not_set(
        self, base_env_vars: dict[str, str]
    ) -> None:
        """Test get_modi_audit_context returns None when audit fields not set."""
        from anncsu.common.config import ClientAssertionSettings

        with patch.dict(os.environ, base_env_vars, clear=True):
            settings = ClientAssertionSettings(_env_file=None)
            audit_context = settings.get_modi_audit_context()

        assert audit_context is None

    def test_get_modi_audit_context_returns_none_when_partial(
        self, base_env_vars: dict[str, str]
    ) -> None:
        """Test get_modi_audit_context returns None when only some fields set."""
        from anncsu.common.config import ClientAssertionSettings

        env_vars = {
            **base_env_vars,
            "PDND_MODI_USER_ID": "batch-user",
            "PDND_MODI_USER_LOCATION": "server",
            # Missing PDND_MODI_LOA
        }

        with patch.dict(os.environ, env_vars, clear=True):
            settings = ClientAssertionSettings(_env_file=None)
            audit_context = settings.get_modi_audit_context()

        assert audit_context is None
