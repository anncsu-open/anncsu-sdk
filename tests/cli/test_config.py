# SPDX-FileCopyrightText: 2025-present Geobeyond <info@geobeyond.it>
# SPDX-License-Identifier: MIT
"""Tests for config CLI commands."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING
from unittest.mock import MagicMock, patch

if TYPE_CHECKING:
    from typer.testing import CliRunner


class TestConfigInit:
    """Tests for config init command."""

    def test_init_creates_anncsu_directory(
        self, cli_runner: CliRunner, tmp_path: Path
    ) -> None:
        """Test that config init creates ~/.anncsu/ directory."""
        from anncsu.cli import app

        with patch("anncsu.cli.commands.config.get_config_dir") as mock_config_dir:
            config_dir = tmp_path / ".anncsu"
            mock_config_dir.return_value = config_dir

            result = cli_runner.invoke(app, ["config", "init"])

            assert result.exit_code == 0
            assert config_dir.exists()
            assert config_dir.is_dir()

    def test_init_creates_env_in_anncsu_directory(
        self, cli_runner: CliRunner, tmp_path: Path
    ) -> None:
        """Test that config init creates .env in ~/.anncsu/ by default."""
        from anncsu.cli import app

        with patch("anncsu.cli.commands.config.get_config_dir") as mock_config_dir:
            config_dir = tmp_path / ".anncsu"
            mock_config_dir.return_value = config_dir

            result = cli_runner.invoke(app, ["config", "init"])

            assert result.exit_code == 0
            env_file = config_dir / ".env"
            assert env_file.exists()

    def test_init_creates_env_file(self, cli_runner: CliRunner, tmp_path: Path) -> None:
        """Test that config init creates a .env template file."""
        from anncsu.cli import app

        with patch("anncsu.cli.commands.config.get_config_dir") as mock_config_dir:
            config_dir = tmp_path / ".anncsu"
            mock_config_dir.return_value = config_dir

            result = cli_runner.invoke(app, ["config", "init"])

            assert result.exit_code == 0
            env_file = config_dir / ".env"
            assert env_file.exists()

    def test_init_env_contains_required_vars(
        self, cli_runner: CliRunner, tmp_path: Path
    ) -> None:
        """Test that generated .env contains all required variables."""
        from anncsu.cli import app

        with patch("anncsu.cli.commands.config.get_config_dir") as mock_config_dir:
            config_dir = tmp_path / ".anncsu"
            mock_config_dir.return_value = config_dir

            result = cli_runner.invoke(app, ["config", "init"])

            assert result.exit_code == 0
            env_content = (config_dir / ".env").read_text()

            # Check all required PDND variables are present
            assert "PDND_KID" in env_content
            assert "PDND_ISSUER" in env_content
            assert "PDND_SUBJECT" in env_content
            assert "PDND_AUDIENCE" in env_content
            assert "PDND_PURPOSE_ID" in env_content
            assert "PDND_KEY_PATH" in env_content or "PDND_PRIVATE_KEY" in env_content

    def test_init_does_not_overwrite_existing(
        self, cli_runner: CliRunner, tmp_path: Path
    ) -> None:
        """Test that config init does not overwrite existing .env."""
        from anncsu.cli import app

        with patch("anncsu.cli.commands.config.get_config_dir") as mock_config_dir:
            config_dir = tmp_path / ".anncsu"
            config_dir.mkdir(parents=True)
            mock_config_dir.return_value = config_dir

            # Create existing .env
            existing_content = "EXISTING_VAR=value"
            (config_dir / ".env").write_text(existing_content)

            result = cli_runner.invoke(app, ["config", "init"])

            # Should warn or error, not overwrite
            assert (config_dir / ".env").read_text() == existing_content
            # Exit code 1 means it refused to overwrite
            assert result.exit_code == 1 or "exists" in result.output.lower()

    def test_init_force_overwrites_existing(
        self, cli_runner: CliRunner, tmp_path: Path
    ) -> None:
        """Test that config init --force overwrites existing .env."""
        from anncsu.cli import app

        with patch("anncsu.cli.commands.config.get_config_dir") as mock_config_dir:
            config_dir = tmp_path / ".anncsu"
            config_dir.mkdir(parents=True)
            mock_config_dir.return_value = config_dir

            # Create existing .env
            (config_dir / ".env").write_text("EXISTING_VAR=value")

            result = cli_runner.invoke(app, ["config", "init", "--force"])

            assert result.exit_code == 0
            env_content = (config_dir / ".env").read_text()
            assert "PDND_KID" in env_content
            assert "EXISTING_VAR" not in env_content

    def test_init_custom_path(self, cli_runner: CliRunner, tmp_path: Path) -> None:
        """Test that config init can write to custom path (overrides default)."""
        from anncsu.cli import app

        with cli_runner.isolated_filesystem(temp_dir=tmp_path):
            result = cli_runner.invoke(
                app, ["config", "init", "--output", "custom.env"]
            )

            assert result.exit_code == 0
            assert Path("custom.env").exists()

    def test_init_shows_config_directory_path(
        self, cli_runner: CliRunner, tmp_path: Path
    ) -> None:
        """Test that config init shows the path where config was created."""
        from anncsu.cli import app

        with patch("anncsu.cli.commands.config.get_config_dir") as mock_config_dir:
            config_dir = tmp_path / ".anncsu"
            mock_config_dir.return_value = config_dir

            result = cli_runner.invoke(app, ["config", "init"])

            assert result.exit_code == 0
            # Should show the path in output
            assert ".anncsu" in result.output or str(config_dir) in result.output


class TestConfigImport:
    """Tests for config import command."""

    def test_import_copies_env_file(
        self, cli_runner: CliRunner, tmp_path: Path
    ) -> None:
        """Test that config import copies an existing .env file."""
        from anncsu.cli import app

        with patch("anncsu.cli.commands.config.get_config_dir") as mock_config_dir:
            config_dir = tmp_path / ".anncsu"
            mock_config_dir.return_value = config_dir

            # Create source .env file
            source_env = tmp_path / "source.env"
            source_env.write_text(
                "PDND_KID=imported-key-id\nPDND_ISSUER=imported-issuer\n"
            )

            result = cli_runner.invoke(app, ["config", "import", str(source_env)])

            assert result.exit_code == 0
            # Should have copied to ~/.anncsu/.env
            assert (config_dir / ".env").exists()
            content = (config_dir / ".env").read_text()
            assert "imported-key-id" in content
            assert "imported-issuer" in content

    def test_import_from_current_directory(
        self, cli_runner: CliRunner, tmp_path: Path
    ) -> None:
        """Test that config import defaults to .env in current directory."""
        from anncsu.cli import app

        with cli_runner.isolated_filesystem(temp_dir=tmp_path):
            # Create .env in current directory
            Path(".env").write_text("PDND_KID=local-key-id\n")

            with patch("anncsu.cli.commands.config.get_config_dir") as mock_config_dir:
                config_dir = tmp_path / ".anncsu"
                mock_config_dir.return_value = config_dir

                result = cli_runner.invoke(app, ["config", "import"])

                assert result.exit_code == 0
                content = (config_dir / ".env").read_text()
                assert "local-key-id" in content

    def test_import_does_not_overwrite_existing(
        self, cli_runner: CliRunner, tmp_path: Path
    ) -> None:
        """Test that config import does not overwrite existing config."""
        from anncsu.cli import app

        with patch("anncsu.cli.commands.config.get_config_dir") as mock_config_dir:
            config_dir = tmp_path / ".anncsu"
            config_dir.mkdir(parents=True)
            mock_config_dir.return_value = config_dir

            # Create existing config
            (config_dir / ".env").write_text("PDND_KID=existing-key\n")

            # Create source file
            source_env = tmp_path / "source.env"
            source_env.write_text("PDND_KID=new-key\n")

            result = cli_runner.invoke(app, ["config", "import", str(source_env)])

            # Should fail without --force
            assert result.exit_code == 1
            assert "exists" in result.output.lower()
            # Original should be preserved
            assert "existing-key" in (config_dir / ".env").read_text()

    def test_import_force_overwrites(
        self, cli_runner: CliRunner, tmp_path: Path
    ) -> None:
        """Test that config import --force overwrites existing config."""
        from anncsu.cli import app

        with patch("anncsu.cli.commands.config.get_config_dir") as mock_config_dir:
            config_dir = tmp_path / ".anncsu"
            config_dir.mkdir(parents=True)
            mock_config_dir.return_value = config_dir

            # Create existing config
            (config_dir / ".env").write_text("PDND_KID=existing-key\n")

            # Create source file
            source_env = tmp_path / "source.env"
            source_env.write_text("PDND_KID=new-key\n")

            result = cli_runner.invoke(
                app, ["config", "import", str(source_env), "--force"]
            )

            assert result.exit_code == 0
            assert "new-key" in (config_dir / ".env").read_text()

    def test_import_file_not_found(self, cli_runner: CliRunner, tmp_path: Path) -> None:
        """Test that config import fails if source file doesn't exist."""
        from anncsu.cli import app

        with patch("anncsu.cli.commands.config.get_config_dir") as mock_config_dir:
            config_dir = tmp_path / ".anncsu"
            mock_config_dir.return_value = config_dir

            result = cli_runner.invoke(
                app, ["config", "import", "/nonexistent/path/.env"]
            )

            assert result.exit_code == 1
            assert (
                "not found" in result.output.lower() or "error" in result.output.lower()
            )

    def test_import_shows_success_message(
        self, cli_runner: CliRunner, tmp_path: Path
    ) -> None:
        """Test that config import shows success message with paths."""
        from anncsu.cli import app

        with patch("anncsu.cli.commands.config.get_config_dir") as mock_config_dir:
            config_dir = tmp_path / ".anncsu"
            mock_config_dir.return_value = config_dir

            source_env = tmp_path / "source.env"
            source_env.write_text("PDND_KID=test\n")

            result = cli_runner.invoke(app, ["config", "import", str(source_env)])

            assert result.exit_code == 0
            assert "import" in result.output.lower() or ".anncsu" in result.output


