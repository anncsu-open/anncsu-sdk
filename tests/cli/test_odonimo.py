# SPDX-FileCopyrightText: 2025-present Geobeyond <info@geobeyond.it>
# SPDX-License-Identifier: MIT
"""Tests for ``anncsu odonimo`` CLI command group."""

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
    monkeypatch.setenv("PDND_PURPOSE_ID_ACCESSI", "")
    monkeypatch.setenv("PDND_PURPOSE_ID_INTERNI", "")
    monkeypatch.setenv("PDND_PURPOSE_ID_ODONIMI", "test-purpose-id-odonimi")


def _create_mock_response(
    id_richiesta: str = "REQ-321",
    esito: str = "0",
    messaggio: str | None = "OK",
    dati: list | None = None,
) -> MagicMock:
    """Mock RispostaOperazione (esito='0' = success per ANNCSU convention)."""
    response = MagicMock()
    response.id_richiesta = id_richiesta
    response.esito = esito
    response.messaggio = messaggio
    response.dati = dati or []
    response.model_dump.return_value = {
        "idRichiesta": id_richiesta,
        "esito": esito,
        "messaggio": messaggio,
        "dati": dati or [],
    }
    return response


# ---------------------------------------------------------------------------
# Group help
# ---------------------------------------------------------------------------


class TestOdonimoGroupHelp:
    """Tests for ``anncsu odonimo`` group help."""

    def test_odonimo_group_registered(self, cli_runner: CliRunner) -> None:
        """Test that odonimo command group appears in main help."""
        from anncsu.cli import app

        result = cli_runner.invoke(app, ["--help"])
        assert result.exit_code == 0
        assert "odonimo" in result.output.lower()

    def test_odonimo_help_shows_subcommands(self, cli_runner: CliRunner) -> None:
        """Test that ``anncsu odonimo --help`` lists all subcommands."""
        from anncsu.cli import app

        result = cli_runner.invoke(app, ["odonimo", "--help"])
        assert result.exit_code == 0
        output_lower = result.output.lower()
        for subcmd in ("insert", "update", "delete", "status"):
            assert subcmd in output_lower


# ---------------------------------------------------------------------------
# Insert (tipo_operazione='I')
# ---------------------------------------------------------------------------


class TestOdonimoInsert:
    """Tests for ``anncsu odonimo insert`` command."""

    def test_insert_requires_codcom(self, cli_runner: CliRunner) -> None:
        from anncsu.cli import app

        result = cli_runner.invoke(app, ["odonimo", "insert"])
        assert result.exit_code != 0

    def test_insert_requires_dug(self, cli_runner: CliRunner) -> None:
        from anncsu.cli import app

        result = cli_runner.invoke(app, ["odonimo", "insert", "--codcom", "A062"])
        assert result.exit_code != 0

    def test_insert_success(
        self, cli_runner: CliRunner, tmp_path: Path, mock_private_key: Path
    ) -> None:
        """Insert with minimum valid args succeeds end-to-end."""
        from anncsu.cli import app

        with cli_runner.isolated_filesystem(temp_dir=tmp_path):
            Path("private_key.pem").write_text(mock_private_key.read_text())
            with patch(
                "anncsu.cli.commands.odonimo.ClientAssertionSettings"
            ) as mock_settings:
                settings = MagicMock()
                settings.has_modi_audit_context.return_value = False
                mock_settings.return_value = settings
                with patch(
                    "anncsu.cli.commands.odonimo.PDNDAuthManager"
                ) as mock_manager:
                    manager = MagicMock()
                    manager.get_access_token.return_value = "mock-token"
                    mock_manager.return_value = manager
                    with patch("anncsu.cli.commands.odonimo.AnncsuOdonimi") as mock_sdk:
                        sdk = MagicMock()
                        sdk.anncsu.gestione_anncsu_odonimi_pdnd.return_value = (
                            _create_mock_response(esito="0")
                        )
                        mock_sdk.return_value = sdk

                        result = cli_runner.invoke(
                            app,
                            [
                                "odonimo",
                                "insert",
                                "--codcom",
                                "A062",
                                "--dug",
                                "VIA",
                                "--denom-delibera",
                                "DELLE ORCHIDEE",
                            ],
                        )

        assert result.exit_code == 0, result.output


# ---------------------------------------------------------------------------
# Update (tipo_operazione='R')
# ---------------------------------------------------------------------------


