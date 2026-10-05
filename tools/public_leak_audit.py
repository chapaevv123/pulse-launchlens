"""Fail closed on credential/private-data shapes in the contest boundary."""

from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EXCLUDED = {"node_modules", ".wrangler", "__pycache__", ".git"}
TEXT_EXTENSIONS = {".py", ".js", ".json", ".jsonc", ".html", ".css", ".md", ".txt", ".toml", ".yaml", ".yml"}
FORBIDDEN_NAMES = {".env", ".dev.vars", "pulse.db"}
PATTERNS = {
    "local_user_path": re.compile(r"(?i)[a-z]:\\users\\[^\\\s]+"),
    "pem_private_key": re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----"),
    "openai_key": re.compile(r"\bsk-[A-Za-z0-9_-]{20,}\b"),
    "telegram_bot_token": re.compile(r"\b\d{8,12}:[A-Za-z0-9_-]{30,}\b"),
    "assigned_secret": re.compile(r"(?i)(api[_-]?key|secret|password|private[_-]?key)\s*[:=]\s*[\"'][^\"']{8,}[\"']"),
    "seed_phrase": re.compile(r"(?i)(mnemonic|seed[_ ]phrase)\s*[:=]\s*[\"'][a-z ]{20,}[\"']"),
}


def scan() -> list[str]:
    findings: list[str] = []
    for path in ROOT.rglob("*"):
        if any(part in EXCLUDED for part in path.parts) or not path.is_file():
            continue
        if path.name.lower() in FORBIDDEN_NAMES or path.suffix.lower() in {".db", ".sqlite", ".sqlite3"}:
            findings.append(f"forbidden_file:{path.relative_to(ROOT)}")
            continue
        if path.suffix.lower() not in TEXT_EXTENSIONS:
            continue
        text = path.read_text(encoding="utf-8", errors="replace")
        for name, pattern in PATTERNS.items():
            if pattern.search(text):
                findings.append(f"{name}:{path.relative_to(ROOT)}")
    return findings


if __name__ == "__main__":
    findings = scan()
    print(f"PUBLIC_LEAK_COUNT={len(findings)}")
    for finding in findings:
        print(finding)
    raise SystemExit(1 if findings else 0)
