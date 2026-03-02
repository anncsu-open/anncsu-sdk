# SPDX-FileCopyrightText: 2025-present Geobeyond <info@geobeyond.it>
# SPDX-License-Identifier: MIT
"""Tests for PA consultazione CLI commands."""

from __future__ import annotations

import json
from typing import TYPE_CHECKING
from unittest.mock import MagicMock, patch

if TYPE_CHECKING:
    from typer.testing import CliRunner


def _mock_odonimo_response(data=None):
    """Create a mock odonimo response."""
    resp = MagicMock()
    if data is None:
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
            "denomloc": "",
            "denomlingua1": "",
            "denomlingua2": "",
        }
        resp.data = [item]
    else:
        resp.data = data
    return resp


def _mock_prognazarea_response(data=None):
    """Create a mock prognazarea response (odonimo lookup by prognaz)."""
    resp = MagicMock()
    if data is None:
        item = MagicMock()
        item.prognaz = "907000"
        item.dug = "VIA"
        item.denomuff = "ROMA"
        item.denomloc = ""
        item.denomlingua1 = ""
        item.denomlingua2 = ""
        item.model_dump.return_value = {
            "prognaz": "907000",
            "dug": "VIA",
            "denomuff": "ROMA",
            "denomloc": "",
            "denomlingua1": "",
            "denomlingua2": "",
        }
        resp.data = [item]
    else:
        resp.data = data
    return resp


def _mock_accesso_response(data=None):
    """Create a mock accesso response (prognazacc lookup)."""
    resp = MagicMock()
    if data is None:
        item = MagicMock()
        item.prognaz = "12345"
        item.dug = "LARGO"
        item.denomuff = "CHIAFFREDO BERGIA"
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
            "dug": "LARGO",
            "denomuff": "CHIAFFREDO BERGIA",
            "denomloc": "",
            "denomlingua1": "",
            "denomlingua2": "",
            "prognazacc": "28586543",
            "civico": "1",
            "esp": "",
            "specif": "",
            "metrico": "",
            "coordX": "13.8808",
            "coordY": "41.9031",
            "quota": "",
            "metodo": "4",
        }
        resp.data = [item]
    else:
        resp.data = data
    return resp


def _mock_accessi_response(data=None):
    """Create a mock accessi response (elencoaccessiprog lookup)."""
    resp = MagicMock()
    if data is None:
        item1 = MagicMock()
        item1.prognazacc = "28586543"
        item1.civico = "1"
        item1.esp = ""
        item1.specif = ""
        item1.metrico = ""
        item1.coord_x = "13.8808"
        item1.coord_y = "41.9031"
        item1.quota = ""
        item1.metodo = "4"
        item1.model_dump.return_value = {
            "prognazacc": "28586543",
            "civico": "1",
            "esp": "",
            "specif": "",
            "metrico": "",
            "coordX": "13.8808",
            "coordY": "41.9031",
            "quota": "",
            "metodo": "4",
        }

        item2 = MagicMock()
        item2.prognazacc = "28586544"
        item2.civico = "2"
        item2.esp = ""
        item2.specif = ""
        item2.metrico = ""
        item2.coord_x = "13.8810"
        item2.coord_y = "41.9032"
        item2.quota = ""
        item2.metodo = "4"
        item2.model_dump.return_value = {
            "prognazacc": "28586544",
            "civico": "2",
            "esp": "",
            "specif": "",
            "metrico": "",
            "coordX": "13.8810",
            "coordY": "41.9032",
            "quota": "",
            "metodo": "4",
        }
        resp.data = [item1, item2]
    else:
        resp.data = data
    return resp


class TestPaGroupHelp:
    """Tests for pa command group help."""

    def test_pa_group_exists(self, cli_runner: CliRunner) -> None:
        """Test that pa command group is registered."""
        from anncsu.cli import app

        result = cli_runner.invoke(app, ["--help"])
        assert result.exit_code == 0
        assert "pa" in result.output.lower()

    def test_pa_help_shows_commands(self, cli_runner: CliRunner) -> None:
        """Test that pa --help shows available commands."""
        from anncsu.cli import app

        result = cli_runner.invoke(app, ["pa", "--help"])
        assert result.exit_code == 0
        assert "odonimo" in result.output.lower()
        assert "accesso" in result.output.lower()
        assert "accessi" in result.output.lower()


