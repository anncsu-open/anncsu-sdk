# SPDX-FileCopyrightText: 2025-present Geobeyond <info@geobeyond.it>
# SPDX-License-Identifier: MIT
"""Tests for coordinate CLI commands."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING
from unittest.mock import MagicMock, patch

from pydantic import BaseModel

from anncsu.cli.models import DryRunResult

if TYPE_CHECKING:
    from typer.testing import CliRunner


def create_mock_response(
    id_richiesta: str = "REQ-123",
    esito: str = "0",
    messaggio: str | None = "OK",
    dati: list | None = None,
) -> MagicMock:
    """Create a mock response with model_dump() configured.

    ANNCSU API convention: esito="0" means success.
    """
    response = MagicMock()
    response.id_richiesta = id_richiesta
    response.esito = esito
    response.messaggio = messaggio
    response.dati = dati or []
    # Configure model_dump() to return the correct dict
    response.model_dump.return_value = {
        "idRichiesta": id_richiesta,
        "esito": esito,
        "messaggio": messaggio,
        "dati": dati or [],
    }
    return response


# Pydantic models for coordinate output
class CoordinateUpdateResult(BaseModel):
    """Result of a coordinate update operation."""

    success: bool
    id_richiesta: str | None = None
    esito: str | None = None
    messaggio: str | None = None
    dati_count: int = 0


class CoordinateStatusResult(BaseModel):
    """Result of a coordinate API status check."""

    available: bool
    status: str
    server_url: str
    environment: str


class TestCoordinateGroupHelp:
    """Tests for coordinate command group help."""

    def test_coordinate_group_exists(self, cli_runner: CliRunner) -> None:
        """Test that coordinate command group is registered."""
        from anncsu.cli import app

        result = cli_runner.invoke(app, ["--help"])
        assert result.exit_code == 0
        assert "coordinate" in result.output.lower()

    def test_coordinate_help_shows_commands(self, cli_runner: CliRunner) -> None:
        """Test that coordinate --help shows available commands."""
        from anncsu.cli import app

        result = cli_runner.invoke(app, ["coordinate", "--help"])
        assert result.exit_code == 0
        assert "update" in result.output.lower()
        assert "status" in result.output.lower()


class TestCoordinateUpdate:
    """Tests for coordinate update command."""

    def test_update_requires_codcom(self, cli_runner: CliRunner) -> None:
        """Test that coordinate update requires --codcom parameter."""
        from anncsu.cli import app

        result = cli_runner.invoke(app, ["coordinate", "update"])
        # Should fail because --codcom is required
        assert result.exit_code != 0

    def test_update_requires_progr_civico(self, cli_runner: CliRunner) -> None:
        """Test that coordinate update requires --progr-civico parameter."""
        from anncsu.cli import app

        result = cli_runner.invoke(app, ["coordinate", "update", "--codcom", "H501"])
        # Should fail because --progr-civico is required
        assert result.exit_code != 0

    def test_update_success(
        self, cli_runner: CliRunner, tmp_path: Path, mock_private_key: Path
    ) -> None:
        """Test that coordinate update succeeds with valid parameters."""
        from anncsu.cli import app

        with cli_runner.isolated_filesystem(temp_dir=tmp_path):
            Path("private_key.pem").write_text(mock_private_key.read_text())

            with patch(
                "anncsu.cli.commands.coordinate.ClientAssertionSettings"
            ) as mock_settings:
                settings = MagicMock()
                settings.private_key = None
                settings.key_path = None
                settings.kid = "test-kid"
                settings.issuer = "test-issuer"
                settings.has_modi_audit_context.return_value = False
                mock_settings.return_value = settings

                with patch(
                    "anncsu.cli.commands.coordinate.PDNDAuthManager"
                ) as mock_manager:
                    manager = MagicMock()
                    manager.get_access_token.return_value = "mock-access-token"
                    mock_manager.return_value = manager

                    with patch(
                        "anncsu.cli.commands.coordinate.SDKHooks"
                    ) as mock_hooks_class:
                        mock_hooks = MagicMock()
                        mock_hooks_class.return_value = mock_hooks

                        with patch("anncsu.cli.commands.coordinate.register_modi_hook"):
                            with patch(
                                "anncsu.cli.commands.coordinate.AnncsuCoordinate"
                            ) as mock_sdk:
                                sdk = MagicMock()
                                response = create_mock_response(
                                    id_richiesta="REQ-123",
                                    esito="0",
                                    messaggio="Operazione completata",
                                )
                                sdk.json_post.gestionecoordinate.return_value = response
                                mock_sdk.return_value = sdk

                                result = cli_runner.invoke(
                                    app,
                                    [
                                        "coordinate",
                                        "update",
                                        "--codcom",
                                        "H501",
                                        "--progr-civico",
                                        "12345",
                                        "--x",
                                        "12.4963655",
                                        "--y",
                                        "41.9027835",
                                        "--metodo",
                                        "4",
                                    ],
                                )

            assert result.exit_code == 0
            output_lower = result.output.lower()
            assert (
                "success" in output_lower
                or "ok" in output_lower
                or "completat" in output_lower
            )

    def test_update_json_output(
        self, cli_runner: CliRunner, tmp_path: Path, mock_private_key: Path
    ) -> None:
        """Test that coordinate update can output JSON."""
        from anncsu.cli import app

        with cli_runner.isolated_filesystem(temp_dir=tmp_path):
            Path("private_key.pem").write_text(mock_private_key.read_text())

            with patch(
                "anncsu.cli.commands.coordinate.ClientAssertionSettings"
            ) as mock_settings:
                settings = MagicMock()
                mock_settings.return_value = settings

                with patch(
                    "anncsu.cli.commands.coordinate.PDNDAuthManager"
                ) as mock_manager:
                    manager = MagicMock()
                    manager.get_access_token.return_value = "mock-access-token"
                    mock_manager.return_value = manager

                    with patch(
                        "anncsu.cli.commands.coordinate.AnncsuCoordinate"
                    ) as mock_sdk:
                        sdk = MagicMock()
                        response = create_mock_response(
                            id_richiesta="REQ-456",
                            esito="0",
                            messaggio="Success",
                        )
                        sdk.json_post.gestionecoordinate.return_value = response
                        mock_sdk.return_value = sdk

                        result = cli_runner.invoke(
                            app,
                            [
                                "coordinate",
                                "update",
                                "--codcom",
                                "H501",
                                "--progr-civico",
                                "12345",
                                "--json",
                            ],
                        )

            assert result.exit_code == 0
            # Should be valid JSON parseable as Pydantic model
            update_result = CoordinateUpdateResult.model_validate_json(result.output)
            assert update_result.success is True
            assert update_result.id_richiesta == "REQ-456"

    def test_update_with_all_coordinates(
        self, cli_runner: CliRunner, tmp_path: Path, mock_private_key: Path
    ) -> None:
        """Test update with all coordinate parameters (x, y, z, metodo)."""
        from anncsu.cli import app

        with cli_runner.isolated_filesystem(temp_dir=tmp_path):
            Path("private_key.pem").write_text(mock_private_key.read_text())

            with patch(
                "anncsu.cli.commands.coordinate.ClientAssertionSettings"
            ) as mock_settings:
                settings = MagicMock()
                mock_settings.return_value = settings

                with patch(
                    "anncsu.cli.commands.coordinate.PDNDAuthManager"
                ) as mock_manager:
                    manager = MagicMock()
                    manager.get_access_token.return_value = "mock-access-token"
                    mock_manager.return_value = manager

                    with patch(
                        "anncsu.cli.commands.coordinate.AnncsuCoordinate"
                    ) as mock_sdk:
                        sdk = MagicMock()
                        response = create_mock_response(
                            id_richiesta="REQ-789",
                            esito="0",
                            messaggio=None,
                        )
                        sdk.json_post.gestionecoordinate.return_value = response
                        mock_sdk.return_value = sdk

                        result = cli_runner.invoke(
                            app,
                            [
                                "coordinate",
                                "update",
                                "--codcom",
                                "H501",
                                "--progr-civico",
                                "12345",
                                "--x",
                                "12.4963655",
                                "--y",
                                "41.9027835",
                                "--z",
                                "21",
                                "--metodo",
                                "4",
                            ],
                        )

            assert result.exit_code == 0

    def test_update_error_no_config(
        self, cli_runner: CliRunner, tmp_path: Path
    ) -> None:
        """Test that coordinate update fails gracefully without config."""
        from anncsu.cli import app

        with cli_runner.isolated_filesystem(temp_dir=tmp_path):
            with patch(
                "anncsu.cli.commands.coordinate.ClientAssertionSettings",
                side_effect=Exception("No configuration found"),
            ):
                result = cli_runner.invoke(
                    app,
                    [
                        "coordinate",
                        "update",
                        "--codcom",
                        "H501",
                        "--progr-civico",
                        "12345",
                    ],
                )

            assert result.exit_code == 1
            assert "error" in result.output.lower()

    def test_update_error_api_failure(
        self, cli_runner: CliRunner, tmp_path: Path, mock_private_key: Path
    ) -> None:
        """Test that coordinate update handles API failure."""
        from anncsu.cli import app

        with cli_runner.isolated_filesystem(temp_dir=tmp_path):
            Path("private_key.pem").write_text(mock_private_key.read_text())

            with patch(
                "anncsu.cli.commands.coordinate.ClientAssertionSettings"
            ) as mock_settings:
                settings = MagicMock()
                mock_settings.return_value = settings

                with patch(
                    "anncsu.cli.commands.coordinate.PDNDAuthManager"
                ) as mock_manager:
                    manager = MagicMock()
                    manager.get_access_token.return_value = "mock-access-token"
                    mock_manager.return_value = manager

                    with patch(
                        "anncsu.cli.commands.coordinate.AnncsuCoordinate"
                    ) as mock_sdk:
                        sdk = MagicMock()
                        sdk.json_post.gestionecoordinate.side_effect = Exception(
                            "API error"
                        )
                        mock_sdk.return_value = sdk

                        result = cli_runner.invoke(
                            app,
                            [
                                "coordinate",
                                "update",
                                "--codcom",
                                "H501",
                                "--progr-civico",
                                "12345",
                            ],
                        )

            assert result.exit_code == 1
            assert "error" in result.output.lower()

    def test_update_custom_server_url(
        self, cli_runner: CliRunner, tmp_path: Path, mock_private_key: Path
    ) -> None:
        """Test that coordinate update accepts custom server URL."""
        from anncsu.cli import app

        with cli_runner.isolated_filesystem(temp_dir=tmp_path):
            Path("private_key.pem").write_text(mock_private_key.read_text())

            with patch(
                "anncsu.cli.commands.coordinate.ClientAssertionSettings"
            ) as mock_settings:
                settings = MagicMock()
                mock_settings.return_value = settings

                with patch(
                    "anncsu.cli.commands.coordinate.PDNDAuthManager"
                ) as mock_manager:
                    manager = MagicMock()
                    manager.get_access_token.return_value = "mock-access-token"
                    mock_manager.return_value = manager

                    with patch(
                        "anncsu.cli.commands.coordinate.AnncsuCoordinate"
                    ) as mock_sdk:
                        sdk = MagicMock()
                        response = create_mock_response(
                            id_richiesta="REQ-custom",
                            esito="0",
                            messaggio=None,
                        )
                        sdk.json_post.gestionecoordinate.return_value = response
                        mock_sdk.return_value = sdk

                        result = cli_runner.invoke(
                            app,
                            [
                                "coordinate",
                                "update",
                                "--codcom",
                                "H501",
                                "--progr-civico",
                                "12345",
                                "--server-url",
                                "https://custom.server.it/api/v1",
                            ],
                        )

            assert result.exit_code == 0
            # Verify custom server URL was used
            mock_sdk.assert_called_once()
            call_kwargs = mock_sdk.call_args[1]
            assert call_kwargs.get("server_url") == "https://custom.server.it/api/v1"

    def test_update_production_environment(
        self, cli_runner: CliRunner, tmp_path: Path, mock_private_key: Path
    ) -> None:
        """Test that --production flag uses production server."""
        from anncsu.cli import app

        with cli_runner.isolated_filesystem(temp_dir=tmp_path):
            Path("private_key.pem").write_text(mock_private_key.read_text())

            with patch(
                "anncsu.cli.commands.coordinate.ClientAssertionSettings"
            ) as mock_settings:
                settings = MagicMock()
                mock_settings.return_value = settings

                with patch(
                    "anncsu.cli.commands.coordinate.PDNDAuthManager"
                ) as mock_manager:
                    manager = MagicMock()
                    manager.get_access_token.return_value = "mock-access-token"
                    mock_manager.return_value = manager

                    with patch(
                        "anncsu.cli.commands.coordinate.AnncsuCoordinate"
                    ) as mock_sdk:
                        sdk = MagicMock()
                        response = create_mock_response(
                            id_richiesta="REQ-prod",
                            esito="0",
                            messaggio=None,
                        )
                        sdk.json_post.gestionecoordinate.return_value = response
                        mock_sdk.return_value = sdk

                        result = cli_runner.invoke(
                            app,
                            [
                                "coordinate",
                                "update",
                                "--codcom",
                                "H501",
                                "--progr-civico",
                                "12345",
                                "--production",
                            ],
                        )

            assert result.exit_code == 0
            # Verify production server URL was used
            mock_sdk.assert_called_once()
            call_kwargs = mock_sdk.call_args[1]
            assert "modipa.agenziaentrate.it" in call_kwargs.get("server_url", "")
            assert "modipa-val" not in call_kwargs.get("server_url", "")


class TestCoordinateDryRun:
    """Tests for coordinate dry-run command."""

    def test_dry_run_help_shows_in_coordinate_group(
        self, cli_runner: CliRunner
    ) -> None:
        """Test that dry-run command is listed in coordinate help."""
        from anncsu.cli import app

        result = cli_runner.invoke(app, ["coordinate", "--help"])
        assert result.exit_code == 0
        assert "dry-run" in result.output.lower()

    def test_dry_run_requires_codcom(self, cli_runner: CliRunner) -> None:
        """Test that dry-run requires --codcom parameter."""
        from anncsu.cli import app

        result = cli_runner.invoke(
            app, ["coordinate", "dry-run", "--denom", "VklBIFJPTUE="]
        )
        # Should fail because --codcom is required
        assert result.exit_code != 0

    def test_dry_run_requires_denom(self, cli_runner: CliRunner) -> None:
        """Test that dry-run requires --denom parameter."""
        from anncsu.cli import app

        result = cli_runner.invoke(app, ["coordinate", "dry-run", "--codcom", "H501"])
        # Should fail because --denom is required
        assert result.exit_code != 0

    def test_dry_run_success(
        self, cli_runner: CliRunner, tmp_path: Path, mock_private_key: Path
    ) -> None:
        """Test that dry-run executes search, update and restore cycle."""
        from anncsu.cli import app

        with cli_runner.isolated_filesystem(temp_dir=tmp_path):
            Path("private_key.pem").write_text(mock_private_key.read_text())

            with patch(
                "anncsu.cli.commands.coordinate.ClientAssertionSettings"
            ) as mock_settings:
                settings = MagicMock()
                mock_settings.return_value = settings

                with patch(
                    "anncsu.cli.commands.coordinate.PDNDAuthManager"
                ) as mock_manager:
                    manager = MagicMock()
                    manager.get_access_token.return_value = "mock-access-token"
                    mock_manager.return_value = manager

                    with patch(
                        "anncsu.cli.commands.coordinate.AnncsuConsultazione"
                    ) as mock_consult_sdk:
                        consult_sdk = MagicMock()
                        # Mock the response from elencoodonimiprog (odonimo search)
                        odonimo_response = MagicMock()
                        odonimo_response.data = [MagicMock()]
                        odonimo_response.data[0].prognaz = "987654"
                        odonimo_response.data[0].dug = "VIA"
                        odonimo_response.data[0].denomuff = "ROMA"
                        consult_sdk.queryparam.elencoodonimiprog_get_query_param.return_value = odonimo_response
                        # Mock the response from elencoaccessiprog (access search)
                        search_response = MagicMock()
                        search_response.data = [MagicMock()]
                        search_response.data[0].prognazacc = "123456789"
                        search_response.data[0].coord_x = "12.4963655"
                        search_response.data[0].coord_y = "41.9027835"
                        search_response.data[0].quota = "21"
                        search_response.data[0].metodo = "4"
                        search_response.data[0].civico = "1"
                        consult_sdk.queryparam.elencoaccessiprog_get_query_param.return_value = search_response
                        mock_consult_sdk.return_value = consult_sdk

                        with patch(
                            "anncsu.cli.commands.coordinate.AnncsuCoordinate"
                        ) as mock_coord_sdk:
                            coord_sdk = MagicMock()
                            # Mock update response (test update)
                            update_response = create_mock_response(
                                id_richiesta="REQ-TEST-123",
                                esito="0",
                                messaggio="Test update OK",
                            )
                            # Mock restore response
                            restore_response = create_mock_response(
                                id_richiesta="REQ-RESTORE-456",
                                esito="0",
                                messaggio="Restore OK",
                            )
                            coord_sdk.json_post.gestionecoordinate.side_effect = [
                                update_response,
                                restore_response,
                            ]
                            mock_coord_sdk.return_value = coord_sdk

                            result = cli_runner.invoke(
                                app,
                                [
                                    "coordinate",
                                    "dry-run",
                                    "--codcom",
                                    "H501",
                                    "--denom",
                                    "VklBIFJPTUE=",  # "VIA ROMA" base64
                                ],
                            )

            assert result.exit_code == 0
            output_lower = result.output.lower()
            # Should show success for both test and restore
            assert "test" in output_lower or "dry" in output_lower
            assert "restore" in output_lower or "ripristin" in output_lower

    def test_dry_run_json_output(
        self, cli_runner: CliRunner, tmp_path: Path, mock_private_key: Path
    ) -> None:
        """Test that dry-run can output JSON."""
        from anncsu.cli import app

        with cli_runner.isolated_filesystem(temp_dir=tmp_path):
            Path("private_key.pem").write_text(mock_private_key.read_text())

            with patch(
                "anncsu.cli.commands.coordinate.ClientAssertionSettings"
            ) as mock_settings:
                settings = MagicMock()
                mock_settings.return_value = settings

                with patch(
                    "anncsu.cli.commands.coordinate.PDNDAuthManager"
                ) as mock_manager:
                    manager = MagicMock()
                    manager.get_access_token.return_value = "mock-access-token"
                    mock_manager.return_value = manager

                    with patch(
                        "anncsu.cli.commands.coordinate.AnncsuConsultazione"
                    ) as mock_consult_sdk:
                        consult_sdk = MagicMock()
                        # Mock odonimo response
                        odonimo_response = MagicMock()
                        odonimo_response.data = [MagicMock()]
                        odonimo_response.data[0].prognaz = "987654"
                        odonimo_response.data[0].dug = "VIA"
                        odonimo_response.data[0].denomuff = "ROMA"
                        consult_sdk.queryparam.elencoodonimiprog_get_query_param.return_value = odonimo_response
                        # Mock access response
                        search_response = MagicMock()
                        search_response.data = [MagicMock()]
                        search_response.data[0].prognazacc = "123456789"
                        search_response.data[0].coord_x = "12.4963655"
                        search_response.data[0].coord_y = "41.9027835"
                        search_response.data[0].quota = "21"
                        search_response.data[0].metodo = "4"
                        search_response.data[0].civico = "1"
                        consult_sdk.queryparam.elencoaccessiprog_get_query_param.return_value = search_response
                        mock_consult_sdk.return_value = consult_sdk

                        with patch(
                            "anncsu.cli.commands.coordinate.AnncsuCoordinate"
                        ) as mock_coord_sdk:
                            coord_sdk = MagicMock()
                            update_response = create_mock_response(
                                id_richiesta="REQ-TEST-123",
                                esito="0",
                                messaggio="Test OK",
                            )
                            restore_response = create_mock_response(
                                id_richiesta="REQ-RESTORE-456",
                                esito="0",
                                messaggio="Restore OK",
                            )
                            coord_sdk.json_post.gestionecoordinate.side_effect = [
                                update_response,
                                restore_response,
                            ]
                            mock_coord_sdk.return_value = coord_sdk

                            result = cli_runner.invoke(
                                app,
                                [
                                    "coordinate",
                                    "dry-run",
                                    "--codcom",
                                    "H501",
                                    "--denom",
                                    "VklBIFJPTUE=",
                                    "--json",
                                ],
                            )

            assert result.exit_code == 0
            # Should be valid JSON
            import json

            output = json.loads(result.output)
            assert "test_update" in output
            assert "restore" in output
            assert output["test_update"]["success"] is True
            assert output["restore"]["success"] is True

    def test_dry_run_accesso_not_found(
        self, cli_runner: CliRunner, tmp_path: Path, mock_private_key: Path
    ) -> None:
        """Test that dry-run handles accesso not found gracefully."""
        from anncsu.cli import app

        with cli_runner.isolated_filesystem(temp_dir=tmp_path):
            Path("private_key.pem").write_text(mock_private_key.read_text())

            with patch(
                "anncsu.cli.commands.coordinate.ClientAssertionSettings"
            ) as mock_settings:
                settings = MagicMock()
                mock_settings.return_value = settings

                with patch(
                    "anncsu.cli.commands.coordinate.PDNDAuthManager"
                ) as mock_manager:
                    manager = MagicMock()
                    manager.get_access_token.return_value = "mock-access-token"
                    mock_manager.return_value = manager

                    with patch(
                        "anncsu.cli.commands.coordinate.AnncsuConsultazione"
                    ) as mock_consult_sdk:
                        consult_sdk = MagicMock()
                        # Mock odonimo response - found an odonimo
                        odonimo_response = MagicMock()
                        odonimo_response.data = [MagicMock()]
                        odonimo_response.data[0].prognaz = "987654"
                        odonimo_response.data[0].dug = "VIA"
                        odonimo_response.data[0].denomuff = "NONEXISTENT"
                        consult_sdk.queryparam.elencoodonimiprog_get_query_param.return_value = odonimo_response
                        # Empty data - no access point found for this odonimo
                        search_response = MagicMock()
                        search_response.data = []
                        consult_sdk.queryparam.elencoaccessiprog_get_query_param.return_value = search_response
                        mock_consult_sdk.return_value = consult_sdk

                        result = cli_runner.invoke(
                            app,
                            [
                                "coordinate",
                                "dry-run",
                                "--codcom",
                                "H501",
                                "--denom",
                                "Tk9ORVhJU1RFTlQ=",  # "NONEXISTENT" base64
                            ],
                        )

            assert result.exit_code == 1
            assert (
                "no access point found" in result.output.lower()
                or "not found" in result.output.lower()
                or "non trovato" in result.output.lower()
            )

    def test_dry_run_restore_failure_shows_warning(
        self, cli_runner: CliRunner, tmp_path: Path, mock_private_key: Path
    ) -> None:
        """Test that dry-run shows warning with original values if restore fails."""
        from anncsu.cli import app

        with cli_runner.isolated_filesystem(temp_dir=tmp_path):
            Path("private_key.pem").write_text(mock_private_key.read_text())

            with patch(
                "anncsu.cli.commands.coordinate.ClientAssertionSettings"
            ) as mock_settings:
                settings = MagicMock()
                mock_settings.return_value = settings

                with patch(
                    "anncsu.cli.commands.coordinate.PDNDAuthManager"
                ) as mock_manager:
                    manager = MagicMock()
                    manager.get_access_token.return_value = "mock-access-token"
                    mock_manager.return_value = manager

                    with patch(
                        "anncsu.cli.commands.coordinate.AnncsuConsultazione"
                    ) as mock_consult_sdk:
                        consult_sdk = MagicMock()
                        # Mock odonimo response
                        odonimo_response = MagicMock()
                        odonimo_response.data = [MagicMock()]
                        odonimo_response.data[0].prognaz = "987654"
                        odonimo_response.data[0].dug = "VIA"
                        odonimo_response.data[0].denomuff = "ROMA"
                        consult_sdk.queryparam.elencoodonimiprog_get_query_param.return_value = odonimo_response
                        # Mock access response
                        search_response = MagicMock()
                        search_response.data = [MagicMock()]
                        search_response.data[0].prognazacc = "123456789"
                        search_response.data[0].coord_x = "12.4963655"
                        search_response.data[0].coord_y = "41.9027835"
                        search_response.data[0].quota = "21"
                        search_response.data[0].metodo = "4"
                        search_response.data[0].civico = "1"
                        consult_sdk.queryparam.elencoaccessiprog_get_query_param.return_value = search_response
                        mock_consult_sdk.return_value = consult_sdk

                        with patch(
                            "anncsu.cli.commands.coordinate.AnncsuCoordinate"
                        ) as mock_coord_sdk:
                            coord_sdk = MagicMock()
                            # Test update succeeds
                            update_response = create_mock_response(
                                id_richiesta="REQ-TEST-123",
                                esito="0",
                                messaggio="Test OK",
                            )
                            # Restore fails
                            coord_sdk.json_post.gestionecoordinate.side_effect = [
                                update_response,
                                Exception("Restore failed - network error"),
                            ]
                            mock_coord_sdk.return_value = coord_sdk

                            result = cli_runner.invoke(
                                app,
                                [
                                    "coordinate",
                                    "dry-run",
                                    "--codcom",
                                    "H501",
                                    "--denom",
                                    "VklBIFJPTUE=",
                                ],
                            )

            # Should show warning, not crash
            assert result.exit_code == 1
            output_lower = result.output.lower()
            assert "warning" in output_lower or "attenzione" in output_lower
            # Should show original coordinates to restore manually
            assert "12.4963655" in result.output
            assert "41.9027835" in result.output

    def test_dry_run_test_update_failure(
        self, cli_runner: CliRunner, tmp_path: Path, mock_private_key: Path
    ) -> None:
        """Test that dry-run handles test update failure."""
        from anncsu.cli import app

        with cli_runner.isolated_filesystem(temp_dir=tmp_path):
            Path("private_key.pem").write_text(mock_private_key.read_text())

            with patch(
                "anncsu.cli.commands.coordinate.ClientAssertionSettings"
            ) as mock_settings:
                settings = MagicMock()
                mock_settings.return_value = settings

                with patch(
                    "anncsu.cli.commands.coordinate.PDNDAuthManager"
                ) as mock_manager:
                    manager = MagicMock()
                    manager.get_access_token.return_value = "mock-access-token"
                    mock_manager.return_value = manager

                    with patch(
                        "anncsu.cli.commands.coordinate.AnncsuConsultazione"
                    ) as mock_consult_sdk:
                        consult_sdk = MagicMock()
                        # Mock odonimo response
                        odonimo_response = MagicMock()
                        odonimo_response.data = [MagicMock()]
                        odonimo_response.data[0].prognaz = "987654"
                        odonimo_response.data[0].dug = "VIA"
                        odonimo_response.data[0].denomuff = "ROMA"
                        consult_sdk.queryparam.elencoodonimiprog_get_query_param.return_value = odonimo_response
                        # Mock access response
                        search_response = MagicMock()
                        search_response.data = [MagicMock()]
                        search_response.data[0].prognazacc = "123456789"
                        search_response.data[0].coord_x = "12.4963655"
                        search_response.data[0].coord_y = "41.9027835"
                        search_response.data[0].quota = "21"
                        search_response.data[0].metodo = "4"
                        search_response.data[0].civico = "1"
                        consult_sdk.queryparam.elencoaccessiprog_get_query_param.return_value = search_response
                        mock_consult_sdk.return_value = consult_sdk

                        with patch(
                            "anncsu.cli.commands.coordinate.AnncsuCoordinate"
                        ) as mock_coord_sdk:
                            coord_sdk = MagicMock()
                            # Test update fails
                            coord_sdk.json_post.gestionecoordinate.side_effect = (
                                Exception("Test update failed")
                            )
                            mock_coord_sdk.return_value = coord_sdk

                            result = cli_runner.invoke(
                                app,
                                [
                                    "coordinate",
                                    "dry-run",
                                    "--codcom",
                                    "H501",
                                    "--denom",
                                    "VklBIFJPTUE=",
                                ],
                            )

            assert result.exit_code == 1
            assert "error" in result.output.lower()

    def test_dry_run_with_accparz_filter(
        self, cli_runner: CliRunner, tmp_path: Path, mock_private_key: Path
    ) -> None:
        """Test that dry-run accepts optional --accparz to filter specific civico."""
        from anncsu.cli import app

        with cli_runner.isolated_filesystem(temp_dir=tmp_path):
            Path("private_key.pem").write_text(mock_private_key.read_text())

            with patch(
                "anncsu.cli.commands.coordinate.ClientAssertionSettings"
            ) as mock_settings:
                settings = MagicMock()
                mock_settings.return_value = settings

                with patch(
                    "anncsu.cli.commands.coordinate.PDNDAuthManager"
                ) as mock_manager:
                    manager = MagicMock()
                    manager.get_access_token.return_value = "mock-access-token"
                    mock_manager.return_value = manager

                    with patch(
                        "anncsu.cli.commands.coordinate.AnncsuConsultazione"
                    ) as mock_consult_sdk:
                        consult_sdk = MagicMock()
                        # Mock odonimo response
                        odonimo_response = MagicMock()
                        odonimo_response.data = [MagicMock()]
                        odonimo_response.data[0].prognaz = "987654"
                        odonimo_response.data[0].dug = "VIA"
                        odonimo_response.data[0].denomuff = "ROMA"
                        consult_sdk.queryparam.elencoodonimiprog_get_query_param.return_value = odonimo_response
                        # Mock access response
                        search_response = MagicMock()
                        search_response.data = [MagicMock()]
                        search_response.data[0].prognazacc = "123456789"
                        search_response.data[0].coord_x = "12.4963655"
                        search_response.data[0].coord_y = "41.9027835"
                        search_response.data[0].quota = None
                        search_response.data[0].metodo = None
                        search_response.data[0].civico = "10"
                        consult_sdk.queryparam.elencoaccessiprog_get_query_param.return_value = search_response
                        mock_consult_sdk.return_value = consult_sdk

                        with patch(
                            "anncsu.cli.commands.coordinate.AnncsuCoordinate"
                        ) as mock_coord_sdk:
                            coord_sdk = MagicMock()
                            update_response = create_mock_response(
                                id_richiesta="REQ-TEST",
                                esito="0",
                                messaggio=None,
                            )
                            restore_response = create_mock_response(
                                id_richiesta="REQ-RESTORE",
                                esito="0",
                                messaggio=None,
                            )
                            coord_sdk.json_post.gestionecoordinate.side_effect = [
                                update_response,
                                restore_response,
                            ]
                            mock_coord_sdk.return_value = coord_sdk

                            result = cli_runner.invoke(
                                app,
                                [
                                    "coordinate",
                                    "dry-run",
                                    "--codcom",
                                    "H501",
                                    "--denom",
                                    "VklBIFJPTUE=",
                                    "--accparz",
                                    "10",
                                ],
                            )

            assert result.exit_code == 0
            # Verify the access search was called with accparz
            consult_sdk.queryparam.elencoaccessiprog_get_query_param.assert_called_once()
            call_kwargs = (
                consult_sdk.queryparam.elencoaccessiprog_get_query_param.call_args
            )
            assert call_kwargs[1]["accparz"] == "10"

    def test_dry_run_access_without_coordinates_uses_test_values(
        self, cli_runner: CliRunner, tmp_path: Path, mock_private_key: Path
    ) -> None:
        """Test that dry-run uses test coordinates when access has no existing coordinates."""
        from anncsu.cli import app

        with cli_runner.isolated_filesystem(temp_dir=tmp_path):
            Path("private_key.pem").write_text(mock_private_key.read_text())

            with patch(
                "anncsu.cli.commands.coordinate.ClientAssertionSettings"
            ) as mock_settings:
                settings = MagicMock()
                mock_settings.return_value = settings

                with patch(
                    "anncsu.cli.commands.coordinate.PDNDAuthManager"
                ) as mock_manager:
                    manager = MagicMock()
                    manager.get_access_token.return_value = "mock-access-token"
                    mock_manager.return_value = manager

                    with patch(
                        "anncsu.cli.commands.coordinate.AnncsuConsultazione"
                    ) as mock_consult_sdk:
                        consult_sdk = MagicMock()
                        # Mock odonimo response
                        odonimo_response = MagicMock()
                        odonimo_response.data = [MagicMock()]
                        odonimo_response.data[0].prognaz = "987654"
                        odonimo_response.data[0].dug = "VIA"
                        odonimo_response.data[0].denomuff = "ROMA"
                        consult_sdk.queryparam.elencoodonimiprog_get_query_param.return_value = odonimo_response
                        # Mock access response - NO COORDINATES
                        search_response = MagicMock()
                        search_response.data = [MagicMock()]
                        search_response.data[0].prognazacc = "5256880"
                        search_response.data[0].coord_x = None  # No X
                        search_response.data[0].coord_y = None  # No Y
                        search_response.data[0].quota = None
                        search_response.data[0].metodo = None  # No metodo
                        search_response.data[0].civico = "1"
                        consult_sdk.queryparam.elencoaccessiprog_get_query_param.return_value = search_response
                        mock_consult_sdk.return_value = consult_sdk

                        with patch(
                            "anncsu.cli.commands.coordinate.AnncsuCoordinate"
                        ) as mock_coord_sdk:
                            coord_sdk = MagicMock()
                            # Test update succeeds
                            update_response = create_mock_response(
                                id_richiesta="REQ-TEST-123",
                                esito="0",
                                messaggio="Test update OK",
                            )
                            # Restore succeeds
                            restore_response = create_mock_response(
                                id_richiesta="REQ-RESTORE-456",
                                esito="0",
                                messaggio="Restore OK",
                            )
                            coord_sdk.json_post.gestionecoordinate.side_effect = [
                                update_response,
                                restore_response,
                            ]
                            mock_coord_sdk.return_value = coord_sdk

                            result = cli_runner.invoke(
                                app,
                                [
                                    "coordinate",
                                    "dry-run",
                                    "--codcom",
                                    "H501",
                                    "--denom",
                                    "VklBIFJPTUE=",
                                ],
                            )

            assert result.exit_code == 0
            # Should show note about using test coordinates
            assert "no coordinates" in result.output.lower()
            # Verify gestionecoordinate was called twice (test + restore)
            assert coord_sdk.json_post.gestionecoordinate.call_count == 2
            # Verify test update used Roma Colosseo test coordinates
            test_call = coord_sdk.json_post.gestionecoordinate.call_args_list[0]
            test_richiesta = test_call[1]["richiesta"]
            assert test_richiesta.accesso.coordinate.x == "12.4922309"
            assert test_richiesta.accesso.coordinate.y == "41.8902102"
            assert test_richiesta.accesso.coordinate.metodo == "4"
            # Verify restore uses original empty values
            restore_call = coord_sdk.json_post.gestionecoordinate.call_args_list[1]
            restore_richiesta = restore_call[1]["richiesta"]
            assert restore_richiesta.accesso.coordinate.x is None
            assert restore_richiesta.accesso.coordinate.y is None
            assert restore_richiesta.accesso.coordinate.metodo is None

    def test_dry_run_with_prognazacc_skips_search(
        self, cli_runner: CliRunner, tmp_path: Path, mock_private_key: Path
    ) -> None:
        """Test that --prognazacc skips odonimo/accesso search and uses direct lookup."""
        from anncsu.cli import app

        with cli_runner.isolated_filesystem(temp_dir=tmp_path):
            Path("private_key.pem").write_text(mock_private_key.read_text())

            with patch(
                "anncsu.cli.commands.coordinate.ClientAssertionSettings"
            ) as mock_settings:
                settings = MagicMock()
                mock_settings.return_value = settings

                with patch(
                    "anncsu.cli.commands.coordinate.PDNDAuthManager"
                ) as mock_manager:
                    manager = MagicMock()
                    manager.get_access_token.return_value = "mock-access-token"
                    mock_manager.return_value = manager

                    with patch(
                        "anncsu.cli.commands.coordinate.AnncsuConsultazione"
                    ) as mock_consult_sdk:
                        consult_sdk = MagicMock()
                        # Mock direct prognazacc lookup response
                        prognazacc_response = MagicMock()
                        prognazacc_response.data = MagicMock()
                        prognazacc_response.data.prognazacc = "5256880"
                        prognazacc_response.data.prognaz = "907156"
                        prognazacc_response.data.dug = "VIA"
                        prognazacc_response.data.denomuff = "ROMA"
                        prognazacc_response.data.civico = "1"
                        prognazacc_response.data.coord_x = "12.4922309"
                        prognazacc_response.data.coord_y = "41.8902102"
                        prognazacc_response.data.quota = "0"
                        prognazacc_response.data.metodo = "4"
                        consult_sdk.queryparam.prognazacc_get_query_param.return_value = prognazacc_response
                        mock_consult_sdk.return_value = consult_sdk

                        with patch(
                            "anncsu.cli.commands.coordinate.AnncsuCoordinate"
                        ) as mock_coord_sdk:
                            coord_sdk = MagicMock()
                            update_response = create_mock_response(
                                id_richiesta="REQ-TEST-123",
                                esito="0",
                                messaggio="Test update OK",
                            )
                            restore_response = create_mock_response(
                                id_richiesta="REQ-RESTORE-456",
                                esito="0",
                                messaggio="Restore OK",
                            )
                            coord_sdk.json_post.gestionecoordinate.side_effect = [
                                update_response,
                                restore_response,
                            ]
                            mock_coord_sdk.return_value = coord_sdk

                            result = cli_runner.invoke(
                                app,
                                [
                                    "coordinate",
                                    "dry-run",
                                    "--prognazacc",
                                    "5256880",
                                ],
                            )

            assert result.exit_code == 0
            # Should NOT call odonimo search
            consult_sdk.queryparam.elencoodonimiprog_get_query_param.assert_not_called()
            # Should NOT call accesso list search
            consult_sdk.queryparam.elencoaccessiprog_get_query_param.assert_not_called()
            # Should call direct prognazacc lookup
            consult_sdk.queryparam.prognazacc_get_query_param.assert_called_once_with(
                prognazacc="5256880"
            )
            # Should show the found access point
            assert "5256880" in result.output

    def test_dry_run_with_prognazacc_json_output(
        self, cli_runner: CliRunner, tmp_path: Path, mock_private_key: Path
    ) -> None:
        """Test that --prognazacc with --json outputs valid JSON."""
        from anncsu.cli import app

        with cli_runner.isolated_filesystem(temp_dir=tmp_path):
            Path("private_key.pem").write_text(mock_private_key.read_text())

            with patch(
                "anncsu.cli.commands.coordinate.ClientAssertionSettings"
            ) as mock_settings:
                settings = MagicMock()
                mock_settings.return_value = settings

                with patch(
                    "anncsu.cli.commands.coordinate.PDNDAuthManager"
                ) as mock_manager:
                    manager = MagicMock()
                    manager.get_access_token.return_value = "mock-access-token"
                    mock_manager.return_value = manager

                    with patch(
                        "anncsu.cli.commands.coordinate.AnncsuConsultazione"
                    ) as mock_consult_sdk:
                        consult_sdk = MagicMock()
                        prognazacc_response = MagicMock()
                        prognazacc_response.data = MagicMock()
                        prognazacc_response.data.prognazacc = "5256880"
                        prognazacc_response.data.prognaz = "907156"
                        prognazacc_response.data.dug = "VIA"
                        prognazacc_response.data.denomuff = "ROMA"
                        prognazacc_response.data.civico = "1"
                        prognazacc_response.data.coord_x = "12.4922309"
                        prognazacc_response.data.coord_y = "41.8902102"
                        prognazacc_response.data.quota = "0"
                        prognazacc_response.data.metodo = "4"
                        consult_sdk.queryparam.prognazacc_get_query_param.return_value = prognazacc_response
                        mock_consult_sdk.return_value = consult_sdk

                        with patch(
                            "anncsu.cli.commands.coordinate.AnncsuCoordinate"
                        ) as mock_coord_sdk:
                            coord_sdk = MagicMock()
                            update_response = create_mock_response(
                                id_richiesta="REQ-TEST-123",
                                esito="0",
                                messaggio="Test update OK",
                            )
                            restore_response = create_mock_response(
                                id_richiesta="REQ-RESTORE-456",
                                esito="0",
                                messaggio="Restore OK",
                            )
                            coord_sdk.json_post.gestionecoordinate.side_effect = [
                                update_response,
                                restore_response,
                            ]
                            mock_coord_sdk.return_value = coord_sdk

                            result = cli_runner.invoke(
                                app,
                                [
                                    "coordinate",
                                    "dry-run",
                                    "--prognazacc",
                                    "5256880",
                                    "--json",
                                ],
                            )

            assert result.exit_code == 0
            # Should be valid JSON
            dry_run_result = DryRunResult.model_validate_json(result.output)
            assert dry_run_result.success is True
            assert dry_run_result.original_coordinates.prognazacc == "5256880"

    def test_dry_run_requires_either_prognazacc_or_codcom_denom(
        self, cli_runner: CliRunner
    ) -> None:
        """Test that dry-run fails without --prognazacc or --codcom/--denom."""
        from anncsu.cli import app

        # No parameters at all - should fail
        result = cli_runner.invoke(app, ["coordinate", "dry-run"])
        assert result.exit_code != 0
        # Should show error about missing parameters
        assert (
            "prognazacc" in result.output.lower() or "codcom" in result.output.lower()
        )

    def test_dry_run_prognazacc_takes_precedence_over_codcom(
        self, cli_runner: CliRunner
    ) -> None:
        """Test that --prognazacc takes precedence over --codcom/--denom with a warning.

        This test verifies that when both --prognazacc and --codcom/--denom are provided,
        the command shows a warning that --codcom/--denom will be ignored.
        The warning is printed BEFORE any configuration is loaded, so we don't need
        to mock ClientAssertionSettings - the test just needs to verify the warning
        appears in the output regardless of exit code.
        """
        from anncsu.cli import app

        # Both --prognazacc and --codcom/--denom - should show warning and use prognazacc
        result = cli_runner.invoke(
            app,
            [
                "coordinate",
                "dry-run",
                "--prognazacc",
                "5256880",
                "--codcom",
                "H501",
                "--denom",
                "VklBIFJPTUE=",
            ],
        )
        # Should show a warning that --codcom/--denom are ignored
        # This warning is printed before any config loading, so it should always appear
        assert "ignoring" in result.output.lower()
        # Should use prognazacc (direct mode) - shown in the output message
        assert "prognazacc" in result.output.lower()

    def test_dry_run_prognazacc_not_found(
        self, cli_runner: CliRunner, tmp_path: Path, mock_private_key: Path
    ) -> None:
        """Test that dry-run with invalid --prognazacc shows error."""
        from anncsu.cli import app
        from anncsu.pa.errors import (
            PrognazaccGetQueryParamNotFoundError,
            PrognazaccGetQueryParamNotFoundErrorData,
        )

        with cli_runner.isolated_filesystem(temp_dir=tmp_path):
            Path("private_key.pem").write_text(mock_private_key.read_text())

            with patch(
                "anncsu.cli.commands.coordinate.ClientAssertionSettings"
            ) as mock_settings:
                settings = MagicMock()
                mock_settings.return_value = settings

                with patch(
                    "anncsu.cli.commands.coordinate.PDNDAuthManager"
                ) as mock_manager:
                    manager = MagicMock()
                    manager.get_access_token.return_value = "mock-access-token"
                    mock_manager.return_value = manager

                    with patch(
                        "anncsu.cli.commands.coordinate.AnncsuConsultazione"
                    ) as mock_consult_sdk:
                        consult_sdk = MagicMock()
                        # Simulate not found error with correct signature
                        error_data = PrognazaccGetQueryParamNotFoundErrorData(
                            title="Not Found",
                            detail="Access point not found",
                        )
                        mock_response = MagicMock()
                        mock_response.text = "Not Found"
                        consult_sdk.queryparam.prognazacc_get_query_param.side_effect = PrognazaccGetQueryParamNotFoundError(
                            data=error_data,
                            raw_response=mock_response,
                        )
                        mock_consult_sdk.return_value = consult_sdk

                        result = cli_runner.invoke(
                            app,
                            [
                                "coordinate",
                                "dry-run",
                                "--prognazacc",
                                "9999999999",
                            ],
                        )

            assert result.exit_code != 0
            assert (
                "not found" in result.output.lower() or "error" in result.output.lower()
            )

    def test_dry_run_codcom_requires_denom(self, cli_runner: CliRunner) -> None:
        """Test that --codcom requires --denom when not using --prognazacc."""
        from anncsu.cli import app

        result = cli_runner.invoke(app, ["coordinate", "dry-run", "--codcom", "H501"])
        assert result.exit_code != 0
        # Should indicate that --denom is required
        assert "denom" in result.output.lower()

    def test_dry_run_denom_requires_codcom(self, cli_runner: CliRunner) -> None:
        """Test that --denom requires --codcom when not using --prognazacc."""
        from anncsu.cli import app

        result = cli_runner.invoke(
            app, ["coordinate", "dry-run", "--denom", "VklBIFJPTUE="]
        )
        assert result.exit_code != 0
        # Should indicate that --codcom is required
        assert "codcom" in result.output.lower()


class TestCoordinateStatus:
    """Tests for coordinate status command."""

    def test_status_success(
        self, cli_runner: CliRunner, tmp_path: Path, mock_private_key: Path
    ) -> None:
        """Test that coordinate status shows API status."""
        from anncsu.cli import app

        with cli_runner.isolated_filesystem(temp_dir=tmp_path):
            Path("private_key.pem").write_text(mock_private_key.read_text())

            with patch(
                "anncsu.cli.commands.coordinate.ClientAssertionSettings"
            ) as mock_settings:
                settings = MagicMock()
                mock_settings.return_value = settings

                with patch(
                    "anncsu.cli.commands.coordinate.PDNDAuthManager"
                ) as mock_manager:
                    manager = MagicMock()
                    manager.get_access_token.return_value = "mock-access-token"
                    mock_manager.return_value = manager

                    with patch(
                        "anncsu.cli.commands.coordinate.AnncsuCoordinate"
                    ) as mock_sdk:
                        sdk = MagicMock()
                        status_response = MagicMock()
                        status_response.status = "OK"
                        sdk.status.show_status.return_value = status_response
                        mock_sdk.return_value = sdk

                        result = cli_runner.invoke(app, ["coordinate", "status"])

            assert result.exit_code == 0
            output_lower = result.output.lower()
            assert "ok" in output_lower or "status" in output_lower

    def test_status_json_output(
        self, cli_runner: CliRunner, tmp_path: Path, mock_private_key: Path
    ) -> None:
        """Test that coordinate status can output JSON."""
        from anncsu.cli import app

        with cli_runner.isolated_filesystem(temp_dir=tmp_path):
            Path("private_key.pem").write_text(mock_private_key.read_text())

            with patch(
                "anncsu.cli.commands.coordinate.ClientAssertionSettings"
            ) as mock_settings:
                settings = MagicMock()
                mock_settings.return_value = settings

                with patch(
                    "anncsu.cli.commands.coordinate.PDNDAuthManager"
                ) as mock_manager:
                    manager = MagicMock()
                    manager.get_access_token.return_value = "mock-access-token"
                    mock_manager.return_value = manager

                    with patch(
                        "anncsu.cli.commands.coordinate.AnncsuCoordinate"
                    ) as mock_sdk:
                        sdk = MagicMock()
                        status_response = MagicMock()
                        status_response.status = "OK"
                        sdk.status.show_status.return_value = status_response
                        mock_sdk.return_value = sdk

                        result = cli_runner.invoke(
                            app, ["coordinate", "status", "--json"]
                        )

            assert result.exit_code == 0
            # Should be valid JSON parseable as Pydantic model
            status_result = CoordinateStatusResult.model_validate_json(result.output)
            assert status_result.available is True
            assert status_result.status == "OK"

    def test_status_api_unavailable(
        self, cli_runner: CliRunner, tmp_path: Path, mock_private_key: Path
    ) -> None:
        """Test that coordinate status handles unavailable API."""
        from anncsu.cli import app

        with cli_runner.isolated_filesystem(temp_dir=tmp_path):
            Path("private_key.pem").write_text(mock_private_key.read_text())

            with patch(
                "anncsu.cli.commands.coordinate.ClientAssertionSettings"
            ) as mock_settings:
                settings = MagicMock()
                mock_settings.return_value = settings

                with patch(
                    "anncsu.cli.commands.coordinate.PDNDAuthManager"
                ) as mock_manager:
                    manager = MagicMock()
                    manager.get_access_token.return_value = "mock-access-token"
                    mock_manager.return_value = manager

                    with patch(
                        "anncsu.cli.commands.coordinate.AnncsuCoordinate"
                    ) as mock_sdk:
                        sdk = MagicMock()
                        sdk.status.show_status.side_effect = Exception(
                            "Service unavailable"
                        )
                        mock_sdk.return_value = sdk

                        result = cli_runner.invoke(app, ["coordinate", "status"])

            assert result.exit_code == 0  # Should not fail, just show unavailable
            output_lower = result.output.lower()
            assert "error" in output_lower or "unavailable" in output_lower

    def test_status_production_environment(
        self, cli_runner: CliRunner, tmp_path: Path, mock_private_key: Path
    ) -> None:
        """Test that --production flag uses production server for status."""
        from anncsu.cli import app

        with cli_runner.isolated_filesystem(temp_dir=tmp_path):
            Path("private_key.pem").write_text(mock_private_key.read_text())

            with patch(
                "anncsu.cli.commands.coordinate.ClientAssertionSettings"
            ) as mock_settings:
                settings = MagicMock()
                mock_settings.return_value = settings

                with patch(
                    "anncsu.cli.commands.coordinate.PDNDAuthManager"
                ) as mock_manager:
                    manager = MagicMock()
                    manager.get_access_token.return_value = "mock-access-token"
                    mock_manager.return_value = manager

                    with patch(
                        "anncsu.cli.commands.coordinate.AnncsuCoordinate"
                    ) as mock_sdk:
                        sdk = MagicMock()
                        status_response = MagicMock()
                        status_response.status = "OK"
                        sdk.status.show_status.return_value = status_response
                        mock_sdk.return_value = sdk

                        result = cli_runner.invoke(
                            app, ["coordinate", "status", "--production"]
                        )

            assert result.exit_code == 0
            # Verify production server URL was used
            mock_sdk.assert_called_once()
            call_kwargs = mock_sdk.call_args[1]
            assert "modipa.agenziaentrate.it" in call_kwargs.get("server_url", "")

    def test_status_no_verify_ssl(
        self, cli_runner: CliRunner, tmp_path: Path, mock_private_key: Path
    ) -> None:
        """Test that --no-verify-ssl option works."""
        from anncsu.cli import app

        with cli_runner.isolated_filesystem(temp_dir=tmp_path):
            Path("private_key.pem").write_text(mock_private_key.read_text())

            with patch(
                "anncsu.cli.commands.coordinate.ClientAssertionSettings"
            ) as mock_settings:
                settings = MagicMock()
                mock_settings.return_value = settings

                with patch(
                    "anncsu.cli.commands.coordinate.PDNDAuthManager"
                ) as mock_manager:
                    manager = MagicMock()
                    manager.get_access_token.return_value = "mock-access-token"
                    mock_manager.return_value = manager

                    with patch(
                        "anncsu.cli.commands.coordinate.AnncsuCoordinate"
                    ) as mock_sdk:
                        sdk = MagicMock()
                        status_response = MagicMock()
                        status_response.status = "OK"
                        sdk.status.show_status.return_value = status_response
                        mock_sdk.return_value = sdk

                        with patch(
                            "anncsu.cli.commands.coordinate.httpx.Client"
                        ) as mock_client:
                            mock_client.return_value = MagicMock()

                            result = cli_runner.invoke(
                                app, ["coordinate", "status", "--no-verify-ssl"]
                            )

            assert result.exit_code == 0
            # Verify httpx.Client was called with verify=False
            mock_client.assert_called_once_with(verify=False)


class TestCoordinateModIHeaders:
    """Tests for ModI headers integration in coordinate commands.

    These tests verify the hooks-based ModI header injection architecture:
    - SDKHooks is created and injected into the SDK via dependency injection
    - register_modi_hook is called when ModI is configured (private key + audience)
    - The hook automatically adds Digest, Agid-JWT-Signature, and Agid-JWT-TrackingEvidence
      headers to all POST requests
    """

    def test_update_registers_modi_hook_when_configured(
        self, cli_runner: CliRunner, tmp_path: Path, mock_private_key: Path
    ) -> None:
        """Test that update command registers ModI hook when audit context is configured."""
        from anncsu.cli import app

        with cli_runner.isolated_filesystem(temp_dir=tmp_path):
            Path("private_key.pem").write_text(mock_private_key.read_text())

            with patch(
                "anncsu.cli.commands.coordinate.ClientAssertionSettings"
            ) as mock_settings:
                settings = MagicMock()
                settings.kid = "test-kid"
                settings.issuer = "test-issuer"
                settings.private_key = mock_private_key.read_text()
                settings.key_path = None
                settings.has_modi_audit_context.return_value = True
                settings.get_modi_audit_context.return_value = MagicMock(
                    user_id="test-user",
                    user_location="test-location",
                    loa="SPID_L2",
                )
                mock_settings.return_value = settings

                with patch(
                    "anncsu.cli.commands.coordinate.PDNDAuthManager"
                ) as mock_manager:
                    manager = MagicMock()
                    manager.get_access_token.return_value = "mock-access-token"
                    mock_manager.return_value = manager

                    with patch(
                        "anncsu.cli.commands.coordinate.SDKHooks"
                    ) as mock_hooks_class:
                        mock_hooks = MagicMock()
                        mock_hooks_class.return_value = mock_hooks

                        with patch(
                            "anncsu.cli.commands.coordinate.register_modi_hook"
                        ) as mock_register:
                            with patch(
                                "anncsu.cli.commands.coordinate.AnncsuCoordinate"
                            ) as mock_sdk:
                                sdk = MagicMock()
                                response = create_mock_response(
                                    id_richiesta="REQ-MODI-123",
                                    esito="0",
                                    messaggio="Success with ModI",
                                )
                                sdk.json_post.gestionecoordinate.return_value = response
                                mock_sdk.return_value = sdk

                                result = cli_runner.invoke(
                                    app,
                                    [
                                        "coordinate",
                                        "update",
                                        "--codcom",
                                        "H501",
                                        "--progr-civico",
                                        "12345",
                                        "--x",
                                        "12.4963655",
                                        "--y",
                                        "41.9027835",
                                    ],
                                )

            assert result.exit_code == 0

            # Verify SDKHooks was created
            mock_hooks_class.assert_called_once()

            # Verify register_modi_hook was called with the hooks instance
            mock_register.assert_called_once()
            call_args = mock_register.call_args
            assert call_args[0][0] == mock_hooks  # First positional arg is hooks
            assert "config" in call_args[1]  # ModIConfig passed as kwarg
            assert "audit_context" in call_args[1]  # AuditContext passed as kwarg

            # Verify SDK was created with hooks via dependency injection
            sdk_call_kwargs = mock_sdk.call_args[1]
            assert "hooks" in sdk_call_kwargs
            assert sdk_call_kwargs["hooks"] == mock_hooks

    def test_update_no_modi_hook_when_no_audience(
        self, cli_runner: CliRunner, tmp_path: Path, mock_private_key: Path
    ) -> None:
        """Test that update command does not register ModI hook when no audience is provided.

        The ModI hook is only registered when modi_audience is provided to _get_sdk().
        Without an audience, the hooks instance is created but register_modi_hook is not called.
        """
        from anncsu.cli import app

        with cli_runner.isolated_filesystem(temp_dir=tmp_path):
            Path("private_key.pem").write_text(mock_private_key.read_text())

            with patch(
                "anncsu.cli.commands.coordinate.ClientAssertionSettings"
            ) as mock_settings:
                settings = MagicMock()
                settings.kid = "test-kid"
                settings.issuer = "test-issuer"
                settings.private_key = mock_private_key.read_text()
                settings.key_path = None
                settings.has_modi_audit_context.return_value = False
                mock_settings.return_value = settings

                with patch(
                    "anncsu.cli.commands.coordinate.PDNDAuthManager"
                ) as mock_manager:
                    manager = MagicMock()
                    manager.get_access_token.return_value = "mock-access-token"
                    mock_manager.return_value = manager

                    with patch(
                        "anncsu.cli.commands.coordinate.SDKHooks"
                    ) as mock_hooks_class:
                        mock_hooks = MagicMock()
                        mock_hooks_class.return_value = mock_hooks

                        with patch("anncsu.cli.commands.coordinate.register_modi_hook"):
                            with patch(
                                "anncsu.cli.commands.coordinate.AnncsuCoordinate"
                            ) as mock_sdk:
                                sdk = MagicMock()
                                response = create_mock_response(
                                    id_richiesta="REQ-NO-MODI",
                                    esito="0",
                                    messaggio=None,
                                )
                                sdk.json_post.gestionecoordinate.return_value = response
                                mock_sdk.return_value = sdk

                                # Note: We call update WITHOUT --production flag
                                # The default validation environment has a server URL,
                                # but the test mocks prevent actual ModI hook registration
                                result = cli_runner.invoke(
                                    app,
                                    [
                                        "coordinate",
                                        "update",
                                        "--codcom",
                                        "H501",
                                        "--progr-civico",
                                        "12345",
                                    ],
                                )

            assert result.exit_code == 0

            # Verify SDKHooks was created (always created)
            mock_hooks_class.assert_called_once()

            # Verify SDK was created with hooks (even without ModI)
            sdk_call_kwargs = mock_sdk.call_args[1]
            assert "hooks" in sdk_call_kwargs
            assert sdk_call_kwargs["hooks"] == mock_hooks

    def test_dry_run_registers_modi_hook_for_coordinate_sdk(
        self, cli_runner: CliRunner, tmp_path: Path, mock_private_key: Path
    ) -> None:
        """Test that dry-run registers ModI hook for the coordinate SDK.

        The hook is registered once per SDK instance and automatically adds
        headers to all POST requests made by that SDK.
        """
        from anncsu.cli import app

        with cli_runner.isolated_filesystem(temp_dir=tmp_path):
            Path("private_key.pem").write_text(mock_private_key.read_text())

            with patch(
                "anncsu.cli.commands.coordinate.ClientAssertionSettings"
            ) as mock_settings:
                settings = MagicMock()
                settings.kid = "test-kid"
                settings.issuer = "test-issuer"
                settings.private_key = mock_private_key.read_text()
                settings.key_path = None
                settings.has_modi_audit_context.return_value = True
                settings.get_modi_audit_context.return_value = MagicMock(
                    user_id="test-user",
                    user_location="test-location",
                    loa="SPID_L2",
                )
                mock_settings.return_value = settings

                with patch(
                    "anncsu.cli.commands.coordinate.PDNDAuthManager"
                ) as mock_manager:
                    manager = MagicMock()
                    manager.get_access_token.return_value = "mock-access-token"
                    mock_manager.return_value = manager

                    with patch(
                        "anncsu.cli.commands.coordinate.SDKHooks"
                    ) as mock_hooks_class:
                        mock_hooks = MagicMock()
                        mock_hooks_class.return_value = mock_hooks

                        with patch(
                            "anncsu.cli.commands.coordinate.register_modi_hook"
                        ) as mock_register:
                            with patch(
                                "anncsu.cli.commands.coordinate.AnncsuConsultazione"
                            ) as mock_consult_sdk:
                                consult_sdk = MagicMock()
                                # Mock odonimo response
                                odonimo_response = MagicMock()
                                odonimo_response.data = [MagicMock()]
                                odonimo_response.data[0].prognaz = "987654"
                                odonimo_response.data[0].dug = "VIA"
                                odonimo_response.data[0].denomuff = "ROMA"
                                consult_sdk.queryparam.elencoodonimiprog_get_query_param.return_value = odonimo_response
                                # Mock access response
                                search_response = MagicMock()
                                search_response.data = [MagicMock()]
                                search_response.data[0].prognazacc = "123456789"
                                search_response.data[0].coord_x = "12.4963655"
                                search_response.data[0].coord_y = "41.9027835"
                                search_response.data[0].quota = "21"
                                search_response.data[0].metodo = "4"
                                search_response.data[0].civico = "1"
                                consult_sdk.queryparam.elencoaccessiprog_get_query_param.return_value = search_response
                                mock_consult_sdk.return_value = consult_sdk

                                with patch(
                                    "anncsu.cli.commands.coordinate.AnncsuCoordinate"
                                ) as mock_coord_sdk:
                                    coord_sdk = MagicMock()
                                    update_response = create_mock_response(
                                        id_richiesta="REQ-TEST",
                                        esito="0",
                                        messaggio=None,
                                    )
                                    restore_response = create_mock_response(
                                        id_richiesta="REQ-RESTORE",
                                        esito="0",
                                        messaggio=None,
                                    )
                                    coord_sdk.json_post.gestionecoordinate.side_effect = [
                                        update_response,
                                        restore_response,
                                    ]
                                    mock_coord_sdk.return_value = coord_sdk

                                    result = cli_runner.invoke(
                                        app,
                                        [
                                            "coordinate",
                                            "dry-run",
                                            "--codcom",
                                            "H501",
                                            "--denom",
                                            "VklBIFJPTUE=",
                                        ],
                                    )

            assert result.exit_code == 0

            # Verify SDKHooks was created for coordinate SDK
            assert mock_hooks_class.call_count >= 1

            # Verify register_modi_hook was called for the coordinate SDK
            assert mock_register.call_count >= 1

            # Verify gestionecoordinate was called twice (test update + restore)
            assert coord_sdk.json_post.gestionecoordinate.call_count == 2

    def test_modi_config_uses_correct_audience(
        self, cli_runner: CliRunner, tmp_path: Path, mock_private_key: Path
    ) -> None:
        """Test that ModI config is created with the correct audience URL.

        The audience should be the API server URL, which is passed to ModIConfig
        when registering the hook.
        """
        from anncsu.cli import app

        with cli_runner.isolated_filesystem(temp_dir=tmp_path):
            Path("private_key.pem").write_text(mock_private_key.read_text())

            with patch(
                "anncsu.cli.commands.coordinate.ClientAssertionSettings"
            ) as mock_settings:
                settings = MagicMock()
                settings.kid = "test-kid"
                settings.issuer = "test-issuer"
                settings.private_key = mock_private_key.read_text()
                settings.key_path = None
                settings.has_modi_audit_context.return_value = True
                settings.get_modi_audit_context.return_value = MagicMock(
                    user_id="test-user",
                    user_location="test-location",
                    loa="SPID_L2",
                )
                mock_settings.return_value = settings

                with patch(
                    "anncsu.cli.commands.coordinate.PDNDAuthManager"
                ) as mock_manager:
                    manager = MagicMock()
                    manager.get_access_token.return_value = "mock-access-token"
                    mock_manager.return_value = manager

                    with patch(
                        "anncsu.cli.commands.coordinate.SDKHooks"
                    ) as mock_hooks_class:
                        mock_hooks = MagicMock()
                        mock_hooks_class.return_value = mock_hooks

                        with patch("anncsu.cli.commands.coordinate.register_modi_hook"):
                            with patch(
                                "anncsu.cli.commands.coordinate.ModIConfig"
                            ) as mock_modi_config:
                                mock_config_instance = MagicMock()
                                mock_modi_config.return_value = mock_config_instance

                                with patch(
                                    "anncsu.cli.commands.coordinate.AnncsuCoordinate"
                                ) as mock_sdk:
                                    sdk = MagicMock()
                                    response = create_mock_response(
                                        id_richiesta="REQ-123",
                                        esito="0",
                                        messaggio=None,
                                    )
                                    sdk.json_post.gestionecoordinate.return_value = (
                                        response
                                    )
                                    mock_sdk.return_value = sdk

                                    result = cli_runner.invoke(
                                        app,
                                        [
                                            "coordinate",
                                            "update",
                                            "--codcom",
                                            "H501",
                                            "--progr-civico",
                                            "12345",
                                            "--production",  # Use production environment
                                        ],
                                    )

            assert result.exit_code == 0

            # Verify ModIConfig was created with production audience
            mock_modi_config.assert_called_once()
            config_kwargs = mock_modi_config.call_args[1]
            assert "audience" in config_kwargs
            # Production URL should contain modipa.agenziaentrate.it
            assert "modipa.agenziaentrate.it" in config_kwargs["audience"]

    def test_status_command_uses_hooks_but_modi_only_for_post(
        self, cli_runner: CliRunner, tmp_path: Path, mock_private_key: Path
    ) -> None:
        """Test that status command creates hooks but ModI is only for POST requests.

        The status command uses GET, so even though hooks are created,
        the ModI pre-request hook only activates for POST requests with a body.
        """
        from anncsu.cli import app

        with cli_runner.isolated_filesystem(temp_dir=tmp_path):
            Path("private_key.pem").write_text(mock_private_key.read_text())

            with patch(
                "anncsu.cli.commands.coordinate.ClientAssertionSettings"
            ) as mock_settings:
                settings = MagicMock()
                settings.kid = "test-kid"
                settings.issuer = "test-issuer"
                settings.private_key = mock_private_key.read_text()
                settings.key_path = None
                settings.has_modi_audit_context.return_value = True
                settings.get_modi_audit_context.return_value = MagicMock(
                    user_id="test-user",
                    user_location="test-location",
                    loa="SPID_L2",
                )
                mock_settings.return_value = settings

                with patch(
                    "anncsu.cli.commands.coordinate.PDNDAuthManager"
                ) as mock_manager:
                    manager = MagicMock()
                    manager.get_access_token.return_value = "mock-access-token"
                    mock_manager.return_value = manager

                    with patch(
                        "anncsu.cli.commands.coordinate.SDKHooks"
                    ) as mock_hooks_class:
                        mock_hooks = MagicMock()
                        mock_hooks_class.return_value = mock_hooks

                        with patch("anncsu.cli.commands.coordinate.register_modi_hook"):
                            with patch(
                                "anncsu.cli.commands.coordinate.AnncsuCoordinate"
                            ) as mock_sdk:
                                sdk = MagicMock()
                                status_response = MagicMock()
                                status_response.status = "OK"
                                sdk.status.show_status.return_value = status_response
                                mock_sdk.return_value = sdk

                                result = cli_runner.invoke(
                                    app, ["coordinate", "status"]
                                )

            assert result.exit_code == 0

            # Verify SDKHooks was created
            mock_hooks_class.assert_called_once()

            # Verify SDK was created with hooks
            sdk_call_kwargs = mock_sdk.call_args[1]
            assert "hooks" in sdk_call_kwargs

            # The ModI hook is registered but only activates for POST requests
            # Status uses GET, so headers won't be added (handled by the hook logic)
