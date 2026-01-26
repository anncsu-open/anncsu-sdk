# SPDX-FileCopyrightText: 2025-present Geobeyond <info@geobeyond.it>
# SPDX-License-Identifier: MIT
"""Tests for ModI header generation."""

from __future__ import annotations

import base64
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import TYPE_CHECKING
from unittest.mock import patch

import pytest

if TYPE_CHECKING:
    from anncsu.common.modi import AuditContext, ModIConfig


class TestAuditContext:
    """Tests for AuditContext dataclass."""

    def test_audit_context_creation(self) -> None:
        """Test that AuditContext can be created with required fields."""
        from anncsu.common.modi import AuditContext

        audit = AuditContext(
            user_id="batch-user-001",
            user_location="server-batch-01",
            loa="SPID_L2",
        )

        assert audit.user_id == "batch-user-001"
        assert audit.user_location == "server-batch-01"
        assert audit.loa == "SPID_L2"

    def test_audit_context_with_different_loa_values(self) -> None:
        """Test AuditContext with various LoA values."""
        from anncsu.common.modi import AuditContext

        loa_values = [
            "SPID_L1",
            "SPID_L2",
            "SPID_L3",
            "CIE_L3",
            "INTERNAL_AUTH",
        ]

        for loa in loa_values:
            audit = AuditContext(
                user_id="user",
                user_location="location",
                loa=loa,
            )
            assert audit.loa == loa


class TestModIConfig:
    """Tests for ModIConfig dataclass."""

    def test_modi_config_creation(self, mock_private_key: Path) -> None:
        """Test that ModIConfig can be created with required fields."""
        from anncsu.common.modi import ModIConfig

        private_key = mock_private_key.read_bytes()

        config = ModIConfig(
            private_key=private_key,
            kid="test-key-id",
            issuer="test-client-id",
            audience="https://modipa-val.anpr.interno.it",
        )

        assert config.private_key == private_key
        assert config.kid == "test-key-id"
        assert config.issuer == "test-client-id"
        assert config.audience == "https://modipa-val.anpr.interno.it"
        assert config.alg == "RS256"  # default
        assert config.validity_seconds == 300  # default

    def test_modi_config_custom_validity(self, mock_private_key: Path) -> None:
        """Test ModIConfig with custom validity seconds."""
        from anncsu.common.modi import ModIConfig

        config = ModIConfig(
            private_key=mock_private_key.read_bytes(),
            kid="key-id",
            issuer="issuer",
            audience="https://api.example.com",
            validity_seconds=600,  # 10 minutes
        )

        assert config.validity_seconds == 600


