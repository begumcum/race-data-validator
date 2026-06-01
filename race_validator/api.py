"""Public API.

The Streamlit app — and any other frontend you build later — calls
exactly this function. Everything else in race_validator is internal.

When the API needs to grow (v0.2 adds entity resolution), add new
functions here. Don't change the signature of validate_file.
"""

from __future__ import annotations

from pathlib import Path

from race_validator.report import ValidationReport
from race_validator.runner import run_pipeline


def validate_file(path: str | Path) -> ValidationReport:
    """Validate a single CSV file against the contract.

    Returns a ValidationReport with one CheckResult per issue found.
    Never raises. Even unreadable files come back as an ERROR result.

    Future expansion:
      - v0.2.0 will add dry_run() and commit() for interactive entity
        resolution. validate_file() keeps its current behavior.
    """
    p = Path(path)
    return run_pipeline(p)
