"""Cross-field consistency rules (§5 of the contract).

Three rules:

  CROSS_FIELD_001
    race_status must be NULL for non-race sessions (practice/qualifying)
    race_status must be POPULATED for race sessions (enum already enforced
    elsewhere; here we just check populated/empty)

  CROSS_FIELD_002
    race_time_ms population depends on session_type and race_status:
      session_type=race + race_status in {FINISHED, LAPPED}  -> required
      session_type=race + race_status in {DNF,DNS,DSQ,DNQ}   -> must be empty
      session_type != race                                   -> must be empty

  CROSS_FIELD_003
    gap_to_leader_ms must be NULL when position_overall == 1
"""

from __future__ import annotations

from race_validator.checks.base import Check, ValidationContext
from race_validator.report import CheckResult


_MAX_EXAMPLES = 5

_NON_FINISHER_STATUSES = {"DNF", "DNS", "DSQ", "DNQ"}
_FINISHER_STATUSES = {"FINISHED", "LAPPED"}


def _empty(v) -> bool:
    return v is None or str(v).strip() == ""


class RaceStatusConsistencyCheck(Check):
    """race_status NULL ⇔ session is not a race."""

    rule_id = "CROSS_FIELD_001"
    contract_section = "§5"
    applies_to_schedule = False

    def run(self, ctx: ValidationContext) -> list[CheckResult]:
        if ctx.df is None:
            return []
        cols_needed = ("session_type", "race_status")
        if not all(c in ctx.df.columns for c in cols_needed):
            return []

        non_race_with_status: list[tuple[int, str, str]] = []  # (row, session_type, status)
        race_without_status: list[int] = []

        for row_idx in range(len(ctx.df)):
            session_type = str(ctx.df.iloc[row_idx]["session_type"] or "").strip()
            race_status = str(ctx.df.iloc[row_idx]["race_status"] or "").strip()

            if session_type == "race":
                if race_status == "":
                    race_without_status.append(row_idx + 1)
            elif session_type in ("practice", "qualifying"):
                if race_status != "":
                    non_race_with_status.append((row_idx + 1, session_type, race_status))

        results: list[CheckResult] = []

        if non_race_with_status:
            examples = non_race_with_status[:_MAX_EXAMPLES]
            example_str = "; ".join(
                f"row {r}: session_type='{st}' has race_status='{rs}'"
                for r, st, rs in examples
            )
            more = (
                f" (+{len(non_race_with_status) - _MAX_EXAMPLES} more)"
                if len(non_race_with_status) > _MAX_EXAMPLES else ""
            )
            results.append(self.make_result(
                message=(
                    f"{len(non_race_with_status)} non-race row(s) have a "
                    f"populated race_status. race_status must be empty for "
                    f"practice and qualifying sessions."
                ),
                location=f"{example_str}{more}",
                fix_hint=(
                    "Leave race_status empty in practice/qualifying rows. "
                    "race_status only applies to race sessions."
                ),
            ))

        if race_without_status:
            examples = race_without_status[:_MAX_EXAMPLES]
            example_str = ", ".join(f"row {r}" for r in examples)
            more = (
                f" (+{len(race_without_status) - _MAX_EXAMPLES} more)"
                if len(race_without_status) > _MAX_EXAMPLES else ""
            )
            results.append(CheckResult(
                severity=self.default_severity,
                rule_id="CROSS_FIELD_001b",
                contract_section=self.contract_section,
                message=(
                    f"{len(race_without_status)} race row(s) have an empty "
                    f"race_status. Every race result must have a status."
                ),
                location=f"{example_str}{more}",
                fix_hint=(
                    "Set race_status to one of: FINISHED, LAPPED, DNF, DNS, "
                    "DSQ, DNQ."
                ),
            ))

        return results


