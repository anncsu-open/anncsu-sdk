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


# ---------------------------------------------------------------------------
# --dry-run flag
# ---------------------------------------------------------------------------


def _patch_settings_and_auth(stack):
    """Helper: enter the standard mock context for settings + auth manager."""
    settings = MagicMock()
    settings.has_modi_audit_context.return_value = False
    stack.enter_context(
        patch(
            "anncsu.cli.commands.accesso.ClientAssertionSettings",
            return_value=settings,
        )
    )
    manager = MagicMock()
    manager.get_access_token.return_value = "mock-token"
    stack.enter_context(
        patch("anncsu.cli.commands.accesso.PDNDAuthManager", return_value=manager)
    )
    return settings, manager


class TestAccessoInsertDryRun:
    """Tests for ``anncsu accesso insert --dry-run`` (I → S rollback)."""

    def test_insert_dry_run_executes_rollback(
        self, cli_runner: CliRunner, tmp_path: Path, mock_private_key: Path
    ) -> None:
        """Insert dry-run sends I then S to rollback the just-created accesso."""
        import contextlib

        from anncsu.cli import app

        with cli_runner.isolated_filesystem(temp_dir=tmp_path):
            Path("private_key.pem").write_text(mock_private_key.read_text())
            with contextlib.ExitStack() as stack:
                _patch_settings_and_auth(stack)
                mock_sdk_cls = stack.enter_context(
                    patch("anncsu.cli.commands.accesso.AnncsuAccessi")
                )
                sdk = MagicMock()
                # Response to I: returns the assigned progr_civico in dati
                insert_resp = create_mock_response(operazione_civico="I", esito="0")
                insert_resp.dati = [MagicMock(progr_civico="9999999")]
                # Response to S: success rollback
                delete_resp = create_mock_response(operazione_civico="S", esito="0")
                sdk.anncsu.gestione_anncsu_pdnd.side_effect = [
                    insert_resp,
                    delete_resp,
                ]
                mock_sdk_cls.return_value = sdk

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
                        "--dry-run",
                    ],
                )

        assert result.exit_code == 0, result.output
        # Both I and S must have been called
        assert sdk.anncsu.gestione_anncsu_pdnd.call_count == 2

    def test_insert_dry_run_persists_pending_log(
        self, cli_runner: CliRunner, tmp_path: Path, mock_private_key: Path
    ) -> None:
        """Pending file must be created before the rollback API call.

        Tests crash-recovery design: if the second call (rollback) fails or
        the process is killed, the user finds the pending file with all the
        info needed to manually clean up.
        """
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
                mock_sdk_cls = stack.enter_context(
                    patch("anncsu.cli.commands.accesso.AnncsuAccessi")
                )
                # Configure HOME-aware config dir
                stack.enter_context(
                    patch(
                        "anncsu.cli.commands.accesso.get_config_dir",
                        return_value=home / ".anncsu",
                    )
                )
                sdk = MagicMock()
                insert_resp = create_mock_response(operazione_civico="I", esito="0")
                insert_resp.dati = [MagicMock(progr_civico="9999999")]
                delete_resp = create_mock_response(operazione_civico="S", esito="0")
                sdk.anncsu.gestione_anncsu_pdnd.side_effect = [
                    insert_resp,
                    delete_resp,
                ]
                mock_sdk_cls.return_value = sdk

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
                        "--dry-run",
                    ],
                )

        assert result.exit_code == 0, result.output
        # Pending file should exist (created before rollback)
        pending = home / ".anncsu" / "dryrun_pending.json"
        assert pending.exists() or "dryrun_pending" in result.output.lower()

    def test_insert_dry_run_json_output_includes_rollback(
        self, cli_runner: CliRunner, tmp_path: Path, mock_private_key: Path
    ) -> None:
        """JSON output of insert --dry-run must show both test_op and rollback."""
        import contextlib
        import json as json_lib

        from anncsu.cli import app

        with cli_runner.isolated_filesystem(temp_dir=tmp_path):
            Path("private_key.pem").write_text(mock_private_key.read_text())
            with contextlib.ExitStack() as stack:
                _patch_settings_and_auth(stack)
                mock_sdk_cls = stack.enter_context(
                    patch("anncsu.cli.commands.accesso.AnncsuAccessi")
                )
                sdk = MagicMock()
                insert_resp = create_mock_response(
                    operazione_civico="I", esito="0", id_richiesta="REQ-I"
                )
                insert_resp.dati = [MagicMock(progr_civico="9999999")]
                delete_resp = create_mock_response(
                    operazione_civico="S", esito="0", id_richiesta="REQ-S"
                )
                sdk.anncsu.gestione_anncsu_pdnd.side_effect = [
                    insert_resp,
                    delete_resp,
                ]
                mock_sdk_cls.return_value = sdk

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
                        "--dry-run",
                        "--json",
                    ],
                )

        assert result.exit_code == 0
        data = json_lib.loads(result.output)
        assert data["success"] is True
        assert data["test_op"]["operazione_civico"] == "I"
        assert data["rollback"]["operazione_civico"] == "S"