class TestModIHeaderGenerator:
    """Tests for ModIHeaderGenerator class."""

    @pytest.fixture
    def modi_config(self, mock_private_key: Path) -> "ModIConfig":
        """Create a ModIConfig for testing."""
        from anncsu.common.modi import ModIConfig

        return ModIConfig(
            private_key=mock_private_key.read_bytes(),
            kid="test-key-id",
            issuer="test-client-id",
            audience="https://modipa-val.anpr.interno.it",
        )

    @pytest.fixture
    def audit_context(self) -> "AuditContext":
        """Create an AuditContext for testing."""
        from anncsu.common.modi import AuditContext

        return AuditContext(
            user_id="batch-user-001",
            user_location="server-batch-01",
            loa="SPID_L2",
        )

    def test_generator_creation_without_audit(self, modi_config: "ModIConfig") -> None:
        """Test generator can be created without audit context."""
        from anncsu.common.modi import ModIHeaderGenerator

        generator = ModIHeaderGenerator(modi_config)

        assert not generator.has_audit_context

    def test_generator_creation_with_audit(
        self, modi_config: "ModIConfig", audit_context: "AuditContext"
    ) -> None:
        """Test generator can be created with audit context."""
        from anncsu.common.modi import ModIHeaderGenerator

        generator = ModIHeaderGenerator(modi_config, audit_context)

        assert generator.has_audit_context

    def test_generate_headers_without_audit(self, modi_config: "ModIConfig") -> None:
        """Test that generate_headers returns only signature when no audit context."""
        from anncsu.common.modi import ModIHeaderGenerator

        generator = ModIHeaderGenerator(modi_config)
        payload = {"codcom": "H501", "operazione": "M"}

        headers = generator.generate_headers(payload)

        assert "Agid-JWT-Signature" in headers
        assert "Agid-JWT-TrackingEvidence" not in headers

    def test_generate_headers_with_audit(
        self, modi_config: "ModIConfig", audit_context: "AuditContext"
    ) -> None:
        """Test that generate_headers returns both headers when audit context present."""
        from anncsu.common.modi import ModIHeaderGenerator

        generator = ModIHeaderGenerator(modi_config, audit_context)
        payload = {"codcom": "H501", "operazione": "M"}

        headers = generator.generate_headers(payload)

        assert "Agid-JWT-Signature" in headers
        assert "Agid-JWT-TrackingEvidence" in headers

    def test_signature_jwt_structure(self, modi_config: "ModIConfig") -> None:
        """Test that signature JWT has correct structure."""
        from anncsu.common.modi import ModIHeaderGenerator

        generator = ModIHeaderGenerator(modi_config)
        payload = {"codcom": "H501", "operazione": "M"}

        headers = generator.generate_headers(payload)
        signature_jwt = headers["Agid-JWT-Signature"]

        # JWT should have 3 parts
        parts = signature_jwt.split(".")
        assert len(parts) == 3

        # Decode header
        header_b64 = parts[0] + "=" * (4 - len(parts[0]) % 4)
        header = json.loads(base64.urlsafe_b64decode(header_b64))

        assert header["alg"] == "RS256"
        assert header["typ"] == "JWT"
        assert header["kid"] == "test-key-id"

    def test_signature_jwt_claims(self, modi_config: "ModIConfig") -> None:
        """Test that signature JWT has correct claims."""
        from anncsu.common.modi import ModIHeaderGenerator

        generator = ModIHeaderGenerator(modi_config)
        payload = {"codcom": "H501", "operazione": "M"}

        headers = generator.generate_headers(payload)
        signature_jwt = headers["Agid-JWT-Signature"]

        # Decode payload
        parts = signature_jwt.split(".")
        payload_b64 = parts[1] + "=" * (4 - len(parts[1]) % 4)
        claims = json.loads(base64.urlsafe_b64decode(payload_b64))

        assert claims["iss"] == "test-client-id"
        assert claims["aud"] == "https://modipa-val.anpr.interno.it"
        assert "iat" in claims
        assert "exp" in claims
        assert "signed_headers" in claims

        # Check signed_headers structure
        signed_headers = claims["signed_headers"]
        assert len(signed_headers) == 2
        assert "digest" in signed_headers[0]
        assert signed_headers[0]["digest"].startswith("SHA-256=")
        assert signed_headers[1]["content-type"] == "application/json"

    def test_signature_digest_is_correct(self, modi_config: "ModIConfig") -> None:
        """Test that the digest in signature JWT matches the payload."""
        from anncsu.common.modi import ModIHeaderGenerator

        generator = ModIHeaderGenerator(modi_config)
        payload = {"codcom": "H501", "operazione": "M"}

        headers = generator.generate_headers(payload)
        signature_jwt = headers["Agid-JWT-Signature"]

        # Extract digest from JWT
        parts = signature_jwt.split(".")
        payload_b64 = parts[1] + "=" * (4 - len(parts[1]) % 4)
        claims = json.loads(base64.urlsafe_b64decode(payload_b64))
        jwt_digest = claims["signed_headers"][0]["digest"]

        # Compute expected digest
        payload_bytes = json.dumps(
            payload, separators=(",", ":"), sort_keys=True
        ).encode("utf-8")
        expected_digest = hashlib.sha256(payload_bytes).digest()
        expected_b64 = (
            base64.urlsafe_b64encode(expected_digest).decode("utf-8").rstrip("=")
        )

        assert jwt_digest == f"SHA-256={expected_b64}"

    def test_tracking_jwt_structure(
        self, modi_config: "ModIConfig", audit_context: "AuditContext"
    ) -> None:
        """Test that tracking JWT has correct structure."""
        from anncsu.common.modi import ModIHeaderGenerator

        generator = ModIHeaderGenerator(modi_config, audit_context)
        payload = {"codcom": "H501"}

        headers = generator.generate_headers(payload)
        tracking_jwt = headers["Agid-JWT-TrackingEvidence"]

        # JWT should have 3 parts
        parts = tracking_jwt.split(".")
        assert len(parts) == 3

        # Decode header
        header_b64 = parts[0] + "=" * (4 - len(parts[0]) % 4)
        header = json.loads(base64.urlsafe_b64decode(header_b64))

        assert header["alg"] == "RS256"
        assert header["typ"] == "JWT"
        assert header["kid"] == "test-key-id"

    def test_tracking_jwt_claims(
        self, modi_config: "ModIConfig", audit_context: "AuditContext"
    ) -> None:
        """Test that tracking JWT has correct claims."""
        from anncsu.common.modi import ModIHeaderGenerator

        generator = ModIHeaderGenerator(modi_config, audit_context)
        payload = {"codcom": "H501"}

        headers = generator.generate_headers(payload)
        tracking_jwt = headers["Agid-JWT-TrackingEvidence"]

        # Decode payload
        parts = tracking_jwt.split(".")
        payload_b64 = parts[1] + "=" * (4 - len(parts[1]) % 4)
        claims = json.loads(base64.urlsafe_b64decode(payload_b64))

        assert claims["iss"] == "test-client-id"
        assert claims["aud"] == "https://modipa-val.anpr.interno.it"
        assert "iat" in claims
        assert "exp" in claims
        assert "jti" in claims
        assert claims["userID"] == "batch-user-001"
        assert claims["userLocation"] == "server-batch-01"
        assert claims["LoA"] == "SPID_L2"

    def test_tracking_jwt_jti_is_unique(
        self, modi_config: "ModIConfig", audit_context: "AuditContext"
    ) -> None:
        """Test that each tracking JWT has a unique jti."""
        from anncsu.common.modi import ModIHeaderGenerator

        generator = ModIHeaderGenerator(modi_config, audit_context)
        payload = {"codcom": "H501"}

        # Generate multiple headers
        jtis = set()
        for _ in range(10):
            headers = generator.generate_headers(payload)
            tracking_jwt = headers["Agid-JWT-TrackingEvidence"]

            parts = tracking_jwt.split(".")
            payload_b64 = parts[1] + "=" * (4 - len(parts[1]) % 4)
            claims = json.loads(base64.urlsafe_b64decode(payload_b64))

            jtis.add(claims["jti"])

        # All jti values should be unique
        assert len(jtis) == 10

    def test_signature_differs_for_different_payloads(
        self, modi_config: "ModIConfig"
    ) -> None:
        """Test that signature JWT differs for different payloads."""
        from anncsu.common.modi import ModIHeaderGenerator

        generator = ModIHeaderGenerator(modi_config)

        payload1 = {"codcom": "H501", "operazione": "M"}
        payload2 = {"codcom": "F205", "operazione": "I"}

        headers1 = generator.generate_headers(payload1)
        headers2 = generator.generate_headers(payload2)

        # Signatures should be different
        assert headers1["Agid-JWT-Signature"] != headers2["Agid-JWT-Signature"]

    def test_jwt_expiration_is_correct(self, modi_config: "ModIConfig") -> None:
        """Test that JWT expiration is set correctly."""
        from anncsu.common.modi import ModIHeaderGenerator

        generator = ModIHeaderGenerator(modi_config)
        payload = {"codcom": "H501"}

        before = int(datetime.now(timezone.utc).timestamp())
        headers = generator.generate_headers(payload)
        after = int(datetime.now(timezone.utc).timestamp())

        # Decode claims
        parts = headers["Agid-JWT-Signature"].split(".")
        payload_b64 = parts[1] + "=" * (4 - len(parts[1]) % 4)
        claims = json.loads(base64.urlsafe_b64decode(payload_b64))

        # iat should be within test execution window
        assert before <= claims["iat"] <= after

        # exp should be iat + validity_seconds (300)
        assert claims["exp"] == claims["iat"] + 300

    def test_generate_tracking_without_audit_raises(
        self, modi_config: "ModIConfig"
    ) -> None:
        """Test that generating tracking header without audit context raises error."""
        from anncsu.common.modi import ModIHeaderGenerator

        generator = ModIHeaderGenerator(modi_config)

        with pytest.raises(ValueError, match="Audit context is required"):
            generator._generate_tracking()


