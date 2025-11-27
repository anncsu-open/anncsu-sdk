"""Tests for the PDND client assertion module.

This module tests the core client assertion generation functionality
used for PDND authentication.
"""

import datetime
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest
from pydantic import ValidationError

from anncsu.common.pdnd_assertion import (
    ClientAssertionConfig,
    ClientAssertionError,
    JWTGenerationError,
    KeyFileError,
    create_client_assertion,
)

# Test RSA key pair for testing (2048-bit) - generated with cryptography library
TEST_PRIVATE_KEY = b"""-----BEGIN RSA PRIVATE KEY-----
MIIEpAIBAAKCAQEAusasn26nL4hTIX8YnML/E5gGWOHvWTXsbuP983clViPko0lt
Z1BTa+7i9K7R8h8MIeQWU3guf4vzf/n3EFixtTpctdWdREksGjUHVt9R4n38+Ik8
MnsLgXsUGcY+ZLmCFIRYxaZGwAV6poY3ve4BfqcYHAYfnJKSajQPqZogluH97dM8
8IcSeim//PfXUup+A+FPu22zrgtyg/oYSg+LRm0XbxPEii5m9UafRLdejJDAFzk1
ejlISbYueLikLeKxNkGgsaSMC69jA4eUvGM+gkbyZjaW3MnoUB1ZxcCNTWhGgcT5
w/4DVcsXA5dsK7lxxxMxMtRMLnDTA9OTEaVJUwIDAQABAoIBACRilbhNVxZkaUVq
PAI13nkTsZDZGsZ3QcLseUlXmZdpUJ4arMxmkonBNMdT0yRmtfdYNp02GWDRg7MX
n/C4Ro42e18U6RknZAcK844R3SLRRlmoamivHbOwpV7MBtWaaePTUHPYi4nWx2jv
VqaSWgoxRPoYm0nmJ822rKJumxCpSi0rLNTInVhXxDxF6GLY4irQemStY0KbGFQ2
JSTeJVv4RzoVn2LI3qRa87JdJacAZuEoOpg0gK7zWhDhw6h8/10s5GI58bzaapyn
zWmnOf9vu7+pA7rBrO1ibQ87yw0UbWwOb0ZAzzUB6yuDD4iIYkmhb+8DXc0dk1Rn
FBf03vkCgYEA8cPaUF1Py2N/toCSGVGDAe7AhjFOIZU5Y+jhPIgm/k9W+z++1vgG
lXbe8pK0Lk52VPgxG/itVVKBWpjGRJs4t9CqbCgbadk4FjtIoHw/wSoscxhxn/05
jXZUirNf2x8aaCBzzkDHSIdd5LHJA6Oe+4B16Gxai5qtj4w+5FyIna8CgYEAxcX3
rlC8UW+hn7FANlczNarCzQFgCcP+p0DVvP92F0ysnTr2+fRnWoXFp+WMZuFnMuKS
16ClGJ0X5Ih28b6k7JSRDuXY3B7aNKN2edNn0BBskK5DTWGCxCQWws6V/NsewdY9
yxw6AktYmZPAbm9cec39KQEe6/q9nr4stFde+50CgYEAk/j7thRmsmXD1T/8K+Ln
/FbVH00uNP/QkIYI1bO/qgeFhWIOvCQyY2jOLEn+XhlH89m0tRoPfRlycrDvKS6Y
GGlu5aPmo3KAEZtXaGKj4uadLhTX9sRWZW73b606DjOLRhAW0TZ0wr+XiFIIZmHO
/MAzan5nLOsPL7z3AW5hb6ECgYAm9woFXgK8SLIfNFziV+vO9wXKPisdwW+6pBt4
URyDGqgnkiZ2uKBkRVbb7W3sFxyt+dXUheIBJ3I9pGVK27TCp8KsnLxNIgb7t/jv
p6ccZx/8oVjBNiT9X97cIreKSeGVbxBdpAIJ0a5zE5kmKOqfVOY73eypsY0KaY2F
OnGMQQKBgQCGTIfvxB6X+RakmD4CuhjW4c2VfpMkWxPmqOtaPdRykNivVvvKHgPW
Ak/MpZsgcm8r1D4LYWA8YYdrupLpYdU1cFoURCDSnnGNHyuGA2d/w92A/dhkALvm
LEXHqTW7d9pHCIMkfGqoaVAFs08b45Htd0umK6MQzefPiXU2gWQ1pw==
-----END RSA PRIVATE KEY-----"""