class TestAccessoUpdateDryRun:
    """Tests for ``anncsu accesso update --dry-run`` (R + R rollback)."""

    def test_update_dry_run_executes_two_R(
        self, cli_runner: CliRunner, tmp_path: Path, mock_private_key: Path
    ) -> None:
        """Update dry-run reads originals via PA, sends R new, sends R old."""
        import contextlib

        from anncsu.cli import app

        with cli_runner.isolated_filesystem(temp_dir=tmp_path):
            Path("private_key.pem").write_text(mock_private_key.read_text())
            with contextlib.ExitStack() as stack:
                _patch_settings_and_auth(stack)
                # Mock PA SDK for the original lookup
                mock_pa_cls = stack.enter_context(
                    patch("anncsu.cli.commands.accesso.AnncsuConsultazione")
                )
                pa_sdk = MagicMock()
                lookup_resp = MagicMock()
                # All required fields populated → pre-check OK
                lookup_resp.data = [
                    MagicMock(
                        prognazacc="1370588",
                        civico="12",
                        metrico=None,
                        coord_x="13.10",
                        coord_y="41.88",
                        quota="0",
                        metodo="3",
                        specif=None,
                        esp=None,
                    )
                ]
                pa_sdk.queryparam.prognazacc_get_query_param.return_value = lookup_resp
                mock_pa_cls.return_value = pa_sdk

                # Mock Accessi SDK
                mock_sdk_cls = stack.enter_context(
                    patch("anncsu.cli.commands.accesso.AnncsuAccessi")
                )
                sdk = MagicMock()
                sdk.anncsu.gestione_anncsu_pdnd.side_effect = [
                    create_mock_response(operazione_civico="R", esito="0"),
                    create_mock_response(operazione_civico="R", esito="0"),
                ]
                mock_sdk_cls.return_value = sdk

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
                        "--coord-x",
                        "13.20",
                        "--coord-y",
                        "41.90",
                        "--metodo",
                        "3",
                        "--dry-run",
                    ],
                )

        assert result.exit_code == 0, result.output
        # Two R calls (test + rollback)
        assert sdk.anncsu.gestione_anncsu_pdnd.call_count == 2

    def test_update_dry_run_aborts_on_legacy_data(
        self, cli_runner: CliRunner, tmp_path: Path, mock_private_key: Path
    ) -> None:
        """Pre-check aborts if originals have null metodo (legacy data)."""
        import contextlib

        from anncsu.cli import app

        with cli_runner.isolated_filesystem(temp_dir=tmp_path):
            Path("private_key.pem").write_text(mock_private_key.read_text())
            with contextlib.ExitStack() as stack:
                _patch_settings_and_auth(stack)
                mock_pa_cls = stack.enter_context(
                    patch("anncsu.cli.commands.accesso.AnncsuConsultazione")
                )
                pa_sdk = MagicMock()
                # metodo is None → legacy data → must abort
                lookup_resp = MagicMock()
                lookup_resp.data = [
                    MagicMock(
                        prognazacc="1370588",
                        civico="12",
                        metrico=None,
                        coord_x="13.10",
                        coord_y="41.88",
                        quota=None,
                        metodo=None,  # legacy null!
                        specif=None,
                        esp=None,
                    )
                ]
                pa_sdk.queryparam.prognazacc_get_query_param.return_value = lookup_resp
                mock_pa_cls.return_value = pa_sdk

                mock_sdk_cls = stack.enter_context(
                    patch("anncsu.cli.commands.accesso.AnncsuAccessi")
                )
                sdk = MagicMock()
                mock_sdk_cls.return_value = sdk

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
                        "--dry-run",
                    ],
                )

        # Must abort with non-zero exit, no R call made
        assert result.exit_code != 0
        assert sdk.anncsu.gestione_anncsu_pdnd.call_count == 0
        # Must abort for the *right* reason (legacy data with null metodo),
        # not because --dry-run is an unknown option.
        output_lower = result.output.lower()
        assert "no such option" not in output_lower
        assert (
            "legacy" in output_lower
            or "metodo" in output_lower
            or "null" in output_lower
            or "originali" in output_lower
        )


