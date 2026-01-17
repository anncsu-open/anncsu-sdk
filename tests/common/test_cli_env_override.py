"""Tests for CLI environment variable override behavior.

This module tests that CLI parameters properly override environment
variable settings loaded via ClientAssertionSettings.
"""

import importlib.util
import tempfile
from pathlib import Path

import pytest
from typer.testing import CliRunner

# Load the CLI module dynamically from scripts directory
SCRIPTS_DIR = Path(__file__).parent.parent.parent / "scripts"
CLI_MODULE_PATH = SCRIPTS_DIR / "create_client_assertion.py"


def _load_cli_app():
    """Load the CLI app from the scripts directory."""
    spec = importlib.util.spec_from_file_location(
        "create_client_assertion", CLI_MODULE_PATH
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.app


# Test RSA key for testing (same as in test_pdnd_assertion.py)
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


@pytest.fixture
def cli_runner():
    """Create a CLI runner for testing."""
    return CliRunner()


@pytest.fixture
def temp_key_file():
    """Create a temporary key file for testing."""
    with tempfile.NamedTemporaryFile(suffix=".pem", delete=False) as f:
        f.write(TEST_PRIVATE_KEY)
        key_path = Path(f.name)
    yield key_path
    key_path.unlink()


@pytest.fixture
def env_settings(monkeypatch, temp_key_file):
    """Set up environment variables for testing."""
    monkeypatch.setenv("PDND_KID", "env-key-id")
    monkeypatch.setenv("PDND_ISSUER", "env-issuer")
    monkeypatch.setenv("PDND_SUBJECT", "env-subject")
    monkeypatch.setenv("PDND_AUDIENCE", "env.example.com/client-assertion")
    monkeypatch.setenv("PDND_PURPOSE_ID", "env-purpose-id")
    monkeypatch.setenv("PDND_KEY_PATH", str(temp_key_file))
    monkeypatch.setenv("PDND_VALIDITY_MINUTES", "60")
    return temp_key_file


class TestCLIWithEnvVariables:
    """Tests for CLI with environment variable support."""

    def test_from_env_uses_environment_variables(self, cli_runner, env_settings):
        """Test that --from-env uses environment variables."""
        app = _load_cli_app()

        result = cli_runner.invoke(app, ["--from-env", "--no-clear"])

        assert result.exit_code == 0
        # Token should be generated (JWT format: header.payload.signature)
        token = result.stdout.strip()
        assert len(token.split(".")) == 3

    def test_cli_param_overrides_env_kid(self, cli_runner, env_settings):
        """Test that CLI --kid overrides PDND_KID environment variable."""
        import base64
        import json

        app = _load_cli_app()

        result = cli_runner.invoke(app, ["--kid", "cli-override-kid", "--no-clear"])

        assert result.exit_code == 0
        token = result.stdout.strip()
        # Decode header to verify kid was overridden
        header_b64 = token.split(".")[0]
        padding = 4 - len(header_b64) % 4
        if padding != 4:
            header_b64 += "=" * padding
        header = json.loads(base64.urlsafe_b64decode(header_b64))
        assert header["kid"] == "cli-override-kid"

    def test_cli_param_overrides_env_issuer(self, cli_runner, env_settings):
        """Test that CLI --issuer overrides PDND_ISSUER environment variable."""
        import base64
        import json

        app = _load_cli_app()

        result = cli_runner.invoke(
            app, ["--issuer", "cli-override-issuer", "--no-clear"]
        )

        assert result.exit_code == 0
        token = result.stdout.strip()
        # Decode payload to verify issuer was overridden
        payload_b64 = token.split(".")[1]
        padding = 4 - len(payload_b64) % 4
        if padding != 4:
            payload_b64 += "=" * padding
        payload = json.loads(base64.urlsafe_b64decode(payload_b64))
        assert payload["iss"] == "cli-override-issuer"

    def test_cli_param_overrides_env_subject(self, cli_runner, env_settings):
        """Test that CLI --subject overrides PDND_SUBJECT environment variable."""
        import base64
        import json

        app = _load_cli_app()

        result = cli_runner.invoke(
            app, ["--subject", "cli-override-subject", "--no-clear"]
        )

        assert result.exit_code == 0
        token = result.stdout.strip()
        payload_b64 = token.split(".")[1]
        padding = 4 - len(payload_b64) % 4
        if padding != 4:
            payload_b64 += "=" * padding
        payload = json.loads(base64.urlsafe_b64decode(payload_b64))
        assert payload["sub"] == "cli-override-subject"

    def test_cli_param_overrides_env_audience(self, cli_runner, env_settings):
        """Test that CLI --audience overrides PDND_AUDIENCE environment variable."""
        import base64
        import json

        app = _load_cli_app()

        result = cli_runner.invoke(
            app,
            ["--audience", "cli.override.com/client-assertion", "--no-clear"],
        )

        assert result.exit_code == 0
        token = result.stdout.strip()
        payload_b64 = token.split(".")[1]
        padding = 4 - len(payload_b64) % 4
        if padding != 4:
            payload_b64 += "=" * padding
        payload = json.loads(base64.urlsafe_b64decode(payload_b64))
        assert payload["aud"] == "cli.override.com/client-assertion"

    def test_cli_param_overrides_env_purpose_id(self, cli_runner, env_settings):
        """Test that CLI --purpose-id overrides PDND_PURPOSE_ID environment variable."""
        import base64
        import json

        app = _load_cli_app()

        result = cli_runner.invoke(
            app, ["--purpose-id", "cli-override-purpose", "--no-clear"]
        )

        assert result.exit_code == 0
        token = result.stdout.strip()
        payload_b64 = token.split(".")[1]
        padding = 4 - len(payload_b64) % 4
        if padding != 4:
            payload_b64 += "=" * padding
        payload = json.loads(base64.urlsafe_b64decode(payload_b64))
        assert payload["purposeId"] == "cli-override-purpose"

    def test_cli_param_overrides_env_validity_minutes(self, cli_runner, env_settings):
        """Test that CLI --validity-minutes overrides PDND_VALIDITY_MINUTES."""
        import base64
        import json

        app = _load_cli_app()

        result = cli_runner.invoke(app, ["--validity-minutes", "120", "--no-clear"])

        assert result.exit_code == 0
        token = result.stdout.strip()
        payload_b64 = token.split(".")[1]
        padding = 4 - len(payload_b64) % 4
        if padding != 4:
            payload_b64 += "=" * padding
        payload = json.loads(base64.urlsafe_b64decode(payload_b64))
        # Check that exp - iat = 120 minutes = 7200 seconds
        assert payload["exp"] - payload["iat"] == 7200

    def test_cli_param_overrides_env_key_path(self, cli_runner, env_settings):
        """Test that CLI --key-path overrides PDND_KEY_PATH environment variable."""
        app = _load_cli_app()

        # Create a second key file
        with tempfile.NamedTemporaryFile(suffix=".pem", delete=False) as f:
            f.write(TEST_PRIVATE_KEY)
            cli_key_path = Path(f.name)

        try:
            result = cli_runner.invoke(
                app, ["--key-path", str(cli_key_path), "--no-clear"]
            )
            assert result.exit_code == 0
            token = result.stdout.strip()
            assert len(token.split(".")) == 3
        finally:
            cli_key_path.unlink()

    def test_multiple_cli_overrides(self, cli_runner, env_settings):
        """Test that multiple CLI params override their respective env vars."""
        import base64
        import json

        app = _load_cli_app()

        result = cli_runner.invoke(
            app,
            [
                "--kid",
                "multi-cli-kid",
                "--issuer",
                "multi-cli-issuer",
                "--purpose-id",
                "multi-cli-purpose",
                "--no-clear",
            ],
        )

        assert result.exit_code == 0
        token = result.stdout.strip()

        # Verify header
        header_b64 = token.split(".")[0]
        padding = 4 - len(header_b64) % 4
        if padding != 4:
            header_b64 += "=" * padding
        header = json.loads(base64.urlsafe_b64decode(header_b64))
        assert header["kid"] == "multi-cli-kid"

        # Verify payload
        payload_b64 = token.split(".")[1]
        padding = 4 - len(payload_b64) % 4
        if padding != 4:
            payload_b64 += "=" * padding
        payload = json.loads(base64.urlsafe_b64decode(payload_b64))
        assert payload["iss"] == "multi-cli-issuer"
        assert payload["purposeId"] == "multi-cli-purpose"
        # These should still be from env
        assert payload["sub"] == "env-subject"
        assert payload["aud"] == "env.example.com/client-assertion"


class TestCLIWithoutEnvVariables:
    """Tests for CLI without environment variables set."""

    @pytest.fixture(autouse=True)
    def clear_env(self, monkeypatch, tmp_path):
        """Clear PDND env vars and change to temp dir to avoid .env file."""
        # Change to temp directory to avoid reading .env file from project root
        monkeypatch.chdir(tmp_path)

        # Clear all PDND env vars
        for key in [
            "PDND_KID",
            "PDND_ISSUER",
            "PDND_SUBJECT",
            "PDND_AUDIENCE",
            "PDND_PURPOSE_ID",
            "PDND_PRIVATE_KEY",
            "PDND_KEY_PATH",
            "PDND_ALG",
            "PDND_TYP",
            "PDND_VALIDITY_MINUTES",
        ]:
            monkeypatch.delenv(key, raising=False)

    def test_missing_required_params_shows_error(self, cli_runner, temp_key_file):
        """Test that missing required params shows error message."""
        app = _load_cli_app()

        result = cli_runner.invoke(app, ["--kid", "test-kid", "--no-clear"])

        assert result.exit_code == 1
        assert "Missing required parameters" in result.stdout

    def test_all_cli_params_without_env(self, cli_runner, temp_key_file):
        """Test that all CLI params work without env variables."""
        app = _load_cli_app()

        result = cli_runner.invoke(
            app,
            [
                "--kid",
                "cli-only-kid",
                "--issuer",
                "cli-only-issuer",
                "--subject",
                "cli-only-subject",
                "--audience",
                "cli.only.com/client-assertion",
                "--purpose-id",
                "cli-only-purpose",
                "--key-path",
                str(temp_key_file),
                "--no-clear",
            ],
        )

        assert result.exit_code == 0
        token = result.stdout.strip()
        assert len(token.split(".")) == 3

    def test_from_env_fails_without_env_vars(self, cli_runner):
        """Test that --from-env fails when env vars are not set."""
        app = _load_cli_app()

        result = cli_runner.invoke(app, ["--from-env", "--no-clear"])

        assert result.exit_code == 1
        assert "required environment variables are not set" in result.stdout


class TestCLIEnvPartialOverride:
    """Tests for partial environment variable settings with CLI overrides."""

    def test_partial_env_with_cli_completion(
        self, cli_runner, monkeypatch, temp_key_file
    ):
        """Test partial env vars completed by CLI params."""
        app = _load_cli_app()

        # Set only some env vars
        monkeypatch.setenv("PDND_KID", "partial-env-kid")
        monkeypatch.setenv("PDND_ISSUER", "partial-env-issuer")
        monkeypatch.setenv("PDND_KEY_PATH", str(temp_key_file))

        # Provide missing params via CLI
        result = cli_runner.invoke(
            app,
            [
                "--subject",
                "cli-subject",
                "--audience",
                "cli.audience.com/client-assertion",
                "--purpose-id",
                "cli-purpose",
                "--no-clear",
            ],
        )

        # Debug output
        print(f"Exit code: {result.exit_code}")
        print(f"Output: {result.output}")

        assert result.exit_code == 0
        token = result.stdout.strip()
        assert len(token.split(".")) == 3