class RaceTimeConsistencyCheck(Check):
    """race_time_ms population depends on session_type + race_status."""

    rule_id = "CROSS_FIELD_002"
    contract_section = "§5"
    applies_to_schedule = False

    def run(self, ctx: ValidationContext) -> list[CheckResult]:
        if ctx.df is None:
            return []
        if not all(c in ctx.df.columns
                   for c in ("session_type", "race_status", "race_time_ms")):
            return []

        wrong_finisher: list[tuple[int, str]] = []      # finisher with empty time
        wrong_non_finisher: list[tuple[int, str, str]] = []  # non-finisher with time
        wrong_non_race: list[tuple[int, str]] = []      # non-race with time

        for row_idx in range(len(ctx.df)):
            session_type = str(ctx.df.iloc[row_idx]["session_type"] or "").strip()
            status = str(ctx.df.iloc[row_idx]["race_status"] or "").strip()
            rtm = str(ctx.df.iloc[row_idx]["race_time_ms"] or "").strip()

            if session_type == "race":
                if status in _FINISHER_STATUSES and rtm == "":
                    wrong_finisher.append((row_idx + 1, status))
                elif status in _NON_FINISHER_STATUSES and rtm != "":
                    wrong_non_finisher.append((row_idx + 1, status, rtm))
            elif session_type in ("practice", "qualifying"):
                if rtm != "":
                    wrong_non_race.append((row_idx + 1, rtm))

        results: list[CheckResult] = []

        if wrong_finisher:
            examples = wrong_finisher[:_MAX_EXAMPLES]
            example_str = "; ".join(
                f"row {r}: race_status='{s}' but race_time_ms empty"
                for r, s in examples
            )
            more = (
                f" (+{len(wrong_finisher) - _MAX_EXAMPLES} more)"
                if len(wrong_finisher) > _MAX_EXAMPLES else ""
            )
            results.append(self.make_result(
                message=(
                    f"{len(wrong_finisher)} finisher row(s) missing "
                    f"race_time_ms. FINISHED and LAPPED rows must have a "
                    f"race time."
                ),
                location=f"{example_str}{more}",
                fix_hint=(
                    "Populate race_time_ms for every row whose race_status "
                    "is FINISHED or LAPPED."
                ),
            ))

        if wrong_non_finisher:
            examples = wrong_non_finisher[:_MAX_EXAMPLES]
            example_str = "; ".join(
                f"row {r}: race_status='{s}' but race_time_ms='{t}'"
                for r, s, t in examples
            )
            more = (
                f" (+{len(wrong_non_finisher) - _MAX_EXAMPLES} more)"
                if len(wrong_non_finisher) > _MAX_EXAMPLES else ""
            )
            results.append(CheckResult(
                severity=self.default_severity,
                rule_id="CROSS_FIELD_002b",
                contract_section=self.contract_section,
                message=(
                    f"{len(wrong_non_finisher)} non-finisher row(s) have a "
                    f"race_time_ms set. Non-finishers (DNF/DNS/DSQ/DNQ) "
                    f"must have an empty race_time_ms."
                ),
                location=f"{example_str}{more}",
                fix_hint=(
                    "Leave race_time_ms blank for rows with race_status in "
                    "{DNF, DNS, DSQ, DNQ}."
                ),
            ))

        if wrong_non_race:
            examples = wrong_non_race[:_MAX_EXAMPLES]
            example_str = "; ".join(
                f"row {r}: race_time_ms='{t}'" for r, t in examples
            )
            more = (
                f" (+{len(wrong_non_race) - _MAX_EXAMPLES} more)"
                if len(wrong_non_race) > _MAX_EXAMPLES else ""
            )
            results.append(CheckResult(
                severity=self.default_severity,
                rule_id="CROSS_FIELD_002c",
                contract_section=self.contract_section,
                message=(
                    f"{len(wrong_non_race)} practice/qualifying row(s) have "
                    f"a race_time_ms set. race_time_ms is for race sessions only."
                ),
                location=f"{example_str}{more}",
                fix_hint=(
                    "Leave race_time_ms empty for practice and qualifying rows."
                ),
            ))

        return results


class GapToLeaderConsistencyCheck(Check):
    """gap_to_leader_ms must be NULL when position_overall == 1."""

    rule_id = "CROSS_FIELD_003"
    contract_section = "§5"
    applies_to_schedule = False

    def run(self, ctx: ValidationContext) -> list[CheckResult]:
        if ctx.df is None:
            return []
        if not all(c in ctx.df.columns
                   for c in ("position_overall", "gap_to_leader_ms")):
            return []

        wrong: list[tuple[int, str]] = []

        for row_idx in range(len(ctx.df)):
            pos = str(ctx.df.iloc[row_idx]["position_overall"] or "").strip()
            gap = str(ctx.df.iloc[row_idx]["gap_to_leader_ms"] or "").strip()

            if pos == "1" and gap != "":
                wrong.append((row_idx + 1, gap))

        if not wrong:
            return []

        examples = wrong[:_MAX_EXAMPLES]
        example_str = "; ".join(
            f"row {r}: gap_to_leader_ms='{g}'" for r, g in examples
        )
        more = f" (+{len(wrong) - _MAX_EXAMPLES} more)" if len(wrong) > _MAX_EXAMPLES else ""

        return [self.make_result(
            message=(
                f"{len(wrong)} P1 row(s) have a non-empty gap_to_leader_ms. "
                f"The race leader has no gap to themselves; this field must "
                f"be empty for position_overall = 1."
            ),
            location=f"{example_str}{more}",
            fix_hint=(
                "Leave gap_to_leader_ms empty for the P1 finisher in each "
                "session. The same applies to gap_to_leader_display."
            ),
        )]
