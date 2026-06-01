"""Tests for race_validator.checks.file_naming."""

from pathlib import Path

import pytest

from race_validator.checks.base import ValidationContext
from race_validator.checks.file_naming import (
    FileNameFormatCheck,
    FileExtensionCheck,
)
from race_validator.report import Severity


def ctx_from(name: str) -> ValidationContext:
    return ValidationContext(file_path=Path(name))


# ---------- FileNameFormatCheck ----------

class TestFileNameFormatCheck:
    @pytest.mark.parametrize("name", [
        "142__2025__results__2026-05-19.csv",
        "87__2025-26__results__2026-05-19.csv",
        "1__2024__schedule__2024-01-01.csv",
        "9999__2030__results__2030-12-31.csv",
    ])
    def test_valid(self, name):
        check = FileNameFormatCheck()
        results = check.run(ctx_from(name))
        assert results == []

    @pytest.mark.parametrize("name", [
        "results.csv",                              # no fields
        "142_2025_results_2026-05-19.csv",          # single underscores, not double
        "142__2025__results__2026-05-19.CSV",       # uppercase ext
        "142__2025__qualifying__2026-05-19.csv",    # wrong file_type
        "142__2025__results__26-05-19.csv",         # wrong date format
        "abc__2025__results__2026-05-19.csv",       # non-numeric series_id
        "142__2025__results.csv",                   # missing fields
        "142__25__results__2026-05-19.csv",         # 2-digit year
    ])
    def test_invalid(self, name):
        check = FileNameFormatCheck()
        results = check.run(ctx_from(name))
        assert len(results) == 1
        assert results[0].severity == Severity.ERROR
        assert results[0].rule_id == "FILE_NAMING_001"

    def test_sets_file_type_in_ctx(self):
        ctx = ctx_from("142__2025__results__2026-05-19.csv")
        FileNameFormatCheck().run(ctx)
        assert ctx.file_type == "results"

        ctx = ctx_from("142__2025__schedule__2026-05-19.csv")
        FileNameFormatCheck().run(ctx)
        assert ctx.file_type == "schedule"

    def test_is_blocking(self):
        # The runner relies on this flag to short-circuit.
        assert FileNameFormatCheck.is_blocking is True


# ---------- FileExtensionCheck ----------

class TestFileExtensionCheck:
    def test_csv_passes(self):
        check = FileExtensionCheck()
        assert check.run(ctx_from("foo.csv")) == []

    @pytest.mark.parametrize("name", [
        "foo.CSV",
        "foo.xlsx",
        "foo.csv.gz",
        "foo",
        "foo.tsv",
    ])
    def test_non_csv_fails(self, name):
        check = FileExtensionCheck()
        results = check.run(ctx_from(name))
        assert len(results) == 1
        assert results[0].severity == Severity.ERROR
