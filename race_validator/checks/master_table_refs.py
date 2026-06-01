"""Master-table reference checks (§4 of the contract).

Each row's IDs and codes must exist in the bundled reference data:
  - country_id (nationality_code) → dim_countries
  - circuit_id                    → dim_circuits
  - series_id                     → dim_series
  - (sport, discipline, category) → dim_categories (composite triple)

This is the heaviest check at runtime, so it stops at MAX_EXAMPLES per
column to keep the report compact. The summary count is always accurate.
"""

from __future__ import annotations

from race_validator.adapters import bundled_data as bd
from race_validator.checks.base import Check, ValidationContext
from race_validator.report import CheckResult, Severity


_MAX_EXAMPLES = 5


class MasterTableRefsCheck(Check):
    """Every ID/code on each row must be present in the bundled dim tables."""

    rule_id = "MASTER_REF_001"
    contract_section = "§4"
    default_severity = Severity.ERROR

    def run(self, ctx: ValidationContext) -> list[CheckResult]:
        if ctx.df is None or ctx.file_type is None:
            return []

        results: list[CheckResult] = []

        # series_id, circuit_id (both file types have these)
        if "series_id" in ctx.df.columns:
            results.extend(self._scalar_check(
                ctx, "series_id", bd.series_id_set(), "dim_series",
                hint="Ask Berkay to add this series to dim_series.csv "
                     "(it's bundled — needs a new library release).",
            ))
        if "circuit_id" in ctx.df.columns:
            results.extend(self._scalar_check(
                ctx, "circuit_id", bd.circuit_id_set(), "dim_circuits",
                hint="Ask Berkay to add this circuit to dim_circuits.csv.",
            ))

        # nationality_code (results only)
        if "nationality_code" in ctx.df.columns:
            results.extend(self._scalar_check(
                ctx, "nationality_code", bd.country_id_set(), "dim_countries",
                hint="Use a valid ISO 3166-1 alpha-3 code. "
                     "Check dim_countries.csv for the canonical list.",
            ))

        # (sport, discipline, category) triple
        triple_cols = ("sport", "discipline", "category")
        if all(c in ctx.df.columns for c in triple_cols):
            results.extend(self._triple_check(ctx, triple_cols))

        return results

    # ---------- helpers ----------

    def _scalar_check(
        self,
        ctx: ValidationContext,
        column: str,
        valid_set: frozenset[str],
        dim_name: str,
        *,
        hint: str,
    ) -> list[CheckResult]:
        bad: list[tuple[int, str]] = []
        for row_idx, value in enumerate(ctx.df[column]):
            value = "" if value is None else str(value)
            if value == "":
                continue  # nullability is value_types' job
            if value not in valid_set:
                bad.append((row_idx + 1, value))

        if not bad:
            return []

        examples = bad[:_MAX_EXAMPLES]
        unique_bad = sorted({v for _, v in bad})
        example_str = "; ".join(f"row {r}: '{v}'" for r, v in examples)
        more = f" (+{len(bad) - _MAX_EXAMPLES} more rows)" if len(bad) > _MAX_EXAMPLES else ""

        return [self.make_result(
            message=(
                f"Column '{column}' has {len(bad)} row(s) with value(s) "
                f"not found in {dim_name}: {', '.join(unique_bad[:10])}"
                + (f" (+{len(unique_bad) - 10} more values)" if len(unique_bad) > 10 else "")
            ),
            location=f"{example_str}{more}",
            fix_hint=hint,
        )]

    def _triple_check(
        self,
        ctx: ValidationContext,
        cols: tuple[str, str, str],
    ) -> list[CheckResult]:
        valid_triples = bd.category_triple_set()
        bad: list[tuple[int, tuple[str, str, str]]] = []

        for row_idx in range(len(ctx.df)):
            row_number = row_idx + 1
            triple = tuple(
                ("" if ctx.df.iloc[row_idx][c] is None
                 else str(ctx.df.iloc[row_idx][c]))
                for c in cols
            )
            if any(v == "" for v in triple):
                continue  # let value_types handle blanks
            if triple not in valid_triples:
                bad.append((row_number, triple))  # type: ignore[arg-type]

        if not bad:
            return []

        unique_bad = sorted({t for _, t in bad})
        examples = bad[:_MAX_EXAMPLES]
        example_str = "; ".join(
            f"row {r}: {'/'.join(t)}" for r, t in examples
        )
        more = f" (+{len(bad) - _MAX_EXAMPLES} more rows)" if len(bad) > _MAX_EXAMPLES else ""

        return [CheckResult(
            severity=self.default_severity,
            rule_id="MASTER_REF_002",
            contract_section=self.contract_section,
            message=(
                f"{len(bad)} row(s) have (sport, discipline, category) "
                f"triples not in dim_categories. Unique bad triples: "
                f"{', '.join('/'.join(t) for t in unique_bad[:5])}"
                + (f" (+{len(unique_bad) - 5} more)" if len(unique_bad) > 5 else "")
            ),
            location=f"{example_str}{more}",
            fix_hint=(
                "Either fix the row to use a valid taxonomy triple, or ask "
                "Berkay to extend dim_categories.csv if this is a genuinely "
                "new combination."
            ),
        )]
