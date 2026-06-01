"""Schema primitives.

A schema is a list of ColumnSpec entries. Each spec says what a column is
called, what type it holds, whether it can be null, and any enum / regex
constraints. The checks read this list to validate a DataFrame.

This is deliberately simple — we are not building pandera. If you find
yourself wanting a more powerful Check, add a method to ColumnSpec.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


class ColumnType(str, Enum):
    """The physical types we use in CSVs.

    Everything starts as a string when we read the CSV (dtype=str in
    csv_io.parse_csv). The type-check phase then tries to coerce each
    value to the declared type and flags failures.
    """

    STRING = "string"           # any text
    INT = "int"                 # signed integer (Python int; mapped to INT64 in BQ)
    FLOAT = "float"             # signed float
    BOOL = "bool"               # TRUE / FALSE
    DATE = "date"               # YYYY-MM-DD
    TIMESTAMP_LOCAL = "timestamp_local"   # ISO 8601 with offset: 2025-12-13 13:00:00+08:00
    TIMESTAMP_UTC = "timestamp_utc"       # ISO 8601 with Z suffix: 2026-05-19T08:00:00Z
    COUNTRY_CODE = "country_code"         # 3-letter ISO 3166-1 alpha-3
    REGION_CODE = "region_code"           # 3-letter region from dim_regions


@dataclass(frozen=True, slots=True)
class ColumnSpec:
    name: str
    type: ColumnType
    nullable: bool = False
    # Enum constraint: value must be one of these (when non-null).
    enum: tuple[str, ...] | None = None
    # Free-form notes for documentation generation; not validated.
    notes: str | None = None
    # For normalized columns: which raw column they pair with.
    # Used by the normalization integrity check.
    normalized_of: str | None = None
    # Which normalizer to apply for normalized_of columns.
    normalizer: str | None = None  # "name" or "identifier"


@dataclass(frozen=True, slots=True)
class Schema:
    """Top-level schema for one file type."""

    file_type: str                            # "results" or "schedule"
    columns: tuple[ColumnSpec, ...]
    # Cross-column rules described declaratively. Checked by dedicated checks.
    rules: tuple = field(default_factory=tuple)

    # ---------- convenience lookups ----------

    def column_names(self) -> tuple[str, ...]:
        return tuple(c.name for c in self.columns)

    def get(self, name: str) -> ColumnSpec | None:
        for c in self.columns:
            if c.name == name:
                return c
        return None

    def normalized_columns(self) -> tuple[ColumnSpec, ...]:
        return tuple(c for c in self.columns if c.normalized_of)
