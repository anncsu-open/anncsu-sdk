# SPDX-FileCopyrightText: 2025-present Geobeyond <info@geobeyond.it>
# SPDX-License-Identifier: MIT
"""Tests for --raw flag on CLI commands."""

from __future__ import annotations

from typing import TYPE_CHECKING
from unittest.mock import MagicMock, patch

if TYPE_CHECKING:
    from typer.testing import CliRunner


def _mock_accesso_response():
    """Create a mock accesso response with model_dump support."""
    resp = MagicMock()
    item = MagicMock()
    item.prognaz = "12345"
    item.dug = "VIA"
    item.denomuff = "ROMA"
    item.denomloc = ""
    item.denomlingua1 = ""
    item.denomlingua2 = ""
    item.prognazacc = "28586543"
    item.civico = "1"
    item.esp = ""
    item.specif = ""
    item.metrico = ""
    item.coord_x = "13.8808"
    item.coord_y = "41.9031"
    item.quota = ""
    item.metodo = "4"
    item.model_dump.return_value = {
        "prognaz": "12345",
        "dug": "VIA",
        "denomuff": "ROMA",
        "prognazacc": "28586543",
        "civico": "1",
        "coordX": "13.8808",
        "coordY": "41.9031",
        "metodo": "4",
    }
    resp.data = [item]
    resp.model_dump.return_value = {
        "res": "OK",
        "data": [item.model_dump.return_value],
    }
    return resp


def _mock_odonimo_response():
    """Create a mock odonimo response with model_dump support."""
    resp = MagicMock()
    item = MagicMock()
    item.prognaz = "12345"
    item.dug = "VIA"
    item.denomuff = "ROMA"
    item.denomloc = ""
    item.denomlingua1 = ""
    item.denomlingua2 = ""
    item.model_dump.return_value = {
        "prognaz": "12345",
        "dug": "VIA",
        "denomuff": "ROMA",
    }
    resp.data = [item]
    resp.model_dump.return_value = {
        "res": "OK",
        "data": [item.model_dump.return_value],
    }
    return resp


class TestPaRawOutput:
    """Tests for --raw flag on PA commands."""

    def test_accesso_raw_prints_to_stderr(self, cli_runner: CliRunner) -> None:
        """--raw should print raw API response to stderr."""
        from anncsu.cli import app

        mock_sdk = MagicMock()
        mock_resp = _mock_accesso_response()
        mock_sdk.queryparam.prognazacc_get_query_param.return_value = mock_resp

        with patch("anncsu.cli.commands.pa._get_consult_sdk", return_value=mock_sdk):
            result = cli_runner.invoke(
                app,
                ["pa", "accesso", "--prognazacc", "28586543", "--raw"],
            )

        assert result.exit_code == 0
        # Raw output goes to stderr (captured in result.output by typer runner)
        assert "Raw API response" in result.output
        assert "28586543" in result.output

    def test_accesso_no_raw_omits_raw_output(self, cli_runner: CliRunner) -> None:
        """Without --raw, no raw API response should appear."""
        from anncsu.cli import app

        mock_sdk = MagicMock()
        mock_resp = _mock_accesso_response()
        mock_sdk.queryparam.prognazacc_get_query_param.return_value = mock_resp

        with patch("anncsu.cli.commands.pa._get_consult_sdk", return_value=mock_sdk):
            result = cli_runner.invoke(
                app,
                ["pa", "accesso", "--prognazacc", "28586543"],
            )

        assert result.exit_code == 0
        assert "Raw API response" not in result.output

    def test_accesso_raw_with_json(self, cli_runner: CliRunner) -> None:
        """--raw + --json should both work together."""
        from anncsu.cli import app

        mock_sdk = MagicMock()
        mock_resp = _mock_accesso_response()
        mock_sdk.queryparam.prognazacc_get_query_param.return_value = mock_resp

        with patch("anncsu.cli.commands.pa._get_consult_sdk", return_value=mock_sdk):
            result = cli_runner.invoke(
                app,
                ["pa", "accesso", "--prognazacc", "28586543", "--raw", "--json"],
            )

        assert result.exit_code == 0
        # Output contains both raw (stderr mixed in) and JSON (stdout)
        assert "Raw API response" in result.output

    def test_odonimo_raw_by_codcom(self, cli_runner: CliRunner) -> None:
        """--raw on odonimo search prints raw response."""
        from anncsu.cli import app

        mock_sdk = MagicMock()
        mock_resp = _mock_odonimo_response()
        mock_sdk.queryparam.elencoodonimiprog_get_query_param.return_value = mock_resp

        with patch("anncsu.cli.commands.pa._get_consult_sdk", return_value=mock_sdk):
            result = cli_runner.invoke(
                app,
                [
                    "pa",
                    "odonimo",
                    "--codcom",
                    "I501",
                    "--denom",
                    "VklBIFJPTUE=",
                    "--raw",
                ],
            )

        assert result.exit_code == 0
        assert "Raw API response" in result.output

    def test_odonimo_raw_by_prognaz(self, cli_runner: CliRunner) -> None:
        """--raw on odonimo lookup by prognaz prints raw response."""
        from anncsu.cli import app

        mock_sdk = MagicMock()
        mock_resp = _mock_odonimo_response()
        mock_sdk.queryparam.prognazarea_get_query_param.return_value = mock_resp

        with patch("anncsu.cli.commands.pa._get_consult_sdk", return_value=mock_sdk):
            result = cli_runner.invoke(
                app,
                ["pa", "odonimo", "--prognaz", "907000", "--raw"],
            )

        assert result.exit_code == 0
        assert "Raw API response" in result.output

    def test_accessi_raw_prints_both_responses(self, cli_runner: CliRunner) -> None:
        """--raw on accessi should print both odonimo and accessi raw responses."""
        from anncsu.cli import app

        mock_sdk = MagicMock()
        mock_sdk.queryparam.elencoodonimiprog_get_query_param.return_value = (
            _mock_odonimo_response()
        )
        mock_sdk.queryparam.elencoaccessiprog_get_query_param.return_value = (
            _mock_accesso_response()
        )

        with patch("anncsu.cli.commands.pa._get_consult_sdk", return_value=mock_sdk):
            result = cli_runner.invoke(
                app,
                [
                    "pa",
                    "accessi",
                    "--codcom",
                    "I501",
                    "--denom",
                    "VklBIFJPTUE=",
                    "--raw",
                ],
            )

        assert result.exit_code == 0
        assert "Raw odonimo response" in result.output
        assert "Raw accessi response" in result.output


