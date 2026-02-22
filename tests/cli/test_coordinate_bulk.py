"""Tests for CLI coordinate bulk commands."""

from __future__ import annotations

import json
from pathlib import Path

from typer.testing import CliRunner

from anncsu.cli.app import app

runner = CliRunner()


def _write_csv(path: Path, content: str) -> Path:
    path.write_text(content, encoding="utf-8")
    return path


class TestBulkValidate:
    """Test 'anncsu coordinate bulk validate' command."""

    def test_validate_valid_csv(self, tmp_path):
        csv_file = _write_csv(
            tmp_path / "valid.csv",
            "codcom,progr_civico,x,y,z,metodo\n"
            "A062,1370588,13.1022000,41.8847600,150,3\n"
            "A062,1370589,14.0,42.0,,2\n",
        )
        result = runner.invoke(app, ["coordinate", "bulk", "validate", str(csv_file)])
        assert result.exit_code == 0
        assert "2" in result.output  # total rows
        assert "valid" in result.output.lower()

    def test_validate_invalid_rows(self, tmp_path):
        csv_file = _write_csv(
            tmp_path / "invalid.csv",
            "codcom,progr_civico,x,y,z,metodo\n"
            "A062,1370588,13.1,,,\n"  # x without y
            "A062,1370589,14.0,42.0,,2\n",
        )
        result = runner.invoke(app, ["coordinate", "bulk", "validate", str(csv_file)])
        assert result.exit_code == 0
        assert "invalid" in result.output.lower() or "1" in result.output

    def test_validate_missing_header(self, tmp_path):
        csv_file = _write_csv(
            tmp_path / "noheader.csv",
            "A062,1370588,13.1,41.8,150,3\n",
        )
        result = runner.invoke(app, ["coordinate", "bulk", "validate", str(csv_file)])
        assert result.exit_code != 0

    def test_validate_nonexistent_file(self):
        result = runner.invoke(
            app, ["coordinate", "bulk", "validate", "/tmp/nonexistent.csv"]
        )
        assert result.exit_code != 0

    def test_validate_json_output(self, tmp_path):
        csv_file = _write_csv(
            tmp_path / "valid.csv",
            "codcom,progr_civico,x,y,z,metodo\nA062,1370588,13.1022000,41.8847600,,3\n",
        )
        result = runner.invoke(
            app, ["coordinate", "bulk", "validate", str(csv_file), "--json"]
        )
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data["total_rows"] == 1
        assert data["valid_rows"] == 1

    def test_validate_semicolon_csv(self, tmp_path):
        csv_file = _write_csv(
            tmp_path / "semi.csv",
            "codcom;progr_civico;x;y;z;metodo\nA062;1370588;13.1;41.8;;3\n",
        )
        result = runner.invoke(app, ["coordinate", "bulk", "validate", str(csv_file)])
        assert result.exit_code == 0


class TestBulkHelp:
    """Test bulk subcommand help and structure."""

    def test_bulk_help(self):
        result = runner.invoke(app, ["coordinate", "bulk", "--help"])
        assert result.exit_code == 0
        assert "validate" in result.output
        assert "bulk" in result.output.lower()

    def test_coordinate_help_shows_bulk(self):
        result = runner.invoke(app, ["coordinate", "--help"])
        assert result.exit_code == 0
        assert "bulk" in result.output