class TestOdonimo:
    """Tests for the odonimo command."""

    def test_odonimo_requires_codcom_and_denom(self, cli_runner: CliRunner) -> None:
        """Test that odonimo fails without required parameters."""
        from anncsu.cli import app

        result = cli_runner.invoke(app, ["pa", "odonimo"])
        assert result.exit_code != 0

    def test_odonimo_success(self, cli_runner: CliRunner) -> None:
        """Test odonimo displays table on success."""
        from anncsu.cli import app

        mock_sdk = MagicMock()
        mock_sdk.queryparam.elencoodonimiprog_get_query_param.return_value = (
            _mock_odonimo_response()
        )

        with patch("anncsu.cli.commands.pa._get_consult_sdk", return_value=mock_sdk):
            result = cli_runner.invoke(
                app, ["pa", "odonimo", "--codcom", "I501", "--denom", "VklBIFJPTUE="]
            )

        assert result.exit_code == 0
        assert "12345" in result.output
        assert "VIA" in result.output
        assert "ROMA" in result.output
        assert "1 result(s) found" in result.output

    def test_odonimo_json_output(self, cli_runner: CliRunner) -> None:
        """Test odonimo --json outputs valid JSON."""
        from anncsu.cli import app

        mock_sdk = MagicMock()
        mock_sdk.queryparam.elencoodonimiprog_get_query_param.return_value = (
            _mock_odonimo_response()
        )

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
                    "--json",
                ],
            )

        assert result.exit_code == 0
        data = json.loads(result.output)
        assert isinstance(data, list)
        assert len(data) == 1
        assert data[0]["prognaz"] == "12345"
        assert data[0]["dug"] == "VIA"

    def test_odonimo_no_results(self, cli_runner: CliRunner) -> None:
        """Test odonimo exits with error when no results."""
        from anncsu.cli import app

        mock_sdk = MagicMock()
        mock_resp = MagicMock()
        mock_resp.data = []
        mock_sdk.queryparam.elencoodonimiprog_get_query_param.return_value = mock_resp

        with patch("anncsu.cli.commands.pa._get_consult_sdk", return_value=mock_sdk):
            result = cli_runner.invoke(
                app, ["pa", "odonimo", "--codcom", "X999", "--denom", "bm9uZXhpc3Q="]
            )

        assert result.exit_code != 0

    def test_odonimo_api_error(self, cli_runner: CliRunner) -> None:
        """Test odonimo handles API errors gracefully."""
        from anncsu.cli import app

        mock_sdk = MagicMock()
        mock_sdk.queryparam.elencoodonimiprog_get_query_param.side_effect = Exception(
            "Connection error"
        )

        with patch("anncsu.cli.commands.pa._get_consult_sdk", return_value=mock_sdk):
            result = cli_runner.invoke(
                app, ["pa", "odonimo", "--codcom", "I501", "--denom", "VklBIFJPTUE="]
            )

        assert result.exit_code != 0


