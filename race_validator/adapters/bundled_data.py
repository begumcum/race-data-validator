"""Loader for reference data CSVs bundled inside the package.

Reads dim_countries.csv, dim_regions.csv, dim_categories.csv, etc. from
race_validator/data/. Cached in module-level dicts so each is read once
per process.

When you ship a new library version, the bundled CSVs update with it.
"""

from __future__ import annotations

from functools import cache
from importlib.resources import files
from io import StringIO

import pandas as pd


_DATA_PKG = "race_validator.data"


def _load_csv(filename: str) -> pd.DataFrame:
    """Read one of the bundled CSVs."""
    resource = files(_DATA_PKG).joinpath(filename)
    text = resource.read_text(encoding="utf-8")
    return pd.read_csv(StringIO(text), dtype=str, keep_default_na=False)


@cache
def get_countries() -> pd.DataFrame:
    """dim_countries: country_id (ISO 3166-1 alpha-3), country_name."""
    return _load_csv("dim_countries.csv")


@cache
def get_regions() -> pd.DataFrame:
    """dim_regions: region_id, region_name."""
    return _load_csv("dim_regions.csv")


@cache
def get_categories() -> pd.DataFrame:
    """dim_categories: sport, discipline, category (all normalized)."""
    return _load_csv("dim_categories.csv")


@cache
def get_series() -> pd.DataFrame:
    """dim_series: series_id, names, scope, country_id, region_id."""
    return _load_csv("dim_series.csv")


@cache
def get_circuits() -> pd.DataFrame:
    """dim_circuits: circuit_id, names, location, geometry."""
    return _load_csv("dim_circuits.csv")


# ---------- convenience lookups ----------

@cache
def country_id_set() -> frozenset[str]:
    return frozenset(get_countries()["country_id"].tolist())


@cache
def region_id_set() -> frozenset[str]:
    return frozenset(get_regions()["region_id"].tolist())


@cache
def category_triple_set() -> frozenset[tuple[str, str, str]]:
    df = get_categories()
    return frozenset(
        (row.sport, row.discipline, row.category)
        for row in df.itertuples(index=False)
    )


@cache
def series_id_set() -> frozenset[str]:
    return frozenset(get_series()["series_id"].tolist())


@cache
def circuit_id_set() -> frozenset[str]:
    return frozenset(get_circuits()["circuit_id"].tolist())
