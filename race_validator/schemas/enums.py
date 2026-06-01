"""Enum constants from the data contract.

Single source of truth. Every check that mentions these values
imports from here.
"""

from __future__ import annotations


# §5 race status enum
RACE_STATUS_VALUES: tuple[str, ...] = (
    "FINISHED",
    "LAPPED",
    "DNF",
    "DNS",
    "DSQ",
    "DNQ",
)

# §5 session type
SESSION_TYPES: tuple[str, ...] = (
    "practice",
    "qualifying",
    "race",
)

# §4 dim_series scope
SCOPES: tuple[str, ...] = (
    "club",
    "national",
    "regional",
    "international",
)

# §5 driver classification (FIA Bronze/Silver/Gold/Platinum)
DRIVER_CLASSIFICATIONS: tuple[str, ...] = (
    "Bronze",
    "Silver",
    "Gold",
    "Platinum",
)

# §5 gender (on dim_drivers, not on result rows; included for completeness)
GENDERS: tuple[str, ...] = ("M", "F", "X")
