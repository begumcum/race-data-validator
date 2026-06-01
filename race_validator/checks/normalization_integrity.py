"""Normalization integrity check (§3a of the contract).

For each column ending in `_normalized` that has a `normalized_of` and
`normalizer` declared in the schema, verify the value equals the canonical
normalizer output applied to the companion column.

This is what stops collectors from "improving" normalization on their own.
"""

from __future__ import annotations

from race_validator.checks.base import Check, ValidationContext
from race_validator.normalize import normalize_identifier, normalize_name
from race_validator.report import CheckResult, Severity
from race_validator.schemas import get_schema


_MAX_EXAMPLES = 5


class NormalizationIntegrityCheck(Check):
    """`_normalized` columns must match the canonical normalizer's output."""

    rule_id = "NORMALIZATION_001"
    contract_section = "§3a"
    default_severity = Severity.ERROR

    def run(self, ctx: ValidationContext) -> list[CheckResult]:
        if ctx.df is None or ctx.file_type is None:
            return []

        schema = get_schema(ctx.file_type)
        results: list[CheckResult] = []

        for spec in schema.normalized_columns():
            source_col = spec.normalized_of
            normalizer_name = spec.normalizer
            if not source_col or not normalizer_name:
                continue
            if source_col not in ctx.df.columns or spec.name not in ctx.df.columns:
                continue

            fn = normalize_name if normalizer_name == "name" else normalize_identifier
            bad: list[tuple[int, str, str, str]] = []

            for row_idx in range(len(ctx.df)):
                raw = ctx.df.iloc[row_idx][source_col]
                norm = ctx.df.iloc[row_idx][spec.name]
                raw = "" if raw is None else str(raw)
                norm = "" if norm is None else str(norm)

                # If raw is blank, normalized must also be blank.
                if raw == "":
                    if norm != "":
                        bad.append((row_idx + 1, raw, norm, ""))
                    continue

                # Compute the canonical output. Catch ValueError from the
                # normalizer (e.g. too-long input).
                try:
                    expected = fn(raw)
                except ValueError:
                    # The normalizer rejected the raw input. That's a separate
                    # error class - flagging here keeps it visible.
                    bad.append((row_idx + 1, raw, norm,
                                "<rejected by normalizer>"))
                    continue

                if norm != expected:
                    bad.append((row_idx + 1, raw, norm, expected))

            if bad:
                examples = bad[:_MAX_EXAMPLES]
                example_str = "; ".join(
                    f"row {r}: raw='{raw}' has normalized='{norm}' "
                    f"but should be '{exp}'"
                    for r, raw, norm, exp in examples
                )
                more = f" (+{len(bad) - _MAX_EXAMPLES} more)" if len(bad) > _MAX_EXAMPLES else ""

                results.append(self.make_result(
                    message=(
                        f"Column '{spec.name}' has {len(bad)} value(s) that "
                        f"don't match the canonical {normalizer_name} normalizer "
                        f"applied to '{source_col}'"
                    ),
                    location=f"{example_str}{more}",
                    fix_hint=(
                        f"Use race_validator.normalize.normalize_{normalizer_name}() "
                        f"to produce '{spec.name}' from '{source_col}'. "
                        f"Do not roll your own normalization."
                    ),
                ))

        return results
