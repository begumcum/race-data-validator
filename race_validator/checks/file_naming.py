"""File-naming check (§1 of the contract).

Filename must match:  <series_id>__<season_label>__<file_type>__<scraped_date>.csv

  series_id     : positive integer (the dim_series.series_id)
  season_label  : "YYYY" or "YYYY-YY"
  file_type     : "results" or "schedule"
  scraped_date  : "YYYY-MM-DD"

Examples:
  142__2025__results__2026-05-19.csv
  87__2025-26__results__2026-05-19.csv
  142__2025__schedule__2026-05-19.csv
"""

from __future__ import annotations

import re

from race_validator.checks.base import Check, ValidationContext
from race_validator.report import CheckResult, Severity


# Full filename pattern, fully anchored.
# Note the `__` (double underscore) between fields.
_FILENAME_RE = re.compile(
    r"^"
    r"(?P<series_id>\d+)"
    r"__"
    r"(?P<season_label>\d{4}(?:-\d{2})?)"
    r"__"
    r"(?P<file_type>results|schedule)"
    r"__"
    r"(?P<scraped_date>\d{4}-\d{2}-\d{2})"
    r"\.csv"
    r"$"
)


class FileNameFormatCheck(Check):
    """Filename must match the contract's strict pattern."""

    rule_id = "FILE_NAMING_001"
    contract_section = "§1"
    default_severity = Severity.ERROR
    is_blocking = True       # if we can't parse the filename, downstream is meaningless

    def run(self, ctx: ValidationContext) -> list[CheckResult]:
        name = ctx.file_path.name
        m = _FILENAME_RE.match(name)
        if not m:
            return [self.make_result(
                message=(
                    f"Filename '{name}' does not match the required pattern: "
                    "<series_id>__<season_label>__<file_type>__<scraped_date>.csv"
                ),
                fix_hint=(
                    "Example: 142__2025__results__2026-05-19.csv. "
                    "Note: DOUBLE underscores between fields, single inside."
                ),
            )]

        # Tuck the inferred file_type into context so later checks see it.
        ctx.file_type = m.group("file_type")  # type: ignore[assignment]
        return []


class FileExtensionCheck(Check):
    """Reject files that aren't .csv outright (catches .CSV, .csv.gz, .xlsx)."""

    rule_id = "FILE_NAMING_002"
    contract_section = "§1"
    default_severity = Severity.ERROR
    is_blocking = True

    def run(self, ctx: ValidationContext) -> list[CheckResult]:
        suffix = ctx.file_path.suffix
        if suffix != ".csv":
            return [self.make_result(
                message=f"File extension must be '.csv' exactly (got '{suffix}')",
                fix_hint="Rename the file with a lowercase .csv extension.",
            )]
        return []
