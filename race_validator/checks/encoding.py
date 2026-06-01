"""Encoding checks (§1 of the contract).

Rules:
  - UTF-8 encoding
  - No BOM
  - Unix line endings (\\n), not Windows (\\r\\n)

These checks run on raw bytes, before any CSV parsing.
"""

from __future__ import annotations

from race_validator.checks.base import Check, ValidationContext
from race_validator.report import CheckResult, Severity


_UTF8_BOM = b"\xef\xbb\xbf"


class Utf8EncodingCheck(Check):
    """File must be valid UTF-8."""

    rule_id = "ENCODING_001"
    contract_section = "§1"
    default_severity = Severity.ERROR
    is_blocking = True

    def run(self, ctx: ValidationContext) -> list[CheckResult]:
        if ctx.file_bytes is None:
            return [self.make_result(
                message="File could not be read as bytes",
                fix_hint="Check the file exists and is readable.",
            )]
        try:
            ctx.file_bytes.decode("utf-8")
        except UnicodeDecodeError as e:
            return [self.make_result(
                message=f"File is not valid UTF-8: {e.reason} at byte {e.start}",
                fix_hint=(
                    "Re-export the CSV with UTF-8 encoding. Most editors offer "
                    "'Save as UTF-8' or 'Encoding: UTF-8' in the export dialog."
                ),
            )]
        return []


class NoBomCheck(Check):
    """File must not start with a UTF-8 BOM."""

    rule_id = "ENCODING_002"
    contract_section = "§1"
    default_severity = Severity.ERROR

    def run(self, ctx: ValidationContext) -> list[CheckResult]:
        if ctx.file_bytes is None:
            return []
        if ctx.file_bytes.startswith(_UTF8_BOM):
            return [self.make_result(
                message="File starts with a UTF-8 BOM (3 bytes: EF BB BF)",
                fix_hint=(
                    "Re-save without BOM. In most editors, choose "
                    "'UTF-8 (no BOM)' rather than 'UTF-8 with BOM'."
                ),
            )]
        return []


class UnixLineEndingsCheck(Check):
    """File must use \\n line endings, not \\r\\n."""

    rule_id = "ENCODING_003"
    contract_section = "§1"
    default_severity = Severity.ERROR

    def run(self, ctx: ValidationContext) -> list[CheckResult]:
        if ctx.file_bytes is None:
            return []
        # We only flag if we find \r\n. Bare \r alone (old Mac) we treat
        # the same way but it's extremely rare.
        if b"\r\n" in ctx.file_bytes:
            return [self.make_result(
                message="File uses Windows line endings (\\r\\n)",
                fix_hint=(
                    "Re-save with Unix line endings (LF only). "
                    "On most editors: View > End-of-line > Unix (LF)."
                ),
            )]
        if b"\r" in ctx.file_bytes and b"\n" not in ctx.file_bytes:
            return [self.make_result(
                message="File uses classic-Mac line endings (\\r only)",
                fix_hint="Re-save with Unix line endings (LF only).",
            )]
        return []