class TestOdonimoUpdate:
    """Tests for ``anncsu odonimo update`` command."""

    def test_update_requires_prognaz(self, cli_runner: CliRunner) -> None:
        from anncsu.cli import app

        result = cli_runner.invoke(
            app, ["odonimo", "update", "--codcom", "A062", "--dug", "VIA"]
        )
        assert result.exit_code != 0

    def test_update_requires_dug(self, cli_runner: CliRunner) -> None:
        from anncsu.cli import app

        result = cli_runner.invoke(
            app,
            ["odonimo", "update", "--codcom", "A062", "--prognaz", "2000449"],
        )
        assert result.exit_code != 0

    def test_update_success(
        self, cli_runner: CliRunner, tmp_path: Path, mock_private_key: Path
    ) -> None:
        from anncsu.cli import app

        with cli_runner.isolated_filesystem(temp_dir=tmp_path):
            Path("private_key.pem").write_text(mock_private_key.read_text())
            with patch(
                "anncsu.cli.commands.odonimo.ClientAssertionSettings"
            ) as mock_settings:
                settings = MagicMock()
                settings.has_modi_audit_context.return_value = False
                mock_settings.return_value = settings
                with patch(
                    "anncsu.cli.commands.odonimo.PDNDAuthManager"
                ) as mock_manager:
                    manager = MagicMock()
                    manager.get_access_token.return_value = "mock-token"
                    mock_manager.return_value = manager
                    with patch("anncsu.cli.commands.odonimo.AnncsuOdonimi") as mock_sdk:
                        sdk = MagicMock()
                        sdk.anncsu.gestione_anncsu_odonimi_pdnd.return_value = (
                            _create_mock_response(esito="0")
                        )
                        mock_sdk.return_value = sdk

                        result = cli_runner.invoke(
                            app,
                            [
                                "odonimo",
                                "update",
                                "--codcom",
                                "A062",
                                "--prognaz",
                                "2000449",
                                "--dug",
                                "VIA",
                                "--denom-delibera",
                                "DEI TIGLI",
                            ],
                        )

        assert result.exit_code == 0, result.output


# ---------------------------------------------------------------------------
# Delete (tipo_operazione='S')
# ---------------------------------------------------------------------------


class TestOdonimoDelete:
    """Tests for ``anncsu odonimo delete`` command."""

    def test_delete_requires_prognaz(self, cli_runner: CliRunner) -> None:
        from anncsu.cli import app

        result = cli_runner.invoke(app, ["odonimo", "delete", "--codcom", "A062"])
        assert result.exit_code != 0

    def test_delete_rejects_dug_flag(self, cli_runner: CliRunner) -> None:
        """Typer must reject ``--dug`` for delete (not in its signature).

        This is the operation-aware validation: ``delete`` does not expose
        --dug at all, so Typer fails at parse time before any API call.
        """
        from anncsu.cli import app

        result = cli_runner.invoke(
            app,
            [
                "odonimo",
                "delete",
                "--codcom",
                "A062",
                "--prognaz",
                "2000449",
                "--dug",
                "VIA",
            ],
        )
        assert result.exit_code != 0
        assert "no such option" in result.output.lower()

    def test_delete_success(
        self, cli_runner: CliRunner, tmp_path: Path, mock_private_key: Path
    ) -> None:
        from anncsu.cli import app

        with cli_runner.isolated_filesystem(temp_dir=tmp_path):
            Path("private_key.pem").write_text(mock_private_key.read_text())
            with patch(
                "anncsu.cli.commands.odonimo.ClientAssertionSettings"
            ) as mock_settings:
                settings = MagicMock()
                settings.has_modi_audit_context.return_value = False
                mock_settings.return_value = settings
                with patch(
                    "anncsu.cli.commands.odonimo.PDNDAuthManager"
                ) as mock_manager:
                    manager = MagicMock()
                    manager.get_access_token.return_value = "mock-token"
                    mock_manager.return_value = manager
                    with patch("anncsu.cli.commands.odonimo.AnncsuOdonimi") as mock_sdk:
                        sdk = MagicMock()
                        sdk.anncsu.gestione_anncsu_odonimi_pdnd.return_value = (
                            _create_mock_response(esito="0")
                        )
                        mock_sdk.return_value = sdk

                        result = cli_runner.invoke(
                            app,
                            [
                                "odonimo",
                                "delete",
                                "--codcom",
                                "A062",
                                "--prognaz",
                                "2000449",
                            ],
                        )

        assert result.exit_code == 0, result.output


# ---------------------------------------------------------------------------
# JSON output
# ---------------------------------------------------------------------------


