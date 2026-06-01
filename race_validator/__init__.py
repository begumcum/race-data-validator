"""race_validator — local validation of race-results CSVs against the data contract."""

from race_validator.version import CONTRACT_VERSION, LIBRARY_VERSION
from race_validator.api import validate_file
from race_validator.report import ValidationReport, Severity

__all__ = [
    "CONTRACT_VERSION",
    "LIBRARY_VERSION",
    "validate_file",
    "ValidationReport",
    "Severity",
]
