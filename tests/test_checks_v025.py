"""Tests for new v0.2.5 checks:
   - whitespace
   - blank rows / unnamed columns
   - cross-field NULL rules (race_status, race_time_ms, gap_to_leader_ms)
   - pole uniqueness, fastest lap uniqueness
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from race_validator.checks.base import ValidationContext
from race_validator.checks.cross_field import (
    GapToLeaderConsistencyCheck,
    RaceStatusConsistencyCheck,
    RaceTimeConsistencyCheck,
)
from race_validator.checks.pole_fastest import (
    FastestLapInClassCheck,
    FastestLapOverallCheck,
    PoleUniquenessCheck,
)
from race_validator.checks.structure import (
    BlankRowsCheck,
    UnnamedColumnsCheck,
)
from race_validator.checks.whitespace import WhitespaceCheck
from race_validator.schemas import RESULTS_SCHEMA


def make_ctx(df: pd.DataFrame, file_type: str = "results") -> ValidationContext:
    return ValidationContext(
        file_path=Path("142__2025__results__2026-05-19.csv"),
        df=df,
        file_type=file_type,
    )


def minimal_row(**overrides) -> dict:
    row = {
        "result_id": "abc",
        "series_id": "1", "season_label": "2025",
        "round_number": "1", "session_type": "race", "session_number": "1",
        "circuit_id": "1",
        "session_datetime_local": "2025-06-08T13:40:00+01:00",
        "sport": "motorsport", "discipline": "single_seater", "category": "formula_4",
        "entry_id": "e1", "car_number": "44", "team_id": "1",
        "team_name_raw": "Prema Racing", "team_name_normalized": "prema_racing",
        "car_model_raw": "", "car_model_normalized": "",
        "driver_id": "1",
        "driver_full_name_raw": "Driver One",
        "driver_full_name_normalized": "driver one",
        "driver_slot": "1", "nationality_code": "ARG",
        "driver_classification": "",
        "race_status": "FINISHED",
        "grid_position": "1", "position_overall": "1", "position_in_class": "1",
        "laps_completed": "30", "laps_down": "0",
        "race_time_ms": "1800000",
        "gap_to_leader_ms": "", "gap_to_leader_display": "",
        "interval_to_ahead_ms": "", "interval_to_ahead_display": "",
        "best_lap_time_ms": "60000", "best_lap_number": "5", "best_lap_speed_kph": "210.5",
        "is_pole": "TRUE", "is_fastest_lap_overall": "FALSE", "is_fastest_lap_in_class": "FALSE",
        "source_url": "https://example.com/x", "source_collector": "berkay",
        "scraped_at": "2026-05-19T08:00:00Z", "ingested_at": "",
    }
    row.update(overrides)
    return row


def make_df(*rows: dict) -> pd.DataFrame:
    cols = RESULTS_SCHEMA.column_names()
    return pd.DataFrame(rows, columns=cols)


# ---------- WhitespaceCheck ----------

class TestWhitespaceCheck:
    def test_clean_passes(self):
        df = make_df(minimal_row())
        assert WhitespaceCheck().run(make_ctx(df)) == []

    def test_leading_space_fails(self):
        df = make_df(minimal_row(driver_full_name_raw=" Lewis Hamilton"))
        assert len(WhitespaceCheck().run(make_ctx(df))) == 1

    def test_trailing_space_fails(self):
        df = make_df(minimal_row(team_name_raw="Prema Racing "))
        assert len(WhitespaceCheck().run(make_ctx(df))) == 1

    def test_double_space_inside_fails(self):
        df = make_df(minimal_row(driver_full_name_raw="Lewis  Hamilton"))
        assert len(WhitespaceCheck().run(make_ctx(df))) == 1


# ---------- BlankRowsCheck ----------

class TestBlankRowsCheck:
    def test_no_blank(self):
        df = make_df(minimal_row())
        assert BlankRowsCheck().run(make_ctx(df)) == []

    def test_one_blank(self):
        cols = RESULTS_SCHEMA.column_names()
        blank = {c: "" for c in cols}
        df = make_df(minimal_row(), blank)
        results = BlankRowsCheck().run(make_ctx(df))
        assert len(results) == 1
        assert "1 fully blank" in results[0].message


# ---------- UnnamedColumnsCheck ----------

class TestUnnamedColumnsCheck:
    def test_clean(self):
        df = make_df(minimal_row())
        assert UnnamedColumnsCheck().run(make_ctx(df)) == []

    def test_unnamed_pandas_default(self):
        df = make_df(minimal_row())
        df["Unnamed: 99"] = ""
        results = UnnamedColumnsCheck().run(make_ctx(df))
        assert len(results) == 1

    def test_empty_header(self):
        df = make_df(minimal_row())
        df[""] = ""
        results = UnnamedColumnsCheck().run(make_ctx(df))
        assert len(results) == 1


# ---------- RaceStatusConsistencyCheck ----------

class TestRaceStatusConsistencyCheck:
    def test_race_with_status_ok(self):
        df = make_df(minimal_row())
        assert RaceStatusConsistencyCheck().run(make_ctx(df)) == []

    def test_practice_without_status_ok(self):
        df = make_df(minimal_row(
            session_type="practice",
            race_status="",
            race_time_ms="",
            grid_position="",
            position_overall="",
            position_in_class="",
            laps_completed="20",
            laps_down="",
            is_pole="FALSE",
        ))
        assert RaceStatusConsistencyCheck().run(make_ctx(df)) == []

    def test_practice_with_status_fails(self):
        df = make_df(minimal_row(session_type="practice", race_status="FINISHED"))
        results = RaceStatusConsistencyCheck().run(make_ctx(df))
        assert len(results) >= 1
        assert any("non-race" in r.message for r in results)

    def test_race_without_status_fails(self):
        df = make_df(minimal_row(race_status=""))
        results = RaceStatusConsistencyCheck().run(make_ctx(df))
        assert any("empty race_status" in r.message for r in results)


# ---------- RaceTimeConsistencyCheck ----------

class TestRaceTimeConsistencyCheck:
    def test_finisher_with_time_ok(self):
        df = make_df(minimal_row())
        assert RaceTimeConsistencyCheck().run(make_ctx(df)) == []

    def test_finisher_without_time_fails(self):
        df = make_df(minimal_row(race_status="FINISHED", race_time_ms=""))
        results = RaceTimeConsistencyCheck().run(make_ctx(df))
        assert any("missing race_time_ms" in r.message for r in results)

    def test_dnf_with_time_fails(self):
        df = make_df(minimal_row(race_status="DNF", race_time_ms="1800000"))
        results = RaceTimeConsistencyCheck().run(make_ctx(df))
        assert any("non-finisher" in r.message for r in results)

    def test_dnf_without_time_ok(self):
        df = make_df(minimal_row(
            race_status="DNF",
            race_time_ms="",
            position_overall="",
            laps_completed="5",
            laps_down="",
        ))
        assert RaceTimeConsistencyCheck().run(make_ctx(df)) == []

    def test_practice_without_time_ok(self):
        df = make_df(minimal_row(
            session_type="practice",
            race_status="",
            race_time_ms="",
            grid_position="",
            position_overall="",
            position_in_class="",
            laps_completed="20",
            laps_down="",
            is_pole="FALSE",
        ))
        assert RaceTimeConsistencyCheck().run(make_ctx(df)) == []


# ---------- GapToLeaderConsistencyCheck ----------

class TestGapToLeaderConsistencyCheck:
    def test_p1_no_gap_ok(self):
        df = make_df(minimal_row(position_overall="1", gap_to_leader_ms=""))
        assert GapToLeaderConsistencyCheck().run(make_ctx(df)) == []

    def test_p1_with_gap_fails(self):
        df = make_df(minimal_row(position_overall="1", gap_to_leader_ms="0"))
        results = GapToLeaderConsistencyCheck().run(make_ctx(df))
        assert len(results) == 1

    def test_p2_with_gap_ok(self):
        df = make_df(minimal_row(
            position_overall="2",
            gap_to_leader_ms="1500",
            grid_position="2",
            position_in_class="2",
            is_pole="FALSE",
        ))
        assert GapToLeaderConsistencyCheck().run(make_ctx(df)) == []


# ---------- PoleUniquenessCheck ----------

class TestPoleUniquenessCheck:
    def test_one_pole_ok(self):
        df = make_df(
            minimal_row(driver_id="1", is_pole="TRUE", position_overall="1"),
            minimal_row(driver_id="2", is_pole="FALSE", position_overall="2",
                        grid_position="2", position_in_class="2",
                        gap_to_leader_ms="1500", result_id="def"),
        )
        assert PoleUniquenessCheck().run(make_ctx(df)) == []

    def test_no_pole_fails(self):
        df = make_df(
            minimal_row(driver_id="1", is_pole="FALSE", position_overall="1"),
        )
        results = PoleUniquenessCheck().run(make_ctx(df))
        assert any("no row with is_pole=TRUE" in r.message for r in results)

    def test_two_pole_fails(self):
        df = make_df(
            minimal_row(driver_id="1", is_pole="TRUE", position_overall="1"),
            minimal_row(driver_id="2", is_pole="TRUE", position_overall="2",
                        grid_position="2", position_in_class="2",
                        gap_to_leader_ms="1500", result_id="def"),
        )
        results = PoleUniquenessCheck().run(make_ctx(df))
        assert any("more than one is_pole=TRUE" in r.message for r in results)

    def test_dns_pole_fails(self):
        df = make_df(
            minimal_row(
                driver_id="1", is_pole="TRUE",
                race_status="DNS", race_time_ms="",
                position_overall="", grid_position="1",
            ),
        )
        results = PoleUniquenessCheck().run(make_ctx(df))
        assert any("race_status=DNS" in r.message for r in results)

    def test_practice_session_not_checked(self):
        """Only race sessions are subject to the pole rule."""
        df = make_df(minimal_row(
            session_type="practice",
            race_status="",
            race_time_ms="",
            grid_position="",
            position_overall="",
            position_in_class="",
            is_pole="FALSE",
            laps_completed="20",
            laps_down="",
        ))
        assert PoleUniquenessCheck().run(make_ctx(df)) == []


# ---------- FastestLapOverallCheck ----------

class TestFastestLapOverallCheck:
    def test_one_overall_ok(self):
        df = make_df(
            minimal_row(driver_id="1", is_fastest_lap_overall="TRUE"),
            minimal_row(driver_id="2", is_fastest_lap_overall="FALSE",
                        position_overall="2", grid_position="2",
                        position_in_class="2",
                        gap_to_leader_ms="1500", is_pole="FALSE",
                        result_id="def"),
        )
        assert FastestLapOverallCheck().run(make_ctx(df)) == []

    def test_zero_overall_ok(self):
        df = make_df(minimal_row(is_fastest_lap_overall="FALSE"))
        assert FastestLapOverallCheck().run(make_ctx(df)) == []

    def test_two_overall_fails(self):
        df = make_df(
            minimal_row(driver_id="1", is_fastest_lap_overall="TRUE"),
            minimal_row(driver_id="2", is_fastest_lap_overall="TRUE",
                        position_overall="2", grid_position="2",
                        position_in_class="2",
                        gap_to_leader_ms="1500", is_pole="FALSE",
                        result_id="def"),
        )
        assert len(FastestLapOverallCheck().run(make_ctx(df))) == 1


# ---------- FastestLapInClassCheck ----------

class TestFastestLapInClassCheck:
    def test_one_per_class_ok(self):
        df = make_df(
            minimal_row(driver_id="1",
                        category="formula_4",
                        is_fastest_lap_in_class="TRUE"),
            minimal_row(driver_id="2",
                        category="formula_4",
                        is_fastest_lap_in_class="FALSE",
                        position_overall="2", grid_position="2",
                        position_in_class="2",
                        gap_to_leader_ms="1500", is_pole="FALSE",
                        result_id="def"),
            # Different class — its own fastest is allowed
            minimal_row(driver_id="3",
                        category="formula_regional",
                        is_fastest_lap_in_class="TRUE",
                        position_overall="3", grid_position="3",
                        position_in_class="1",
                        gap_to_leader_ms="3000", is_pole="FALSE",
                        result_id="ghi"),
        )
        assert FastestLapInClassCheck().run(make_ctx(df)) == []

    def test_two_in_same_class_fails(self):
        df = make_df(
            minimal_row(driver_id="1",
                        is_fastest_lap_in_class="TRUE"),
            minimal_row(driver_id="2",
                        is_fastest_lap_in_class="TRUE",
                        position_overall="2", grid_position="2",
                        position_in_class="2",
                        gap_to_leader_ms="1500", is_pole="FALSE",
                        result_id="def"),
        )
        assert len(FastestLapInClassCheck().run(make_ctx(df))) == 1