class TestOdonimoJsonOutput:
    """Tests for ``--json`` flag on insert."""

    def test_insert_json_output(
        self, cli_runner: CliRunner, tmp_path: Path, mock_private_key: Path
    ) -> None:
        """``--json`` outputs structured JSON parseable by other tools."""
        import json as json_lib

        from anncsu.cli import app

        with cli_runner.isolated_filesystem(temp_dir=tmp_path):
            Path("private_key.pem").write_text(mock_private_key.read_text())
            with patch(
                "anncsu.cli.commands.odonimo.ClientAssertionSettings"
            ) as mock_settings:
                settings = MagicMock()
                settings.has_modi_audit_context.return_value = False
                mock_settings.return_value = settings
                with patch(
                    "anncsu.cli.commands.odonimo.PDNDAuthManager"
                ) as mock_manager:
                    manager = MagicMock()
                    manager.get_access_token.return_value = "mock-token"
                    mock_manager.return_value = manager
                    with patch("anncsu.cli.commands.odonimo.AnncsuOdonimi") as mock_sdk:
                        sdk = MagicMock()
                        sdk.anncsu.gestione_anncsu_odonimi_pdnd.return_value = (
                            _create_mock_response(
                                id_richiesta="REQ-J1",
                                esito="0",
                                messaggio="OK",
                            )
                        )
                        mock_sdk.return_value = sdk

                        result = cli_runner.invoke(
                            app,
                            [
                                "odonimo",
                                "insert",
                                "--codcom",
                                "A062",
                                "--dug",
                                "VIA",
                                "--denom-delibera",
                                "DELLE ORCHIDEE",
                                "--json",
                            ],
                        )

        assert result.exit_code == 0
        data = json_lib.loads(result.output)
        assert data["success"] is True
        assert data["tipo_operazione"] == "I"
        assert data["id_richiesta"] == "REQ-J1"


# ---------------------------------------------------------------------------
# --auto-resolve (lookup prognaz via PA)
# ---------------------------------------------------------------------------


class TestOdonimoAutoResolve:
    """Tests for ``--auto-resolve`` flag on update/delete."""

    def test_update_auto_resolve_requires_denom(self, cli_runner: CliRunner) -> None:
        """``--auto-resolve`` without ``--denom`` is a setup error."""
        from anncsu.cli import app

        result = cli_runner.invoke(
            app,
            [
                "odonimo",
                "update",
                "--codcom",
                "A062",
                "--dug",
                "VIA",
                "--auto-resolve",
            ],
        )
        assert result.exit_code != 0
        assert "--denom" in result.output.lower()

    def test_delete_auto_resolve_requires_denom(self, cli_runner: CliRunner) -> None:
        from anncsu.cli import app

        result = cli_runner.invoke(
            app,
            ["odonimo", "delete", "--codcom", "A062", "--auto-resolve"],
        )
        assert result.exit_code != 0
        assert "--denom" in result.output.lower()

    def test_update_auto_resolve_success(
        self, cli_runner: CliRunner, tmp_path: Path, mock_private_key: Path
    ) -> None:
        """``--auto-resolve`` resolves prognaz via PA, then proceeds with R."""
        from anncsu.cli import app

        with cli_runner.isolated_filesystem(temp_dir=tmp_path):
            Path("private_key.pem").write_text(mock_private_key.read_text())
            with patch(
                "anncsu.cli.commands.odonimo.ClientAssertionSettings"
            ) as mock_settings:
                settings = MagicMock()
                settings.has_modi_audit_context.return_value = False
                mock_settings.return_value = settings
                with patch(
                    "anncsu.cli.commands.odonimo.PDNDAuthManager"
                ) as mock_manager:
                    manager = MagicMock()
                    manager.get_access_token.return_value = "mock-token"
                    mock_manager.return_value = manager
                    # Mock the PA consult SDK used by --auto-resolve
                    with patch(
                        "anncsu.cli.commands.odonimo.AnncsuConsultazione"
                    ) as mock_consult:
                        match = MagicMock()
                        match.prognaz = "2000449"
                        pa_response = MagicMock()
                        pa_response.data = [match]
                        consult = MagicMock()
                        consult.queryparam.elencoodonimiprog_get_query_param.return_value = pa_response
                        mock_consult.return_value = consult
                        with patch(
                            "anncsu.cli.commands.odonimo.AnncsuOdonimi"
                        ) as mock_sdk:
                            sdk = MagicMock()
                            sdk.anncsu.gestione_anncsu_odonimi_pdnd.return_value = (
                                _create_mock_response(esito="0")
                            )
                            mock_sdk.return_value = sdk

                            result = cli_runner.invoke(
                                app,
                                [
                                    "odonimo",
                                    "update",
                                    "--codcom",
                                    "A062",
                                    "--auto-resolve",
                                    "--denom",
                                    "VklBIERFTCBDT1JTTw==",
                                    "--dug",
                                    "VIA",
                                ],
                            )

        assert result.exit_code == 0, result.output


