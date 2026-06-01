"""Duplicate-row checks (§8 of the contract).

Two distinct rules:
  - No fully-identical rows
  - No duplicate result_id values (the natural-key hash must be unique)
"""

from __future__ import annotations

from race_validator.checks.base import Check, ValidationContext
from race_validator.report import CheckResult, Severity


class DuplicateRowsCheck(Check):
    """Two rows with identical values everywhere is a scraper bug."""

    rule_id = "DUPLICATE_001"
    contract_section = "§8"
    default_severity = Severity.ERROR

    def run(self, ctx: ValidationContext) -> list[CheckResult]:
        if ctx.df is None:
            return []
        dupes = ctx.df[ctx.df.duplicated(keep=False)]
        if dupes.empty:
            return []
        # Group by all columns to count occurrences
        n_dupes = len(dupes)
        n_groups = len(ctx.df[ctx.df.duplicated(keep="first")])

        sample_rows = sorted(dupes.index[:10] + 1)
        sample_str = ", ".join(str(r) for r in sample_rows)

        return [self.make_result(
            message=(
                f"{n_dupes} rows are exact duplicates across all columns "
                f"({n_groups} duplicate row(s) beyond the first occurrence)"
            ),
            location=f"sample rows: {sample_str}",
            fix_hint=(
                "Check the scraper for double-emit bugs. Common cause: "
                "iterating both the visible table and a hidden one on the same page."
            ),
        )]


class DuplicateResultIdCheck(Check):
    """result_id must be unique across the file."""

    rule_id = "DUPLICATE_002"
    contract_section = "§8"
    default_severity = Severity.ERROR

    applies_to_schedule = False  # schedule has no result_id

    def run(self, ctx: ValidationContext) -> list[CheckResult]:
        if ctx.df is None or "result_id" not in ctx.df.columns:
            return []

        seen: dict[str, list[int]] = {}
        for row_idx, value in enumerate(ctx.df["result_id"]):
            v = "" if value is None else str(value)
            if v == "":
                continue
            seen.setdefault(v, []).append(row_idx + 1)

        dupes = {k: v for k, v in seen.items() if len(v) > 1}
        if not dupes:
            return []

        n_dupes = sum(len(v) for v in dupes.values())
        examples = list(dupes.items())[:3]
        example_str = "; ".join(
            f"'{rid}' appears at rows {', '.join(str(r) for r in rows)}"
            for rid, rows in examples
        )
        more = f" (+{len(dupes) - 3} more duplicate IDs)" if len(dupes) > 3 else ""

        return [self.make_result(
            message=(
                f"{n_dupes} row(s) share a result_id with another row; "
                f"{len(dupes)} unique result_id value(s) are duplicated"
            ),
            location=f"{example_str}{more}",
            fix_hint=(
                "result_id must uniquely identify each (series, season, "
                "round, session, entry, driver). Two rows with the same "
                "result_id mean either a duplicate row or a result_id "
                "generation bug."
            ),
        )]
