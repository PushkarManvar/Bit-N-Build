#!/usr/bin/env python3
"""Print aggregate composition for persisted pending identity reviews.

This local diagnostic emits only channel, score, conflict-presence, evidence
field names, normalized decision reasons, and counts. It never emits raw event
payloads, identifier values, profile IDs, or hidden evaluation truth.

Usage:
    python scripts/audit_review_queue_composition.py
"""

from __future__ import annotations

import json
import sys
from dataclasses import asdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.db.session import SessionLocal  # noqa: E402
from app.services.review_queue_composition_audit import (  # noqa: E402
    audit_pending_review_composition,
)


def main() -> int:
    """Print the current persisted review composition as aggregate JSON."""
    db = SessionLocal()
    try:
        audit = audit_pending_review_composition(db)
    finally:
        db.close()

    print(json.dumps(asdict(audit), indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
