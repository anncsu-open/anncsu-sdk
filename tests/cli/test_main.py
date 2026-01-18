# SPDX-FileCopyrightText: 2025-present Geobeyond <info@geobeyond.it>
# SPDX-License-Identifier: MIT
"""Tests for main CLI application."""

from __future__ import annotations

import re
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from typer.testing import CliRunner


class TestMainApp:
    """Tests for main CLI app entry point."""

    def test_app_exists(self) -> None:
        """Test that the CLI app can be imported."""
        from anncsu.cli import app

        assert app is not None

    def test_app_help(self, cli_runner: CliRunner) -> None:
        """Test that --help shows usage information."""
        from anncsu.cli import app

        result = cli_runner.invoke(app, ["--help"])

        assert result.exit_code == 0
        assert "anncsu" in result.output.lower() or "usage" in result.output.lower()
        # Should show available command groups
        assert "auth" in result.output.lower()
        assert "config" in result.output.lower()
        assert "assertion" in result.output.lower()

    def test_app_version(self, cli_runner: CliRunner) -> None:
        """Test that --version shows version information."""
        from anncsu.cli import app

        result = cli_runner.invoke(app, ["--version"])

        assert result.exit_code == 0
        # Version should be a semver-like pattern
        assert re.search(r"\d+\.\d+\.\d+", result.output)

    def test_app_no_args_shows_help(self, cli_runner: CliRunner) -> None:
        """Test that running without arguments shows help."""
        from anncsu.cli import app

        result = cli_runner.invoke(app, [])

        # With no_args_is_help=True, Typer shows help and exits with code 0 or 2
        assert result.exit_code in (0, 2)
        assert "auth" in result.output.lower() or "usage" in result.output.lower()


class TestCommandGroups:
    """Tests for command group registration."""

    def test_auth_group_exists(self, cli_runner: CliRunner) -> None:
        """Test that auth command group is registered."""
        from anncsu.cli import app

        result = cli_runner.invoke(app, ["auth", "--help"])

        assert result.exit_code == 0
        assert "auth" in result.output.lower()

    def test_config_group_exists(self, cli_runner: CliRunner) -> None:
        """Test that config command group is registered."""
        from anncsu.cli import app

        result = cli_runner.invoke(app, ["config", "--help"])

        assert result.exit_code == 0
        assert "config" in result.output.lower()

    def test_assertion_group_exists(self, cli_runner: CliRunner) -> None:
        """Test that assertion command group is registered."""
        from anncsu.cli import app

        result = cli_runner.invoke(app, ["assertion", "--help"])

        assert result.exit_code == 0
        assert "assertion" in result.output.lower()


class TestAuthGroupHelp:
    """Tests for auth group help and commands listing."""

    def test_auth_help_shows_login(self, cli_runner: CliRunner) -> None:
        """Test that auth --help shows login command."""
        from anncsu.cli import app

        result = cli_runner.invoke(app, ["auth", "--help"])

        assert result.exit_code == 0
        assert "login" in result.output.lower()

    def test_auth_help_shows_status(self, cli_runner: CliRunner) -> None:
        """Test that auth --help shows status command."""
        from anncsu.cli import app

        result = cli_runner.invoke(app, ["auth", "--help"])

        assert result.exit_code == 0
        assert "status" in result.output.lower()

    def test_auth_help_shows_refresh(self, cli_runner: CliRunner) -> None:
        """Test that auth --help shows refresh command."""
        from anncsu.cli import app

        result = cli_runner.invoke(app, ["auth", "--help"])

        assert result.exit_code == 0
        assert "refresh" in result.output.lower()

    def test_auth_help_shows_token(self, cli_runner: CliRunner) -> None:
        """Test that auth --help shows token command."""
        from anncsu.cli import app

        result = cli_runner.invoke(app, ["auth", "--help"])

        assert result.exit_code == 0
        assert "token" in result.output.lower()


class TestConfigGroupHelp:
    """Tests for config group help and commands listing."""

    def test_config_help_shows_init(self, cli_runner: CliRunner) -> None:
        """Test that config --help shows init command."""
        from anncsu.cli import app

        result = cli_runner.invoke(app, ["config", "--help"])

        assert result.exit_code == 0
        assert "init" in result.output.lower()

    def test_config_help_shows_import(self, cli_runner: CliRunner) -> None:
        """Test that config --help shows import command."""
        from anncsu.cli import app

        result = cli_runner.invoke(app, ["config", "--help"])

        assert result.exit_code == 0
        assert "import" in result.output.lower()

    def test_config_help_shows_show(self, cli_runner: CliRunner) -> None:
        """Test that config --help shows show command."""
        from anncsu.cli import app

        result = cli_runner.invoke(app, ["config", "--help"])

        assert result.exit_code == 0
        assert "show" in result.output.lower()

    def test_config_help_shows_validate(self, cli_runner: CliRunner) -> None:
        """Test that config --help shows validate command."""
        from anncsu.cli import app

        result = cli_runner.invoke(app, ["config", "--help"])

        assert result.exit_code == 0
        assert "validate" in result.output.lower()

    def test_config_help_shows_set(self, cli_runner: CliRunner) -> None:
        """Test that config --help shows set command."""
        from anncsu.cli import app

        result = cli_runner.invoke(app, ["config", "--help"])

        assert result.exit_code == 0
        assert "set" in result.output.lower()


class TestAssertionGroupHelp:
    """Tests for assertion group help and commands listing."""

    def test_assertion_help_shows_create(self, cli_runner: CliRunner) -> None:
        """Test that assertion --help shows create command."""
        from anncsu.cli import app

        result = cli_runner.invoke(app, ["assertion", "--help"])

        assert result.exit_code == 0
        assert "create" in result.output.lower()

    def test_assertion_help_shows_info(self, cli_runner: CliRunner) -> None:
        """Test that assertion --help shows info command."""
        from anncsu.cli import app

        result = cli_runner.invoke(app, ["assertion", "--help"])

        assert result.exit_code == 0
        assert "info" in result.output.lower()

    def test_assertion_help_shows_decode(self, cli_runner: CliRunner) -> None:
        """Test that assertion --help shows decode command."""
        from anncsu.cli import app

        result = cli_runner.invoke(app, ["assertion", "--help"])

        assert result.exit_code == 0
        assert "decode" in result.output.lower()
