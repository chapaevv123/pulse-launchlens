"""Read-only extraction into the deliberately narrow LaunchLens schema."""

from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .decision import decide

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DB = ROOT / "data" / "fast_money" / "robinhood_shadow_v1.db"
DEFAULT_REPLAY = Path(__file__).resolve().parent / "demo" / "replay.json"

PUBLIC_FIELDS = {
    "launch_id", "chain", "token_address", "token_symbol", "token_name",
    "launch_source", "detected_at", "age_seconds", "liquidity_usd",
    "volume_24h_usd", "price_usd", "market_data_status",
    "entry_executable", "exit_executable", "round_trip_result",
    "freshness_state", "market_freshness", "market_source", "market_observed_at",
    "decision", "decision_reasons", "evidence", "links", "record_mode",
}

EXPLORER_BASE = "https://robinhoodchain.blockscout.com"
PONS_BASE = "https://www.ponsfamily.com/launchpad"


def _iso(value: str | None) -> datetime | None:
    if not value:
        return None
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def _loss(value: Any) -> float | None:
    if value is None:
        return None
    return round(abs(float(value)), 2)


def _market_freshness(observed_at: str | None, now: datetime) -> str:
    observed = _iso(observed_at)
    if observed is None:
        return "UNKNOWN"
    seconds = max(0, (now - observed).total_seconds())
    if seconds <= 15 * 60:
        return "FRESH"
    if seconds <= 60 * 60:
        return "RECENT"
    return "STALE"


def _links(row: dict[str, Any]) -> dict[str, str | None]:
    contract = row.get("token_address")
    block = row.get("block_number")
    source = str(row.get("launch_source") or "").upper()
    is_pons = source.startswith("PONS")
    return {
        "contract_explorer": f"{EXPLORER_BASE}/address/{contract}" if contract else None,
        "block_explorer": f"{EXPLORER_BASE}/block/{block}" if block is not None else None,
        "launch_source": f"{PONS_BASE}/{contract}" if contract and is_pons else None,
        "market_source": f"{PONS_BASE}/{contract}" if contract and is_pons else None,
    }


def _build_public(row: dict[str, Any], *, now: datetime, mode: str) -> dict[str, Any]:
    detected = _iso(row.get("detected_at"))
    age_seconds = max(0, int((now - detected).total_seconds())) if detected else None
    price = row.get("price_usd") or row.get("entry_effective_price")
    liquidity = row.get("liquidity_usd") or row.get("t0_liquidity")
    volume = row.get("volume_24h_usd")
    entry = None if row.get("entry_executable") is None else bool(row["entry_executable"])
    exit_ = None if row.get("exit_executable") is None else bool(row["exit_executable"])
    market_status = "AVAILABLE" if any(v is not None for v in (liquidity, volume)) else (
        "QUOTE_ONLY" if entry is not None else "UNAVAILABLE"
    )
    result = {
        "benchmark_notional_usd": row.get("quote_notional_usd"),
        "immediate_exit_value_usd": row.get("immediate_sell_back_usd"),
        "loss_percent": _loss(row.get("round_trip_loss_pct")),
        "observed_at": row.get("quote_observed_at"),
        "disclaimer": "Read-only historical quote; not a trade or guarantee.",
    }
    public = {
        "launch_id": row.get("launch_id"),
        "chain": "Robinhood Chain",
        "token_address": row.get("token_address"),
        "token_symbol": row.get("token_symbol"),
        "token_name": row.get("token_name"),
        "launch_source": row.get("launch_source"),
        "detected_at": row.get("detected_at"),
        "age_seconds": age_seconds,
        "liquidity_usd": liquidity,
        "volume_24h_usd": volume,
        "price_usd": price,
        "market_data_status": market_status,
        "market_source": row.get("market_source") or ("Pons read-only quote" if entry is not None else None),
        "market_observed_at": row.get("market_observed_at") or row.get("quote_observed_at"),
        "entry_executable": entry,
        "exit_executable": exit_,
        "round_trip_result": result,
        "freshness_state": row.get("freshness_state") or "UNKNOWN",
        "market_freshness": _market_freshness(row.get("market_observed_at") or row.get("quote_observed_at"), now),
        "decision": "WATCH",
        "decision_reasons": [],
        "evidence": {
            "source_event_id": row.get("source_event_id"),
            "block_number": row.get("block_number"),
            "block_timestamp": row.get("block_timestamp"),
            "quote_source": row.get("quote_source"),
            "route": row.get("quote_route"),
        },
        "links": _links(row),
        "record_mode": mode.upper(),
        "no_chase_state": row.get("no_chase_state") or "UNKNOWN",
    }
    verdict = decide(public)
    public["decision"] = verdict.value
    public["decision_reasons"] = list(verdict.reasons)
    public.pop("no_chase_state")
    assert set(public) == PUBLIC_FIELDS
    return public


LIVE_QUERY = """
SELECT f.launch_id, f.token_address, f.source_id AS launch_source,
       f.detected_at, f.freshness_class AS freshness_state,
       t.name AS token_name, t.symbol AS token_symbol,
       g.quote_notional_usd, g.entry_effective_price,
       g.immediate_sell_back_usd, g.immediate_round_trip_loss_pct AS round_trip_loss_pct,
       g.t0_liquidity, g.created_at AS quote_observed_at,
       g.executable_quote_available AS entry_executable,
       r.immediate_sell_would_fill AS exit_executable,
       r.entry_quote_source AS quote_source, r.entry_route AS quote_route,
       o.source_event_id, o.block_number, o.block_timestamp, o.no_chase_state
FROM fast_money_forward_launches_v1 f
JOIN fast_money_gem_entry_features_v1 g ON g.launch_id = f.launch_id
LEFT JOIN fast_money_forward_round_trips_v1 r ON r.launch_id = f.launch_id
LEFT JOIN fast_money_tokens t ON t.token_id = f.token_id
LEFT JOIN robinhood_production_observation_v1 o ON o.source_event_id = f.launch_id
WHERE f.source_id LIKE '%ROBINHOOD%'
ORDER BY g.created_at DESC
LIMIT ?
"""


def load_live(db_path: Path = DEFAULT_DB, *, limit: int = 40) -> list[dict[str, Any]]:
    """Read persisted production observations with SQLite immutable read-only mode."""
    uri = f"file:{db_path.resolve().as_posix()}?mode=ro&immutable=1"
    with sqlite3.connect(uri, uri=True) as connection:
        connection.row_factory = sqlite3.Row
        rows = [dict(row) for row in connection.execute(LIVE_QUERY, (limit,))]
    now = datetime.now(timezone.utc)
    return [_build_public(row, now=now, mode="live") for row in rows]


def load_replay(path: Path = DEFAULT_REPLAY) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    now = _iso(payload["reference_time"])
    if now is None:
        raise ValueError("Replay reference_time is required")
    rows = [_build_public(row, now=now, mode="replay") for row in payload["observations"]]
    return {k: payload[k] for k in ("dataset", "captured_at", "reference_time", "source")}, rows


def load_feed(mode: str, db_path: Path = DEFAULT_DB) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    if mode == "live":
        rows = load_live(db_path)
        return {"dataset": "live", "captured_at": datetime.now(timezone.utc).isoformat(), "source": "read-only SQLite"}, rows
    return load_replay()
