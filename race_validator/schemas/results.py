"""Schema for the `results` CSV file (§5 of the contract).

Order matters: column order in the file must match this list exactly.
"""

from __future__ import annotations

from race_validator.schemas.base import ColumnSpec, ColumnType, Schema
from race_validator.schemas.enums import (
    DRIVER_CLASSIFICATIONS,
    RACE_STATUS_VALUES,
    SESSION_TYPES,
)


RESULTS_COLUMNS: tuple[ColumnSpec, ...] = (
    # ---------- Identity & context ----------
    ColumnSpec("result_id", ColumnType.STRING),
    ColumnSpec("series_id", ColumnType.INT),
    ColumnSpec("season_label", ColumnType.STRING,
               notes='"2025" or "2025-26"'),
    ColumnSpec("round_number", ColumnType.INT),
    ColumnSpec("session_type", ColumnType.STRING, enum=SESSION_TYPES),
    ColumnSpec("session_number", ColumnType.INT),
    ColumnSpec("circuit_id", ColumnType.INT),
    ColumnSpec("session_datetime_local", ColumnType.TIMESTAMP_LOCAL),

    # ---------- Taxonomy ----------
    ColumnSpec("sport", ColumnType.STRING,
               notes="must match dim_categories.sport"),
    ColumnSpec("discipline", ColumnType.STRING,
               notes="must match dim_categories.discipline"),
    ColumnSpec("category", ColumnType.STRING,
               notes="must match dim_categories.category"),

    # ---------- Entry (car) ----------
    ColumnSpec("entry_id", ColumnType.STRING),
    ColumnSpec("car_number", ColumnType.INT),
    ColumnSpec("team_id", ColumnType.INT),
    ColumnSpec("team_name_raw", ColumnType.STRING),
    ColumnSpec("team_name_normalized", ColumnType.STRING,
               normalized_of="team_name_raw", normalizer="identifier"),
    ColumnSpec("car_model_raw", ColumnType.STRING, nullable=True),
    ColumnSpec("car_model_normalized", ColumnType.STRING, nullable=True,
               normalized_of="car_model_raw", normalizer="identifier"),

    # ---------- Driver ----------
    ColumnSpec("driver_id", ColumnType.INT),
    ColumnSpec("driver_full_name_raw", ColumnType.STRING),
    ColumnSpec("driver_full_name_normalized", ColumnType.STRING,
               normalized_of="driver_full_name_raw", normalizer="name"),
    ColumnSpec("driver_slot", ColumnType.INT,
               notes="1 for sprint, 1..N for endurance"),
    ColumnSpec("nationality_code", ColumnType.COUNTRY_CODE,
               notes="ISO 3166-1 alpha-3; must exist in dim_countries"),
    ColumnSpec("driver_classification", ColumnType.STRING, nullable=True,
               enum=DRIVER_CLASSIFICATIONS),

    # ---------- Result ----------
    ColumnSpec("race_status", ColumnType.STRING, nullable=True,
               enum=RACE_STATUS_VALUES,
               notes="NULL for non-race sessions"),
    ColumnSpec("grid_position", ColumnType.INT, nullable=True),
    ColumnSpec("position_overall", ColumnType.INT, nullable=True),
    ColumnSpec("position_in_class", ColumnType.INT, nullable=True),
    ColumnSpec("laps_completed", ColumnType.INT),
    ColumnSpec("laps_down", ColumnType.INT, nullable=True),
    ColumnSpec("race_time_ms", ColumnType.INT, nullable=True),
    ColumnSpec("gap_to_leader_ms", ColumnType.INT, nullable=True),
    ColumnSpec("gap_to_leader_display", ColumnType.STRING, nullable=True),
    ColumnSpec("interval_to_ahead_ms", ColumnType.INT, nullable=True),
    ColumnSpec("interval_to_ahead_display", ColumnType.STRING, nullable=True),
    ColumnSpec("best_lap_time_ms", ColumnType.INT, nullable=True),
    ColumnSpec("best_lap_number", ColumnType.INT, nullable=True),
    ColumnSpec("best_lap_speed_kph", ColumnType.FLOAT, nullable=True),
    ColumnSpec("is_pole", ColumnType.BOOL),
    ColumnSpec("is_fastest_lap_overall", ColumnType.BOOL),
    ColumnSpec("is_fastest_lap_in_class", ColumnType.BOOL),

    # ---------- Lineage ----------
    ColumnSpec("source_url", ColumnType.STRING),
    ColumnSpec("source_collector", ColumnType.STRING),
    ColumnSpec("scraped_at", ColumnType.TIMESTAMP_UTC),
    ColumnSpec("ingested_at", ColumnType.TIMESTAMP_UTC, nullable=True,
               notes="left blank in CSV; pipeline populates"),
)


RESULTS_SCHEMA = Schema(
    file_type="results",
    columns=RESULTS_COLUMNS,
)
