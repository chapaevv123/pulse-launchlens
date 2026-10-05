"""Build the deployable public replay artifact from the canonical replay file."""

from __future__ import annotations

import json
from pathlib import Path

from launchlens.read_model import load_replay


def main() -> None:
    meta, launches = load_replay()
    target = Path(__file__).resolve().parents[1] / "public" / "data" / "launches.json"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(
        json.dumps({"meta": meta, "launches": launches}, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(f"Exported {len(launches)} public replay records")


if __name__ == "__main__":
    main()
