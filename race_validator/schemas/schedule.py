"""Schema for the `schedule` CSV file (§7 of the contract).

A schedule row is a planned session — no driver, no team, no result.
"""

from __future__ import annotations

from race_validator.schemas.base import ColumnSpec, ColumnType, Schema
from race_validator.schemas.enums import SESSION_TYPES


SCHEDULE_COLUMNS: tuple[ColumnSpec, ...] = (
    ColumnSpec("series_id", ColumnType.INT),
    ColumnSpec("season_label", ColumnType.STRING),
    ColumnSpec("round_number", ColumnType.INT),
    ColumnSpec("session_type", ColumnType.STRING, enum=SESSION_TYPES),
    ColumnSpec("session_number", ColumnType.INT),
    ColumnSpec("circuit_id", ColumnType.INT),
    ColumnSpec("session_datetime_local", ColumnType.TIMESTAMP_LOCAL),
    ColumnSpec("sport", ColumnType.STRING),
    ColumnSpec("discipline", ColumnType.STRING),
    ColumnSpec("category", ColumnType.STRING),
    ColumnSpec("planned_duration_minutes", ColumnType.INT, nullable=True),
    ColumnSpec("source_url", ColumnType.STRING),
    ColumnSpec("source_collector", ColumnType.STRING),
    ColumnSpec("scraped_at", ColumnType.TIMESTAMP_UTC),
)


SCHEDULE_SCHEMA = Schema(
    file_type="schedule",
    columns=SCHEDULE_COLUMNS,
)