class TestAccesso:
    """Tests for the accesso command."""

    def test_accesso_requires_prognazacc(self, cli_runner: CliRunner) -> None:
        """Test that accesso fails without required parameter."""
        from anncsu.cli import app

        result = cli_runner.invoke(app, ["pa", "accesso"])
        assert result.exit_code != 0

    def test_accesso_success(self, cli_runner: CliRunner) -> None:
        """Test accesso displays detail table on success."""
        from anncsu.cli import app

        mock_sdk = MagicMock()
        mock_sdk.queryparam.prognazacc_get_query_param.return_value = (
            _mock_accesso_response()
        )

        with patch("anncsu.cli.commands.pa._get_consult_sdk", return_value=mock_sdk):
            result = cli_runner.invoke(
                app, ["pa", "accesso", "--prognazacc", "28586543"]
            )

        assert result.exit_code == 0
        assert "28586543" in result.output
        assert "LARGO" in result.output
        assert "CHIAFFREDO BERGIA" in result.output
        assert "13.8808" in result.output
        assert "41.9031" in result.output

    def test_accesso_json_output(self, cli_runner: CliRunner) -> None:
        """Test accesso --json outputs valid JSON."""
        from anncsu.cli import app

        mock_sdk = MagicMock()
        mock_sdk.queryparam.prognazacc_get_query_param.return_value = (
            _mock_accesso_response()
        )

        with patch("anncsu.cli.commands.pa._get_consult_sdk", return_value=mock_sdk):
            result = cli_runner.invoke(
                app, ["pa", "accesso", "--prognazacc", "28586543", "--json"]
            )

        assert result.exit_code == 0
        data = json.loads(result.output)
        assert isinstance(data, list)
        assert len(data) == 1
        assert data[0]["prognazacc"] == "28586543"
        assert data[0]["coordX"] == "13.8808"

    def test_accesso_not_found(self, cli_runner: CliRunner) -> None:
        """Test accesso exits with error when not found."""
        from anncsu.cli import app

        mock_sdk = MagicMock()
        mock_resp = MagicMock()
        mock_resp.data = []
        mock_sdk.queryparam.prognazacc_get_query_param.return_value = mock_resp

        with patch("anncsu.cli.commands.pa._get_consult_sdk", return_value=mock_sdk):
            result = cli_runner.invoke(
                app, ["pa", "accesso", "--prognazacc", "99999999"]
            )

        assert result.exit_code != 0

    def test_accesso_api_error(self, cli_runner: CliRunner) -> None:
        """Test accesso handles API errors gracefully."""
        from anncsu.cli import app

        mock_sdk = MagicMock()
        mock_sdk.queryparam.prognazacc_get_query_param.side_effect = Exception(
            "API error"
        )

        with patch("anncsu.cli.commands.pa._get_consult_sdk", return_value=mock_sdk):
            result = cli_runner.invoke(
                app, ["pa", "accesso", "--prognazacc", "28586543"]
            )

        assert result.exit_code != 0


class TestAccessi:
    """Tests for the accessi command."""

    def test_accessi_requires_codcom_and_denom(self, cli_runner: CliRunner) -> None:
        """Test that accessi fails without required parameters."""
        from anncsu.cli import app

        result = cli_runner.invoke(app, ["pa", "accessi"])
        assert result.exit_code != 0

    def test_accessi_success(self, cli_runner: CliRunner) -> None:
        """Test accessi displays table with access points."""
        from anncsu.cli import app

        mock_sdk = MagicMock()
        mock_sdk.queryparam.elencoodonimiprog_get_query_param.return_value = (
            _mock_odonimo_response()
        )
        mock_sdk.queryparam.elencoaccessiprog_get_query_param.return_value = (
            _mock_accessi_response()
        )

        with patch("anncsu.cli.commands.pa._get_consult_sdk", return_value=mock_sdk):
            result = cli_runner.invoke(
                app, ["pa", "accessi", "--codcom", "I501", "--denom", "VklBIFJPTUE="]
            )

        assert result.exit_code == 0
        # Rich table may truncate long values, check for prefix
        assert "28586" in result.output
        assert "2 access point(s) found" in result.output

    def test_accessi_json_output(self, cli_runner: CliRunner) -> None:
        """Test accessi --json outputs valid JSON."""
        from anncsu.cli import app

        mock_sdk = MagicMock()
        mock_sdk.queryparam.elencoodonimiprog_get_query_param.return_value = (
            _mock_odonimo_response()
        )
        mock_sdk.queryparam.elencoaccessiprog_get_query_param.return_value = (
            _mock_accessi_response()
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
                    "--json",
                ],
            )

        assert result.exit_code == 0
        data = json.loads(result.output)
        assert "odonimo" in data
        assert "accessi" in data
        assert len(data["accessi"]) == 2
        assert data["accessi"][0]["prognazacc"] == "28586543"

    def test_accessi_with_accparz(self, cli_runner: CliRunner) -> None:
        """Test accessi with --accparz filter."""
        from anncsu.cli import app

        mock_sdk = MagicMock()
        mock_sdk.queryparam.elencoodonimiprog_get_query_param.return_value = (
            _mock_odonimo_response()
        )
        mock_sdk.queryparam.elencoaccessiprog_get_query_param.return_value = (
            _mock_accessi_response()
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
                    "--accparz",
                    "1",
                ],
            )

        assert result.exit_code == 0
        # Verify accparz was passed to the SDK call
        mock_sdk.queryparam.elencoaccessiprog_get_query_param.assert_called_once_with(
            prognaz="12345",
            accparz="1",
        )

    def test_accessi_odonimo_not_found(self, cli_runner: CliRunner) -> None:
        """Test accessi exits with error when odonimo not found."""
        from anncsu.cli import app

        mock_sdk = MagicMock()
        mock_resp = MagicMock()
        mock_resp.data = []
        mock_sdk.queryparam.elencoodonimiprog_get_query_param.return_value = mock_resp

        with patch("anncsu.cli.commands.pa._get_consult_sdk", return_value=mock_sdk):
            result = cli_runner.invoke(
                app, ["pa", "accessi", "--codcom", "X999", "--denom", "bm9uZXhpc3Q="]
            )

        assert result.exit_code != 0

    def test_accessi_no_access_points(self, cli_runner: CliRunner) -> None:
        """Test accessi exits with error when no access points found."""
        from anncsu.cli import app

        mock_sdk = MagicMock()
        mock_sdk.queryparam.elencoodonimiprog_get_query_param.return_value = (
            _mock_odonimo_response()
        )
        mock_resp = MagicMock()
        mock_resp.data = []
        mock_sdk.queryparam.elencoaccessiprog_get_query_param.return_value = mock_resp

        with patch("anncsu.cli.commands.pa._get_consult_sdk", return_value=mock_sdk):
            result = cli_runner.invoke(
                app, ["pa", "accessi", "--codcom", "I501", "--denom", "VklBIFJPTUE="]
            )

        assert result.exit_code != 0

    def test_accessi_odonimo_api_error(self, cli_runner: CliRunner) -> None:
        """Test accessi handles odonimo API errors."""
        from anncsu.cli import app

        mock_sdk = MagicMock()
        mock_sdk.queryparam.elencoodonimiprog_get_query_param.side_effect = Exception(
            "API error"
        )

        with patch("anncsu.cli.commands.pa._get_consult_sdk", return_value=mock_sdk):
            result = cli_runner.invoke(
                app, ["pa", "accessi", "--codcom", "I501", "--denom", "VklBIFJPTUE="]
            )

        assert result.exit_code != 0

    def test_accessi_access_api_error(self, cli_runner: CliRunner) -> None:
        """Test accessi handles access search API errors."""
        from anncsu.cli import app

        mock_sdk = MagicMock()
        mock_sdk.queryparam.elencoodonimiprog_get_query_param.return_value = (
            _mock_odonimo_response()
        )
        mock_sdk.queryparam.elencoaccessiprog_get_query_param.side_effect = Exception(
            "API error"
        )

        with patch("anncsu.cli.commands.pa._get_consult_sdk", return_value=mock_sdk):
            result = cli_runner.invoke(
                app, ["pa", "accessi", "--codcom", "I501", "--denom", "VklBIFJPTUE="]
            )

        assert result.exit_code != 0


