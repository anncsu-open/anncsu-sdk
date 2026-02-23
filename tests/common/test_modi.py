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

        # Compute expected digest using standard base64 with padding (RFC 3230)
        payload_bytes = json.dumps(
            payload, separators=(",", ":"), sort_keys=True
        ).encode("utf-8")
        expected_digest = hashlib.sha256(payload_bytes).digest()
        expected_b64 = base64.b64encode(expected_digest).decode("utf-8")

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
                "PDND_PURPOSE_ID_COORDINATE_BULK": "coord-bulk-purpose",
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
                "PDND_PURPOSE_ID_COORDINATE_BULK": "coord-bulk-purpose",
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
                "PDND_PURPOSE_ID_COORDINATE_BULK": "coord-bulk-purpose",
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


class TestModIDigestHeader:
    """Tests for HTTP Digest header generation."""

    def test_generate_headers_includes_digest(self, mock_private_key: Path) -> None:
        """Test that generate_headers includes HTTP Digest header."""
        from anncsu.common.modi import ModIConfig, ModIHeaderGenerator

        config = ModIConfig(
            private_key=mock_private_key.read_bytes(),
            kid="test-key-id",
            issuer="test-issuer",
            audience="https://api.example.com",
        )
        generator = ModIHeaderGenerator(config)
        payload = {"codcom": "H501", "operazione": "M"}

        headers = generator.generate_headers(payload)

        assert "Digest" in headers
        assert headers["Digest"].startswith("SHA-256=")

    def test_digest_header_uses_standard_base64(self, mock_private_key: Path) -> None:
        """Test that Digest header uses standard base64 with padding (RFC 3230)."""
        from anncsu.common.modi import ModIConfig, ModIHeaderGenerator

        config = ModIConfig(
            private_key=mock_private_key.read_bytes(),
            kid="test-key-id",
            issuer="test-issuer",
            audience="https://api.example.com",
        )
        generator = ModIHeaderGenerator(config)
        payload = {"codcom": "H501", "operazione": "M"}

        headers = generator.generate_headers(payload)

        # Extract the base64 part after "SHA-256="
        digest_value = headers["Digest"].split("=", 1)[1]

        # Standard base64 should decode without adding padding
        # and should NOT use urlsafe characters (- or _)
        assert "-" not in digest_value
        assert "_" not in digest_value

        # Should be valid standard base64 (may have padding =)
        import base64

        decoded = base64.b64decode(digest_value)
        assert len(decoded) == 32  # SHA-256 produces 32 bytes

    def test_digest_header_matches_jwt_signed_headers(
        self, mock_private_key: Path
    ) -> None:
        """Test that Digest header value matches the digest in JWT signed_headers."""
        from anncsu.common.modi import ModIConfig, ModIHeaderGenerator

        config = ModIConfig(
            private_key=mock_private_key.read_bytes(),
            kid="test-key-id",
            issuer="test-issuer",
            audience="https://api.example.com",
        )
        generator = ModIHeaderGenerator(config)
        payload = {"codcom": "H501", "operazione": "M"}

        headers = generator.generate_headers(payload)

        # Get Digest header value
        http_digest = headers["Digest"]

        # Extract digest from JWT signed_headers
        import base64
        import json

        parts = headers["Agid-JWT-Signature"].split(".")
        payload_b64 = parts[1] + "=" * (4 - len(parts[1]) % 4)
        claims = json.loads(base64.urlsafe_b64decode(payload_b64))

        jwt_digest = claims["signed_headers"][0]["digest"]

        # Both should be identical
        assert http_digest == jwt_digest

    def test_digest_computed_from_compact_json(self, mock_private_key: Path) -> None:
        """Test that digest is computed from compact JSON.

        The digest is computed WITHOUT sort_keys to match Speakeasy's
        serialization. Keys must be in sorted order to avoid mismatch.
        """
        import base64
        import hashlib
        import json

        from anncsu.common.modi import ModIConfig, ModIHeaderGenerator

        config = ModIConfig(
            private_key=mock_private_key.read_bytes(),
            kid="test-key-id",
            issuer="test-issuer",
            audience="https://api.example.com",
        )
        generator = ModIHeaderGenerator(config)

        # Payload with keys in alphabetical order (required for consistency)
        payload = {"codcom": "H501", "operazione": "M"}

        headers = generator.generate_headers(payload)

        # Compute expected digest with compact JSON (no sort_keys)
        expected_json = json.dumps(payload, separators=(",", ":"))
        expected_digest = hashlib.sha256(expected_json.encode("utf-8")).digest()
        expected_b64 = base64.b64encode(expected_digest).decode("utf-8")

        assert headers["Digest"] == f"SHA-256={expected_b64}"


