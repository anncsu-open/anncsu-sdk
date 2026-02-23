"""Tests for CSV import and validation into DuckDB."""

from __future__ import annotations

from pathlib import Path

import pytest

from anncsu.coordinate.bulk.db import BulkDB, RowStatus
from anncsu.coordinate.bulk.importer import (
    CSVImportError,
    CSVImportResult,
    detect_separator,
    import_csv,
    validate_csv_header,
)


REQUIRED_COLUMNS = {"codcom", "progr_civico"}
ALL_COLUMNS = {"codcom", "progr_civico", "x", "y", "z", "metodo"}


def _write_csv(path: Path, content: str) -> Path:
    """Helper to write CSV content to a file."""
    path.write_text(content, encoding="utf-8")
    return path


class TestDetectSeparator:
    """Test CSV separator detection."""

    def test_detect_comma(self, tmp_path):
        csv_file = _write_csv(
            tmp_path / "comma.csv",
            "codcom,progr_civico,x,y,z,metodo\nA062,1370588,13.1,41.8,150,3\n",
        )
        assert detect_separator(csv_file) == ","

    def test_detect_semicolon(self, tmp_path):
        csv_file = _write_csv(
            tmp_path / "semi.csv",
            "codcom;progr_civico;x;y;z;metodo\nA062;1370588;13.1;41.8;150;3\n",
        )
        assert detect_separator(csv_file) == ";"

    def test_detect_fallback_to_comma(self, tmp_path):
        csv_file = _write_csv(
            tmp_path / "single_col.csv",
            "codcom\nA062\n",
        )
        assert detect_separator(csv_file) == ","


class TestValidateCSVHeader:
    """Test CSV header validation."""

    def test_valid_header_all_columns(self, tmp_path):
        csv_file = _write_csv(
            tmp_path / "valid.csv",
            "codcom,progr_civico,x,y,z,metodo\nA062,1370588,13.1,41.8,150,3\n",
        )
        validate_csv_header(csv_file, separator=",")

    def test_valid_header_required_only(self, tmp_path):
        csv_file = _write_csv(
            tmp_path / "minimal.csv",
            "codcom,progr_civico\nA062,1370588\n",
        )
        validate_csv_header(csv_file, separator=",")

    def test_missing_required_column(self, tmp_path):
        csv_file = _write_csv(
            tmp_path / "missing.csv",
            "codcom,x,y\nA062,13.1,41.8\n",
        )
        with pytest.raises(CSVImportError, match="progr_civico"):
            validate_csv_header(csv_file, separator=",")

    def test_empty_file(self, tmp_path):
        csv_file = _write_csv(tmp_path / "empty.csv", "")
        with pytest.raises(CSVImportError, match="[Ee]mpty|[Hh]eader"):
            validate_csv_header(csv_file, separator=",")

    def test_unknown_column_ignored(self, tmp_path):
        csv_file = _write_csv(
            tmp_path / "extra.csv",
            "codcom,progr_civico,extra_col\nA062,1370588,ignored\n",
        )
        validate_csv_header(csv_file, separator=",")

    def test_semicolon_header(self, tmp_path):
        csv_file = _write_csv(
            tmp_path / "semi.csv",
            "codcom;progr_civico;x;y;z;metodo\nA062;1370588;13.1;41.8;150;3\n",
        )
        validate_csv_header(csv_file, separator=";")