class TestOdonimoByPrognaz:
    """Tests for the odonimo command with --prognaz (direct lookup)."""

    def test_odonimo_prognaz_success(self, cli_runner: CliRunner) -> None:
        """Test odonimo --prognaz displays table on success."""
        from anncsu.cli import app

        mock_sdk = MagicMock()
        mock_sdk.queryparam.prognazarea_get_query_param.return_value = (
            _mock_prognazarea_response()
        )

        with patch("anncsu.cli.commands.pa._get_consult_sdk", return_value=mock_sdk):
            result = cli_runner.invoke(app, ["pa", "odonimo", "--prognaz", "907000"])

        assert result.exit_code == 0
        assert "907000" in result.output
        assert "VIA" in result.output
        assert "ROMA" in result.output
        assert "1 result(s) found" in result.output
        mock_sdk.queryparam.prognazarea_get_query_param.assert_called_once_with(
            prognaz="907000"
        )

    def test_odonimo_prognaz_json_output(self, cli_runner: CliRunner) -> None:
        """Test odonimo --prognaz --json outputs valid JSON."""
        from anncsu.cli import app

        mock_sdk = MagicMock()
        mock_sdk.queryparam.prognazarea_get_query_param.return_value = (
            _mock_prognazarea_response()
        )

        with patch("anncsu.cli.commands.pa._get_consult_sdk", return_value=mock_sdk):
            result = cli_runner.invoke(
                app, ["pa", "odonimo", "--prognaz", "907000", "--json"]
            )

        assert result.exit_code == 0
        data = json.loads(result.output)
        assert isinstance(data, list)
        assert len(data) == 1
        assert data[0]["prognaz"] == "907000"
        assert data[0]["dug"] == "VIA"

    def test_odonimo_prognaz_not_found(self, cli_runner: CliRunner) -> None:
        """Test odonimo --prognaz exits with error when not found."""
        from anncsu.cli import app

        mock_sdk = MagicMock()
        mock_resp = MagicMock()
        mock_resp.data = []
        mock_sdk.queryparam.prognazarea_get_query_param.return_value = mock_resp

        with patch("anncsu.cli.commands.pa._get_consult_sdk", return_value=mock_sdk):
            result = cli_runner.invoke(app, ["pa", "odonimo", "--prognaz", "999999"])

        assert result.exit_code != 0

    def test_odonimo_prognaz_api_error(self, cli_runner: CliRunner) -> None:
        """Test odonimo --prognaz handles API errors gracefully."""
        from anncsu.cli import app

        mock_sdk = MagicMock()
        mock_sdk.queryparam.prognazarea_get_query_param.side_effect = Exception(
            "Connection error"
        )

        with patch("anncsu.cli.commands.pa._get_consult_sdk", return_value=mock_sdk):
            result = cli_runner.invoke(app, ["pa", "odonimo", "--prognaz", "907000"])

        assert result.exit_code != 0

    def test_odonimo_prognaz_does_not_call_elencoodonimiprog(
        self, cli_runner: CliRunner
    ) -> None:
        """Test that --prognaz uses prognazarea, not elencoodonimiprog."""
        from anncsu.cli import app

        mock_sdk = MagicMock()
        mock_sdk.queryparam.prognazarea_get_query_param.return_value = (
            _mock_prognazarea_response()
        )

        with patch("anncsu.cli.commands.pa._get_consult_sdk", return_value=mock_sdk):
            result = cli_runner.invoke(app, ["pa", "odonimo", "--prognaz", "907000"])

        assert result.exit_code == 0
        mock_sdk.queryparam.elencoodonimiprog_get_query_param.assert_not_called()

    # --- Mutual exclusivity tests ---

    def test_odonimo_prognaz_with_codcom_is_error(self, cli_runner: CliRunner) -> None:
        """Test that --prognaz and --codcom together is an error."""
        from anncsu.cli import app

        result = cli_runner.invoke(
            app, ["pa", "odonimo", "--prognaz", "907000", "--codcom", "H501"]
        )

        assert result.exit_code != 0
        assert (
            "mutually exclusive" in result.output.lower()
            or "mutually exclusive" in (getattr(result, "stderr", "") or "")
        )

    def test_odonimo_prognaz_with_codcom_and_denom_is_error(
        self, cli_runner: CliRunner
    ) -> None:
        """Test that --prognaz with --codcom and --denom together is an error."""
        from anncsu.cli import app

        result = cli_runner.invoke(
            app,
            [
                "pa",
                "odonimo",
                "--prognaz",
                "907000",
                "--codcom",
                "H501",
                "--denom",
                "VklBIFJPTUE=",
            ],
        )

        assert result.exit_code != 0

    def test_odonimo_prognaz_with_denom_is_error(self, cli_runner: CliRunner) -> None:
        """Test that --prognaz and --denom together is an error."""
        from anncsu.cli import app

        result = cli_runner.invoke(
            app, ["pa", "odonimo", "--prognaz", "907000", "--denom", "VklBIFJPTUE="]
        )

        assert result.exit_code != 0

    def test_odonimo_no_options_is_error(self, cli_runner: CliRunner) -> None:
        """Test that odonimo without any option is an error."""
        from anncsu.cli import app

        result = cli_runner.invoke(app, ["pa", "odonimo"])

        assert result.exit_code != 0

    def test_odonimo_only_codcom_without_denom_is_error(
        self, cli_runner: CliRunner
    ) -> None:
        """Test that --codcom alone without --denom is an error."""
        from anncsu.cli import app

        result = cli_runner.invoke(app, ["pa", "odonimo", "--codcom", "H501"])

        assert result.exit_code != 0

    def test_odonimo_only_denom_without_codcom_is_error(
        self, cli_runner: CliRunner
    ) -> None:
        """Test that --denom alone without --codcom is an error."""
        from anncsu.cli import app

        result = cli_runner.invoke(app, ["pa", "odonimo", "--denom", "VklBIFJPTUE="])

        assert result.exit_code != 0