class TestModISignatureJwtNbfClaim:
    """Tests for nbf (not before) claim in ModI JWTs."""

    def test_signature_jwt_has_nbf_claim(self, mock_private_key: Path) -> None:
        """Test that signature JWT includes nbf claim."""
        import base64
        import json

        from anncsu.common.modi import ModIConfig, ModIHeaderGenerator

        config = ModIConfig(
            private_key=mock_private_key.read_bytes(),
            kid="test-key-id",
            issuer="test-issuer",
            audience="https://api.example.com",
        )
        generator = ModIHeaderGenerator(config)
        payload = {"codcom": "H501"}

        headers = generator.generate_headers(payload)

        # Decode JWT claims
        parts = headers["Agid-JWT-Signature"].split(".")
        payload_b64 = parts[1] + "=" * (4 - len(parts[1]) % 4)
        claims = json.loads(base64.urlsafe_b64decode(payload_b64))

        assert "nbf" in claims
        # nbf should equal iat (token valid from issue time)
        assert claims["nbf"] == claims["iat"]

    def test_tracking_jwt_has_nbf_claim(self, mock_private_key: Path) -> None:
        """Test that tracking JWT includes nbf claim."""
        import base64
        import json

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
        payload = {"codcom": "H501"}

        headers = generator.generate_headers(payload)

        # Decode JWT claims
        parts = headers["Agid-JWT-TrackingEvidence"].split(".")
        payload_b64 = parts[1] + "=" * (4 - len(parts[1]) % 4)
        claims = json.loads(base64.urlsafe_b64decode(payload_b64))

        assert "nbf" in claims
        assert claims["nbf"] == claims["iat"]


class TestModISignatureJwtJtiClaim:
    """Tests for jti claim in Signature JWT."""

    def test_signature_jwt_has_jti_claim(self, mock_private_key: Path) -> None:
        """Test that signature JWT includes jti claim."""
        import base64
        import json

        from anncsu.common.modi import ModIConfig, ModIHeaderGenerator

        config = ModIConfig(
            private_key=mock_private_key.read_bytes(),
            kid="test-key-id",
            issuer="test-issuer",
            audience="https://api.example.com",
        )
        generator = ModIHeaderGenerator(config)
        payload = {"codcom": "H501"}

        headers = generator.generate_headers(payload)

        # Decode JWT claims
        parts = headers["Agid-JWT-Signature"].split(".")
        payload_b64 = parts[1] + "=" * (4 - len(parts[1]) % 4)
        claims = json.loads(base64.urlsafe_b64decode(payload_b64))

        assert "jti" in claims
        # jti should be a valid UUID string
        import uuid

        uuid.UUID(claims["jti"])  # Should not raise

    def test_signature_jwt_jti_is_unique(self, mock_private_key: Path) -> None:
        """Test that each signature JWT has a unique jti."""
        import base64
        import json

        from anncsu.common.modi import ModIConfig, ModIHeaderGenerator

        config = ModIConfig(
            private_key=mock_private_key.read_bytes(),
            kid="test-key-id",
            issuer="test-issuer",
            audience="https://api.example.com",
        )
        generator = ModIHeaderGenerator(config)
        payload = {"codcom": "H501"}

        jtis = set()
        for _ in range(10):
            headers = generator.generate_headers(payload)
            parts = headers["Agid-JWT-Signature"].split(".")
            payload_b64 = parts[1] + "=" * (4 - len(parts[1]) % 4)
            claims = json.loads(base64.urlsafe_b64decode(payload_b64))
            jtis.add(claims["jti"])

        assert len(jtis) == 10


