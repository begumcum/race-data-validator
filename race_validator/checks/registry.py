"""Registry of active checks for the current library version.

Ordering matters: blocking checks (file naming, encoding) come first,
so the runner can short-circuit before doing expensive parsing.
"""

from __future__ import annotations

from race_validator.checks.base import Check
from race_validator.checks.column_names import (
    ColumnNamesCheck,
    ColumnOrderCheck,
)
from race_validator.checks.cross_field import (
    GapToLeaderConsistencyCheck,
    RaceStatusConsistencyCheck,
    RaceTimeConsistencyCheck,
)
from race_validator.checks.duplicates import (
    DuplicateResultIdCheck,
    DuplicateRowsCheck,
)
from race_validator.checks.encoding import (
    NoBomCheck,
    UnixLineEndingsCheck,
    Utf8EncodingCheck,
)
from race_validator.checks.file_naming import (
    FileExtensionCheck,
    FileNameFormatCheck,
)
from race_validator.checks.forbidden_chars import ForbiddenCharsCheck
from race_validator.checks.master_table_refs import MasterTableRefsCheck
from race_validator.checks.normalization_integrity import (
    NormalizationIntegrityCheck,
)
from race_validator.checks.pole_fastest import (
    FastestLapInClassCheck,
    FastestLapOverallCheck,
    PoleUniquenessCheck,
)
from race_validator.checks.structure import (
    BlankRowsCheck,
    UnnamedColumnsCheck,
)
from race_validator.checks.timestamps import (
    TimestampLocalCheck,
    TimestampUtcCheck,
)
from race_validator.checks.value_types import ValueTypesCheck
from race_validator.checks.whitespace import WhitespaceCheck


# v0.2.5 checks.
ALL_CHECKS: list[Check] = [
    # ---- Pre-parse (blocking) ----
    FileExtensionCheck(),
    FileNameFormatCheck(),
    Utf8EncodingCheck(),
    NoBomCheck(),
    UnixLineEndingsCheck(),

    # ---- Post-parse: structural ----
    UnnamedColumnsCheck(),
    BlankRowsCheck(),

    # ---- Post-parse: columns ----
    ColumnNamesCheck(),
    ColumnOrderCheck(),

    # ---- Post-parse: per-value ----
    ValueTypesCheck(),
    TimestampLocalCheck(),
    TimestampUtcCheck(),
    ForbiddenCharsCheck(),
    WhitespaceCheck(),
    NormalizationIntegrityCheck(),

    # ---- Cross-reference ----
    MasterTableRefsCheck(),

    # ---- Cross-field logical rules ----
    RaceStatusConsistencyCheck(),
    RaceTimeConsistencyCheck(),
    GapToLeaderConsistencyCheck(),

    # ---- Cross-row rules ----
    DuplicateRowsCheck(),
    DuplicateResultIdCheck(),
    PoleUniquenessCheck(),
    FastestLapOverallCheck(),
    FastestLapInClassCheck(),
]
