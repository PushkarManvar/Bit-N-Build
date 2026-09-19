#!/usr/bin/env python3
"""Print aggregate composition for the newest persisted pipeline events.

This is a local diagnostic only. It reads operational tables and emits no
event payloads, identifiers, profile IDs, or hidden synthetic truth data.

Usage:
    python scripts/audit_pipeline_composition.py [--limit 25]
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.db.session import SessionLocal  # noqa: E402
from app.services.pipeline_composition_audit import (  # noqa: E402
    audit_pipeline_composition,
)


def main() -> int:
    parser = argparse.ArgumentParser(description="Audit pipeline event composition.")
    parser.add_argument("--limit", type=int, default=25)
    args = parser.parse_args()

    if args.limit < 1:
        parser.error("--limit must be at least 1")

    db = SessionLocal()
    try:
        audit = audit_pipeline_composition(db, limit=args.limit)
    finally:
        db.close()

    print(json.dumps(asdict(audit), indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
