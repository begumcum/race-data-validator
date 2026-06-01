"""Forbidden character check (§3 of the contract).

In all text fields, the following are forbidden:
  - Control characters (anything below U+0020 except tab)
  - Tab (\\t)
  - Newline / carriage return (\\n, \\r)
  - Double quote (")
  - Backslash (\\)
  - Forward slash (/)
  - Pipe (|)
  - NULL byte
"""

from __future__ import annotations

from race_validator.checks.base import Check, ValidationContext
from race_validator.report import CheckResult, Severity
from race_validator.schemas import get_schema
from race_validator.schemas.base import ColumnType


_MAX_EXAMPLES = 5

_FORBIDDEN = set('"\\/|\t\r\n\0')

# Columns where forbidden characters are legitimate (URLs contain `/`, etc.)
_EXEMPT_COLUMNS = frozenset({"source_url"})


def _has_forbidden(value: str) -> bool:
    if any(c in _FORBIDDEN for c in value):
        return True
    # Control characters (U+0000–U+001F except already-listed ones)
    return any(ord(c) < 0x20 for c in value)


class ForbiddenCharsCheck(Check):
    """Text fields must not contain forbidden characters."""

    rule_id = "FORBIDDEN_CHARS_001"
    contract_section = "§3"
    default_severity = Severity.ERROR

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
            if spec.name in _EXEMPT_COLUMNS:
                continue

            bad: list[tuple[int, str]] = []
            for row_idx, value in enumerate(ctx.df[spec.name]):
                value = "" if value is None else str(value)
                if value == "":
                    continue
                if _has_forbidden(value):
                    bad.append((row_idx + 1, value))

            if bad:
                examples = bad[:_MAX_EXAMPLES]
                example_str = "; ".join(
                    f"row {r}: '{_safe_repr(v)}'" for r, v in examples
                )
                more = f" (+{len(bad) - _MAX_EXAMPLES} more)" if len(bad) > _MAX_EXAMPLES else ""

                results.append(self.make_result(
                    message=(
                        f"Column '{spec.name}' has {len(bad)} value(s) "
                        f"containing forbidden characters"
                    ),
                    location=f"{example_str}{more}",
                    fix_hint=(
                        "Forbidden: control chars, tab, newline, quotes, "
                        "backslash, forward slash, pipe, NULL. Strip these "
                        "in the scraper before output."
                    ),
                ))

        return results


def _safe_repr(value: str) -> str:
    """Make any control characters visible in the report."""
    return value.encode("unicode_escape").decode("ascii")
