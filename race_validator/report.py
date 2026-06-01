"""Report data structures.

A ValidationReport is the structured output of validating a file.
The Streamlit app renders it; future formatters can produce JSON, HTML, etc.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Iterable


class Severity(str, Enum):
    """How serious a check result is.

    ERROR    - file is rejected; collector must fix and re-validate
    WARNING  - file passes but the collector should know about this
    INFO     - context only; never blocks
    """

    ERROR = "error"
    WARNING = "warning"
    INFO = "info"


@dataclass(frozen=True, slots=True)
class CheckResult:
    """One issue found by a Check.

    A Check that finds nothing wrong returns an empty list of CheckResults.
    A Check that finds three issues returns three CheckResults.
    """

    severity: Severity
    rule_id: str               # e.g. "FILE_NAMING_001"
    contract_section: str      # e.g. "§1"
    message: str               # human-readable summary
    location: str | None = None    # "row 47" / "row 47, column 'race_time_ms'" / None for file-level
    fix_hint: str | None = None    # short, actionable, fits on one line

    def __post_init__(self) -> None:
        if not self.rule_id:
            raise ValueError("CheckResult requires rule_id")
        if not self.message:
            raise ValueError("CheckResult requires message")


@dataclass(slots=True)
class ValidationReport:
    """The full result of validating one file.

    `results` may contain successes (with severity=INFO) for diagnostics,
    or only failures. The CLI/UI decides what to display.
    """

    filename: str
    contract_version: str
    library_version: str
    results: list[CheckResult] = field(default_factory=list)
    checks_run: int = 0
    checks_passed: int = 0

    # ---------- aggregations ----------

    @property
    def errors(self) -> list[CheckResult]:
        return [r for r in self.results if r.severity == Severity.ERROR]

    @property
    def warnings(self) -> list[CheckResult]:
        return [r for r in self.results if r.severity == Severity.WARNING]

    @property
    def passed(self) -> bool:
        return len(self.errors) == 0

    @property
    def error_count(self) -> int:
        return len(self.errors)

    @property
    def warning_count(self) -> int:
        return len(self.warnings)

    # ---------- mutation ----------

    def extend(self, more: Iterable[CheckResult]) -> None:
        self.results.extend(more)

    def add(self, result: CheckResult) -> None:
        self.results.append(result)

    # ---------- serialization ----------

    def to_dict(self) -> dict:
        """JSON-safe representation, for download as a report."""
        return {
            "filename": self.filename,
            "contract_version": self.contract_version,
            "library_version": self.library_version,
            "checks_run": self.checks_run,
            "checks_passed": self.checks_passed,
            "passed": self.passed,
            "error_count": self.error_count,
            "warning_count": self.warning_count,
            "results": [
                {
                    "severity": r.severity.value,
                    "rule_id": r.rule_id,
                    "contract_section": r.contract_section,
                    "message": r.message,
                    "location": r.location,
                    "fix_hint": r.fix_hint,
                }
                for r in self.results
            ],
        }
