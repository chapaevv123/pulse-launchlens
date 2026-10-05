"""Explainable LaunchLens decisions. No score and no trading authority."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


VERIFIED_SOURCES = {
    "PONS_ROBINHOOD",
    "PONS_V2_ROBINHOOD",
    "BANKR_ROBINHOOD",
    "HOOD_DEV_ROBINHOOD",
    "LUNCH_FUN_ROBINHOOD",
    "LUNCH_FUN_V3_ROBINHOOD",
    "LUNCH_FUN_V4_ROBINHOOD",
}
BLOCKING_NO_CHASE = {"BLOCK", "BLOCKED", "CHASE", "DONT_CHASE", "NO_CHASE", "TOO_LATE"}


@dataclass(frozen=True)
class Decision:
    value: str
    reasons: tuple[str, ...]


def decide(record: dict[str, Any]) -> Decision:
    """Return RESEARCH/WATCH/SUPPRESS from explicit evidence only.

    The decision is deliberately conservative. Missing evidence can never
    become RESEARCH, and a quote is evidence of executability—not a promise
    about future execution or token quality.
    """
    source = str(record.get("launch_source") or "").upper()
    freshness = str(record.get("freshness_state") or "UNKNOWN").upper()
    no_chase = str(record.get("no_chase_state") or "UNKNOWN").upper()
    entry = record.get("entry_executable")
    exit_ = record.get("exit_executable")
    market_status = str(record.get("market_data_status") or "UNKNOWN").upper()
    result = record.get("round_trip_result") or {}
    loss = result.get("loss_percent")

    if source not in VERIFIED_SOURCES:
        return Decision("SUPPRESS", ("Source identity is incomplete or unverified.",))
    if no_chase in BLOCKING_NO_CHASE:
        return Decision("SUPPRESS", ("A blocking no-chase condition is active.",))
    if freshness == "STALE":
        return Decision("SUPPRESS", ("The launch is outside the useful freshness window.",))
    if entry is False:
        return Decision("SUPPRESS", ("The benchmark entry path did not execute.",))
    if exit_ is False:
        return Decision("SUPPRESS", ("The benchmark exit path did not execute.",))

    if entry is True and exit_ is True and loss is not None:
        if float(loss) <= 20.0 and freshness in {"FRESH", "RECENT"}:
            reasons = [
                "Launch source is verified.",
                "A benchmark entry and immediate exit both executed in read-only quotes.",
                f"Observed round-trip impact was {float(loss):.1f}%.",
            ]
            if market_status == "QUOTE_ONLY":
                reasons.append("Executability is known; aggregate liquidity and volume are not yet available.")
            return Decision("RESEARCH", tuple(reasons))
        return Decision(
            "WATCH",
            (
                "Entry and exit paths exist, but observed round-trip impact is too high for RESEARCH.",
                "Wait for a healthier market state.",
            ),
        )

    return Decision(
        "WATCH",
        (
            "The launch is verified but market or executability evidence is incomplete.",
            "Wait for enough evidence before researching further.",
        ),
    )