class TestCoordinateRawOutput:
    """Tests for --raw flag on coordinate commands."""

    def test_update_raw_prints_response(self, cli_runner: CliRunner) -> None:
        """--raw on coordinate update prints raw API response."""
        from anncsu.cli import app

        mock_response = MagicMock()
        mock_response.esito = "0"
        mock_response.id_richiesta = None
        mock_response.messaggio = None
        mock_response.dati = []
        mock_response.model_dump.return_value = {
            "esito": "0",
            "dati": [],
        }

        mock_sdk = MagicMock()
        mock_sdk.json_post.gestionecoordinate.return_value = mock_response

        with patch(
            "anncsu.cli.commands.coordinate._get_sdk",
            return_value=(mock_sdk, None),
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
                    "--x",
                    "12.49",
                    "--y",
                    "41.90",
                    "--metodo",
                    "3",
                    "--raw",
                ],
            )

        assert result.exit_code == 0
        assert "Raw API response" in result.output

    def test_update_no_raw_omits_raw_output(self, cli_runner: CliRunner) -> None:
        """Without --raw, no raw API response should appear."""
        from anncsu.cli import app

        mock_response = MagicMock()
        mock_response.esito = "0"
        mock_response.id_richiesta = None
        mock_response.messaggio = None
        mock_response.dati = []
        mock_response.model_dump.return_value = {
            "esito": "0",
            "dati": [],
        }

        mock_sdk = MagicMock()
        mock_sdk.json_post.gestionecoordinate.return_value = mock_response

        with patch(
            "anncsu.cli.commands.coordinate._get_sdk",
            return_value=(mock_sdk, None),
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
                    "--x",
                    "12.49",
                    "--y",
                    "41.90",
                    "--metodo",
                    "3",
                ],
            )

        assert result.exit_code == 0
        assert "Raw API response" not in result.output

    def test_status_raw_prints_response(self, cli_runner: CliRunner) -> None:
        """--raw on coordinate status prints raw API response."""
        from anncsu.cli import app

        mock_response = MagicMock()
        mock_response.status = "OK"
        mock_response.model_dump.return_value = {"status": "OK"}

        mock_sdk = MagicMock()
        mock_sdk.status.show_status.return_value = mock_response

        with patch(
            "anncsu.cli.commands.coordinate._get_sdk",
            return_value=(mock_sdk, None),
        ):
            result = cli_runner.invoke(
                app,
                ["coordinate", "status", "--raw"],
            )

        assert result.exit_code == 0
        assert "Raw API response" in result.output
