"""Pole and fastest-lap uniqueness rules (§8 of the contract).

Three rules, all RACE-SESSION ONLY:

  POLE_001
    Exactly one row per race session has is_pole = TRUE.
    Grouping: (series_id, season_label, round_number, session_type=race,
              session_number).
    The pole-sitter must have race_status != DNS (the pole is whoever
    physically started P1, not who set the fastest qualifying time).

  FASTEST_001
    At most one row per race session has is_fastest_lap_overall = TRUE.
    Grouping: same as POLE_001.

  FASTEST_002
    At most one row per race session per class has is_fastest_lap_in_class
    = TRUE.
    Grouping: (series, season, round, session_type=race, session_number,
              discipline, category).
"""

from __future__ import annotations

from collections import defaultdict

from race_validator.checks.base import Check, ValidationContext
from race_validator.report import CheckResult


_MAX_EXAMPLES = 5


def _val(df, row_idx, col) -> str:
    if col not in df.columns:
        return ""
    v = df.iloc[row_idx][col]
    return "" if v is None else str(v).strip()


def _format_group(group_key: tuple) -> str:
    """Human-readable label for a session group key."""
    return "/".join(str(x) for x in group_key)


class PoleUniquenessCheck(Check):
    """Each race session must have exactly one is_pole=TRUE row,
    and that row must not be DNS."""

    rule_id = "POLE_001"
    contract_section = "§8"
    applies_to_schedule = False

    def run(self, ctx: ValidationContext) -> list[CheckResult]:
        if ctx.df is None:
            return []
        required = ("series_id", "season_label", "round_number",
                    "session_type", "session_number", "is_pole",
                    "race_status")
        if not all(c in ctx.df.columns for c in required):
            return []

        # Group race rows by (series, season, round, session_number).
        # For each group, count rows with is_pole=TRUE and check the
        # status of those rows.
        groups: dict[tuple, list[tuple[int, str]]] = defaultdict(list)
        # group_key -> list of (row_number, race_status_of_pole_row)

        race_session_groups: set[tuple] = set()
        # all distinct race session keys, even those with no pole rows

        for row_idx in range(len(ctx.df)):
            session_type = _val(ctx.df, row_idx, "session_type")
            if session_type != "race":
                continue
            key = (
                _val(ctx.df, row_idx, "series_id"),
                _val(ctx.df, row_idx, "season_label"),
                _val(ctx.df, row_idx, "round_number"),
                _val(ctx.df, row_idx, "session_number"),
            )
            race_session_groups.add(key)
            is_pole = _val(ctx.df, row_idx, "is_pole")
            if is_pole == "TRUE":
                race_status = _val(ctx.df, row_idx, "race_status")
                groups[key].append((row_idx + 1, race_status))

        results: list[CheckResult] = []
        missing_pole: list[tuple] = []
        duplicate_pole: list[tuple[tuple, list[int]]] = []
        dns_pole: list[tuple[tuple, int]] = []

        for key in race_session_groups:
            pole_rows = groups.get(key, [])
            n = len(pole_rows)
            if n == 0:
                missing_pole.append(key)
            elif n > 1:
                duplicate_pole.append((key, [r for r, _ in pole_rows]))
            else:
                row_number, status = pole_rows[0]
                if status == "DNS":
                    dns_pole.append((key, row_number))

        # --- missing pole ---
        if missing_pole:
            examples = missing_pole[:_MAX_EXAMPLES]
            example_str = "; ".join(_format_group(k) for k in examples)
            more = (
                f" (+{len(missing_pole) - _MAX_EXAMPLES} more)"
                if len(missing_pole) > _MAX_EXAMPLES else ""
            )
            results.append(self.make_result(
                message=(
                    f"{len(missing_pole)} race session(s) have no row with "
                    f"is_pole=TRUE. Every race must have one pole-sitter."
                ),
                location=f"sessions (series/season/round/session_number): {example_str}{more}",
                fix_hint=(
                    "Mark the driver who started P1 with is_pole=TRUE. "
                    "If qualifying determined pole but they DNS'd, set "
                    "is_pole=TRUE on the driver who actually started first."
                ),
            ))

        # --- duplicate pole ---
        if duplicate_pole:
            examples = duplicate_pole[:_MAX_EXAMPLES]
            example_str = "; ".join(
                f"{_format_group(k)} (rows {', '.join(str(r) for r in rs)})"
                for k, rs in examples
            )
            more = (
                f" (+{len(duplicate_pole) - _MAX_EXAMPLES} more)"
                if len(duplicate_pole) > _MAX_EXAMPLES else ""
            )
            results.append(CheckResult(
                severity=self.default_severity,
                rule_id="POLE_001b",
                contract_section=self.contract_section,
                message=(
                    f"{len(duplicate_pole)} race session(s) have more than "
                    f"one is_pole=TRUE row. Only one driver can start from "
                    f"pole."
                ),
                location=f"{example_str}{more}",
                fix_hint=(
                    "In each race session, set is_pole=TRUE on exactly one "
                    "driver (the one who started P1)."
                ),
            ))

        # --- DNS pole ---
        if dns_pole:
            examples = dns_pole[:_MAX_EXAMPLES]
            example_str = "; ".join(
                f"{_format_group(k)} (row {r})" for k, r in examples
            )
            more = (
                f" (+{len(dns_pole) - _MAX_EXAMPLES} more)"
                if len(dns_pole) > _MAX_EXAMPLES else ""
            )
            results.append(CheckResult(
                severity=self.default_severity,
                rule_id="POLE_001c",
                contract_section=self.contract_section,
                message=(
                    f"{len(dns_pole)} pole-sitter row(s) have "
                    f"race_status=DNS. A DNS driver did not start; the "
                    f"actual P1 starter holds the pole."
                ),
                location=f"{example_str}{more}",
                fix_hint=(
                    "Set is_pole=FALSE on the DNS driver. Move is_pole=TRUE "
                    "to whoever physically started P1 instead."
                ),
            ))

        return results