class TestImportCSV:
    """Test full CSV import into DuckDB."""

    def test_import_basic(self, tmp_path):
        csv_file = _write_csv(
            tmp_path / "basic.csv",
            "codcom,progr_civico,x,y,z,metodo\n"
            "A062,1370588,13.1022000,41.8847600,150,3\n"
            "A062,1370589,13.1025000,41.8850000,,2\n",
        )
        with BulkDB(":memory:") as db:
            result = import_csv(db=db, csv_path=csv_file, mode="update")
            assert result.total_rows == 2
            assert result.run_id is not None
            assert result.codcom == "A062"

    def test_import_semicolon(self, tmp_path):
        csv_file = _write_csv(
            tmp_path / "semi.csv",
            "codcom;progr_civico;x;y;z;metodo\n"
            "A062;1370588;13.1022000;41.8847600;150;3\n",
        )
        with BulkDB(":memory:") as db:
            result = import_csv(db=db, csv_path=csv_file, mode="update")
            assert result.total_rows == 1

    def test_import_validates_rows(self, tmp_path):
        csv_file = _write_csv(
            tmp_path / "mixed.csv",
            "codcom,progr_civico,x,y,z,metodo\n"
            "A062,1370588,13.1022000,41.8847600,150,3\n"  # valid
            "A062,1370589,13.1025000,,,\n"  # invalid: x without y
            "A062,1370590,,,,,\n",  # valid: no coordinates
        )
        with BulkDB(":memory:") as db:
            result = import_csv(db=db, csv_path=csv_file, mode="update")
            assert result.total_rows == 3
            assert result.valid_rows == 2
            assert result.invalid_rows == 1

    def test_import_stores_validation_error(self, tmp_path):
        csv_file = _write_csv(
            tmp_path / "invalid.csv",
            "codcom,progr_civico,x,y,z,metodo\n"
            "A062,1370588,13.1022000,,,\n",  # x without y
        )
        with BulkDB(":memory:") as db:
            result = import_csv(db=db, csv_path=csv_file, mode="update")
            assert result.invalid_rows == 1
            rows = db.get_rows_by_status(run_id=result.run_id, status=RowStatus.INVALID)
            assert len(rows) == 1
            assert rows[0]["validation_error"] is not None
            assert "Y" in rows[0]["validation_error"]

    def test_import_creates_run(self, tmp_path):
        csv_file = _write_csv(
            tmp_path / "run.csv",
            "codcom,progr_civico\nA062,1370588\n",
        )
        with BulkDB(":memory:") as db:
            result = import_csv(db=db, csv_path=csv_file, mode="update")
            summary = db.get_run_summary(result.run_id)
            assert summary is not None
            assert summary["mode"] == "update"
            assert summary["codcom"] == "A062"
            assert summary["total_rows"] == 1

    def test_import_extracts_codcom(self, tmp_path):
        csv_file = _write_csv(
            tmp_path / "codcom.csv",
            "codcom,progr_civico\nH501,1370588\nH501,1370589\n",
        )
        with BulkDB(":memory:") as db:
            result = import_csv(db=db, csv_path=csv_file, mode="update")
            assert result.codcom == "H501"

    def test_import_missing_header_raises(self, tmp_path):
        csv_file = _write_csv(
            tmp_path / "no_header.csv",
            "A062,1370588,13.1,41.8,150,3\n",
        )
        with pytest.raises(CSVImportError):
            with BulkDB(":memory:") as db:
                import_csv(db=db, csv_path=csv_file, mode="update")

    def test_import_empty_optional_fields(self, tmp_path):
        csv_file = _write_csv(
            tmp_path / "empty_opt.csv",
            "codcom,progr_civico,x,y,z,metodo\nA062,1370588,,,,,\n",
        )
        with BulkDB(":memory:") as db:
            result = import_csv(db=db, csv_path=csv_file, mode="update")
            assert result.valid_rows == 1
            rows = db.get_rows_by_status(run_id=result.run_id, status=RowStatus.VALID)
            assert rows[0]["x"] is None or rows[0]["x"] == ""

    def test_import_metodo_out_of_range(self, tmp_path):
        csv_file = _write_csv(
            tmp_path / "metodo.csv",
            "codcom,progr_civico,x,y,z,metodo\n"
            "A062,1370588,13.1022000,41.8847600,,9\n",  # metodo=9 invalid
        )
        with BulkDB(":memory:") as db:
            result = import_csv(db=db, csv_path=csv_file, mode="update")
            assert result.invalid_rows == 1

    def test_import_result_dataclass(self, tmp_path):
        csv_file = _write_csv(
            tmp_path / "result.csv",
            "codcom,progr_civico,x,y,z,metodo\n"
            "A062,1370588,13.1022000,41.8847600,150,3\n",
        )
        with BulkDB(":memory:") as db:
            result = import_csv(db=db, csv_path=csv_file, mode="dryrun")
            assert isinstance(result, CSVImportResult)
            assert result.total_rows == 1
            assert result.valid_rows == 1
            assert result.invalid_rows == 0
            assert result.run_id is not None
            assert result.codcom == "A062"

    def test_import_duplicate_progr_civico_allowed(self, tmp_path):
        """Duplicate progr_civico rows are allowed (different updates)."""
        csv_file = _write_csv(
            tmp_path / "dup.csv",
            "codcom,progr_civico,x,y,z,metodo\n"
            "A062,1370588,13.1022000,41.8847600,,3\n"
            "A062,1370588,14.0000000,42.0000000,,2\n",
        )
        with BulkDB(":memory:") as db:
            result = import_csv(db=db, csv_path=csv_file, mode="update")
            assert result.total_rows == 2