class TestCreateModiConfigFromSettings:
    """Tests for create_modi_config_from_settings function."""

    def test_create_config_from_settings_with_key_path(
        self, mock_private_key: Path
    ) -> None:
        """Test creating ModIConfig from settings with key_path."""
        from anncsu.common.config import ClientAssertionSettings
        from anncsu.common.modi import create_modi_config_from_settings

        # Save key content before it might change
        expected_key_bytes = mock_private_key.read_bytes()

        # Create real settings with mocked environment, disable .env file loading
        with patch.dict(
            "os.environ",
            {
                "PDND_KID": "test-key-id",
                "PDND_ISSUER": "test-client-id",
                "PDND_SUBJECT": "test-subject",
                "PDND_AUDIENCE": "https://auth.example.com",
                "PDND_KEY_PATH": str(mock_private_key),
                "PDND_PURPOSE_ID_PA": "pa-purpose",
                "PDND_PURPOSE_ID_COORDINATE": "coord-purpose",
                "PDND_PURPOSE_ID_ACCESSI": "",
                "PDND_PURPOSE_ID_INTERNI": "",
                "PDND_PURPOSE_ID_ODONIMI": "",
            },
            clear=False,
        ):
            # Use _env_file=None to prevent loading from .env file
            settings = ClientAssertionSettings(_env_file=None)
            config = create_modi_config_from_settings(
                settings,
                api_audience="https://modipa-val.anpr.interno.it",
            )

        assert config.kid == "test-key-id"
        assert config.issuer == "test-client-id"
        assert config.audience == "https://modipa-val.anpr.interno.it"
        assert config.private_key == expected_key_bytes

    def test_create_config_from_settings_with_private_key_string(
        self, mock_private_key: Path
    ) -> None:
        """Test creating ModIConfig from settings with private_key string."""
        from anncsu.common.config import ClientAssertionSettings
        from anncsu.common.modi import create_modi_config_from_settings

        key_content = mock_private_key.read_text()

        # Create real settings with mocked environment, disable .env file loading
        with patch.dict(
            "os.environ",
            {
                "PDND_KID": "test-key-id",
                "PDND_ISSUER": "test-client-id",
                "PDND_SUBJECT": "test-subject",
                "PDND_AUDIENCE": "https://auth.example.com",
                "PDND_PRIVATE_KEY": key_content,
                "PDND_PURPOSE_ID_PA": "pa-purpose",
                "PDND_PURPOSE_ID_COORDINATE": "coord-purpose",
                "PDND_PURPOSE_ID_ACCESSI": "",
                "PDND_PURPOSE_ID_INTERNI": "",
                "PDND_PURPOSE_ID_ODONIMI": "",
            },
            clear=False,
        ):
            # Use _env_file=None to prevent loading from .env file
            settings = ClientAssertionSettings(_env_file=None)
            config = create_modi_config_from_settings(
                settings,
                api_audience="https://api.example.com",
            )

        assert config.private_key == key_content.encode("utf-8")

    def test_create_config_raises_without_key(self) -> None:
        """Test that create_modi_config_from_settings raises without key."""
        from anncsu.common.config import ClientAssertionSettings

        # This test expects ValidationError because settings requires a key
        # We test this by verifying the validation works
        with patch.dict(
            "os.environ",
            {
                "PDND_KID": "test-key-id",
                "PDND_ISSUER": "test-client-id",
                "PDND_SUBJECT": "test-subject",
                "PDND_AUDIENCE": "https://auth.example.com",
                "PDND_PURPOSE_ID_PA": "pa-purpose",
                "PDND_PURPOSE_ID_COORDINATE": "coord-purpose",
                "PDND_PURPOSE_ID_ACCESSI": "",
                "PDND_PURPOSE_ID_INTERNI": "",
                "PDND_PURPOSE_ID_ODONIMI": "",
            },
            clear=False,
        ):
            # Without _env_file=None, validation will fail because no key is provided
            # The settings validation requires either private_key or key_path
            from pydantic import ValidationError

            with pytest.raises(
                ValidationError, match="PDND_PRIVATE_KEY.*PDND_KEY_PATH"
            ):
                ClientAssertionSettings(_env_file=None)


