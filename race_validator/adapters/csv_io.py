"""CSV file I/O.

Reading is two-step: raw bytes (for encoding checks) and parsed DataFrame
(for schema/value checks). The runner does both, populating the
ValidationContext at each stage.
"""

from __future__ import annotations

from io import BytesIO
from pathlib import Path

import pandas as pd


def read_bytes(path: Path) -> bytes:
    """Read the raw file content. May raise IOError."""
    return path.read_bytes()


def parse_csv(file_bytes: bytes) -> pd.DataFrame:
    """Parse UTF-8 CSV bytes into a DataFrame.

    Strict-ish settings:
      - utf-8 only (encoding check has already passed if we got here)
      - no automatic comment handling; the `# contract_version` line is
        handled separately (TODO once that check exists)
      - keep_default_na=False so empty strings stay empty strings,
        not NaN. The contract says empty string is the missing marker.
    """
    return pd.read_csv(
        BytesIO(file_bytes),
        encoding="utf-8",
        dtype=str,                    # everything as string first; type checks come later
        keep_default_na=False,
        na_values=[],
    )
