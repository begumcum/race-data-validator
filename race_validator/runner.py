"""Pipeline runner.

Orchestrates the sequence of checks. Public entry point is validate_file()
in api.py; this module is the implementation.

Phases:
  0. Read raw bytes from disk
  1. PRE-PARSE pass: run blocking checks (file naming, encoding).
     These only need raw bytes / filename.
  2. Parse CSV bytes into a DataFrame.
  3. POST-PARSE pass: run all remaining checks against the DataFrame.

If a blocking check fails in phase 1, the pipeline aborts before phase 2
because post-parse checks cannot meaningfully run on an unparseable file.
"""

from __future__ import annotations

from pathlib import Path

from race_validator.adapters.csv_io import parse_csv, read_bytes
from race_validator.checks.base import Check, ValidationContext
from race_validator.checks.registry import ALL_CHECKS
from race_validator.report import CheckResult, Severity, ValidationReport
from race_validator.version import CONTRACT_VERSION, LIBRARY_VERSION


def run_pipeline(path: Path) -> ValidationReport:
    """Validate a single file end-to-end. Always returns a report; never raises."""

    report = ValidationReport(
        filename=path.name,
        contract_version=CONTRACT_VERSION,
        library_version=LIBRARY_VERSION,
    )
    ctx = ValidationContext(file_path=path)

    # --- Phase 0: read bytes ---
    try:
        ctx.file_bytes = read_bytes(path)
    except (OSError, IOError) as e:
        report.add(CheckResult(
            severity=Severity.ERROR,
            rule_id="IO_001",
            contract_section="N/A",
            message=f"Could not read file: {e}",
            fix_hint="Check file exists, is readable, and is not in use.",
        ))
        report.checks_run = 1
        return report

    # Split checks into pre-parse (blocking) and post-parse buckets.
    pre_checks = [c for c in ALL_CHECKS if c.is_blocking]
    post_checks = [c for c in ALL_CHECKS if not c.is_blocking]

    # --- Phase 1: pre-parse checks ---
    blocked = False
    for check in pre_checks:
        results = _safely_run(check, ctx)
        report.extend(results)
        report.checks_run += 1
        if not results:
            report.checks_passed += 1
        if any(r.severity == Severity.ERROR for r in results):
            blocked = True

    if blocked:
        return report  # don't try to parse a file that failed validation gates

    # --- Phase 2: parse the CSV ---
    try:
        ctx.df = parse_csv(ctx.file_bytes)
    except Exception as e:
        report.add(CheckResult(
            severity=Severity.ERROR,
            rule_id="IO_002",
            contract_section="N/A",
            message=f"CSV parsing failed: {e}",
            fix_hint=(
                "Check that the file has a header row, consistent column "
                "counts on every row, and is comma-delimited."
            ),
        ))
        report.checks_run += 1
        return report

    # --- Phase 3: post-parse checks ---
    for check in post_checks:
        if not check.applies(ctx.file_type):
            continue
        results = _safely_run(check, ctx)
        report.extend(results)
        report.checks_run += 1
        if not results:
            report.checks_passed += 1

    return report


def _safely_run(check: Check, ctx: ValidationContext) -> list[CheckResult]:
    """Run a check and convert any crash into a CheckResult error.

    Checks should never raise, but if one does, we don't want the
    whole validation to die. Capture and report.
    """
    try:
        return check.run(ctx)
    except Exception as e:
        return [CheckResult(
            severity=Severity.ERROR,
            rule_id=check.rule_id,
            contract_section=check.contract_section,
            message=f"Check crashed unexpectedly: {type(e).__name__}: {e}",
            fix_hint=(
                "This is a bug in the validator, not your file. "
                "Please report it to Berkay."
            ),
        )]
