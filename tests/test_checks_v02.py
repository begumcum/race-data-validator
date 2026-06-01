"""Tests for column / value / timestamp / normalization / dupe checks.

These tests use a minimal results schema fixture to keep tests focused.
The schemas module is real; we just feed it small DataFrames.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from race_validator.checks.base import ValidationContext
from race_validator.checks.column_names import ColumnNamesCheck, ColumnOrderCheck
from race_validator.checks.duplicates import (
    DuplicateResultIdCheck,
    DuplicateRowsCheck,
)
from race_validator.checks.forbidden_chars import ForbiddenCharsCheck
from race_validator.checks.normalization_integrity import (
    NormalizationIntegrityCheck,
)
from race_validator.checks.timestamps import TimestampLocalCheck, TimestampUtcCheck
from race_validator.checks.value_types import ValueTypesCheck
from race_validator.schemas import RESULTS_SCHEMA


def make_ctx(df: pd.DataFrame, file_type: str = "results") -> ValidationContext:
    return ValidationContext(
        file_path=Path("142__2025__results__2026-05-19.csv"),
        df=df,
        file_type=file_type,
    )


def minimal_row() -> dict:
    """A row populating every column with a valid value."""
    return {
        "result_id": "abc",
        "series_id": "1",
        "season_label": "2025",
        "round_number": "1",
        "session_type": "race",
        "session_number": "1",
        "circuit_id": "1",
        "session_datetime_local": "2025-06-08T13:40:00+01:00",
        "sport": "motorsport",
        "discipline": "single_seater",
        "category": "formula_4",
        "entry_id": "e1",
        "car_number": "44",
        "team_id": "1",
        "team_name_raw": "Prema Racing",
        "team_name_normalized": "prema_racing",
        "car_model_raw": "",
        "car_model_normalized": "",
        "driver_id": "1",
        "driver_full_name_raw": "Nicolás Varrone",
        "driver_full_name_normalized": "nicolas varrone",
        "driver_slot": "1",
        "nationality_code": "ARG",
        "driver_classification": "",
        "race_status": "FINISHED",
        "grid_position": "1",
        "position_overall": "1",
        "position_in_class": "1",
        "laps_completed": "30",
        "laps_down": "0",
        "race_time_ms": "1800000",
        "gap_to_leader_ms": "",
        "gap_to_leader_display": "",
        "interval_to_ahead_ms": "",
        "interval_to_ahead_display": "",
        "best_lap_time_ms": "60000",
        "best_lap_number": "5",
        "best_lap_speed_kph": "210.5",
        "is_pole": "TRUE",
        "is_fastest_lap_overall": "FALSE",
        "is_fastest_lap_in_class": "FALSE",
        "source_url": "https://example.com/results",
        "source_collector": "berkay",
        "scraped_at": "2026-05-19T08:00:00Z",
        "ingested_at": "",
    }


def make_df(*rows: dict) -> pd.DataFrame:
    cols = RESULTS_SCHEMA.column_names()
    return pd.DataFrame(rows, columns=cols)


# ---------- ColumnNamesCheck ----------

class TestColumnNamesCheck:
    def test_valid(self):
        df = make_df(minimal_row())
        assert ColumnNamesCheck().run(make_ctx(df)) == []

    def test_missing_column(self):
        df = make_df(minimal_row()).drop(columns=["driver_id"])
        results = ColumnNamesCheck().run(make_ctx(df))
        assert len(results) == 1
        assert "driver_id" in results[0].message

    def test_extra_column(self):
        row = minimal_row()
        row["fake_column"] = "x"
        df = pd.DataFrame([row])
        results = ColumnNamesCheck().run(make_ctx(df))
        assert any("fake_column" in r.message for r in results)


# ---------- ColumnOrderCheck ----------

class TestColumnOrderCheck:
    def test_correct_order(self):
        df = make_df(minimal_row())
        assert ColumnOrderCheck().run(make_ctx(df)) == []

    def test_wrong_order(self):
        df = make_df(minimal_row())
        # Swap the first two columns
        cols = list(df.columns)
        cols[0], cols[1] = cols[1], cols[0]
        df = df[cols]
        results = ColumnOrderCheck().run(make_ctx(df))
        assert len(results) == 1


# ---------- ValueTypesCheck ----------

class TestValueTypesCheck:
    def test_clean_passes(self):
        df = make_df(minimal_row())
        assert ValueTypesCheck().run(make_ctx(df)) == []

    def test_bad_int(self):
        row = minimal_row()
        row["car_number"] = "44 laps"
        df = make_df(row)
        results = ValueTypesCheck().run(make_ctx(df))
        assert any("car_number" in r.message for r in results)

    def test_bad_bool(self):
        row = minimal_row()
        row["is_pole"] = "yes"
        df = make_df(row)
        results = ValueTypesCheck().run(make_ctx(df))
        assert any("is_pole" in r.message for r in results)

    def test_bad_enum_race_status(self):
        row = minimal_row()
        row["race_status"] = "BANANA"
        df = make_df(row)
        results = ValueTypesCheck().run(make_ctx(df))
        assert any("race_status" in r.message for r in results)

    def test_null_in_required(self):
        row = minimal_row()
        row["driver_id"] = ""
        df = make_df(row)
        results = ValueTypesCheck().run(make_ctx(df))
        assert any("driver_id" in r.message for r in results)

    def test_null_in_nullable_ok(self):
        row = minimal_row()
        # gap_to_leader_ms is nullable; leaving it blank is fine
        row["gap_to_leader_ms"] = ""
        df = make_df(row)
        assert ValueTypesCheck().run(make_ctx(df)) == []

    def test_int_with_trailing_dot_zero_rejected(self):
        row = minimal_row()
        row["car_number"] = "44.0"
        df = make_df(row)
        results = ValueTypesCheck().run(make_ctx(df))
        assert any("car_number" in r.message for r in results)


# ---------- TimestampLocalCheck ----------

class TestTimestampLocalCheck:
    def test_valid_with_offset(self):
        df = make_df(minimal_row())
        assert TimestampLocalCheck().run(make_ctx(df)) == []

    def test_z_suffix_rejected(self):
        row = minimal_row()
        row["session_datetime_local"] = "2025-06-08T13:40:00Z"
        df = make_df(row)
        results = TimestampLocalCheck().run(make_ctx(df))
        assert len(results) == 1
        assert "session_datetime_local" in results[0].message

    def test_naive_rejected(self):
        row = minimal_row()
        row["session_datetime_local"] = "2025-06-08 13:40:00"
        df = make_df(row)
        results = TimestampLocalCheck().run(make_ctx(df))
        assert len(results) == 1


# ---------- TimestampUtcCheck ----------

class TestTimestampUtcCheck:
    def test_valid_with_z(self):
        df = make_df(minimal_row())
        assert TimestampUtcCheck().run(make_ctx(df)) == []

    def test_offset_rejected(self):
        row = minimal_row()
        row["scraped_at"] = "2026-05-19T08:00:00+00:00"
        df = make_df(row)
        results = TimestampUtcCheck().run(make_ctx(df))
        assert len(results) == 1


# ---------- NormalizationIntegrityCheck ----------

class TestNormalizationIntegrityCheck:
    def test_valid(self):
        df = make_df(minimal_row())
        assert NormalizationIntegrityCheck().run(make_ctx(df)) == []

    def test_uppercase_in_normalized_fails(self):
        row = minimal_row()
        row["driver_full_name_normalized"] = "Nicolas Varrone"   # uppercase N
        df = make_df(row)
        results = NormalizationIntegrityCheck().run(make_ctx(df))
        assert len(results) == 1
        assert "driver_full_name_normalized" in results[0].message

    def test_wrong_separator_in_identifier_fails(self):
        row = minimal_row()
        row["team_name_normalized"] = "prema racing"  # spaces, not underscores
        df = make_df(row)
        results = NormalizationIntegrityCheck().run(make_ctx(df))
        assert len(results) == 1


# ---------- ForbiddenCharsCheck ----------

class TestForbiddenCharsCheck:
    def test_clean_passes(self):
        df = make_df(minimal_row())
        assert ForbiddenCharsCheck().run(make_ctx(df)) == []

    def test_double_quote_rejected(self):
        row = minimal_row()
        row["team_name_raw"] = 'Prema"Racing'
        df = make_df(row)
        results = ForbiddenCharsCheck().run(make_ctx(df))
        assert len(results) == 1

    def test_pipe_rejected(self):
        row = minimal_row()
        row["team_name_raw"] = "A|B"
        df = make_df(row)
        results = ForbiddenCharsCheck().run(make_ctx(df))
        assert len(results) == 1

    def test_source_url_exempt(self):
        # URLs contain `/` which is forbidden elsewhere.
        df = make_df(minimal_row())
        assert ForbiddenCharsCheck().run(make_ctx(df)) == []


# ---------- DuplicateRowsCheck ----------

class TestDuplicateRowsCheck:
    def test_no_dupes(self):
        df = make_df(minimal_row())
        assert DuplicateRowsCheck().run(make_ctx(df)) == []

    def test_exact_duplicate_detected(self):
        row = minimal_row()
        df = make_df(row, row)
        results = DuplicateRowsCheck().run(make_ctx(df))
        assert len(results) == 1


# ---------- DuplicateResultIdCheck ----------

class TestDuplicateResultIdCheck:
    def test_unique(self):
        a, b = minimal_row(), minimal_row()
        b["result_id"] = "xyz"
        b["driver_id"] = "2"
        df = make_df(a, b)
        assert DuplicateResultIdCheck().run(make_ctx(df)) == []

    def test_duplicate_id_detected(self):
        a, b = minimal_row(), minimal_row()
        # both have result_id="abc"; make them otherwise different so
        # DuplicateRowsCheck doesn't trigger
        b["driver_id"] = "2"
        df = make_df(a, b)
        results = DuplicateResultIdCheck().run(make_ctx(df))
        assert len(results) == 1
        assert "abc" in results[0].location
