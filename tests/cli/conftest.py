# SPDX-FileCopyrightText: 2025-present Geobeyond <info@geobeyond.it>
# SPDX-License-Identifier: MIT
"""Shared fixtures for CLI tests."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING
from unittest.mock import MagicMock, patch

import pytest
from typer.testing import CliRunner

if TYPE_CHECKING:
    from collections.abc import Generator


@pytest.fixture
def cli_runner() -> CliRunner:
    """Create a Typer CLI test runner."""
    return CliRunner()


@pytest.fixture
def isolated_runner(cli_runner: CliRunner, tmp_path: Path) -> CliRunner:
    """Create a CLI runner with isolated filesystem."""
    return CliRunner(mix_stderr=False, env={"HOME": str(tmp_path)})


@pytest.fixture
def mock_env_file(tmp_path: Path) -> Path:
    """Create a mock .env file with test credentials."""
    env_content = """
PDND_KID=test-key-id
PDND_ISSUER=test-client-id
PDND_SUBJECT=test-client-id
PDND_AUDIENCE=auth.uat.interop.pagopa.it/client-assertion
PDND_PURPOSE_ID_PA=test-purpose-id-pa
PDND_PURPOSE_ID_COORDINATE=test-purpose-id-coordinate
PDND_PURPOSE_ID_ACCESSI=
PDND_PURPOSE_ID_INTERNI=
PDND_PURPOSE_ID_ODONIMI=
PDND_KEY_PATH=./test_private_key.pem
"""
    env_file = tmp_path / ".env"
    env_file.write_text(env_content.strip())
    return env_file


@pytest.fixture
def mock_private_key(tmp_path: Path) -> Path:
    """Create a mock private key file."""
    # This is a test-only RSA key, not used in production
    key_content = """-----BEGIN RSA PRIVATE KEY-----
MIIEowIBAAKCAQEA0Z3VS5JJcds3xfn/ygWyF8PbnGy0AHB7MlUj5LqeKj3WAMTP
xMHECP4xmGdn7YHEHxAPPrHrBQiIQ5axdmfYAIVCD+FuSjGOv8CD7EYEz3h/5SMx
N8ek5YDfKP8kMXmhu/kDjE5rmZDL2K8hYWKx8D+OlXVxF5nXQBgFOJnHMAqhwuWT
PjsHaGQ4JlJblNq7JHQK8MLNHZ6MMB5/UYPHtgP+U5Z5Z1YKPcUIBe3NBvlM1Wao
pMWPrNMJCPr+PLWN6vUGXZN+faCD/B9TLr3N8T0ZT5c8FVWb1Q5ue3+hZ/ghaBzn
CstVCERSTnN7kAPP6pgkQwuMy4MGJzjn2hRtCwIDAQABAoIBADcBPfHl8MzVihzf
p5+SSHQA9V0dL7vQ5Khh4SYnklkRhSIHBxEOaxLvFrE8TYcJzTkD3wYl3zNPfGRM
p5+PxtHxOmEHx2TN4bQgGl/GfQKzpkBerQLAO+uthJb7P4yF8+PU8WNgvTzqklsz
dB3P/Hwbm7zQu3lG3z3XCmP/cBk/xyf4McXZzjH4qkqBDRqMjp0SBqdpHvIBdwHq
LzVJwJh1oc8FzrBL7hTQ4OaApJbR8DXx3FZvbqfmXUvJQZPNDEX4jPXjdS3PnB9z
N0+Tj2RQYAJgDUC4ssoOS7lYcRbUjKY7hPP8WM0mMTKKWGnHHvnNbRhYVSmIAi7A
bJ8uZOECgYEA7fj7LXRN4j/VVPLi8a3VvzLDcBVl0mwZGT7JfGmKvYn4VPOzNYQs
jKzg2XthM8PCQZ6pWphGxPC+Xk1N7b/Nsf8s5n/HgHPNThG5FWtsDFXJJXbHNzXX
DKbVTVSHPBjSF1ZaxHDB1qGzjd3xLvqFWN3dJf8M4J2C1qRMj0CRQCsCgYEA4bkH
aHBiSuTXcMYPzMJcjG3+K/0sJkSQd2VXmLJMN0dMnk8TqhzsDLhH7yXmIRrXJhxv
Q8QsWHTDkCqvT5jVQDaLxcuN4qAdnK9rpWg5aN/1PBTCqsEnL6c0cPmU4RFnS6SR
AuPTXDRqhKF/mxWFzqB7uS3q0p8K3qmS0JlWN8ECgYAaJ3GPF2pPGaB4/rPn/Eph
TdYaH9Q8i8KOu2y3FrFXD1WcM/M8DXhZ8e5mN/YCDwqKQboaPkZvPUWm8kB4Q2sN
cG0ShHPMfPMX8K5/iXcNxH1T9WR3R2dNXcqMW4shBfpPPqKqZJKjfnxO8fIGpnhn
Jz5RCgU3kXh2pPMdy+XHSwKBgGKjLhJ7vi6BTLXEPM5gLkFQal0lVneJzPbXsdCV
vpjnU4v3N/OBB6ZhMqvGQdUVxVqnJPYWz8ggUJJhPPX8dMyVXblRa3RSaC8QYqBk
r7X2FDHq9dHjkI3SFuN9e3r3ql8dNzCWfhDXedmZlBQ8MhPL/dRQbPDlQy4MJhUF
9S6BAoGBAM/8u3pPJh7NMgj1ELlWrTJvaNqsFoqMDE3XOp0XZHi8LLWu1zyLBhBh
KAZJQZ3mHwFDhPzVNkw8l7MhLCq5MPi1vXVQ8TBQJW3v6gPnq+5rJlVp3T3VAvB9
C7SLZL2GdCrp2bHvZJQp/V+f3N+tqD/YC1ymPkTLvY0rMVqvZxzy
-----END RSA PRIVATE KEY-----"""
    key_file = tmp_path / "test_private_key.pem"
    key_file.write_text(key_content)
    return key_file


@pytest.fixture
def mock_settings() -> Generator[MagicMock, None, None]:
    """Mock ClientAssertionSettings for testing."""
    with patch("anncsu.cli.commands.auth.ClientAssertionSettings") as mock:
        settings = MagicMock()
        settings.kid = "test-key-id"
        settings.issuer = "test-client-id"
        settings.subject = "test-client-id"
        settings.audience = "auth.uat.interop.pagopa.it/client-assertion"
        settings.purpose_id = "test-purpose-id"
        settings.key_path = Path("./test_private_key.pem")
        settings.validity_minutes = 43200
        mock.return_value = settings
        yield mock


@pytest.fixture
def mock_auth_manager() -> Generator[MagicMock, None, None]:
    """Mock PDNDAuthManager for testing."""
    with patch("anncsu.cli.commands.auth.PDNDAuthManager") as mock:
        manager = MagicMock()
        manager.get_client_assertion.return_value = "mock-client-assertion-jwt"
        manager.get_access_token.return_value = "mock-access-token-jwt"
        manager.client_assertion_expires_at = None
        manager.access_token_expires_at = None
        mock.return_value = manager
        yield mock


@pytest.fixture
def mock_create_assertion() -> Generator[MagicMock, None, None]:
    """Mock create_client_assertion for testing."""
    with patch("anncsu.cli.commands.assertion.create_client_assertion") as mock:
        mock.return_value = "mock-client-assertion-jwt"
        yield mock
