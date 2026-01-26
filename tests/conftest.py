"""Pytest configuration for ANNCSU SDK tests."""

import sys
from pathlib import Path

import pytest

# Add src directory to path so tests can import modules
src_path = Path(__file__).parent.parent / "src"
sys.path.insert(0, str(src_path))


@pytest.fixture
def mock_private_key(tmp_path: Path) -> Path:
    """Create a mock private key file for testing.

    This is a test-only RSA key, not used in production.
    Generated using cryptography library.
    """
    # Generate a valid RSA key at runtime for tests
    from cryptography.hazmat.primitives import serialization
    from cryptography.hazmat.primitives.asymmetric import rsa

    private_key = rsa.generate_private_key(
        public_exponent=65537,
        key_size=2048,
    )

    pem = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.TraditionalOpenSSL,
        encryption_algorithm=serialization.NoEncryption(),
    )

    key_path = tmp_path / "test_private_key.pem"
    key_path.write_bytes(pem)
    return key_path