class TestClientAssertionConfig:
    """Tests for ClientAssertionConfig model."""

    def test_config_with_private_key(self):
        """Test configuration with private key bytes."""
        config = ClientAssertionConfig(
            kid="test-key-id",
            issuer="test-issuer",
            subject="test-subject",
            audience="https://auth.example.com/token",
            purpose_id="test-purpose",
            private_key=TEST_PRIVATE_KEY,
        )
        assert config.kid == "test-key-id"
        assert config.issuer == "test-issuer"
        assert config.subject == "test-subject"
        assert config.audience == "https://auth.example.com/token"
        assert config.purpose_id == "test-purpose"
        assert config.private_key == TEST_PRIVATE_KEY
        assert config.alg == "RS256"
        assert config.typ == "JWT"
        assert config.validity_minutes == 43200

    def test_config_with_key_path(self):
        """Test configuration with key file path."""
        with tempfile.NamedTemporaryFile(suffix=".pem", delete=False) as f:
            f.write(TEST_PRIVATE_KEY)
            key_path = Path(f.name)

        try:
            config = ClientAssertionConfig(
                kid="test-key-id",
                issuer="test-issuer",
                subject="test-subject",
                audience="https://auth.example.com/token",
                purpose_id="test-purpose",
                key_path=key_path,
            )
            assert config.key_path == key_path
            assert config.private_key is None
        finally:
            key_path.unlink()

    def test_config_requires_key_source(self):
        """Test that either private_key or key_path is required."""
        with pytest.raises(ValidationError) as exc_info:
            ClientAssertionConfig(
                kid="test-key-id",
                issuer="test-issuer",
                subject="test-subject",
                audience="https://auth.example.com/token",
                purpose_id="test-purpose",
            )
        assert "Either 'private_key' or 'key_path' must be provided" in str(
            exc_info.value
        )

    def test_config_validates_audience_https(self):
        """Test that audience must be HTTPS URL."""
        with pytest.raises(ValidationError) as exc_info:
            ClientAssertionConfig(
                kid="test-key-id",
                issuer="test-issuer",
                subject="test-subject",
                audience="http://auth.example.com/token",  # HTTP, not HTTPS
                purpose_id="test-purpose",
                private_key=TEST_PRIVATE_KEY,
            )
        # Pattern validation catches this before field_validator
        assert "audience" in str(exc_info.value)
        assert "https://" in str(exc_info.value) or "pattern" in str(exc_info.value)

    def test_config_validates_key_path_exists(self):
        """Test that key_path must exist."""
        with pytest.raises(ValidationError) as exc_info:
            ClientAssertionConfig(
                kid="test-key-id",
                issuer="test-issuer",
                subject="test-subject",
                audience="https://auth.example.com/token",
                purpose_id="test-purpose",
                key_path=Path("/nonexistent/path/key.pem"),
            )
        assert "Key file not found" in str(exc_info.value)

    def test_config_validates_key_path_is_file(self):
        """Test that key_path must be a file, not a directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            with pytest.raises(ValidationError) as exc_info:
                ClientAssertionConfig(
                    kid="test-key-id",
                    issuer="test-issuer",
                    subject="test-subject",
                    audience="https://auth.example.com/token",
                    purpose_id="test-purpose",
                    key_path=Path(tmpdir),
                )
            assert "Key path is not a file" in str(exc_info.value)

    def test_config_validates_kid_not_empty(self):
        """Test that kid cannot be empty."""
        with pytest.raises(ValidationError):
            ClientAssertionConfig(
                kid="",
                issuer="test-issuer",
                subject="test-subject",
                audience="https://auth.example.com/token",
                purpose_id="test-purpose",
                private_key=TEST_PRIVATE_KEY,
            )

    def test_config_validates_issuer_not_empty(self):
        """Test that issuer cannot be empty."""
        with pytest.raises(ValidationError):
            ClientAssertionConfig(
                kid="test-key-id",
                issuer="",
                subject="test-subject",
                audience="https://auth.example.com/token",
                purpose_id="test-purpose",
                private_key=TEST_PRIVATE_KEY,
            )

    def test_config_validates_subject_not_empty(self):
        """Test that subject cannot be empty."""
        with pytest.raises(ValidationError):
            ClientAssertionConfig(
                kid="test-key-id",
                issuer="test-issuer",
                subject="",
                audience="https://auth.example.com/token",
                purpose_id="test-purpose",
                private_key=TEST_PRIVATE_KEY,
            )

    def test_config_validates_purpose_id_not_empty(self):
        """Test that purpose_id cannot be empty."""
        with pytest.raises(ValidationError):
            ClientAssertionConfig(
                kid="test-key-id",
                issuer="test-issuer",
                subject="test-subject",
                audience="https://auth.example.com/token",
                purpose_id="",
                private_key=TEST_PRIVATE_KEY,
            )

    def test_config_validates_alg_rs256_only(self):
        """Test that alg must be RS256."""
        with pytest.raises(ValidationError):
            ClientAssertionConfig(
                kid="test-key-id",
                issuer="test-issuer",
                subject="test-subject",
                audience="https://auth.example.com/token",
                purpose_id="test-purpose",
                private_key=TEST_PRIVATE_KEY,
                alg="HS256",  # Not allowed
            )

    def test_config_validates_typ_jwt_only(self):
        """Test that typ must be JWT."""
        with pytest.raises(ValidationError):
            ClientAssertionConfig(
                kid="test-key-id",
                issuer="test-issuer",
                subject="test-subject",
                audience="https://auth.example.com/token",
                purpose_id="test-purpose",
                private_key=TEST_PRIVATE_KEY,
                typ="JWE",  # Not allowed
            )

    def test_config_validates_validity_minutes_positive(self):
        """Test that validity_minutes must be positive."""
        with pytest.raises(ValidationError):
            ClientAssertionConfig(
                kid="test-key-id",
                issuer="test-issuer",
                subject="test-subject",
                audience="https://auth.example.com/token",
                purpose_id="test-purpose",
                private_key=TEST_PRIVATE_KEY,
                validity_minutes=0,
            )

    def test_config_validates_validity_minutes_max(self):
        """Test that validity_minutes has a maximum of 43200 (30 days)."""
        with pytest.raises(ValidationError):
            ClientAssertionConfig(
                kid="test-key-id",
                issuer="test-issuer",
                subject="test-subject",
                audience="https://auth.example.com/token",
                purpose_id="test-purpose",
                private_key=TEST_PRIVATE_KEY,
                validity_minutes=43201,  # Exceeds 30 days
            )

    def test_config_custom_validity_minutes(self):
        """Test configuration with custom validity_minutes."""
        config = ClientAssertionConfig(
            kid="test-key-id",
            issuer="test-issuer",
            subject="test-subject",
            audience="https://auth.example.com/token",
            purpose_id="test-purpose",
            private_key=TEST_PRIVATE_KEY,
            validity_minutes=1440,  # 24 hours
        )
        assert config.validity_minutes == 1440


class TestClientAssertionConfigGetPrivateKey:
    """Tests for ClientAssertionConfig.get_private_key method."""

    def test_get_private_key_from_bytes(self):
        """Test getting private key from bytes."""
        config = ClientAssertionConfig(
            kid="test-key-id",
            issuer="test-issuer",
            subject="test-subject",
            audience="https://auth.example.com/token",
            purpose_id="test-purpose",
            private_key=TEST_PRIVATE_KEY,
        )
        assert config.get_private_key() == TEST_PRIVATE_KEY

    def test_get_private_key_from_file(self):
        """Test getting private key from file."""
        with tempfile.NamedTemporaryFile(suffix=".pem", delete=False) as f:
            f.write(TEST_PRIVATE_KEY)
            key_path = Path(f.name)

        try:
            config = ClientAssertionConfig(
                kid="test-key-id",
                issuer="test-issuer",
                subject="test-subject",
                audience="https://auth.example.com/token",
                purpose_id="test-purpose",
                key_path=key_path,
            )
            assert config.get_private_key() == TEST_PRIVATE_KEY
        finally:
            key_path.unlink()

    def test_get_private_key_file_not_found(self):
        """Test KeyFileError when file is deleted after config creation."""
        with tempfile.NamedTemporaryFile(suffix=".pem", delete=False) as f:
            f.write(TEST_PRIVATE_KEY)
            key_path = Path(f.name)

        config = ClientAssertionConfig(
            kid="test-key-id",
            issuer="test-issuer",
            subject="test-subject",
            audience="https://auth.example.com/token",
            purpose_id="test-purpose",
            key_path=key_path,
        )

        # Delete the file after config creation
        key_path.unlink()

        with pytest.raises(KeyFileError) as exc_info:
            config.get_private_key()
        assert "Key file not found" in str(exc_info.value)

    def test_get_private_key_permission_denied(self):
        """Test KeyFileError when file is not readable."""
        with tempfile.NamedTemporaryFile(suffix=".pem", delete=False) as f:
            f.write(TEST_PRIVATE_KEY)
            key_path = Path(f.name)

        try:
            config = ClientAssertionConfig(
                kid="test-key-id",
                issuer="test-issuer",
                subject="test-subject",
                audience="https://auth.example.com/token",
                purpose_id="test-purpose",
                key_path=key_path,
            )

            # Mock the read_bytes to raise PermissionError
            with patch.object(Path, "read_bytes", side_effect=PermissionError()):
                with pytest.raises(KeyFileError) as exc_info:
                    config.get_private_key()
                assert "Permission denied" in str(exc_info.value)
        finally:
            key_path.unlink()


class TestCreateClientAssertion:
    """Tests for create_client_assertion function."""

    def test_create_assertion_basic(self):
        """Test basic client assertion generation."""
        config = ClientAssertionConfig(
            kid="test-key-id",
            issuer="test-issuer",
            subject="test-subject",
            audience="https://auth.example.com/token",
            purpose_id="test-purpose",
            private_key=TEST_PRIVATE_KEY,
        )
        token = create_client_assertion(config)

        # Token should be a string with 3 parts (header.payload.signature)
        assert isinstance(token, str)
        parts = token.split(".")
        assert len(parts) == 3

    def test_create_assertion_with_custom_issued_at(self):
        """Test client assertion with custom issued_at."""
        config = ClientAssertionConfig(
            kid="test-key-id",
            issuer="test-issuer",
            subject="test-subject",
            audience="https://auth.example.com/token",
            purpose_id="test-purpose",
            private_key=TEST_PRIVATE_KEY,
            validity_minutes=60,
        )
        issued_at = datetime.datetime(2024, 1, 1, 12, 0, 0, tzinfo=datetime.UTC)
        token = create_client_assertion(config, issued_at=issued_at)

        # Decode and verify the token
        import base64
        import json

        payload_b64 = token.split(".")[1]
        # Add padding if needed
        padding = 4 - len(payload_b64) % 4
        if padding != 4:
            payload_b64 += "=" * padding
        payload = json.loads(base64.urlsafe_b64decode(payload_b64))

        assert payload["iat"] == int(issued_at.timestamp())
        expected_exp = issued_at + datetime.timedelta(minutes=60)
        assert payload["exp"] == int(expected_exp.timestamp())

    def test_create_assertion_with_custom_jti(self):
        """Test client assertion with custom jti."""
        config = ClientAssertionConfig(
            kid="test-key-id",
            issuer="test-issuer",
            subject="test-subject",
            audience="https://auth.example.com/token",
            purpose_id="test-purpose",
            private_key=TEST_PRIVATE_KEY,
        )
        custom_jti = "custom-jti-12345"
        token = create_client_assertion(config, jti=custom_jti)

        # Decode and verify the token
        import base64
        import json

        payload_b64 = token.split(".")[1]
        padding = 4 - len(payload_b64) % 4
        if padding != 4:
            payload_b64 += "=" * padding
        payload = json.loads(base64.urlsafe_b64decode(payload_b64))

        assert payload["jti"] == custom_jti

    def test_create_assertion_header_claims(self):
        """Test that header contains correct claims."""
        config = ClientAssertionConfig(
            kid="my-key-id-123",
            issuer="test-issuer",
            subject="test-subject",
            audience="https://auth.example.com/token",
            purpose_id="test-purpose",
            private_key=TEST_PRIVATE_KEY,
        )
        token = create_client_assertion(config)

        # Decode header
        import base64
        import json

        header_b64 = token.split(".")[0]
        padding = 4 - len(header_b64) % 4
        if padding != 4:
            header_b64 += "=" * padding
        header = json.loads(base64.urlsafe_b64decode(header_b64))

        assert header["kid"] == "my-key-id-123"
        assert header["alg"] == "RS256"
        assert header["typ"] == "JWT"

    def test_create_assertion_payload_claims(self):
        """Test that payload contains correct claims."""
        config = ClientAssertionConfig(
            kid="test-key-id",
            issuer="my-issuer",
            subject="my-subject",
            audience="https://auth.example.com/token",
            purpose_id="my-purpose-id",
            private_key=TEST_PRIVATE_KEY,
        )
        token = create_client_assertion(config)

        # Decode payload
        import base64
        import json

        payload_b64 = token.split(".")[1]
        padding = 4 - len(payload_b64) % 4
        if padding != 4:
            payload_b64 += "=" * padding
        payload = json.loads(base64.urlsafe_b64decode(payload_b64))

        assert payload["iss"] == "my-issuer"
        assert payload["sub"] == "my-subject"
        assert payload["aud"] == "https://auth.example.com/token"
        assert payload["purposeId"] == "my-purpose-id"
        assert "jti" in payload
        assert "iat" in payload
        assert "exp" in payload

    def test_create_assertion_from_key_file(self):
        """Test client assertion generation from key file."""
        with tempfile.NamedTemporaryFile(suffix=".pem", delete=False) as f:
            f.write(TEST_PRIVATE_KEY)
            key_path = Path(f.name)

        try:
            config = ClientAssertionConfig(
                kid="test-key-id",
                issuer="test-issuer",
                subject="test-subject",
                audience="https://auth.example.com/token",
                purpose_id="test-purpose",
                key_path=key_path,
            )
            token = create_client_assertion(config)
            assert isinstance(token, str)
            assert len(token.split(".")) == 3
        finally:
            key_path.unlink()

    def test_create_assertion_jwt_generation_error(self):
        """Test JWTGenerationError on invalid key."""
        config = ClientAssertionConfig(
            kid="test-key-id",
            issuer="test-issuer",
            subject="test-subject",
            audience="https://auth.example.com/token",
            purpose_id="test-purpose",
            private_key=b"invalid-key-content",
        )
        with pytest.raises(JWTGenerationError) as exc_info:
            create_client_assertion(config)
        assert "Failed to generate JWT" in str(exc_info.value)

    def test_create_assertion_unique_jti(self):
        """Test that each assertion has a unique jti by default."""
        config = ClientAssertionConfig(
            kid="test-key-id",
            issuer="test-issuer",
            subject="test-subject",
            audience="https://auth.example.com/token",
            purpose_id="test-purpose",
            private_key=TEST_PRIVATE_KEY,
        )

        import base64
        import json

        jtis = set()
        for _ in range(10):
            token = create_client_assertion(config)
            payload_b64 = token.split(".")[1]
            padding = 4 - len(payload_b64) % 4
            if padding != 4:
                payload_b64 += "=" * padding
            payload = json.loads(base64.urlsafe_b64decode(payload_b64))
            jtis.add(payload["jti"])

        # All JTIs should be unique
        assert len(jtis) == 10


class TestExceptionHierarchy:
    """Tests for exception class hierarchy."""

    def test_key_file_error_is_client_assertion_error(self):
        """Test that KeyFileError inherits from ClientAssertionError."""
        assert issubclass(KeyFileError, ClientAssertionError)
        error = KeyFileError("test error")
        assert isinstance(error, ClientAssertionError)

    def test_jwt_generation_error_is_client_assertion_error(self):
        """Test that JWTGenerationError inherits from ClientAssertionError."""
        assert issubclass(JWTGenerationError, ClientAssertionError)
        error = JWTGenerationError("test error")
        assert isinstance(error, ClientAssertionError)

    def test_client_assertion_error_is_exception(self):
        """Test that ClientAssertionError inherits from Exception."""
        assert issubclass(ClientAssertionError, Exception)
        error = ClientAssertionError("test error")
        assert isinstance(error, Exception)


class TestPackageExports:
    """Tests for package-level exports."""

    def test_imports_from_pdnd_assertion(self):
        """Test that all exports are importable from pdnd_assertion module."""
        from anncsu.common.pdnd_assertion import (
            ClientAssertionConfig,
            ClientAssertionError,
            JWTGenerationError,
            KeyFileError,
            create_client_assertion,
        )

        assert ClientAssertionConfig is not None
        assert ClientAssertionError is not None
        assert KeyFileError is not None
        assert JWTGenerationError is not None
        assert create_client_assertion is not None

    def test_imports_from_common_package(self):
        """Test that all exports are importable from common package."""
        from anncsu.common import (
            ClientAssertionConfig,
            ClientAssertionError,
            JWTGenerationError,
            KeyFileError,
            create_client_assertion,
        )

        assert ClientAssertionConfig is not None
        assert ClientAssertionError is not None
        assert KeyFileError is not None
        assert JWTGenerationError is not None
        assert create_client_assertion is not None