class TestAccessoDeleteDryRun:
    """Tests for ``anncsu accesso delete --dry-run`` (read → S → I)."""

    def test_delete_dry_run_executes_S_then_I(
        self, cli_runner: CliRunner, tmp_path: Path, mock_private_key: Path
    ) -> None:
        """Delete dry-run reads original, deletes, then re-inserts."""
        import contextlib

        from anncsu.cli import app

        with cli_runner.isolated_filesystem(temp_dir=tmp_path):
            Path("private_key.pem").write_text(mock_private_key.read_text())
            with contextlib.ExitStack() as stack:
                _patch_settings_and_auth(stack)
                mock_pa_cls = stack.enter_context(
                    patch("anncsu.cli.commands.accesso.AnncsuConsultazione")
                )
                pa_sdk = MagicMock()
                lookup_resp = MagicMock()
                lookup_resp.data = [
                    MagicMock(
                        prognazacc="1370588",
                        civico="12",
                        metrico=None,
                        coord_x="13.10",
                        coord_y="41.88",
                        quota="0",
                        metodo="3",
                        specif=None,
                        esp=None,
                    )
                ]
                pa_sdk.queryparam.prognazacc_get_query_param.return_value = lookup_resp
                mock_pa_cls.return_value = pa_sdk

                mock_sdk_cls = stack.enter_context(
                    patch("anncsu.cli.commands.accesso.AnncsuAccessi")
                )
                sdk = MagicMock()
                sdk.anncsu.gestione_anncsu_pdnd.side_effect = [
                    create_mock_response(operazione_civico="S", esito="0"),
                    create_mock_response(operazione_civico="I", esito="0"),
                ]
                mock_sdk_cls.return_value = sdk

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
                        "--dry-run",
                    ],
                )

        assert result.exit_code == 0, result.output
        assert sdk.anncsu.gestione_anncsu_pdnd.call_count == 2


# ---------------------------------------------------------------------------
# --auto-resolve flag (for update/delete)
# ---------------------------------------------------------------------------