class FastestLapOverallCheck(Check):
    """At most one is_fastest_lap_overall=TRUE per race session."""

    rule_id = "FASTEST_001"
    contract_section = "§8"
    applies_to_schedule = False

    def run(self, ctx: ValidationContext) -> list[CheckResult]:
        if ctx.df is None:
            return []
        required = ("series_id", "season_label", "round_number",
                    "session_type", "session_number",
                    "is_fastest_lap_overall")
        if not all(c in ctx.df.columns for c in required):
            return []

        groups: dict[tuple, list[int]] = defaultdict(list)
        for row_idx in range(len(ctx.df)):
            if _val(ctx.df, row_idx, "session_type") != "race":
                continue
            if _val(ctx.df, row_idx, "is_fastest_lap_overall") != "TRUE":
                continue
            key = (
                _val(ctx.df, row_idx, "series_id"),
                _val(ctx.df, row_idx, "season_label"),
                _val(ctx.df, row_idx, "round_number"),
                _val(ctx.df, row_idx, "session_number"),
            )
            groups[key].append(row_idx + 1)

        dupes = [(k, v) for k, v in groups.items() if len(v) > 1]
        if not dupes:
            return []

        examples = dupes[:_MAX_EXAMPLES]
        example_str = "; ".join(
            f"{_format_group(k)} (rows {', '.join(str(r) for r in rs)})"
            for k, rs in examples
        )
        more = f" (+{len(dupes) - _MAX_EXAMPLES} more)" if len(dupes) > _MAX_EXAMPLES else ""

        return [self.make_result(
            message=(
                f"{len(dupes)} race session(s) have more than one "
                f"is_fastest_lap_overall=TRUE row. Only one driver can hold "
                f"the overall fastest lap."
            ),
            location=f"{example_str}{more}",
            fix_hint=(
                "In each race session, set is_fastest_lap_overall=TRUE on "
                "at most one driver."
            ),
        )]


class FastestLapInClassCheck(Check):
    """At most one is_fastest_lap_in_class=TRUE per race session per class."""

    rule_id = "FASTEST_002"
    contract_section = "§8"
    applies_to_schedule = False

    def run(self, ctx: ValidationContext) -> list[CheckResult]:
        if ctx.df is None:
            return []
        required = ("series_id", "season_label", "round_number",
                    "session_type", "session_number",
                    "discipline", "category",
                    "is_fastest_lap_in_class")
        if not all(c in ctx.df.columns for c in required):
            return []

        groups: dict[tuple, list[int]] = defaultdict(list)
        for row_idx in range(len(ctx.df)):
            if _val(ctx.df, row_idx, "session_type") != "race":
                continue
            if _val(ctx.df, row_idx, "is_fastest_lap_in_class") != "TRUE":
                continue
            key = (
                _val(ctx.df, row_idx, "series_id"),
                _val(ctx.df, row_idx, "season_label"),
                _val(ctx.df, row_idx, "round_number"),
                _val(ctx.df, row_idx, "session_number"),
                _val(ctx.df, row_idx, "discipline"),
                _val(ctx.df, row_idx, "category"),
            )
            groups[key].append(row_idx + 1)

        dupes = [(k, v) for k, v in groups.items() if len(v) > 1]
        if not dupes:
            return []

        examples = dupes[:_MAX_EXAMPLES]
        example_str = "; ".join(
            f"{_format_group(k)} (rows {', '.join(str(r) for r in rs)})"
            for k, rs in examples
        )
        more = f" (+{len(dupes) - _MAX_EXAMPLES} more)" if len(dupes) > _MAX_EXAMPLES else ""

        return [self.make_result(
            message=(
                f"{len(dupes)} (race session, class) group(s) have more than "
                f"one is_fastest_lap_in_class=TRUE row."
            ),
            location=f"{example_str}{more}",
            fix_hint=(
                "In each race session, each class can have at most one "
                "is_fastest_lap_in_class=TRUE row."
            ),
        )]
