"""Value-type and nullability checks (§3 of the contract).

For each column in the parsed DataFrame, this check:
  1. Verifies every value is parseable as the declared type
  2. Verifies the column's nullability rule (empty string = NULL)
  3. Verifies enum constraints when present

Each violating row produces one CheckResult so the collector sees
exactly which rows are wrong.
"""

from __future__ import annotations

import re

from race_validator.checks.base import Check, ValidationContext
from race_validator.report import CheckResult, Severity
from race_validator.schemas import get_schema
from race_validator.schemas.base import ColumnSpec, ColumnType


# How many bad-value examples to show per column before truncating.
_MAX_EXAMPLES_PER_COLUMN = 5

# Regex patterns reused below.
_INT_RE = re.compile(r"^-?\d+$")
_FLOAT_RE = re.compile(r"^-?(\d+\.\d+|\d+\.|\.\d+|\d+)([eE][+-]?\d+)?$")
_DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
_COUNTRY_CODE_RE = re.compile(r"^[A-Z]{3}$")


def _is_empty(v) -> bool:
    return v is None or v == ""


def _coerce_int(v: str) -> bool:
    if not _INT_RE.match(v):
        return False
    # Forbid integers written like "17.0"
    return "." not in v


def _coerce_float(v: str) -> bool:
    return bool(_FLOAT_RE.match(v))


def _coerce_bool(v: str) -> bool:
    return v in ("TRUE", "FALSE")


def _coerce_date(v: str) -> bool:
    if not _DATE_RE.match(v):
        return False
    # Cheap sanity check on the parts
    y, m, d = v.split("-")
    return 1 <= int(m) <= 12 and 1 <= int(d) <= 31


def _coerce_country_code(v: str) -> bool:
    return bool(_COUNTRY_CODE_RE.match(v))


class ValueTypesCheck(Check):
    """Validate every value's type, nullability, and enum constraint."""

    rule_id = "VALUE_TYPE_001"
    contract_section = "§3"
    default_severity = Severity.ERROR

    def run(self, ctx: ValidationContext) -> list[CheckResult]:
        if ctx.df is None or ctx.file_type is None:
            return []

        schema = get_schema(ctx.file_type)
        results: list[CheckResult] = []

        for spec in schema.columns:
            if spec.name not in ctx.df.columns:
                # ColumnNamesCheck already reported this. Skip silently here.
                continue
            results.extend(self._check_column(ctx, spec))

        return results

    # ---------- per-column ----------

    def _check_column(
        self, ctx: ValidationContext, spec: ColumnSpec
    ) -> list[CheckResult]:
        series = ctx.df[spec.name]
        type_violations: list[tuple[int, str]] = []   # (row_number, value)
        null_violations: list[int] = []
        enum_violations: list[tuple[int, str]] = []

        for row_idx, value in enumerate(series):
            # row_idx is 0-based in the data; row_number is 1-based AND
            # excludes the header. So row 1 = first data row.
            row_number = row_idx + 1
            value = "" if value is None else str(value)

            # Null handling first
            if _is_empty(value):
                if not spec.nullable:
                    null_violations.append(row_number)
                continue  # nothing else to check on a blank

            # Type coercion
            if not self._value_parses_as_type(value, spec.type):
                type_violations.append((row_number, value))
                continue

            # Enum constraint (skipped when type didn't parse)
            if spec.enum is not None and value not in spec.enum:
                enum_violations.append((row_number, value))

        out: list[CheckResult] = []

        if null_violations:
            out.append(self.make_result(
                message=(
                    f"Column '{spec.name}' has {len(null_violations)} empty "
                    f"value(s) but is required (non-nullable)"
                ),
                location=self._format_rows(null_violations),
                fix_hint=(
                    f"Provide a value of type {spec.type.value} in every row "
                    f"for '{spec.name}', or check the contract — this column "
                    f"may not actually be required for your file type."
                ),
            ))

        if type_violations:
            examples = type_violations[:_MAX_EXAMPLES_PER_COLUMN]
            example_str = "; ".join(
                f"row {r}: '{v}'" for r, v in examples
            )
            more = (
                f" (+{len(type_violations) - _MAX_EXAMPLES_PER_COLUMN} more)"
                if len(type_violations) > _MAX_EXAMPLES_PER_COLUMN else ""
            )
            out.append(CheckResult(
                severity=self.default_severity,
                rule_id="VALUE_TYPE_002",
                contract_section=self.contract_section,
                message=(
                    f"Column '{spec.name}' has {len(type_violations)} "
                    f"value(s) that don't parse as {spec.type.value}"
                ),
                location=f"{example_str}{more}",
                fix_hint=self._type_hint(spec.type),
            ))

        if enum_violations:
            examples = enum_violations[:_MAX_EXAMPLES_PER_COLUMN]
            example_str = "; ".join(
                f"row {r}: '{v}'" for r, v in examples
            )
            allowed = ", ".join(spec.enum or ())
            out.append(CheckResult(
                severity=self.default_severity,
                rule_id="VALUE_TYPE_003",
                contract_section=self.contract_section,
                message=(
                    f"Column '{spec.name}' has {len(enum_violations)} "
                    f"value(s) not in the allowed enum"
                ),
                location=example_str,
                fix_hint=f"Allowed values: {allowed}",
            ))

        return out

    # ---------- helpers ----------

    @staticmethod
    def _value_parses_as_type(value: str, t: ColumnType) -> bool:
        if t == ColumnType.STRING:
            return True
        if t == ColumnType.INT:
            return _coerce_int(value)
        if t == ColumnType.FLOAT:
            return _coerce_float(value)
        if t == ColumnType.BOOL:
            return _coerce_bool(value)
        if t == ColumnType.DATE:
            return _coerce_date(value)
        if t == ColumnType.COUNTRY_CODE or t == ColumnType.REGION_CODE:
            return _coerce_country_code(value)
        if t == ColumnType.TIMESTAMP_LOCAL or t == ColumnType.TIMESTAMP_UTC:
            # Timestamps have their own dedicated check.
            # Here we just confirm it's not blank, which we already did.
            return True
        return True

    @staticmethod
    def _type_hint(t: ColumnType) -> str:
        return {
            ColumnType.INT: "Use plain integers like '17', never '17.0' or '17 laps'.",
            ColumnType.FLOAT: "Use a number with a period as decimal separator, e.g. '5.891'.",
            ColumnType.BOOL: "Must be exactly 'TRUE' or 'FALSE' (uppercase).",
            ColumnType.DATE: "Use ISO format YYYY-MM-DD.",
            ColumnType.COUNTRY_CODE: "Use 3-letter ISO 3166-1 alpha-3 codes, e.g. 'USA', 'GBR'.",
            ColumnType.REGION_CODE: "Use 3-letter region codes from dim_regions.",
            ColumnType.TIMESTAMP_LOCAL: "Use ISO 8601 with timezone offset, e.g. '2025-12-13 13:00:00+08:00'.",
            ColumnType.TIMESTAMP_UTC: "Use ISO 8601 with Z suffix, e.g. '2026-05-19T08:00:00Z'.",
        }.get(t, "Check the contract for the correct format.")

    @staticmethod
    def _format_rows(rows: list[int]) -> str:
        if len(rows) <= 5:
            return "rows " + ", ".join(str(r) for r in rows)
        return f"rows {', '.join(str(r) for r in rows[:5])} (+{len(rows) - 5} more)"
