"""Dependency-free local LaunchLens demo server."""

from __future__ import annotations

import argparse
import json
import sqlite3
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import unquote, urlparse

from .read_model import DEFAULT_DB, load_feed

PUBLIC = Path(__file__).resolve().parent / "public"


class LaunchLensHandler(BaseHTTPRequestHandler):
    mode = "replay"
    db_path = DEFAULT_DB

    def _send(self, status: int, body: bytes, content_type: str) -> None:
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.end_headers()
        self.wfile.write(body)

    def _json(self, status: int, payload: object) -> None:
        self._send(status, json.dumps(payload, ensure_ascii=False).encode(), "application/json; charset=utf-8")

    def do_GET(self) -> None:  # noqa: N802
        path = unquote(urlparse(self.path).path)
        if path in {"/", "/index.html"}:
            return self._send(200, (PUBLIC / "index.html").read_bytes(), "text/html; charset=utf-8")
        if path == "/app.js":
            return self._send(200, (PUBLIC / "app.js").read_bytes(), "text/javascript; charset=utf-8")
        if path == "/styles.css":
            return self._send(200, (PUBLIC / "styles.css").read_bytes(), "text/css; charset=utf-8")
        if path == "/links.css":
            return self._send(200, (PUBLIC / "links.css").read_bytes(), "text/css; charset=utf-8")
        if path == "/mobile.css":
            return self._send(200, (PUBLIC / "mobile.css").read_bytes(), "text/css; charset=utf-8")
        if path == "/api/health":
            return self._json(200, {"status": "ok", "mode": self.mode, "read_only": True})
        try:
            metadata, launches = load_feed(self.mode, self.db_path)
        except (OSError, sqlite3.Error, ValueError):  # pragma: no cover - defensive boundary
            # Do not return exception text: SQLite errors may contain a local path.
            return self._json(503, {"error": "data_unavailable"})
        if path == "/api/launches":
            return self._json(200, {"meta": metadata, "launches": launches})
        if path.startswith("/api/launches/"):
            launch_id = path.rsplit("/", 1)[-1]
            match = next((item for item in launches if item["launch_id"] == launch_id), None)
            return self._json(200 if match else 404, match or {"error": "not_found"})
        self._json(404, {"error": "not_found"})

    def do_POST(self) -> None:  # noqa: N802
        self._json(405, {"error": "read_only"})

    def log_message(self, format: str, *args: object) -> None:
        return


def main() -> None:
    parser = argparse.ArgumentParser(description="Pulse LaunchLens")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8780)
    parser.add_argument("--mode", choices=("replay", "live"), default="replay")
    parser.add_argument("--db", type=Path, default=DEFAULT_DB)
    args = parser.parse_args()
    LaunchLensHandler.mode = args.mode
    LaunchLensHandler.db_path = args.db
    server = ThreadingHTTPServer((args.host, args.port), LaunchLensHandler)
    print(f"LaunchLens {args.mode} demo: http://{args.host}:{args.port}")
    server.serve_forever()


if __name__ == "__main__":
    main()