class TestAccessoAutoResolve:
    """Tests for the ``--auto-resolve`` flag on update/delete."""

    def test_update_auto_resolve_requires_civico(self, cli_runner: CliRunner) -> None:
        """When --auto-resolve is used without --progr-civico, --civico is
        required so the CLI can look up the progr_civico via PA API."""
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
                "--auto-resolve",
                "--numero",
                "12",
            ],
        )
        # without --civico (the value needed for lookup) → error.
        assert result.exit_code != 0
        # Must fail for the *right* reason (missing --civico), not because
        # --auto-resolve is an unknown option.
        output_lower = result.output.lower()
        assert "no such option: --auto-resolve" not in output_lower
        assert "--civico" in output_lower or "civico" in output_lower

    def test_delete_auto_resolve_success(
        self, cli_runner: CliRunner, tmp_path: Path, mock_private_key: Path
    ) -> None:
        """--auto-resolve resolves progr_civico via PA accesso lookup."""
        import contextlib

        from anncsu.cli import app

        with cli_runner.isolated_filesystem(temp_dir=tmp_path):
            Path("private_key.pem").write_text(mock_private_key.read_text())
            with contextlib.ExitStack() as stack:
                _patch_settings_and_auth(stack)
                # PA lookup returns a single match → progr_civico resolved
                mock_pa_cls = stack.enter_context(
                    patch("anncsu.cli.commands.accesso.AnncsuConsultazione")
                )
                pa_sdk = MagicMock()
                lookup_resp = MagicMock()
                lookup_resp.data = [MagicMock(prognazacc="1370588", civico="12")]
                pa_sdk.queryparam.elencoaccessiprog_get_query_param.return_value = (
                    lookup_resp
                )
                mock_pa_cls.return_value = pa_sdk

                mock_sdk_cls = stack.enter_context(
                    patch("anncsu.cli.commands.accesso.AnncsuAccessi")
                )
                sdk = MagicMock()
                sdk.anncsu.gestione_anncsu_pdnd.return_value = create_mock_response(
                    operazione_civico="S", esito="0"
                )
                mock_sdk_cls.return_value = sdk

                result = cli_runner.invoke(
                    app,
                    [
                        "accesso",
                        "delete",
                        "--codcom",
                        "A062",
                        "--prognaz",
                        "2000449",
                        "--auto-resolve",
                        "--civico",
                        "12",
                    ],
                )

        assert result.exit_code == 0, result.output

    def test_delete_auto_resolve_ambiguous_fails(
        self, cli_runner: CliRunner, tmp_path: Path, mock_private_key: Path
    ) -> None:
        """--auto-resolve errors when PA returns 0 or >1 matches."""
        import contextlib

        from anncsu.cli import app

        with cli_runner.isolated_filesystem(temp_dir=tmp_path):
            Path("private_key.pem").write_text(mock_private_key.read_text())
            with contextlib.ExitStack() as stack:
                _patch_settings_and_auth(stack)
                mock_pa_cls = stack.enter_context(
                    patch("anncsu.cli.commands.accesso.AnncsuConsultazione")
                )
                pa_sdk = MagicMock()
                lookup_resp = MagicMock()
                # Two matches → ambiguous
                lookup_resp.data = [
                    MagicMock(prognazacc="1370588", civico="12"),
                    MagicMock(prognazacc="1370589", civico="12"),
                ]
                pa_sdk.queryparam.elencoaccessiprog_get_query_param.return_value = (
                    lookup_resp
                )
                mock_pa_cls.return_value = pa_sdk

                result = cli_runner.invoke(
                    app,
                    [
                        "accesso",
                        "delete",
                        "--codcom",
                        "A062",
                        "--prognaz",
                        "2000449",
                        "--auto-resolve",
                        "--civico",
                        "12",
                    ],
                )

        assert result.exit_code != 0
        assert (
            "ambig" in result.output.lower()
            or "multiple" in result.output.lower()
            or "more than one" in result.output.lower()
        )

    def test_delete_auto_resolve_no_match_fails(
        self, cli_runner: CliRunner, tmp_path: Path, mock_private_key: Path
    ) -> None:
        """--auto-resolve errors when PA returns no match."""
        import contextlib

        from anncsu.cli import app

        with cli_runner.isolated_filesystem(temp_dir=tmp_path):
            Path("private_key.pem").write_text(mock_private_key.read_text())
            with contextlib.ExitStack() as stack:
                _patch_settings_and_auth(stack)
                mock_pa_cls = stack.enter_context(
                    patch("anncsu.cli.commands.accesso.AnncsuConsultazione")
                )
                pa_sdk = MagicMock()
                lookup_resp = MagicMock()
                lookup_resp.data = []  # no match
                pa_sdk.queryparam.elencoaccessiprog_get_query_param.return_value = (
                    lookup_resp
                )
                mock_pa_cls.return_value = pa_sdk

                result = cli_runner.invoke(
                    app,
                    [
                        "accesso",
                        "delete",
                        "--codcom",
                        "A062",
                        "--prognaz",
                        "2000449",
                        "--auto-resolve",
                        "--civico",
                        "99",
                    ],
                )

        assert result.exit_code != 0
        assert (
            "not found" in result.output.lower()
            or "no match" in result.output.lower()
            or "no accesso" in result.output.lower()
        )
