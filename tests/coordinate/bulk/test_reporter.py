"""Tests for bulk report generation from DuckDB."""

from __future__ import annotations

import csv
import json
from io import StringIO
from pathlib import Path


from anncsu.coordinate.bulk.db import BulkDB, RowStatus
from anncsu.coordinate.bulk.importer import import_csv
from anncsu.coordinate.bulk.reporter import (
    BulkReporter,
    ReportFormat,
    RunSummary,
)


def _write_csv(path: Path, content: str) -> Path:
    path.write_text(content, encoding="utf-8")
    return path


def _setup_db_with_results(tmp_path):
    """Create a DB with imported CSV and some results."""
    csv_file = _write_csv(
        tmp_path / "input.csv",
        "codcom,progr_civico,x,y,z,metodo\n"
        "A062,100,13.1,41.8,,3\n"
        "A062,200,14.0,42.0,,2\n"
        "A062,300,15.0,43.0,,1\n",
    )
    db = BulkDB(":memory:")
    result = import_csv(db=db, csv_path=csv_file, mode="update")

    # Simulate some results
    db.insert_result(
        row_id=1,
        run_id=result.run_id,
        operation="update",
        esito="0",
        messaggio="OK",
        id_richiesta="5144",
    )
    db.update_row_status(row_id=1, status=RowStatus.DONE)

    db.insert_result(
        row_id=2,
        run_id=result.run_id,
        operation="update",
        esito="23",
        messaggio="Errore di validazione",
        id_richiesta="5145",
    )
    db.update_row_status(row_id=2, status=RowStatus.ERROR)

    db.insert_result(
        row_id=3,
        run_id=result.run_id,
        operation="update",
        esito="0",
        messaggio="OK",
        id_richiesta="5146",
    )
    db.update_row_status(row_id=3, status=RowStatus.DONE)

    db.update_run_counts(
        run_id=result.run_id,
        processed=3,
        succeeded=2,
        failed=1,
    )

    return db, result


class TestBulkReporterSummary:
    """Test run summary generation."""

    def test_get_summary(self, tmp_path):
        db, result = _setup_db_with_results(tmp_path)
        reporter = BulkReporter(db=db, run_id=result.run_id)
        summary = reporter.get_summary()

        assert isinstance(summary, RunSummary)
        assert summary.total_rows == 3
        assert summary.valid_rows == 3
        assert summary.processed == 3
        assert summary.succeeded == 2
        assert summary.failed == 1
        assert summary.codcom == "A062"
        db.close()

    def test_get_summary_unknown_run(self):
        db = BulkDB(":memory:")
        reporter = BulkReporter(db=db, run_id="nonexistent")
        summary = reporter.get_summary()
        assert summary is None
        db.close()


class TestBulkReporterCSV:
    """Test CSV report export."""

    def test_export_csv(self, tmp_path):
        db, result = _setup_db_with_results(tmp_path)
        reporter = BulkReporter(db=db, run_id=result.run_id)

        output = StringIO()
        reporter.export_results(output, fmt=ReportFormat.CSV)

        output.seek(0)
        reader = csv.DictReader(output)
        rows = list(reader)

        assert len(rows) == 3
        assert rows[0]["esito"] == "0"
        assert rows[1]["esito"] == "23"
        assert rows[2]["esito"] == "0"
        db.close()

    def test_export_csv_to_file(self, tmp_path):
        db, result = _setup_db_with_results(tmp_path)
        reporter = BulkReporter(db=db, run_id=result.run_id)

        output_path = tmp_path / "results.csv"
        with open(output_path, "w", newline="", encoding="utf-8") as f:
            reporter.export_results(f, fmt=ReportFormat.CSV)

        assert output_path.exists()
        with open(output_path, encoding="utf-8") as f:
            reader = csv.DictReader(f)
            rows = list(reader)
        assert len(rows) == 3
        db.close()

    def test_csv_has_expected_columns(self, tmp_path):
        db, result = _setup_db_with_results(tmp_path)
        reporter = BulkReporter(db=db, run_id=result.run_id)

        output = StringIO()
        reporter.export_results(output, fmt=ReportFormat.CSV)

        output.seek(0)
        reader = csv.DictReader(output)
        row = next(reader)
        assert "codcom" in row
        assert "progr_civico" in row
        assert "esito" in row
        assert "messaggio" in row
        assert "id_richiesta" in row
        db.close()


class TestBulkReporterJSON:
    """Test JSON report export."""

    def test_export_json(self, tmp_path):
        db, result = _setup_db_with_results(tmp_path)
        reporter = BulkReporter(db=db, run_id=result.run_id)

        output = StringIO()
        reporter.export_results(output, fmt=ReportFormat.JSON)

        output.seek(0)
        data = json.loads(output.read())

        assert "summary" in data
        assert "results" in data
        assert data["summary"]["total_rows"] == 3
        assert data["summary"]["succeeded"] == 2
        assert len(data["results"]) == 3
        db.close()


class TestBulkReporterErrorDetails:
    """Test error detail queries."""

    def test_get_errors(self, tmp_path):
        db, result = _setup_db_with_results(tmp_path)
        reporter = BulkReporter(db=db, run_id=result.run_id)
        errors = reporter.get_errors()

        assert len(errors) == 1
        assert errors[0]["esito"] == "23"
        assert errors[0]["progr_civico"] == "200"
        db.close()

    def test_get_errors_empty(self, tmp_path):
        csv_file = _write_csv(
            tmp_path / "ok.csv",
            "codcom,progr_civico,x,y,z,metodo\nA062,100,13.1,41.8,,3\n",
        )
        db = BulkDB(":memory:")
        result = import_csv(db=db, csv_path=csv_file, mode="update")
        db.insert_result(
            row_id=1,
            run_id=result.run_id,
            operation="update",
            esito="0",
            messaggio="OK",
        )

        reporter = BulkReporter(db=db, run_id=result.run_id)
        errors = reporter.get_errors()
        assert len(errors) == 0
        db.close()


class TestBulkReporterValidationErrors:
    """Test validation error queries."""

    def test_get_validation_errors(self, tmp_path):
        csv_file = _write_csv(
            tmp_path / "mixed.csv",
            "codcom,progr_civico,x,y,z,metodo\n"
            "A062,100,13.1,,,\n"  # invalid: x without y
            "A062,200,13.1,41.8,,3\n",  # valid
        )
        db = BulkDB(":memory:")
        result = import_csv(db=db, csv_path=csv_file, mode="update")

        reporter = BulkReporter(db=db, run_id=result.run_id)
        val_errors = reporter.get_validation_errors()

        assert len(val_errors) == 1
        assert val_errors[0]["progr_civico"] == "100"
        assert val_errors[0]["validation_error"] is not None
        db.close()


class TestReportFormat:
    """Test ReportFormat enum."""

    def test_format_values(self):
        assert ReportFormat.CSV == "csv"
        assert ReportFormat.JSON == "json"
        assert ReportFormat.TABLE == "table"