# ---------------------------------------------------------------------------
# --dry-run (ciclo CRUD su denominazione fittizia)
# ---------------------------------------------------------------------------


def _patch_settings_and_auth(stack):
    """Common stack of patches for dry-run tests (mock settings + auth)."""
    mock_settings = stack.enter_context(
        patch("anncsu.cli.commands.odonimo.ClientAssertionSettings")
    )
    settings = MagicMock()
    settings.has_modi_audit_context.return_value = False
    mock_settings.return_value = settings
    mock_manager = stack.enter_context(
        patch("anncsu.cli.commands.odonimo.PDNDAuthManager")
    )
    manager = MagicMock()
    manager.get_access_token.return_value = "mock-token"
    mock_manager.return_value = manager


class TestOdonimoInsertDryRun:
    """Tests for ``anncsu odonimo insert --dry-run`` (I → S cycle)."""

    def test_insert_dry_run_executes_rollback(
        self, cli_runner: CliRunner, tmp_path: Path, mock_private_key: Path
    ) -> None:
        """``--dry-run`` calls I then S to rollback the new odonimo."""
        import contextlib

        from anncsu.cli import app

        with cli_runner.isolated_filesystem(temp_dir=tmp_path):
            Path("private_key.pem").write_text(mock_private_key.read_text())
            with contextlib.ExitStack() as stack:
                _patch_settings_and_auth(stack)
                mock_sdk_cls = stack.enter_context(
                    patch("anncsu.cli.commands.odonimo.AnncsuOdonimi")
                )
                sdk = MagicMock()
                insert_resp = _create_mock_response(esito="0")
                insert_resp.dati = [MagicMock(progr_nazionale="9999991")]
                delete_resp = _create_mock_response(esito="0")
                sdk.anncsu.gestione_anncsu_odonimi_pdnd.side_effect = [
                    insert_resp,
                    delete_resp,
                ]
                mock_sdk_cls.return_value = sdk

                result = cli_runner.invoke(
                    app,
                    [
                        "odonimo",
                        "insert",
                        "--codcom",
                        "A062",
                        "--dug",
                        "VIA",
                        "--denom-delibera",
                        "DELLE ORCHIDEE",
                        "--dry-run",
                    ],
                )

        assert result.exit_code == 0, result.output
        assert sdk.anncsu.gestione_anncsu_odonimi_pdnd.call_count == 2

    def test_insert_dry_run_persists_pending_log(
        self, cli_runner: CliRunner, tmp_path: Path, mock_private_key: Path
    ) -> None:
        """Pending file must be created before the rollback API call."""
        import contextlib

        from anncsu.cli import app

        with cli_runner.isolated_filesystem(temp_dir=tmp_path):
            Path("private_key.pem").write_text(mock_private_key.read_text())
            home = tmp_path / "fake-home"
            home.mkdir()
            with (
                patch.dict("os.environ", {"HOME": str(home)}, clear=False),
                contextlib.ExitStack() as stack,
            ):
                _patch_settings_and_auth(stack)
                stack.enter_context(
                    patch(
                        "anncsu.cli.commands.odonimo.get_config_dir",
                        return_value=home / ".anncsu",
                    )
                )
                mock_sdk_cls = stack.enter_context(
                    patch("anncsu.cli.commands.odonimo.AnncsuOdonimi")
                )
                sdk = MagicMock()
                insert_resp = _create_mock_response(esito="0")
                insert_resp.dati = [MagicMock(progr_nazionale="9999991")]
                delete_resp = _create_mock_response(esito="0")
                sdk.anncsu.gestione_anncsu_odonimi_pdnd.side_effect = [
                    insert_resp,
                    delete_resp,
                ]
                mock_sdk_cls.return_value = sdk

                result = cli_runner.invoke(
                    app,
                    [
                        "odonimo",
                        "insert",
                        "--codcom",
                        "A062",
                        "--dug",
                        "VIA",
                        "--denom-delibera",
                        "DELLE ORCHIDEE",
                        "--dry-run",
                    ],
                )

        assert result.exit_code == 0, result.output
        pending = home / ".anncsu" / "dryrun_pending.json"
        assert pending.exists() or "dryrun_pending" in result.output.lower()


