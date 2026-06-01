"""Schema definitions for race-results CSV files."""

from race_validator.schemas.base import ColumnSpec, ColumnType, Schema
from race_validator.schemas.enums import (
    DRIVER_CLASSIFICATIONS,
    GENDERS,
    RACE_STATUS_VALUES,
    SCOPES,
    SESSION_TYPES,
)
from race_validator.schemas.results import RESULTS_SCHEMA
from race_validator.schemas.schedule import SCHEDULE_SCHEMA


def get_schema(file_type: str) -> Schema:
    """Look up the schema for a file type string."""
    if file_type == "results":
        return RESULTS_SCHEMA
    if file_type == "schedule":
        return SCHEDULE_SCHEMA
    raise ValueError(f"Unknown file_type: {file_type!r}")


__all__ = [
    "ColumnSpec",
    "ColumnType",
    "Schema",
    "RESULTS_SCHEMA",
    "SCHEDULE_SCHEMA",
    "get_schema",
    "RACE_STATUS_VALUES",
    "SESSION_TYPES",
    "SCOPES",
    "DRIVER_CLASSIFICATIONS",
    "GENDERS",
]
