"""Normalization library (§3a of the data contract).

Two functions, deterministic and idempotent:

  normalize_name(s)       - for person names (drivers)
                            Output: lowercase ASCII, single-spaced

  normalize_identifier(s) - for entity identifiers (series, circuits,
                            teams, car models, taxonomy values)
                            Output: lowercase ASCII, underscored

These are the canonical implementations. Anywhere else that touches
normalization MUST call into this module; ad-hoc normalization is a
contract violation.
"""

from __future__ import annotations

import re
import unicodedata

_MAX_LEN = 200

# Characters NFKD does not decompose. We pre-map them to their conventional
# Latin transliteration before running the rest of the algorithm.
_PRE_MAP = {
    "ø": "o", "Ø": "O",
    "æ": "ae", "Æ": "AE",
    "œ": "oe", "Œ": "OE",
    "ß": "ss",
    "ð": "d", "Ð": "D",
    "þ": "th", "Þ": "TH",
    "ł": "l", "Ł": "L",
    "đ": "d", "Đ": "D",
    "ı": "i",
    "ŋ": "n", "Ŋ": "N",
}


def _apply_pre_map(s: str) -> str:
    return "".join(_PRE_MAP.get(c, c) for c in s)


def _check_input(s: str, function_name: str) -> None:
    """Shared input validation. Both normalizers reject the same things."""
    if not isinstance(s, str):
        raise TypeError(
            f"{function_name}: expected str, got {type(s).__name__}"
        )
    if not s or not s.strip():
        raise ValueError(f"{function_name}: empty input")
    if len(s) > _MAX_LEN:
        raise ValueError(
            f"{function_name}: input exceeds {_MAX_LEN} characters "
            f"(got {len(s)}); real names are shorter than this"
        )


def _strip_diacritics(s: str) -> str:
    """NFKD decompose, drop combining marks. Pre-map characters NFKD misses."""
    s = _apply_pre_map(s)
    decomposed = unicodedata.normalize("NFKD", s)
    return "".join(c for c in decomposed if not unicodedata.combining(c))


def normalize_name(s: str) -> str:
    """Normalize a person's name.

    Algorithm (§3a):
      1. NFKD decompose, strip combining marks
      2. Replace any non-[A-Za-z0-9 ] character with a space
      3. Lowercase
      4. Collapse consecutive whitespace
      5. Strip leading/trailing whitespace

    Examples:
      "Nicolás Varrone"          -> "nicolas varrone"
      "Jean-Éric Vergne"         -> "jean eric vergne"
      "  Lewis   Hamilton  "     -> "lewis hamilton"
    """
    _check_input(s, "normalize_name")
    ascii_only = _strip_diacritics(s)
    cleaned = re.sub(r"[^A-Za-z0-9 ]", " ", ascii_only)
    return re.sub(r"\s+", " ", cleaned).strip().lower()


def normalize_identifier(s: str) -> str:
    """Normalize an entity identifier (series, circuit, team, car model, etc.).

    Algorithm (§3a):
      1. NFKD decompose, strip combining marks
      2. Replace any non-[A-Za-z0-9] run with a single '_'
      3. Lowercase
      4. Strip leading/trailing '_'

    Examples:
      "Formula 1"                  -> "formula_1"
      "Autódromo José Carlos Pace" -> "autodromo_jose_carlos_pace"
      "Brands Hatch (GP)"          -> "brands_hatch_gp"
      "Oreca 07 - Gibson"          -> "oreca_07_gibson"
    """
    _check_input(s, "normalize_identifier")
    ascii_only = _strip_diacritics(s)
    underscored = re.sub(r"[^A-Za-z0-9]+", "_", ascii_only)
    return underscored.strip("_").lower()