class TestConfigShow:
    """Tests for config show command."""

    def test_show_displays_config(
        self, cli_runner: CliRunner, mock_env_file: Path, tmp_path: Path
    ) -> None:
        """Test that config show displays current configuration."""
        from anncsu.cli import app

        with cli_runner.isolated_filesystem(temp_dir=tmp_path):
            # Copy mock env file to current directory
            Path(".env").write_text(mock_env_file.read_text())

            with patch("anncsu.cli.commands.config.ClientAssertionSettings") as mock:
                settings = MagicMock()
                settings.kid = "test-key-id"
                settings.issuer = "test-client-id"
                settings.subject = "test-client-id"
                settings.audience = "auth.uat.interop.pagopa.it/client-assertion"
                settings.purpose_id = "test-purpose-id"
                settings.key_path = Path("./test_private_key.pem")
                settings.validity_minutes = 43200
                mock.return_value = settings

                result = cli_runner.invoke(app, ["config", "show"])

            assert result.exit_code == 0
            # Should show configuration values (possibly masked)
            assert "kid" in result.output.lower() or "key" in result.output.lower()

    def test_show_masks_sensitive_values(
        self, cli_runner: CliRunner, tmp_path: Path
    ) -> None:
        """Test that config show masks sensitive values."""
        from anncsu.cli import app

        with cli_runner.isolated_filesystem(temp_dir=tmp_path):
            with patch("anncsu.cli.commands.config.ClientAssertionSettings") as mock:
                settings = MagicMock()
                settings.kid = "secret-key-id-12345"
                settings.issuer = "client-uuid-12345"
                settings.subject = "client-uuid-12345"
                settings.audience = "auth.uat.interop.pagopa.it/client-assertion"
                settings.purpose_id = "purpose-uuid-12345"
                settings.key_path = Path("./private_key.pem")
                settings.validity_minutes = 43200
                mock.return_value = settings

                result = cli_runner.invoke(app, ["config", "show"])

            assert result.exit_code == 0
            # Full secrets should not be visible
            assert "secret-key-id-12345" not in result.output
            # Should show partial/masked version
            assert "***" in result.output or "..." in result.output

    def test_show_no_config_error(self, cli_runner: CliRunner, tmp_path: Path) -> None:
        """Test that config show errors when no config exists."""
        from anncsu.cli import app

        with cli_runner.isolated_filesystem(temp_dir=tmp_path):
            with patch(
                "anncsu.cli.commands.config.ClientAssertionSettings",
                side_effect=Exception("No configuration found"),
            ):
                result = cli_runner.invoke(app, ["config", "show"])

            assert result.exit_code == 1
            assert (
                "error" in result.output.lower() or "not found" in result.output.lower()
            )