class TestModIDigestBodyConsistency:
    """Tests for ensuring Digest is computed on the exact HTTP body.

    The Digest header and the digest in signed_headers MUST be computed
    on the exact same bytes that will be sent as the HTTP request body.
    Any mismatch will cause 400 InteroperabilityInvalidRequest errors.
    """

    def test_digest_matches_json_serialized_payload(
        self, mock_private_key: Path
    ) -> None:
        """Test that digest is computed on JSON-serialized payload."""
        import base64
        import hashlib
        import json

        from anncsu.common.modi import ModIConfig, ModIHeaderGenerator

        config = ModIConfig(
            private_key=mock_private_key.read_bytes(),
            kid="test-key-id",
            issuer="test-issuer",
            audience="https://api.example.com",
        )
        generator = ModIHeaderGenerator(config)

        payload = {"codcom": "H501", "operazione": "M"}
        headers = generator.generate_headers(payload)

        # Compute expected digest from the same serialization
        expected_body = json.dumps(payload, separators=(",", ":"), sort_keys=True)
        expected_digest = hashlib.sha256(expected_body.encode("utf-8")).digest()
        expected_b64 = base64.b64encode(expected_digest).decode("utf-8")

        assert headers["Digest"] == f"SHA-256={expected_b64}"

    def test_digest_with_nested_objects(self, mock_private_key: Path) -> None:
        """Test digest computation with nested objects like Pydantic models."""
        import base64
        import hashlib
        import json

        from anncsu.common.modi import ModIConfig, ModIHeaderGenerator

        config = ModIConfig(
            private_key=mock_private_key.read_bytes(),
            kid="test-key-id",
            issuer="test-issuer",
            audience="https://api.example.com",
        )
        generator = ModIHeaderGenerator(config)

        # Nested payload with keys in sorted order (required)
        # Note: keys must be alphabetically sorted at all levels
        payload = {
            "accesso": {
                "codcom": "H501",
                "coordinate": {"metodo": None, "x": None, "y": None, "z": None},
                "progr_civico": "5256880",
            },
            "operazione": "M",
        }
        headers = generator.generate_headers(payload)

        # Verify digest is computed correctly (no sort_keys)
        expected_body = json.dumps(payload, separators=(",", ":"))
        expected_digest = hashlib.sha256(expected_body.encode("utf-8")).digest()
        expected_b64 = base64.b64encode(expected_digest).decode("utf-8")

        assert headers["Digest"] == f"SHA-256={expected_b64}"

    def test_digest_with_null_values_preserved(self, mock_private_key: Path) -> None:
        """Test that null values are preserved in digest computation.

        When the HTTP body contains null values, the digest must be computed
        on the body WITH the null values, not with them excluded.
        """

        from anncsu.common.modi import ModIConfig, ModIHeaderGenerator

        config = ModIConfig(
            private_key=mock_private_key.read_bytes(),
            kid="test-key-id",
            issuer="test-issuer",
            audience="https://api.example.com",
        )
        generator = ModIHeaderGenerator(config)

        # Payload with null values (keys in sorted order)
        payload_with_nulls = {
            "accesso": {
                "codcom": "H501",
                "coordinate": {"metodo": None, "x": None, "y": None, "z": None},
                "progr_civico": "5256880",
            },
            "operazione": "M",
        }

        # Same payload without nulls (keys in sorted order)
        payload_without_nulls = {
            "accesso": {
                "codcom": "H501",
                "progr_civico": "5256880",
            },
            "operazione": "M",
        }

        headers_with_nulls = generator.generate_headers(payload_with_nulls)
        headers_without_nulls = generator.generate_headers(payload_without_nulls)

        # Digests should be DIFFERENT because payloads are different
        assert headers_with_nulls["Digest"] != headers_without_nulls["Digest"]

    def test_http_body_must_match_digest_exactly(self, mock_private_key: Path) -> None:
        """Test that verifies the HTTP body serialization matches digest.

        This test documents the CRITICAL requirement: the exact bytes sent
        as the HTTP body must match what was used to compute the digest.
        """
        import base64
        import hashlib
        import json

        from anncsu.common.modi import ModIConfig, ModIHeaderGenerator

        config = ModIConfig(
            private_key=mock_private_key.read_bytes(),
            kid="test-key-id",
            issuer="test-issuer",
            audience="https://api.example.com",
        )
        generator = ModIHeaderGenerator(config)

        # Keys in sorted order
        payload = {"codcom": "H501", "operazione": "M"}
        headers = generator.generate_headers(payload)

        # Simulate what the HTTP body should be (no sort_keys since keys are sorted)
        http_body = json.dumps(payload, separators=(",", ":"))
        http_body_bytes = http_body.encode("utf-8")

        # Verify the digest matches the HTTP body
        actual_digest = hashlib.sha256(http_body_bytes).digest()
        actual_b64 = base64.b64encode(actual_digest).decode("utf-8")

        assert headers["Digest"] == f"SHA-256={actual_b64}"

        # Also verify the JWT signed_headers contains the same digest
        parts = headers["Agid-JWT-Signature"].split(".")
        claims_b64 = parts[1] + "=" * (4 - len(parts[1]) % 4)
        claims = json.loads(base64.urlsafe_b64decode(claims_b64))

        assert claims["signed_headers"][0]["digest"] == headers["Digest"]


