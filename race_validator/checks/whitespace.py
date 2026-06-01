"""Whitespace check (§3 of the contract).

Text values must not have:
  - Leading whitespace
  - Trailing whitespace
  - Double spaces inside

Applies to all STRING-typed columns.
"""

from __future__ import annotations

import re

from race_validator.checks.base import Check, ValidationContext
from race_validator.report import CheckResult
from race_validator.schemas import get_schema
from race_validator.schemas.base import ColumnType


_MAX_EXAMPLES = 5
_DOUBLE_SPACE = re.compile(r"  +")


class WhitespaceCheck(Check):
    """Text fields: no leading/trailing whitespace, no double spaces."""

    rule_id = "WHITESPACE_001"
    contract_section = "§3"

    def run(self, ctx: ValidationContext) -> list[CheckResult]:
        if ctx.df is None or ctx.file_type is None:
            return []

        schema = get_schema(ctx.file_type)
        results: list[CheckResult] = []

        for spec in schema.columns:
            if spec.type != ColumnType.STRING:
                continue
            if spec.name not in ctx.df.columns:
                continue

            bad: list[tuple[int, str, str]] = []  # (row, value, kind)
            for row_idx, value in enumerate(ctx.df[spec.name]):
                value = "" if value is None else str(value)
                if value == "":
                    continue
                row_number = row_idx + 1
                if value != value.strip():
                    bad.append((row_number, value, "leading/trailing whitespace"))
                elif _DOUBLE_SPACE.search(value):
                    bad.append((row_number, value, "double space inside"))

            if bad:
                examples = bad[:_MAX_EXAMPLES]
                example_str = "; ".join(
                    f"row {r}: {kind} in '{v}'" for r, v, kind in examples
                )
                more = f" (+{len(bad) - _MAX_EXAMPLES} more)" if len(bad) > _MAX_EXAMPLES else ""
                results.append(self.make_result(
                    message=(
                        f"Column '{spec.name}' has {len(bad)} value(s) "
                        f"with extra whitespace"
                    ),
                    location=f"{example_str}{more}",
                    fix_hint=(
                        "Trim leading/trailing whitespace and collapse "
                        "internal multiple spaces in the scraper output."
                    ),
                ))
        return results