class TestImportCSVSQLValidation:
    """Tests for validation edge cases (ensures SQL validation parity with Pydantic)."""

    def test_import_y_without_x(self, tmp_path):
        """Y without X should be invalid."""
        csv_file = _write_csv(
            tmp_path / "y_no_x.csv",
            "codcom,progr_civico,x,y,z,metodo\nA062,1370588,,41.8,,\n",
        )
        with BulkDB(":memory:") as db:
            result = import_csv(db=db, csv_path=csv_file, mode="validate")
            assert result.invalid_rows == 1
            rows = db.get_rows_by_status(run_id=result.run_id, status=RowStatus.INVALID)
            assert "X" in rows[0]["validation_error"]

    def test_import_metodo_not_allowed(self, tmp_path):
        """Metodo without X and Y should be invalid."""
        csv_file = _write_csv(
            tmp_path / "metodo_alone.csv",
            "codcom,progr_civico,x,y,z,metodo\nA062,1370588,,,,3\n",
        )
        with BulkDB(":memory:") as db:
            result = import_csv(db=db, csv_path=csv_file, mode="validate")
            assert result.invalid_rows == 1
            rows = db.get_rows_by_status(run_id=result.run_id, status=RowStatus.INVALID)
            assert "metodo" in rows[0]["validation_error"].lower()

    def test_import_z_without_coords(self, tmp_path):
        """Z without X and Y should be invalid."""
        csv_file = _write_csv(
            tmp_path / "z_alone.csv",
            "codcom,progr_civico,x,y,z,metodo\nA062,1370588,,,150,\n",
        )
        with BulkDB(":memory:") as db:
            result = import_csv(db=db, csv_path=csv_file, mode="validate")
            assert result.invalid_rows == 1
            rows = db.get_rows_by_status(run_id=result.run_id, status=RowStatus.INVALID)
            assert "Z" in rows[0]["validation_error"]

    def test_import_x_out_of_range(self, tmp_path):
        """X outside Italy bounds should be invalid."""
        csv_file = _write_csv(
            tmp_path / "x_range.csv",
            "codcom,progr_civico,x,y,z,metodo\nA062,1370588,99.0,41.8,,3\n",
        )
        with BulkDB(":memory:") as db:
            result = import_csv(db=db, csv_path=csv_file, mode="validate")
            assert result.invalid_rows == 1

    def test_import_y_out_of_range(self, tmp_path):
        """Y outside Italy bounds should be invalid."""
        csv_file = _write_csv(
            tmp_path / "y_range.csv",
            "codcom,progr_civico,x,y,z,metodo\nA062,1370588,13.1,99.0,,3\n",
        )
        with BulkDB(":memory:") as db:
            result = import_csv(db=db, csv_path=csv_file, mode="validate")
            assert result.invalid_rows == 1

    def test_import_csv_only_required_columns(self, tmp_path):
        """CSV with only codcom and progr_civico should be all valid."""
        csv_file = _write_csv(
            tmp_path / "required_only.csv",
            "codcom,progr_civico\nA062,1370588\nA062,1370589\n",
        )
        with BulkDB(":memory:") as db:
            result = import_csv(db=db, csv_path=csv_file, mode="validate")
            assert result.total_rows == 2
            assert result.valid_rows == 2
            assert result.invalid_rows == 0

    def test_import_whitespace_values_treated_as_null(self, tmp_path):
        """Whitespace-only values in optional fields should be treated as NULL."""
        csv_file = _write_csv(
            tmp_path / "whitespace.csv",
            "codcom,progr_civico,x,y,z,metodo\nA062,1370588, , , , \n",
        )
        with BulkDB(":memory:") as db:
            result = import_csv(db=db, csv_path=csv_file, mode="validate")
            assert result.valid_rows == 1

    def test_import_x_exceeds_max_length(self, tmp_path):
        """X with more than 12 characters should be invalid."""
        csv_file = _write_csv(
            tmp_path / "x_long.csv",
            "codcom,progr_civico,x,y,z,metodo\n"
            "A062,1370588,12.3476928612,41.7942647,150,3\n",
        )
        with BulkDB(":memory:") as db:
            result = import_csv(db=db, csv_path=csv_file, mode="validate")
            assert result.invalid_rows == 1
            row = db.con.execute(
                "SELECT validation_error FROM bulk_input WHERE status = 'invalid'"
            ).fetchone()
            assert "lunghezza massima" in row[0]
            assert "'x'" in row[0]

    def test_import_y_exceeds_max_length(self, tmp_path):
        """Y with more than 12 characters should be invalid."""
        csv_file = _write_csv(
            tmp_path / "y_long.csv",
            "codcom,progr_civico,x,y,z,metodo\n"
            "A062,1370588,12.4922309,41.7942647923,150,3\n",
        )
        with BulkDB(":memory:") as db:
            result = import_csv(db=db, csv_path=csv_file, mode="validate")
            assert result.invalid_rows == 1
            row = db.con.execute(
                "SELECT validation_error FROM bulk_input WHERE status = 'invalid'"
            ).fetchone()
            assert "lunghezza massima" in row[0]
            assert "'y'" in row[0]

    def test_import_z_exceeds_max_length(self, tmp_path):
        """Z with more than 7 characters should be invalid."""
        csv_file = _write_csv(
            tmp_path / "z_long.csv",
            "codcom,progr_civico,x,y,z,metodo\n"
            "A062,1370588,12.4922309,41.8902102,12345678,3\n",
        )
        with BulkDB(":memory:") as db:
            result = import_csv(db=db, csv_path=csv_file, mode="validate")
            assert result.invalid_rows == 1
            row = db.con.execute(
                "SELECT validation_error FROM bulk_input WHERE status = 'invalid'"
            ).fetchone()
            assert "lunghezza massima" in row[0]
            assert "'z'" in row[0]

    def test_import_x_exactly_12_chars_valid(self, tmp_path):
        """X with exactly 12 characters should be valid."""
        csv_file = _write_csv(
            tmp_path / "x_exact.csv",
            "codcom,progr_civico,x,y,z,metodo\n"
            "A062,1370588,12.49223090,41.8902102,,3\n",
        )
        with BulkDB(":memory:") as db:
            result = import_csv(db=db, csv_path=csv_file, mode="validate")
            assert result.valid_rows == 1
            assert result.invalid_rows == 0
