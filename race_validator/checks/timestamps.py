"""Timestamp format checks (§3 of the contract).

Two timestamp shapes are allowed in the contract:

  TIMESTAMP_LOCAL  - "2025-12-13 13:00:00+08:00" or "2025-12-13T13:00:00+08:00"
                     Has a timezone offset, NOT the Z marker.
                     Used for: session_datetime_local (anything tied to a venue)

  TIMESTAMP_UTC    - "2026-05-19T08:00:00Z"
                     Strict ISO with Z suffix.
                     Used for: scraped_at, ingested_at (machine events)

A timestamp without an offset (naive datetime) is always wrong.
"""

from __future__ import annotations

import re
from datetime import datetime

from race_validator.checks.base import Check, ValidationContext
from race_validator.report import CheckResult, Severity
from race_validator.schemas import get_schema
from race_validator.schemas.base import ColumnType


_MAX_EXAMPLES = 5

# Accept either space or T between date and time for local timestamps.
# Examples:
#   2025-12-13 13:00:00+08:00
#   2025-12-13T13:00:00+08:00
#   2025-12-13 13:00:00.123+08:00
_LOCAL_RE = re.compile(
    r"^\d{4}-\d{2}-\d{2}[ T]\d{2}:\d{2}:\d{2}(\.\d+)?[+-]\d{2}:\d{2}$"
)

# Strict T-separator, Z suffix for UTC.
_UTC_RE = re.compile(
    r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(\.\d+)?Z$"
)


class TimestampLocalCheck(Check):
    """All TIMESTAMP_LOCAL columns must have a tz offset (NOT Z)."""

    rule_id = "TIMESTAMP_001"
    contract_section = "§3"
    default_severity = Severity.ERROR

    def run(self, ctx: ValidationContext) -> list[CheckResult]:
        return _check_timestamps(ctx, ColumnType.TIMESTAMP_LOCAL,
                                 rule_id=self.rule_id,
                                 section=self.contract_section,
                                 severity=self.default_severity)


class TimestampUtcCheck(Check):
    """All TIMESTAMP_UTC columns must end in Z."""

    rule_id = "TIMESTAMP_002"
    contract_section = "§3"
    default_severity = Severity.ERROR

    def run(self, ctx: ValidationContext) -> list[CheckResult]:
        return _check_timestamps(ctx, ColumnType.TIMESTAMP_UTC,
                                 rule_id=self.rule_id,
                                 section=self.contract_section,
                                 severity=self.default_severity)


def _check_timestamps(
    ctx: ValidationContext,
    target_type: ColumnType,
    *,
    rule_id: str,
    section: str,
    severity: Severity,
) -> list[CheckResult]:
    if ctx.df is None or ctx.file_type is None:
        return []

    schema = get_schema(ctx.file_type)
    results: list[CheckResult] = []

    for spec in schema.columns:
        if spec.type != target_type:
            continue
        if spec.name not in ctx.df.columns:
            continue

        bad: list[tuple[int, str]] = []
        regex = _LOCAL_RE if target_type == ColumnType.TIMESTAMP_LOCAL else _UTC_RE

        for row_idx, value in enumerate(ctx.df[spec.name]):
            value = "" if value is None else str(value)
            row_number = row_idx + 1
            if value == "":
                # Null handling is the value_types check's job.
                continue
            if not regex.match(value):
                bad.append((row_number, value))
                continue
            # Even if regex matches, parsing might still fail (e.g. month 13)
            if not _safe_parse(value):
                bad.append((row_number, value))

        if bad:
            examples = bad[:_MAX_EXAMPLES]
            example_str = "; ".join(f"row {r}: '{v}'" for r, v in examples)
            more = f" (+{len(bad) - _MAX_EXAMPLES} more)" if len(bad) > _MAX_EXAMPLES else ""
            if target_type == ColumnType.TIMESTAMP_LOCAL:
                fix = (
                    "Use ISO 8601 with timezone offset, e.g. "
                    "'2025-12-13 13:00:00+08:00'. Do not use 'Z' — keep the "
                    "local offset so we can resolve the venue's timezone."
                )
            else:
                fix = (
                    "Use ISO 8601 with Z suffix, e.g. '2026-05-19T08:00:00Z'. "
                    "This is a machine event, always in UTC."
                )
            results.append(CheckResult(
                severity=severity,
                rule_id=rule_id,
                contract_section=section,
                message=(
                    f"Column '{spec.name}' has {len(bad)} timestamp(s) "
                    f"in the wrong format"
                ),
                location=f"{example_str}{more}",
                fix_hint=fix,
            ))

    return results


def _safe_parse(value: str) -> bool:
    """Try strptime with a few accepted format strings."""
    # Normalize T separator to space, drop Z to +00:00 for parsing
    v = value.replace("T", " ")
    if v.endswith("Z"):
        v = v[:-1] + "+00:00"
    # Try with and without fractional seconds
    fmts = ("%Y-%m-%d %H:%M:%S%z", "%Y-%m-%d %H:%M:%S.%f%z")
    for fmt in fmts:
        try:
            datetime.strptime(v, fmt)
            return True
        except ValueError:
            continue
    return False
