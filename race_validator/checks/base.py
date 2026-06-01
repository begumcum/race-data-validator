"""Check base class.

Every validation rule subclasses Check, declares its identity, and
implements `run(ctx)` that returns a list of CheckResults.

Adding a new check:
  1. Create a new file in race_validator/checks/
  2. Subclass Check
  3. Set rule_id, contract_section, severity
  4. Implement run(ctx)
  5. Register in race_validator/checks/registry.py
  6. Write tests in tests/test_<check>.py

No check ever raises during normal validation. If a check encounters
unexpected data, it returns an ERROR CheckResult — never lets the
exception bubble.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

import pandas as pd

from race_validator.report import CheckResult, Severity


FileType = Literal["results", "schedule"]


@dataclass(slots=True)
class ValidationContext:
    """Everything a check might need to inspect the file.

    Constructed once by the runner, passed to every check.
    Fields are populated lazily — early checks (encoding, filename)
    don't have a parsed DataFrame yet, so `df` may be None for them.
    """

    file_path: Path
    file_bytes: bytes | None = None       # raw file content
    parsed_first_line: str | None = None  # the `# contract_version: ...` comment
    df: pd.DataFrame | None = None        # populated after CSV is parsed
    file_type: FileType | None = None     # inferred from filename


class Check(ABC):
    """Abstract validation rule."""

    rule_id: str                 # e.g. "FILE_NAMING_001"
    contract_section: str        # e.g. "§1"
    default_severity: Severity = Severity.ERROR

    # If True, the runner stops the whole pipeline when this check fails.
    # Use sparingly — encoding/file-naming/parse failures only.
    is_blocking: bool = False

    # Which file types this check applies to. Default: both.
    applies_to_results: bool = True
    applies_to_schedule: bool = True

    @abstractmethod
    def run(self, ctx: ValidationContext) -> list[CheckResult]:
        """Inspect ctx, return zero or more CheckResults."""
        raise NotImplementedError

    # ---------- helpers ----------

    def applies(self, file_type: FileType | None) -> bool:
        """Should this check run for the given file type?"""
        if file_type is None:
            # Pre-parse phase — only run truly file-level checks.
            return True
        if file_type == "results":
            return self.applies_to_results
        if file_type == "schedule":
            return self.applies_to_schedule
        return False

    def make_result(
        self,
        message: str,
        *,
        severity: Severity | None = None,
        location: str | None = None,
        fix_hint: str | None = None,
    ) -> CheckResult:
        """Convenience: build a CheckResult prefilled with this check's identity."""
        return CheckResult(
            severity=severity or self.default_severity,
            rule_id=self.rule_id,
            contract_section=self.contract_section,
            message=message,
            location=location,
            fix_hint=fix_hint,
        )
