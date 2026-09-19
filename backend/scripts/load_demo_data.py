#!/usr/bin/env python3
"""Load the visible synthetic dataset into the database (G6/G7).

Reads ``data/raw/*.jsonl`` (frozen G1 envelopes) and pushes every event
through the real ingestion pipeline (normalize -> identity -> alerts).

Usage:
    docker compose run --rm backend python scripts/load_demo_data.py
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from pydantic import ValidationError  # noqa: E402

from app.db.session import SessionLocal  # noqa: E402
from app.schemas.events import EventIngestionRequest  # noqa: E402
from app.services.event_ingestion import ingest_event  # noqa: E402

RAW_FILES = [
    "web_events.jsonl",
    "mobile_events.jsonl",
    "call_center_events.jsonl",
    "store_events.jsonl",
]


def default_data_dir() -> Path:
    env = os.environ.get("JOURNEYLENS_DATA_DIR")
    if env:
        return Path(env)
    if Path("/data").is_dir():
        return Path("/data")
    return Path(__file__).resolve().parents[2] / "data"


def load_demo_data(data_dir: Path) -> dict[str, int]:
    db = SessionLocal()
    counts = {"received": 0, "duplicates": 0, "failed": 0, "invalid": 0}
    try:
        for filename in RAW_FILES:
            path = data_dir / "raw" / filename
            if not path.exists():
                continue
            with path.open("r", encoding="utf-8") as handle:
                for line in handle:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        envelope = EventIngestionRequest.model_validate_json(line)
                    except ValidationError:
                        counts["invalid"] += 1
                        continue
                    result = ingest_event(db, envelope)
                    if result.http_status == 201:
                        counts["received"] += 1
                    elif result.http_status == 200:
                        counts["duplicates"] += 1
                    else:
                        counts["failed"] += 1
        db.commit()
        return counts
    finally:
        db.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-dir", type=Path, default=None)
    args = parser.parse_args()

    counts = load_demo_data(args.data_dir or default_data_dir())
    for key, value in counts.items():
        print(f"{key}: {value}")