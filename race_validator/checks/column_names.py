"""Column name and order checks (§2 of the contract).

These two checks need the parsed DataFrame, so they run after the
file is read. They use the schema declared in race_validator.schemas.
"""

from __future__ import annotations

from race_validator.checks.base import Check, ValidationContext
from race_validator.report import CheckResult, Severity
from race_validator.schemas import get_schema


class ColumnNamesCheck(Check):
    """Headers must be exactly the schema's column names (set equality)."""

    rule_id = "COLUMN_NAMES_001"
    contract_section = "§2"
    default_severity = Severity.ERROR

    def run(self, ctx: ValidationContext) -> list[CheckResult]:
        if ctx.df is None or ctx.file_type is None:
            return []

        expected = set(get_schema(ctx.file_type).column_names())
        actual = set(ctx.df.columns)

        missing = sorted(expected - actual)
        extra = sorted(actual - expected)
        results: list[CheckResult] = []

        if missing:
            results.append(self.make_result(
                message=f"Missing required columns: {', '.join(missing)}",
                fix_hint=(
                    "Add these columns to your scraper output. Check the "
                    "contract §5 for the full results schema."
                ),
            ))
        if extra:
            results.append(self.make_result(
                message=f"Unexpected columns present: {', '.join(extra)}",
                fix_hint=(
                    "Remove these columns. The CSV must contain only the "
                    "columns defined in the contract. Common cause: header "
                    "typos (e.g. 'Driver Name' instead of 'driver_full_name_raw')."
                ),
            ))
        return results


class ColumnOrderCheck(Check):
    """Headers must appear in the schema's exact order."""

    rule_id = "COLUMN_NAMES_002"
    contract_section = "§2"
    default_severity = Severity.ERROR

    def run(self, ctx: ValidationContext) -> list[CheckResult]:
        if ctx.df is None or ctx.file_type is None:
            return []

        expected = list(get_schema(ctx.file_type).column_names())
        actual = list(ctx.df.columns)

        # Only meaningful if the SET of names matches; otherwise let the
        # names check produce the clearer error and skip.
        if set(actual) != set(expected):
            return []

        if actual == expected:
            return []

        # Build a list of the first 3 misplaced columns to keep the message readable
        wrong: list[tuple[int, str, str]] = []
        for i, (got, want) in enumerate(zip(actual, expected)):
            if got != want:
                wrong.append((i + 1, got, want))
            if len(wrong) >= 3:
                break

        diff_str = "; ".join(
            f"position {pos}: got '{got}', expected '{want}'"
            for pos, got, want in wrong
        )

        return [self.make_result(
            message=f"Column order is wrong. {diff_str}",
            fix_hint=(
                "Reorder the columns to match the contract's exact sequence. "
                "Order is part of the schema, not just the names."
            ),
        )]
