"""Structural checks (§1 of the contract).

Catches degenerate CSV structures that survive parsing but indicate
scraper bugs:

  - Fully blank rows (every cell empty)
  - Unnamed columns (empty header or pandas 'Unnamed: N' default)
"""

from __future__ import annotations

import re

from race_validator.checks.base import Check, ValidationContext
from race_validator.report import CheckResult


_UNNAMED_RE = re.compile(r"^Unnamed:\s*\d+$")


class BlankRowsCheck(Check):
    """No row may be fully blank."""

    rule_id = "STRUCTURE_001"
    contract_section = "§1"

    def run(self, ctx: ValidationContext) -> list[CheckResult]:
        if ctx.df is None:
            return []

        blank_rows: list[int] = []
        for row_idx in range(len(ctx.df)):
            row = ctx.df.iloc[row_idx]
            if all(("" if v is None else str(v).strip()) == "" for v in row):
                blank_rows.append(row_idx + 1)

        if not blank_rows:
            return []

        return [self.make_result(
            message=f"{len(blank_rows)} fully blank row(s) found",
            location=(
                "rows " + ", ".join(str(r) for r in blank_rows[:5])
                + (f" (+{len(blank_rows) - 5} more)" if len(blank_rows) > 5 else "")
            ),
            fix_hint=(
                "Remove blank rows in the scraper. Common cause: a pandas "
                "to_csv that left trailing newlines, or a row separator "
                "that produced empty rows."
            ),
        )]


class UnnamedColumnsCheck(Check):
    """No column header may be empty or pandas-default 'Unnamed: N'."""

    rule_id = "STRUCTURE_002"
    contract_section = "§1"

    def run(self, ctx: ValidationContext) -> list[CheckResult]:
        if ctx.df is None:
            return []

        bad: list[tuple[int, str]] = []
        for i, col in enumerate(ctx.df.columns):
            name = str(col).strip()
            if name == "" or _UNNAMED_RE.match(name):
                bad.append((i + 1, str(col)))

        if not bad:
            return []

        return [self.make_result(
            message=f"{len(bad)} unnamed column(s) in header",
            location="; ".join(
                f"position {pos}: '{name}'" for pos, name in bad
            ),
            fix_hint=(
                "Every column needs a non-empty snake_case header. "
                "Common cause: a trailing comma in the header row, or a "
                "scraper that emits an extra empty column at the end."
            ),
        )]