class TestModIHeadersIntegration:
    """Integration tests for ModI headers with real JWT verification."""

    def test_signature_jwt_is_valid(self, mock_private_key: Path) -> None:
        """Test that generated signature JWT can be decoded."""
        from anncsu.common.modi import ModIConfig, ModIHeaderGenerator

        config = ModIConfig(
            private_key=mock_private_key.read_bytes(),
            kid="test-key-id",
            issuer="test-issuer",
            audience="https://api.example.com",
        )
        generator = ModIHeaderGenerator(config)

        payload = {"test": "data"}
        headers = generator.generate_headers(payload)

        # JWT should be decodable (without verification since we don't have public key)
        signature_jwt = headers["Agid-JWT-Signature"]
        parts = signature_jwt.split(".")
        assert len(parts) == 3

        # All parts should be valid base64
        for part in parts[:2]:  # header and payload
            padded = part + "=" * (4 - len(part) % 4)
            decoded = base64.urlsafe_b64decode(padded)
            json.loads(decoded)  # Should not raise

    def test_tracking_jwt_is_valid(self, mock_private_key: Path) -> None:
        """Test that generated tracking JWT can be decoded."""
        from anncsu.common.modi import (
            AuditContext,
            ModIConfig,
            ModIHeaderGenerator,
        )

        config = ModIConfig(
            private_key=mock_private_key.read_bytes(),
            kid="test-key-id",
            issuer="test-issuer",
            audience="https://api.example.com",
        )
        audit = AuditContext(
            user_id="user",
            user_location="location",
            loa="SPID_L2",
        )
        generator = ModIHeaderGenerator(config, audit)

        payload = {"test": "data"}
        headers = generator.generate_headers(payload)

        tracking_jwt = headers["Agid-JWT-TrackingEvidence"]
        parts = tracking_jwt.split(".")
        assert len(parts) == 3

        # All parts should be valid base64
        for part in parts[:2]:
            padded = part + "=" * (4 - len(part) % 4)
            decoded = base64.urlsafe_b64decode(padded)
            json.loads(decoded)

    def test_headers_can_be_used_in_http_request(self, mock_private_key: Path) -> None:
        """Test that generated headers have correct format for HTTP requests."""
        from anncsu.common.modi import (
            AuditContext,
            ModIConfig,
            ModIHeaderGenerator,
        )

        config = ModIConfig(
            private_key=mock_private_key.read_bytes(),
            kid="test-key-id",
            issuer="test-issuer",
            audience="https://api.example.com",
        )
        audit = AuditContext(
            user_id="user",
            user_location="location",
            loa="SPID_L2",
        )
        generator = ModIHeaderGenerator(config, audit)

        payload = {"codcom": "H501", "operazione": "M"}
        headers = generator.generate_headers(payload)

        # Headers should be strings suitable for HTTP
        assert isinstance(headers["Agid-JWT-Signature"], str)
        assert isinstance(headers["Agid-JWT-TrackingEvidence"], str)

        # Headers should not contain newlines or invalid characters
        for header_value in headers.values():
            assert "\n" not in header_value
            assert "\r" not in header_value
            assert " " not in header_value or header_value.count(".") == 2