class TestConfigValidate:
    """Tests for config validate command."""

    def test_validate_success(
        self, cli_runner: CliRunner, tmp_path: Path, mock_private_key: Path
    ) -> None:
        """Test that config validate succeeds with valid config."""
        from anncsu.cli import app

        with cli_runner.isolated_filesystem(temp_dir=tmp_path):
            # Copy private key to current dir
            Path("private_key.pem").write_text(mock_private_key.read_text())

            with patch("anncsu.cli.commands.config.ClientAssertionSettings") as mock:
                settings = MagicMock()
                settings.kid = "test-key-id"
                settings.issuer = "test-client-id"
                settings.subject = "test-client-id"
                settings.audience = "auth.uat.interop.pagopa.it/client-assertion"
                settings.purpose_id = "test-purpose-id"
                settings.key_path = Path("./private_key.pem")
                settings.validity_minutes = 43200
                mock.return_value = settings

                result = cli_runner.invoke(app, ["config", "validate"])

            assert result.exit_code == 0
            assert (
                "valid" in result.output.lower()
                or "ok" in result.output.lower()
                or "success" in result.output.lower()
            )

    def test_validate_missing_key_file(
        self, cli_runner: CliRunner, tmp_path: Path
    ) -> None:
        """Test that config validate fails when key file is missing."""
        from anncsu.cli import app

        with cli_runner.isolated_filesystem(temp_dir=tmp_path):
            with patch("anncsu.cli.commands.config.ClientAssertionSettings") as mock:
                settings = MagicMock()
                settings.key_path = Path("./nonexistent_key.pem")
                mock.return_value = settings

                result = cli_runner.invoke(app, ["config", "validate"])

            assert result.exit_code == 1
            assert (
                "not found" in result.output.lower()
                or "error" in result.output.lower()
                or "missing" in result.output.lower()
            )

    def test_validate_invalid_audience(
        self, cli_runner: CliRunner, tmp_path: Path, mock_private_key: Path
    ) -> None:
        """Test that config validate warns on invalid audience format."""
        from anncsu.cli import app

        with cli_runner.isolated_filesystem(temp_dir=tmp_path):
            Path("private_key.pem").write_text(mock_private_key.read_text())

            with patch("anncsu.cli.commands.config.ClientAssertionSettings") as mock:
                settings = MagicMock()
                settings.kid = "test-key-id"
                settings.issuer = "test-client-id"
                settings.subject = "test-client-id"
                settings.audience = "invalid-audience"  # Missing /client-assertion
                settings.purpose_id = "test-purpose-id"
                settings.key_path = Path("./private_key.pem")
                settings.validity_minutes = 43200
                mock.return_value = settings

                result = cli_runner.invoke(app, ["config", "validate"])

            # Should warn about audience format
            assert (
                "warning" in result.output.lower()
                or "audience" in result.output.lower()
            )


