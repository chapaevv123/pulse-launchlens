from __future__ import annotations

import json
import re
import sqlite3
import tempfile
import threading
import unittest
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

from launchlens.decision import decide
from launchlens.read_model import DEFAULT_DB, DEFAULT_REPLAY, PUBLIC_FIELDS, _build_public, load_live, load_replay
from launchlens.server import LaunchLensHandler, ThreadingHTTPServer
from launchlens.tools.public_leak_audit import scan


BASE = {
    "launch_id": "test",
    "token_address": "0x" + "1" * 40,
    "launch_source": "PONS_ROBINHOOD",
    "detected_at": "2026-10-05T03:00:00+00:00",
    "freshness_state": "FRESH",
    "entry_executable": True,
    "exit_executable": True,
    "round_trip_loss_pct": -8.0,
    "quote_notional_usd": 100,
}


class DecisionTests(unittest.TestCase):
    def test_research_logic(self):
        row = _build_public(BASE, now=datetime(2026, 10, 5, 4, tzinfo=timezone.utc), mode="replay")
        self.assertEqual(row["decision"], "RESEARCH")

    def test_watch_logic(self):
        record = {"launch_source": "PONS_ROBINHOOD", "freshness_state": "RECENT", "entry_executable": True,
                  "exit_executable": True, "round_trip_result": {"loss_percent": 24}}
        self.assertEqual(decide(record).value, "WATCH")

    def test_suppress_logic(self):
        record = {"launch_source": "DOPPLER_UNATTRIBUTED_ROBINHOOD", "freshness_state": "FRESH"}
        self.assertEqual(decide(record).value, "SUPPRESS")

    def test_unknown_never_becomes_research(self):
        record = {"launch_source": "PONS_ROBINHOOD", "freshness_state": "UNKNOWN",
                  "entry_executable": None, "exit_executable": None}
        self.assertEqual(decide(record).value, "WATCH")

    def test_entry_and_exit_are_preserved(self):
        row = _build_public(BASE, now=datetime(2026, 10, 5, 4, tzinfo=timezone.utc), mode="replay")
        self.assertIs(row["entry_executable"], True)
        self.assertIs(row["exit_executable"], True)


class PublicBoundaryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.meta, cls.rows = load_replay()

    def test_public_safe_serialization(self):
        self.assertTrue(self.rows)
        self.assertTrue(all(set(row) == PUBLIC_FIELDS for row in self.rows))

    def test_no_private_or_secret_fields(self):
        serialized = json.dumps(self.rows).lower()
        forbidden = ("telegram", "discord", "wallet", "api_key", "secret", "owner_note", "run_id", "c:\\\\users")
        for marker in forbidden:
            self.assertNotIn(marker, serialized)

    def test_provenance_retained(self):
        for row in self.rows:
            self.assertTrue(row["evidence"]["source_event_id"])
            self.assertIsNotNone(row["evidence"]["block_number"])

    def test_replay_records_exist_in_production_db(self):
        if not DEFAULT_DB.exists():
            self.skipTest("Production observation database is unavailable")
        connection = sqlite3.connect(f"file:{DEFAULT_DB.resolve().as_posix()}?mode=ro", uri=True)
        try:
            for raw in json.loads(DEFAULT_REPLAY.read_text(encoding="utf-8"))["observations"]:
                count = connection.execute(
                    "SELECT COUNT(*) FROM robinhood_production_observation_v1 WHERE source_event_id=? AND contract=?",
                    (raw["source_event_id"], raw["token_address"]),
                ).fetchone()[0]
                self.assertGreater(count, 0, raw["source_event_id"])
        finally:
            connection.close()

    def test_replay_has_all_decisions(self):
        self.assertEqual({row["decision"] for row in self.rows}, {"RESEARCH", "WATCH", "SUPPRESS"})

    def test_quote_only_does_not_infer_liquidity(self):
        quoted = next(row for row in self.rows if row["market_data_status"] == "QUOTE_ONLY")
        self.assertIsNone(quoted["liquidity_usd"])
        self.assertIsNone(quoted["volume_24h_usd"])
        self.assertIsNotNone(quoted["price_usd"])

    def test_market_freshness_is_evidence_based(self):
        quoted = next(row for row in self.rows if row["decision"] == "RESEARCH")
        self.assertEqual(quoted["market_freshness"], "FRESH")
        unavailable = next(row for row in self.rows if row["market_data_status"] == "UNAVAILABLE")
        self.assertEqual(unavailable["market_freshness"], "UNKNOWN")

    def test_explorer_links_are_exact_and_https(self):
        for row in self.rows:
            self.assertEqual(
                row["links"]["contract_explorer"],
                f"https://robinhoodchain.blockscout.com/address/{row['token_address']}",
            )
            self.assertRegex(row["links"]["block_explorer"], r"^https://robinhoodchain\.blockscout\.com/block/\d+$")

    def test_unattributed_source_has_no_platform_fallback(self):
        row = next(item for item in self.rows if item["launch_source"].startswith("DOPPLER_UNATTRIBUTED"))
        self.assertIsNone(row["links"]["launch_source"])
        self.assertIsNone(row["links"]["market_source"])

    def test_live_read_is_safe_and_nonempty(self):
        if not DEFAULT_DB.exists():
            self.skipTest("Production observation database is unavailable")
        rows = load_live(limit=3)
        self.assertEqual(len(rows), 3)
        self.assertTrue(all(set(row) == PUBLIC_FIELDS for row in rows))

    def test_replay_file_contains_no_credential_shape(self):
        raw = DEFAULT_REPLAY.read_text(encoding="utf-8")
        patterns = [r"(?i)(api[_-]?key|token|secret|password)\s*[:=]\s*[\"'][^\"']{8,}", r"\b[1-9A-HJ-NP-Za-km-z]{44,88}\b"]
        for pattern in patterns:
            self.assertIsNone(re.search(pattern, raw))


class ServerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        LaunchLensHandler.mode = "replay"
        cls.server = ThreadingHTTPServer(("127.0.0.1", 0), LaunchLensHandler)
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()
        cls.base = f"http://127.0.0.1:{cls.server.server_port}"

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()

    def test_ui_and_api_render(self):
        html = urllib.request.urlopen(self.base + "/", timeout=2).read().decode()
        payload = json.load(urllib.request.urlopen(self.base + "/api/launches", timeout=2))
        self.assertIn("Pulse LaunchLens", html)
        self.assertEqual(len(payload["launches"]), 4)

    def test_detail_endpoint_renders_one_launch(self):
        payload = json.load(urllib.request.urlopen(self.base + "/api/launches", timeout=2))
        expected = payload["launches"][0]
        detail = json.load(urllib.request.urlopen(self.base + f"/api/launches/{expected['launch_id']}", timeout=2))
        self.assertEqual(detail, expected)

    def test_ui_has_detail_and_safe_external_link_contract(self):
        app = (Path(__file__).resolve().parents[1] / "public" / "app.js").read_text(encoding="utf-8")
        self.assertIn("PROVENANCE & EVIDENCE", app)
        self.assertIn('rel="noopener noreferrer"', app)
        self.assertIn("MARKET FRESHNESS", app)

    def test_basic_responsive_breakpoint_exists(self):
        css = (Path(__file__).resolve().parents[1] / "public" / "styles.css").read_text(encoding="utf-8")
        self.assertIn("@media(max-width:760px)", css)

    def test_cloudflare_boundary_has_no_db_or_cron(self):
        config = (Path(__file__).resolve().parents[1] / "wrangler.jsonc").read_text(encoding="utf-8")
        self.assertNotIn("d1_databases", config)
        self.assertNotIn('"crons"', config)
        self.assertIn('"run_worker_first": true', config)

    def test_entire_contest_boundary_has_zero_public_leaks(self):
        self.assertEqual(scan(), [])

    def test_detail_deep_link_supports_judge_demo(self):
        app = (Path(__file__).resolve().parents[1] / "public" / "app.js").read_text(encoding="utf-8")
        self.assertIn("#launch=", app)

    def test_health_declares_read_only(self):
        health = json.load(urllib.request.urlopen(self.base + "/api/health", timeout=2))
        self.assertIs(health["read_only"], True)

    def test_writes_are_rejected(self):
        request = urllib.request.Request(self.base + "/api/launches", data=b"{}", method="POST")
        with self.assertRaises(urllib.error.HTTPError) as error:
            urllib.request.urlopen(request, timeout=2)
        self.assertEqual(error.exception.code, 405)

    def test_no_trade_or_messaging_dependencies(self):
        root = Path(__file__).resolve().parents[1]
        code = "\n".join(path.read_text(encoding="utf-8") for path in root.glob("*.py"))
        self.assertNotRegex(code, r"(?m)^\s*(from|import)\s+.*(telegram|web3|discord|wallet)")
        self.assertNotIn("eth_sendRawTransaction", code)


if __name__ == "__main__":
    unittest.main()