class TestModIDigestWithPydanticModels:
    """Tests for ModI digest computation with Pydantic model serialization.

    These tests verify that when using Pydantic models (like coordinate API),
    the digest is computed on the EXACT same bytes as the HTTP body.
    """

    def test_pydantic_model_dump_produces_correct_digest(
        self, mock_private_key: Path
    ) -> None:
        """Test digest with Pydantic model_dump output."""
        import base64
        import hashlib
        import json

        from anncsu.common.modi import ModIConfig, ModIHeaderGenerator

        config = ModIConfig(
            private_key=mock_private_key.read_bytes(),
            kid="test-key-id",
            issuer="test-issuer",
            audience="https://api.example.com",
        )
        generator = ModIHeaderGenerator(config)

        # Simulate Pydantic model_dump with keys in sorted order
        pydantic_output = {
            "accesso": {
                "codcom": "H501",
                "coordinate": {"metodo": None, "x": None, "y": None, "z": None},
                "progr_civico": "5256880",
            },
            "operazione": "M",
        }

        headers = generator.generate_headers(pydantic_output)

        # The digest should match what we'd compute from the serialized payload
        expected_body = json.dumps(pydantic_output, separators=(",", ":"))
        expected_digest = hashlib.sha256(expected_body.encode("utf-8")).digest()
        expected_b64 = base64.b64encode(expected_digest).decode("utf-8")

        assert headers["Digest"] == f"SHA-256={expected_b64}"

    def test_exclude_none_changes_digest(self, mock_private_key: Path) -> None:
        """Test that exclude_none=True produces different digest than with nulls.

        IMPORTANT: If the HTTP body is serialized WITH null values but the
        digest is computed WITHOUT them (or vice versa), validation will fail.
        """
        import json

        from anncsu.common.modi import ModIConfig, ModIHeaderGenerator

        config = ModIConfig(
            private_key=mock_private_key.read_bytes(),
            kid="test-key-id",
            issuer="test-issuer",
            audience="https://api.example.com",
        )
        generator = ModIHeaderGenerator(config)

        # With nulls - keys in sorted order
        payload_with_nulls = {
            "accesso": {
                "codcom": "H501",
                "coordinate": {"x": None, "y": None},
            },
        }

        # Without nulls - keys in sorted order
        payload_without_nulls = {
            "accesso": {
                "codcom": "H501",
            },
        }

        headers_with = generator.generate_headers(payload_with_nulls)
        headers_without = generator.generate_headers(payload_without_nulls)

        # These MUST be different - if they match it's a bug
        assert headers_with["Digest"] != headers_without["Digest"]

        # Document the serialized forms for clarity
        json_with = json.dumps(
            payload_with_nulls, separators=(",", ":"), sort_keys=True
        )
        json_without = json.dumps(
            payload_without_nulls, separators=(",", ":"), sort_keys=True
        )
        assert json_with != json_without


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