class TestConfigSet:
    """Tests for config set command."""

    def test_set_single_value(self, cli_runner: CliRunner, tmp_path: Path) -> None:
        """Test that config set can update a single value."""
        from anncsu.cli import app

        with patch("anncsu.cli.commands.config.get_config_dir") as mock_config_dir:
            config_dir = tmp_path / ".anncsu"
            config_dir.mkdir(parents=True)
            mock_config_dir.return_value = config_dir

            # Create initial .env
            (config_dir / ".env").write_text("PDND_KID=old-value\n")

            result = cli_runner.invoke(app, ["config", "set", "--kid", "new-key-id"])

            assert result.exit_code == 0
            env_content = (config_dir / ".env").read_text()
            assert "new-key-id" in env_content

    def test_set_multiple_values(self, cli_runner: CliRunner, tmp_path: Path) -> None:
        """Test that config set can update multiple values."""
        from anncsu.cli import app

        with patch("anncsu.cli.commands.config.get_config_dir") as mock_config_dir:
            config_dir = tmp_path / ".anncsu"
            config_dir.mkdir(parents=True)
            mock_config_dir.return_value = config_dir

            # Create initial .env
            (config_dir / ".env").write_text(
                "PDND_KID=old-kid\nPDND_ISSUER=old-issuer\n"
            )

            result = cli_runner.invoke(
                app,
                ["config", "set", "--kid", "new-kid", "--issuer", "new-issuer"],
            )

            assert result.exit_code == 0
            env_content = (config_dir / ".env").read_text()
            assert "new-kid" in env_content
            assert "new-issuer" in env_content

    def test_set_creates_env_if_missing(
        self, cli_runner: CliRunner, tmp_path: Path
    ) -> None:
        """Test that config set creates .env in ~/.anncsu/ if it doesn't exist."""
        from anncsu.cli import app

        with patch("anncsu.cli.commands.config.get_config_dir") as mock_config_dir:
            config_dir = tmp_path / ".anncsu"
            mock_config_dir.return_value = config_dir

            result = cli_runner.invoke(app, ["config", "set", "--kid", "my-key-id"])

            assert result.exit_code == 0
            assert (config_dir / ".env").exists()
            assert "my-key-id" in (config_dir / ".env").read_text()

    def test_set_preserves_other_values(
        self, cli_runner: CliRunner, tmp_path: Path
    ) -> None:
        """Test that config set preserves values not being updated."""
        from anncsu.cli import app

        with patch("anncsu.cli.commands.config.get_config_dir") as mock_config_dir:
            config_dir = tmp_path / ".anncsu"
            config_dir.mkdir(parents=True)
            mock_config_dir.return_value = config_dir

            (config_dir / ".env").write_text(
                "PDND_KID=old-kid\nPDND_ISSUER=keep-this\nOTHER_VAR=also-keep\n"
            )

            result = cli_runner.invoke(app, ["config", "set", "--kid", "new-kid"])

            assert result.exit_code == 0
            env_content = (config_dir / ".env").read_text()
            assert "new-kid" in env_content
            assert "keep-this" in env_content
            assert "also-keep" in env_content

    def test_set_with_custom_env_file(
        self, cli_runner: CliRunner, tmp_path: Path
    ) -> None:
        """Test that config set can use a custom env file path."""
        from anncsu.cli import app

        with cli_runner.isolated_filesystem(temp_dir=tmp_path):
            # Create custom .env file
            Path("custom.env").write_text("PDND_KID=old-value\n")

            result = cli_runner.invoke(
                app,
                [
                    "config",
                    "set",
                    "--kid",
                    "new-key-id",
                    "--env-file",
                    "custom.env",
                ],
            )

            assert result.exit_code == 0
            env_content = Path("custom.env").read_text()
            assert "new-key-id" in env_content