class TestOdonimoUpdateDryRun:
    """Tests for ``anncsu odonimo update --dry-run`` (I → R → S cycle)."""

    def test_update_dry_run_executes_three_calls(
        self, cli_runner: CliRunner, tmp_path: Path, mock_private_key: Path
    ) -> None:
        """``update --dry-run`` calls I (fake) → R (user data) → S (cleanup)."""
        import contextlib

        from anncsu.cli import app

        with cli_runner.isolated_filesystem(temp_dir=tmp_path):
            Path("private_key.pem").write_text(mock_private_key.read_text())
            with contextlib.ExitStack() as stack:
                _patch_settings_and_auth(stack)
                mock_sdk_cls = stack.enter_context(
                    patch("anncsu.cli.commands.odonimo.AnncsuOdonimi")
                )
                sdk = MagicMock()
                insert_resp = _create_mock_response(esito="0")
                insert_resp.dati = [MagicMock(progr_nazionale="9999992")]
                update_resp = _create_mock_response(esito="0")
                delete_resp = _create_mock_response(esito="0")
                sdk.anncsu.gestione_anncsu_odonimi_pdnd.side_effect = [
                    insert_resp,
                    update_resp,
                    delete_resp,
                ]
                mock_sdk_cls.return_value = sdk

                result = cli_runner.invoke(
                    app,
                    [
                        "odonimo",
                        "update",
                        "--codcom",
                        "A062",
                        "--dug",
                        "VIA",
                        "--denom-delibera",
                        "DEI TIGLI",
                        "--dry-run",
                    ],
                )

        assert result.exit_code == 0, result.output
        assert sdk.anncsu.gestione_anncsu_odonimi_pdnd.call_count == 3


class TestOdonimoDeleteDryRun:
    """Tests for ``anncsu odonimo delete --dry-run`` (I → S smoke-test)."""

    def test_delete_dry_run_executes_two_calls(
        self, cli_runner: CliRunner, tmp_path: Path, mock_private_key: Path
    ) -> None:
        """``delete --dry-run`` creates a fake odonimo and immediately deletes it."""
        import contextlib

        from anncsu.cli import app

        with cli_runner.isolated_filesystem(temp_dir=tmp_path):
            Path("private_key.pem").write_text(mock_private_key.read_text())
            with contextlib.ExitStack() as stack:
                _patch_settings_and_auth(stack)
                mock_sdk_cls = stack.enter_context(
                    patch("anncsu.cli.commands.odonimo.AnncsuOdonimi")
                )
                sdk = MagicMock()
                insert_resp = _create_mock_response(esito="0")
                insert_resp.dati = [MagicMock(progr_nazionale="9999993")]
                delete_resp = _create_mock_response(esito="0")
                sdk.anncsu.gestione_anncsu_odonimi_pdnd.side_effect = [
                    insert_resp,
                    delete_resp,
                ]
                mock_sdk_cls.return_value = sdk

                result = cli_runner.invoke(
                    app,
                    [
                        "odonimo",
                        "delete",
                        "--codcom",
                        "A062",
                        "--dry-run",
                    ],
                )

        assert result.exit_code == 0, result.output
        assert sdk.anncsu.gestione_anncsu_odonimi_pdnd.call_count == 2

    def test_delete_dry_run_json_output_includes_rollback(
        self, cli_runner: CliRunner, tmp_path: Path, mock_private_key: Path
    ) -> None:
        """JSON output of ``delete --dry-run`` must include test_op + rollback."""
        import contextlib
        import json as json_lib

        from anncsu.cli import app

        with cli_runner.isolated_filesystem(temp_dir=tmp_path):
            Path("private_key.pem").write_text(mock_private_key.read_text())
            with contextlib.ExitStack() as stack:
                _patch_settings_and_auth(stack)
                mock_sdk_cls = stack.enter_context(
                    patch("anncsu.cli.commands.odonimo.AnncsuOdonimi")
                )
                sdk = MagicMock()
                insert_resp = _create_mock_response(id_richiesta="REQ-I", esito="0")
                insert_resp.dati = [MagicMock(progr_nazionale="9999994")]
                delete_resp = _create_mock_response(id_richiesta="REQ-S", esito="0")
                sdk.anncsu.gestione_anncsu_odonimi_pdnd.side_effect = [
                    insert_resp,
                    delete_resp,
                ]
                mock_sdk_cls.return_value = sdk

                result = cli_runner.invoke(
                    app,
                    [
                        "odonimo",
                        "delete",
                        "--codcom",
                        "A062",
                        "--dry-run",
                        "--json",
                    ],
                )

        assert result.exit_code == 0, result.output
        data = json_lib.loads(result.output)
        assert data["success"] is True
        assert data["tipo_operazione"] == "S"
        assert data["test_op"]["id_richiesta"] == "REQ-I"
        assert data["rollback"]["id_richiesta"] == "REQ-S"
        assert data["fake_prognaz"] == "9999994"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