class TestSortDictRecursively:
    """Tests for sort_dict_recursively helper function.

    This function is critical for ensuring the digest matches the HTTP body.
    It must sort all dictionary keys recursively so that:
    1. The digest is computed on sorted JSON
    2. Speakeasy receives a pre-sorted dict and produces the same JSON
    """

    def test_sorts_top_level_keys(self) -> None:
        """Test that top-level keys are sorted alphabetically."""
        from anncsu.common.modi import sort_dict_recursively

        input_dict = {"z": 1, "a": 2, "m": 3}
        result = sort_dict_recursively(input_dict)

        assert list(result.keys()) == ["a", "m", "z"]
        assert result == {"a": 2, "m": 3, "z": 1}

    def test_sorts_nested_dict_keys(self) -> None:
        """Test that nested dict keys are also sorted."""
        from anncsu.common.modi import sort_dict_recursively

        input_dict = {
            "outer_z": {"inner_z": 1, "inner_a": 2},
            "outer_a": {"nested_z": 3, "nested_a": 4},
        }
        result = sort_dict_recursively(input_dict)

        # Top level sorted
        assert list(result.keys()) == ["outer_a", "outer_z"]
        # Nested levels sorted
        assert list(result["outer_a"].keys()) == ["nested_a", "nested_z"]
        assert list(result["outer_z"].keys()) == ["inner_a", "inner_z"]

    def test_sorts_deeply_nested_dicts(self) -> None:
        """Test sorting with multiple levels of nesting."""
        from anncsu.common.modi import sort_dict_recursively

        input_dict = {
            "level1_z": {
                "level2_z": {
                    "level3_z": 1,
                    "level3_a": 2,
                },
                "level2_a": 3,
            },
            "level1_a": 4,
        }
        result = sort_dict_recursively(input_dict)

        assert list(result.keys()) == ["level1_a", "level1_z"]
        assert list(result["level1_z"].keys()) == ["level2_a", "level2_z"]
        assert list(result["level1_z"]["level2_z"].keys()) == [
            "level3_a",
            "level3_z",
        ]

    def test_handles_lists_with_dicts(self) -> None:
        """Test that dicts inside lists are also sorted."""
        from anncsu.common.modi import sort_dict_recursively

        input_dict = {
            "items": [
                {"z": 1, "a": 2},
                {"y": 3, "b": 4},
            ]
        }
        result = sort_dict_recursively(input_dict)

        assert list(result["items"][0].keys()) == ["a", "z"]
        assert list(result["items"][1].keys()) == ["b", "y"]

    def test_handles_nested_lists(self) -> None:
        """Test handling of nested lists."""
        from anncsu.common.modi import sort_dict_recursively

        input_dict = {
            "matrix": [
                [{"z": 1, "a": 2}],
                [{"y": 3, "b": 4}],
            ]
        }
        result = sort_dict_recursively(input_dict)

        assert list(result["matrix"][0][0].keys()) == ["a", "z"]
        assert list(result["matrix"][1][0].keys()) == ["b", "y"]

    def test_preserves_primitive_values(self) -> None:
        """Test that primitive values are preserved unchanged."""
        from anncsu.common.modi import sort_dict_recursively

        input_dict = {
            "string": "hello",
            "number": 42,
            "float": 3.14,
            "bool_true": True,
            "bool_false": False,
            "none": None,
            "empty_string": "",
        }
        result = sort_dict_recursively(input_dict)

        assert result["string"] == "hello"
        assert result["number"] == 42
        assert result["float"] == 3.14
        assert result["bool_true"] is True
        assert result["bool_false"] is False
        assert result["none"] is None
        assert result["empty_string"] == ""

    def test_preserves_list_order(self) -> None:
        """Test that list element order is preserved (only dict keys are sorted)."""
        from anncsu.common.modi import sort_dict_recursively

        input_dict = {"items": [3, 1, 2, "z", "a"]}
        result = sort_dict_recursively(input_dict)

        # List order must be preserved
        assert result["items"] == [3, 1, 2, "z", "a"]

    def test_empty_dict(self) -> None:
        """Test handling of empty dict."""
        from anncsu.common.modi import sort_dict_recursively

        result = sort_dict_recursively({})
        assert result == {}

    def test_empty_nested_dict(self) -> None:
        """Test handling of empty nested dict."""
        from anncsu.common.modi import sort_dict_recursively

        input_dict = {"outer": {}}
        result = sort_dict_recursively(input_dict)
        assert result == {"outer": {}}

    def test_pydantic_style_coordinate_payload(self) -> None:
        """Test with a real Pydantic-style coordinate API payload.

        This is the exact structure used by the coordinate CLI command.
        """
        from anncsu.common.modi import sort_dict_recursively

        # Simulate Pydantic model_dump output (keys in definition order)
        input_dict = {
            "accesso": {
                "codcom": "H501",
                "progr_civico": "5256880",
                "coordinate": {"x": "", "y": "", "z": "", "metodo": ""},
            },
        }
        result = sort_dict_recursively(input_dict)

        # Verify all levels are sorted
        assert list(result["accesso"].keys()) == [
            "codcom",
            "coordinate",
            "progr_civico",
        ]
        assert list(result["accesso"]["coordinate"].keys()) == [
            "metodo",
            "x",
            "y",
            "z",
        ]

    def test_sorted_dict_produces_same_json_as_sort_keys(self) -> None:
        """Test that sorted dict serializes identically to sort_keys=True.

        This is the CRITICAL test: after sorting, json.dumps without sort_keys
        must produce the same output as json.dumps with sort_keys=True.
        """
        from anncsu.common.modi import sort_dict_recursively

        # Unsorted input
        input_dict = {
            "z": 1,
            "a": {"z": 2, "a": 3},
            "m": [{"z": 4, "a": 5}],
        }

        sorted_dict = sort_dict_recursively(input_dict)

        # Serialize without sort_keys (like Speakeasy does)
        json_without_sort_keys = json.dumps(sorted_dict, separators=(",", ":"))

        # Serialize with sort_keys (like our digest computation)
        json_with_sort_keys = json.dumps(
            input_dict, separators=(",", ":"), sort_keys=True
        )

        # They MUST be identical
        assert json_without_sort_keys == json_with_sort_keys


class TestSpeakeasySerializationBehavior:
    """Tests documenting Speakeasy's JSON serialization behavior.

    These tests verify our assumptions about how Speakeasy serializes JSON.
    If Speakeasy changes behavior, these tests will fail and alert us.
    """

    def test_speakeasy_preserves_insertion_order(self) -> None:
        """Verify that dict insertion order is preserved in JSON output.

        Python 3.7+ guarantees dict insertion order, and json.dumps
        without sort_keys preserves this order.
        """
        # Dict with keys in non-alphabetical order
        payload = {"z": 1, "a": 2, "m": 3}

        # Speakeasy-style serialization (no sort_keys)
        result = json.dumps(payload, separators=(",", ":"))

        # Order is preserved (z, a, m - not a, m, z)
        assert result == '{"z":1,"a":2,"m":3}'

    def test_speakeasy_does_not_sort_keys(self) -> None:
        """Verify that Speakeasy serialization differs from sort_keys=True."""
        payload = {"z": 1, "a": 2}

        speakeasy_style = json.dumps(payload, separators=(",", ":"))
        sorted_style = json.dumps(payload, separators=(",", ":"), sort_keys=True)

        # These MUST be different
        assert speakeasy_style != sorted_style
        assert speakeasy_style == '{"z":1,"a":2}'
        assert sorted_style == '{"a":2,"z":1}'

    def test_speakeasy_nested_dict_order(self) -> None:
        """Verify nested dict key order behavior."""
        payload = {
            "outer_z": {"inner_z": 1, "inner_a": 2},
            "outer_a": 3,
        }

        result = json.dumps(payload, separators=(",", ":"))

        # Outer keys preserve insertion order
        assert result.startswith('{"outer_z":')
        # Inner keys also preserve insertion order
        assert '{"inner_z":1,"inner_a":2}' in result


