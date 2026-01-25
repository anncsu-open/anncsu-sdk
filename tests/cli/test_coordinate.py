# SPDX-FileCopyrightText: 2025-present Geobeyond <info@geobeyond.it>
# SPDX-License-Identifier: MIT
"""Tests for coordinate CLI commands."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING
from unittest.mock import MagicMock, patch

from pydantic import BaseModel

if TYPE_CHECKING:
    from typer.testing import CliRunner


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
                        response = MagicMock()
                        response.id_richiesta = "REQ-123"
                        response.esito = "OK"
                        response.messaggio = "Operazione completata"
                        response.dati = []
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
                        response = MagicMock()
                        response.id_richiesta = "REQ-456"
                        response.esito = "OK"
                        response.messaggio = "Success"
                        response.dati = []
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
                        response = MagicMock()
                        response.id_richiesta = "REQ-789"
                        response.esito = "OK"
                        response.messaggio = None
                        response.dati = []
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
                        response = MagicMock()
                        response.id_richiesta = "REQ-custom"
                        response.esito = "OK"
                        response.messaggio = None
                        response.dati = []
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
                        response = MagicMock()
                        response.id_richiesta = "REQ-prod"
                        response.esito = "OK"
                        response.messaggio = None
                        response.dati = []
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
                            update_response = MagicMock()
                            update_response.id_richiesta = "REQ-TEST-123"
                            update_response.esito = "OK"
                            update_response.messaggio = "Test update OK"
                            update_response.dati = []
                            # Mock restore response
                            restore_response = MagicMock()
                            restore_response.id_richiesta = "REQ-RESTORE-456"
                            restore_response.esito = "OK"
                            restore_response.messaggio = "Restore OK"
                            restore_response.dati = []
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
                            update_response = MagicMock()
                            update_response.id_richiesta = "REQ-TEST-123"
                            update_response.esito = "OK"
                            update_response.messaggio = "Test OK"
                            update_response.dati = []
                            restore_response = MagicMock()
                            restore_response.id_richiesta = "REQ-RESTORE-456"
                            restore_response.esito = "OK"
                            restore_response.messaggio = "Restore OK"
                            restore_response.dati = []
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
                            update_response = MagicMock()
                            update_response.id_richiesta = "REQ-TEST-123"
                            update_response.esito = "OK"
                            update_response.messaggio = "Test OK"
                            update_response.dati = []
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
                            update_response = MagicMock()
                            update_response.id_richiesta = "REQ-TEST"
                            update_response.esito = "OK"
                            update_response.messaggio = None
                            update_response.dati = []
                            restore_response = MagicMock()
                            restore_response.id_richiesta = "REQ-RESTORE"
                            restore_response.esito = "OK"
                            restore_response.messaggio = None
                            restore_response.dati = []
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
