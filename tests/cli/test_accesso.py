# SPDX-FileCopyrightText: 2025-present Geobeyond <info@geobeyond.it>
# SPDX-License-Identifier: MIT
"""Tests for ``anncsu accesso`` CLI command group."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING
from unittest.mock import MagicMock, patch

import pytest

if TYPE_CHECKING:
    from typer.testing import CliRunner


@pytest.fixture(autouse=True)
def _mock_pdnd_env(monkeypatch):
    """Provide mock PDND credentials so ClientAssertionSettings validates.

    All ``PDND_PURPOSE_ID_*`` vars must be present (can be empty) — see
    the ``ClientAssertionSettings`` validator.
    """
    monkeypatch.setenv("PDND_KID", "test-kid")
    monkeypatch.setenv("PDND_ISSUER", "test-issuer")
    monkeypatch.setenv("PDND_SUBJECT", "test-subject")
    monkeypatch.setenv("PDND_AUDIENCE", "auth.uat.interop.pagopa.it/client-assertion")
    monkeypatch.setenv("PDND_KEY_PATH", "/tmp/dummy.pem")
    monkeypatch.setenv("PDND_PURPOSE_ID_PA", "")
    monkeypatch.setenv("PDND_PURPOSE_ID_COORDINATE", "")
    monkeypatch.setenv("PDND_PURPOSE_ID_COORDINATE_BULK", "")
    monkeypatch.setenv("PDND_PURPOSE_ID_ACCESSI", "test-purpose-id-accessi")
    monkeypatch.setenv("PDND_PURPOSE_ID_INTERNI", "")
    monkeypatch.setenv("PDND_PURPOSE_ID_ODONIMI", "")


def create_mock_response(
    id_richiesta: str = "REQ-123",
    operazione_civico: str = "I",
    esito: str = "0",
    messaggio: str | None = "OK",
    dati: list | None = None,
) -> MagicMock:
    """Create a mock RispostaOperazione with model_dump() configured.

    ANNCSU API convention: esito='0' means success.
    """
    response = MagicMock()
    response.id_richiesta = id_richiesta
    response.operazione_civico = operazione_civico
    response.esito = esito
    response.messaggio = messaggio
    response.dati = dati or []
    response.model_dump.return_value = {
        "idRichiesta": id_richiesta,
        "operazione_civico": operazione_civico,
        "esito": esito,
        "messaggio": messaggio,
        "dati": dati or [],
    }
    return response


# ---------------------------------------------------------------------------
# Group help
# ---------------------------------------------------------------------------


class TestAccessoGroupHelp:
    """Tests for ``anncsu accesso`` group help."""

    def test_accesso_group_registered(self, cli_runner: CliRunner) -> None:
        """Test that accesso command group appears in main help."""
        from anncsu.cli import app

        result = cli_runner.invoke(app, ["--help"])
        assert result.exit_code == 0
        assert "accesso" in result.output.lower()

    def test_accesso_help_shows_subcommands(self, cli_runner: CliRunner) -> None:
        """Test that ``anncsu accesso --help`` lists all subcommands."""
        from anncsu.cli import app

        result = cli_runner.invoke(app, ["accesso", "--help"])
        assert result.exit_code == 0
        output_lower = result.output.lower()
        for subcmd in ("insert", "update", "delete", "status"):
            assert subcmd in output_lower


# ---------------------------------------------------------------------------
# Insert (operazione_civico='I')
# ---------------------------------------------------------------------------


class TestAccessoInsert:
    """Tests for ``anncsu accesso insert`` command."""

    def test_insert_requires_codcom(self, cli_runner: CliRunner) -> None:
        """``--codcom`` is required."""
        from anncsu.cli import app

        result = cli_runner.invoke(app, ["accesso", "insert"])
        assert result.exit_code != 0

    def test_insert_requires_prognaz(self, cli_runner: CliRunner) -> None:
        """``--prognaz`` is required."""
        from anncsu.cli import app

        result = cli_runner.invoke(app, ["accesso", "insert", "--codcom", "A062"])
        assert result.exit_code != 0

    def test_insert_success_with_numero(
        self, cli_runner: CliRunner, tmp_path: Path, mock_private_key: Path
    ) -> None:
        """Insert with civico numero succeeds end-to-end."""
        from anncsu.cli import app

        with cli_runner.isolated_filesystem(temp_dir=tmp_path):
            Path("private_key.pem").write_text(mock_private_key.read_text())
            with patch(
                "anncsu.cli.commands.accesso.ClientAssertionSettings"
            ) as mock_settings:
                settings = MagicMock()
                settings.has_modi_audit_context.return_value = False
                mock_settings.return_value = settings
                with patch(
                    "anncsu.cli.commands.accesso.PDNDAuthManager"
                ) as mock_manager:
                    manager = MagicMock()
                    manager.get_access_token.return_value = "mock-token"
                    mock_manager.return_value = manager
                    with patch("anncsu.cli.commands.accesso.AnncsuAccessi") as mock_sdk:
                        sdk = MagicMock()
                        sdk.anncsu.gestione_anncsu_pdnd.return_value = (
                            create_mock_response(operazione_civico="I", esito="0")
                        )
                        mock_sdk.return_value = sdk

                        result = cli_runner.invoke(
                            app,
                            [
                                "accesso",
                                "insert",
                                "--codcom",
                                "A062",
                                "--prognaz",
                                "2000449",
                                "--numero",
                                "12",
                            ],
                        )

        assert result.exit_code == 0, result.output

    def test_insert_rejects_both_numero_and_metrico(
        self, cli_runner: CliRunner
    ) -> None:
        """ValidatedAccesso rejects numero and metrico together for I."""
        from anncsu.cli import app

        result = cli_runner.invoke(
            app,
            [
                "accesso",
                "insert",
                "--codcom",
                "A062",
                "--prognaz",
                "2000449",
                "--numero",
                "12",
                "--metrico",
                "300",
            ],
        )
        assert result.exit_code != 0

    def test_insert_rejects_neither_numero_nor_metrico(
        self, cli_runner: CliRunner
    ) -> None:
        """ValidatedAccesso requires one of numero or metrico for I."""
        from anncsu.cli import app

        result = cli_runner.invoke(
            app,
            [
                "accesso",
                "insert",
                "--codcom",
                "A062",
                "--prognaz",
                "2000449",
            ],
        )
        assert result.exit_code != 0


# ---------------------------------------------------------------------------
# Update (operazione_civico='R')
# ---------------------------------------------------------------------------


class TestAccessoUpdate:
    """Tests for ``anncsu accesso update`` command."""

    def test_update_requires_codcom(self, cli_runner: CliRunner) -> None:
        from anncsu.cli import app

        result = cli_runner.invoke(app, ["accesso", "update"])
        assert result.exit_code != 0

    def test_update_requires_progr_civico(self, cli_runner: CliRunner) -> None:
        from anncsu.cli import app

        result = cli_runner.invoke(
            app,
            [
                "accesso",
                "update",
                "--codcom",
                "A062",
                "--prognaz",
                "2000449",
                "--numero",
                "12",
            ],
        )
        # missing --progr-civico → either typer error or ProgrCivicoRequiredError
        assert result.exit_code != 0

    def test_update_success(
        self, cli_runner: CliRunner, tmp_path: Path, mock_private_key: Path
    ) -> None:
        """Update with progr_civico + numero succeeds."""
        from anncsu.cli import app

        with cli_runner.isolated_filesystem(temp_dir=tmp_path):
            Path("private_key.pem").write_text(mock_private_key.read_text())
            with patch(
                "anncsu.cli.commands.accesso.ClientAssertionSettings"
            ) as mock_settings:
                settings = MagicMock()
                settings.has_modi_audit_context.return_value = False
                mock_settings.return_value = settings
                with patch(
                    "anncsu.cli.commands.accesso.PDNDAuthManager"
                ) as mock_manager:
                    manager = MagicMock()
                    manager.get_access_token.return_value = "mock-token"
                    mock_manager.return_value = manager
                    with patch("anncsu.cli.commands.accesso.AnncsuAccessi") as mock_sdk:
                        sdk = MagicMock()
                        sdk.anncsu.gestione_anncsu_pdnd.return_value = (
                            create_mock_response(operazione_civico="R", esito="0")
                        )
                        mock_sdk.return_value = sdk

                        result = cli_runner.invoke(
                            app,
                            [
                                "accesso",
                                "update",
                                "--codcom",
                                "A062",
                                "--prognaz",
                                "2000449",
                                "--progr-civico",
                                "1370588",
                                "--numero",
                                "12",
                            ],
                        )

        assert result.exit_code == 0, result.output


# ---------------------------------------------------------------------------
# Delete (operazione_civico='S')
# ---------------------------------------------------------------------------


class TestAccessoDelete:
    """Tests for ``anncsu accesso delete`` command."""

    def test_delete_requires_codcom(self, cli_runner: CliRunner) -> None:
        from anncsu.cli import app

        result = cli_runner.invoke(app, ["accesso", "delete"])
        assert result.exit_code != 0

    def test_delete_requires_progr_civico(self, cli_runner: CliRunner) -> None:
        from anncsu.cli import app

        result = cli_runner.invoke(
            app,
            [
                "accesso",
                "delete",
                "--codcom",
                "A062",
                "--prognaz",
                "2000449",
            ],
        )
        assert result.exit_code != 0

    def test_delete_does_not_accept_numero(self, cli_runner: CliRunner) -> None:
        """``delete`` signature must NOT expose ``--numero``."""
        from anncsu.cli import app

        result = cli_runner.invoke(
            app,
            [
                "accesso",
                "delete",
                "--codcom",
                "A062",
                "--prognaz",
                "2000449",
                "--progr-civico",
                "1370588",
                "--numero",
                "12",
            ],
        )
        # Typer rejects unknown option.
        assert result.exit_code != 0
        assert (
            "no such option" in result.output.lower()
            or "unexpected" in result.output.lower()
        )

    def test_delete_success(
        self, cli_runner: CliRunner, tmp_path: Path, mock_private_key: Path
    ) -> None:
        """Minimal delete succeeds end-to-end."""
        from anncsu.cli import app

        with cli_runner.isolated_filesystem(temp_dir=tmp_path):
            Path("private_key.pem").write_text(mock_private_key.read_text())
            with patch(
                "anncsu.cli.commands.accesso.ClientAssertionSettings"
            ) as mock_settings:
                settings = MagicMock()
                settings.has_modi_audit_context.return_value = False
                mock_settings.return_value = settings
                with patch(
                    "anncsu.cli.commands.accesso.PDNDAuthManager"
                ) as mock_manager:
                    manager = MagicMock()
                    manager.get_access_token.return_value = "mock-token"
                    mock_manager.return_value = manager
                    with patch("anncsu.cli.commands.accesso.AnncsuAccessi") as mock_sdk:
                        sdk = MagicMock()
                        sdk.anncsu.gestione_anncsu_pdnd.return_value = (
                            create_mock_response(operazione_civico="S", esito="0")
                        )
                        mock_sdk.return_value = sdk

                        result = cli_runner.invoke(
                            app,
                            [
                                "accesso",
                                "delete",
                                "--codcom",
                                "A062",
                                "--prognaz",
                                "2000449",
                                "--progr-civico",
                                "1370588",
                            ],
                        )

        assert result.exit_code == 0, result.output


# ---------------------------------------------------------------------------
# Status
# ---------------------------------------------------------------------------


class TestAccessoStatus:
    """Tests for ``anncsu accesso status`` command (GET /status)."""

    def test_status_success(
        self, cli_runner: CliRunner, tmp_path: Path, mock_private_key: Path
    ) -> None:
        from anncsu.cli import app

        with cli_runner.isolated_filesystem(temp_dir=tmp_path):
            Path("private_key.pem").write_text(mock_private_key.read_text())
            with patch(
                "anncsu.cli.commands.accesso.ClientAssertionSettings"
            ) as mock_settings:
                settings = MagicMock()
                settings.has_modi_audit_context.return_value = False
                mock_settings.return_value = settings
                with patch(
                    "anncsu.cli.commands.accesso.PDNDAuthManager"
                ) as mock_manager:
                    manager = MagicMock()
                    manager.get_access_token.return_value = "mock-token"
                    mock_manager.return_value = manager
                    with patch("anncsu.cli.commands.accesso.AnncsuAccessi") as mock_sdk:
                        sdk = MagicMock()
                        status_response = MagicMock()
                        status_response.status = "OK"
                        sdk.status.show_status.return_value = status_response
                        mock_sdk.return_value = sdk

                        result = cli_runner.invoke(app, ["accesso", "status"])

        assert result.exit_code == 0
        output_lower = result.output.lower()
        assert "ok" in output_lower or "status" in output_lower


# ---------------------------------------------------------------------------
# JSON output / Raw flag
# ---------------------------------------------------------------------------


class TestAccessoJsonOutput:
    """Tests for ``--json`` flag."""

    def test_insert_json_output(
        self, cli_runner: CliRunner, tmp_path: Path, mock_private_key: Path
    ) -> None:
        """``--json`` outputs structured JSON parseable by other tools."""
        import json as json_lib

        from anncsu.cli import app

        with cli_runner.isolated_filesystem(temp_dir=tmp_path):
            Path("private_key.pem").write_text(mock_private_key.read_text())
            with patch(
                "anncsu.cli.commands.accesso.ClientAssertionSettings"
            ) as mock_settings:
                settings = MagicMock()
                settings.has_modi_audit_context.return_value = False
                mock_settings.return_value = settings
                with patch(
                    "anncsu.cli.commands.accesso.PDNDAuthManager"
                ) as mock_manager:
                    manager = MagicMock()
                    manager.get_access_token.return_value = "mock-token"
                    mock_manager.return_value = manager
                    with patch("anncsu.cli.commands.accesso.AnncsuAccessi") as mock_sdk:
                        sdk = MagicMock()
                        sdk.anncsu.gestione_anncsu_pdnd.return_value = (
                            create_mock_response(
                                id_richiesta="REQ-001",
                                operazione_civico="I",
                                esito="0",
                                messaggio="OK",
                            )
                        )
                        mock_sdk.return_value = sdk

                        result = cli_runner.invoke(
                            app,
                            [
                                "accesso",
                                "insert",
                                "--codcom",
                                "A062",
                                "--prognaz",
                                "2000449",
                                "--numero",
                                "12",
                                "--json",
                            ],
                        )

        assert result.exit_code == 0
        # output should be parseable JSON
        data = json_lib.loads(result.output)
        assert data["success"] is True
        assert data["id_richiesta"] == "REQ-001"
        assert data["operazione_civico"] == "I"