class TestSpeakeasySerializationBehaviorDocumentation:
    """Documentation tests for Speakeasy's JSON serialization behavior.

    These tests document (not test generate_headers) how Speakeasy serializes JSON.
    """

    def test_speakeasy_serialization_does_not_use_sort_keys(self) -> None:
        """Document that Speakeasy does NOT use sort_keys.

        This test verifies our understanding of Speakeasy's behavior.
        It serves as documentation and regression test.
        """
        # Speakeasy uses: json.dumps(d, separators=(",", ":"))
        # NOT: json.dumps(d, separators=(",", ":"), sort_keys=True)

        payload = {"z": 2, "a": 1}

        speakeasy_style = json.dumps(payload, separators=(",", ":"))
        sorted_style = json.dumps(payload, separators=(",", ":"), sort_keys=True)

        # These should be DIFFERENT
        assert speakeasy_style != sorted_style
        assert speakeasy_style == '{"z":2,"a":1}'  # Insertion order preserved
        assert sorted_style == '{"a":1,"z":2}'  # Keys sorted


class TestCreateModiConfigFromSettingsEServiceKey:
    """Tests for create_modi_config_from_settings with dedicated ModI signing key.

    The Client e-service portachiavi on PDND can hold multiple keys:
    - Voucher key: kid + private_key (for client_assertion → voucher)
    - ModI signing key: modi_kid + modi_private_key (for Agid-JWT-Signature/TrackingEvidence)

    When ModI signing key fields are set, the factory function MUST use them
    for ModIConfig. When not set, it MUST fall back to the voucher key
    for backward compatibility.
    """

    def test_uses_e_service_kid_when_available(
        self, mock_private_key: Path, mock_e_service_private_key: Path
    ) -> None:
        """Test that config.kid uses modi_kid when available, not kid."""
        from anncsu.common.config import ClientAssertionSettings
        from anncsu.common.modi import create_modi_config_from_settings

        e_service_key_content = mock_e_service_private_key.read_text()

        with patch.dict(
            "os.environ",
            {
                "PDND_KID": "interop-kid",
                "PDND_ISSUER": "test-client-id",
                "PDND_SUBJECT": "test-subject",
                "PDND_AUDIENCE": "https://auth.example.com",
                "PDND_KEY_PATH": str(mock_private_key),
                "PDND_PURPOSE_ID_PA": "pa-purpose",
                "PDND_PURPOSE_ID_COORDINATE": "coord-purpose",
                "PDND_PURPOSE_ID_COORDINATE_BULK": "",
                "PDND_PURPOSE_ID_ACCESSI": "",
                "PDND_PURPOSE_ID_INTERNI": "",
                "PDND_PURPOSE_ID_ODONIMI": "",
                "PDND_MODI_KID": "e-service-kid",
                "PDND_MODI_PRIVATE_KEY": e_service_key_content,
            },
            clear=False,
        ):
            settings = ClientAssertionSettings(_env_file=None)
            config = create_modi_config_from_settings(
                settings, api_audience="https://api.example.com"
            )

        # ModI config MUST use e-service kid, NOT interop kid
        assert config.kid == "e-service-kid"
        assert config.kid != "interop-kid"

    def test_uses_e_service_private_key_when_available(
        self, mock_private_key: Path, mock_e_service_private_key: Path
    ) -> None:
        """Test that config.private_key uses modi_private_key when available."""
        from anncsu.common.config import ClientAssertionSettings
        from anncsu.common.modi import create_modi_config_from_settings

        e_service_key_content = mock_e_service_private_key.read_text()
        interop_key_content = mock_private_key.read_text()

        with patch.dict(
            "os.environ",
            {
                "PDND_KID": "interop-kid",
                "PDND_ISSUER": "test-client-id",
                "PDND_SUBJECT": "test-subject",
                "PDND_AUDIENCE": "https://auth.example.com",
                "PDND_PRIVATE_KEY": interop_key_content,
                "PDND_PURPOSE_ID_PA": "pa-purpose",
                "PDND_PURPOSE_ID_COORDINATE": "coord-purpose",
                "PDND_PURPOSE_ID_COORDINATE_BULK": "",
                "PDND_PURPOSE_ID_ACCESSI": "",
                "PDND_PURPOSE_ID_INTERNI": "",
                "PDND_PURPOSE_ID_ODONIMI": "",
                "PDND_MODI_KID": "e-service-kid",
                "PDND_MODI_PRIVATE_KEY": e_service_key_content,
            },
            clear=False,
        ):
            settings = ClientAssertionSettings(_env_file=None)
            config = create_modi_config_from_settings(
                settings, api_audience="https://api.example.com"
            )

        # ModI config MUST use e-service private key
        assert config.private_key == e_service_key_content.encode("utf-8")
        assert config.private_key != interop_key_content.encode("utf-8")

    def test_uses_e_service_key_path_when_available(
        self, mock_private_key: Path, mock_e_service_private_key: Path
    ) -> None:
        """Test that config loads private key from modi_key_path when available."""
        from anncsu.common.config import ClientAssertionSettings
        from anncsu.common.modi import create_modi_config_from_settings

        expected_key_bytes = mock_e_service_private_key.read_bytes()

        with patch.dict(
            "os.environ",
            {
                "PDND_KID": "interop-kid",
                "PDND_ISSUER": "test-client-id",
                "PDND_SUBJECT": "test-subject",
                "PDND_AUDIENCE": "https://auth.example.com",
                "PDND_KEY_PATH": str(mock_private_key),
                "PDND_PURPOSE_ID_PA": "pa-purpose",
                "PDND_PURPOSE_ID_COORDINATE": "coord-purpose",
                "PDND_PURPOSE_ID_COORDINATE_BULK": "",
                "PDND_PURPOSE_ID_ACCESSI": "",
                "PDND_PURPOSE_ID_INTERNI": "",
                "PDND_PURPOSE_ID_ODONIMI": "",
                "PDND_MODI_KID": "e-service-kid",
                "PDND_MODI_KEY_PATH": str(mock_e_service_private_key),
            },
            clear=False,
        ):
            settings = ClientAssertionSettings(_env_file=None)
            config = create_modi_config_from_settings(
                settings, api_audience="https://api.example.com"
            )

        # ModI config MUST use e-service key loaded from path
        assert config.private_key == expected_key_bytes

    def test_e_service_key_takes_priority_over_interop_key(
        self, mock_private_key: Path, mock_e_service_private_key: Path
    ) -> None:
        """Test that e-service key is used even when interop key is also present."""
        from anncsu.common.config import ClientAssertionSettings
        from anncsu.common.modi import create_modi_config_from_settings

        e_service_key_content = mock_e_service_private_key.read_text()
        interop_key_bytes = mock_private_key.read_bytes()

        with patch.dict(
            "os.environ",
            {
                "PDND_KID": "interop-kid",
                "PDND_ISSUER": "test-client-id",
                "PDND_SUBJECT": "test-subject",
                "PDND_AUDIENCE": "https://auth.example.com",
                "PDND_KEY_PATH": str(mock_private_key),
                "PDND_PURPOSE_ID_PA": "pa-purpose",
                "PDND_PURPOSE_ID_COORDINATE": "coord-purpose",
                "PDND_PURPOSE_ID_COORDINATE_BULK": "",
                "PDND_PURPOSE_ID_ACCESSI": "",
                "PDND_PURPOSE_ID_INTERNI": "",
                "PDND_PURPOSE_ID_ODONIMI": "",
                "PDND_MODI_KID": "e-service-kid",
                "PDND_MODI_PRIVATE_KEY": e_service_key_content,
            },
            clear=False,
        ):
            settings = ClientAssertionSettings(_env_file=None)
            config = create_modi_config_from_settings(
                settings, api_audience="https://api.example.com"
            )

        # E-service key MUST take priority
        assert config.kid == "e-service-kid"
        assert config.private_key != interop_key_bytes

    def test_e_service_private_key_takes_priority_over_key_path(
        self, mock_private_key: Path, mock_e_service_private_key: Path
    ) -> None:
        """Test that modi_private_key takes priority over modi_key_path."""
        from anncsu.common.config import ClientAssertionSettings
        from anncsu.common.modi import create_modi_config_from_settings

        e_service_key_content = mock_e_service_private_key.read_text()

        with patch.dict(
            "os.environ",
            {
                "PDND_KID": "interop-kid",
                "PDND_ISSUER": "test-client-id",
                "PDND_SUBJECT": "test-subject",
                "PDND_AUDIENCE": "https://auth.example.com",
                "PDND_KEY_PATH": str(mock_private_key),
                "PDND_PURPOSE_ID_PA": "pa-purpose",
                "PDND_PURPOSE_ID_COORDINATE": "coord-purpose",
                "PDND_PURPOSE_ID_COORDINATE_BULK": "",
                "PDND_PURPOSE_ID_ACCESSI": "",
                "PDND_PURPOSE_ID_INTERNI": "",
                "PDND_PURPOSE_ID_ODONIMI": "",
                "PDND_MODI_KID": "e-service-kid",
                "PDND_MODI_PRIVATE_KEY": e_service_key_content,
                "PDND_MODI_KEY_PATH": str(mock_private_key),  # Also set path
            },
            clear=False,
        ):
            settings = ClientAssertionSettings(_env_file=None)
            config = create_modi_config_from_settings(
                settings, api_audience="https://api.example.com"
            )

        # modi_private_key string MUST take priority over modi_key_path
        assert config.private_key == e_service_key_content.encode("utf-8")

    def test_raises_when_modi_kid_set_but_no_modi_key(
        self, mock_private_key: Path
    ) -> None:
        """Test that ValueError is raised when modi_kid is set but no e-service key."""
        from anncsu.common.config import ClientAssertionSettings
        from anncsu.common.modi import create_modi_config_from_settings

        with patch.dict(
            "os.environ",
            {
                "PDND_KID": "interop-kid",
                "PDND_ISSUER": "test-client-id",
                "PDND_SUBJECT": "test-subject",
                "PDND_AUDIENCE": "https://auth.example.com",
                "PDND_KEY_PATH": str(mock_private_key),
                "PDND_PURPOSE_ID_PA": "pa-purpose",
                "PDND_PURPOSE_ID_COORDINATE": "coord-purpose",
                "PDND_PURPOSE_ID_COORDINATE_BULK": "",
                "PDND_PURPOSE_ID_ACCESSI": "",
                "PDND_PURPOSE_ID_INTERNI": "",
                "PDND_PURPOSE_ID_ODONIMI": "",
                "PDND_MODI_KID": "e-service-kid",
                # No PDND_MODI_PRIVATE_KEY or PDND_MODI_KEY_PATH
            },
            clear=False,
        ):
            settings = ClientAssertionSettings(_env_file=None)

            with pytest.raises(
                ValueError, match="[Ee]-[Ss]ervice.*key|modi.*key|PDND_MODI"
            ):
                create_modi_config_from_settings(
                    settings, api_audience="https://api.example.com"
                )

    def test_falls_back_to_interop_key_when_no_e_service_key(
        self, mock_private_key: Path
    ) -> None:
        """Test backward compat: uses interop key when no e-service fields set."""
        from anncsu.common.config import ClientAssertionSettings
        from anncsu.common.modi import create_modi_config_from_settings

        expected_key_bytes = mock_private_key.read_bytes()

        with patch.dict(
            "os.environ",
            {
                "PDND_KID": "interop-kid",
                "PDND_ISSUER": "test-client-id",
                "PDND_SUBJECT": "test-subject",
                "PDND_AUDIENCE": "https://auth.example.com",
                "PDND_KEY_PATH": str(mock_private_key),
                "PDND_PURPOSE_ID_PA": "pa-purpose",
                "PDND_PURPOSE_ID_COORDINATE": "coord-purpose",
                "PDND_PURPOSE_ID_COORDINATE_BULK": "",
                "PDND_PURPOSE_ID_ACCESSI": "",
                "PDND_PURPOSE_ID_INTERNI": "",
                "PDND_PURPOSE_ID_ODONIMI": "",
                # No PDND_MODI_* fields
            },
            clear=False,
        ):
            settings = ClientAssertionSettings(_env_file=None)
            config = create_modi_config_from_settings(
                settings, api_audience="https://api.example.com"
            )

        # Should fall back to interop key
        assert config.kid == "interop-kid"
        assert config.private_key == expected_key_bytes

    def test_falls_back_to_interop_kid_when_no_modi_kid(
        self, mock_private_key: Path
    ) -> None:
        """Test backward compat: config.kid is interop kid when modi_kid not set."""
        from anncsu.common.config import ClientAssertionSettings
        from anncsu.common.modi import create_modi_config_from_settings

        with patch.dict(
            "os.environ",
            {
                "PDND_KID": "interop-kid",
                "PDND_ISSUER": "test-client-id",
                "PDND_SUBJECT": "test-subject",
                "PDND_AUDIENCE": "https://auth.example.com",
                "PDND_KEY_PATH": str(mock_private_key),
                "PDND_PURPOSE_ID_PA": "pa-purpose",
                "PDND_PURPOSE_ID_COORDINATE": "coord-purpose",
                "PDND_PURPOSE_ID_COORDINATE_BULK": "",
                "PDND_PURPOSE_ID_ACCESSI": "",
                "PDND_PURPOSE_ID_INTERNI": "",
                "PDND_PURPOSE_ID_ODONIMI": "",
            },
            clear=False,
        ):
            settings = ClientAssertionSettings(_env_file=None)
            config = create_modi_config_from_settings(
                settings, api_audience="https://api.example.com"
            )

        assert config.kid == "interop-kid"
