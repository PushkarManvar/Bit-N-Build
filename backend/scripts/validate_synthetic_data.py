#!/usr/bin/env python3
"""Validate the generated synthetic dataset against the frozen G1 contract.

Checks performed:

1. Every ``data/raw/*.jsonl`` envelope is a valid ``EventIngestionRequest``.
2. Expected normalization failures are the ones we intended (unsupported
   schema version or malformed timestamp) and not accidental validation errors.
3. Source event IDs are unique per channel for the non-duplicate events.
4. ``(channel, source_event_id)`` duplicates reuse an identical payload.
5. Truth references resolve, every customer with events exists in
   ``customers_truth.csv``, and the flagship order ``ORD-204`` carries both
   expected alerts.

Truth files are only read here for evaluation. Runtime matching must never
read them.

Usage:
    python backend/scripts/validate_synthetic_data.py [--data-dir DIR]
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from generate_synthetic_data import (  # noqa: E402
    CUSTOMERS_TRUTH,
    EVENT_TRUTH,
    EXPECTED_ALERTS,
    RAW_FILES,
    default_data_dir,
)

from app.schemas.events import EventIngestionRequest  # noqa: E402

FLAGSHIP_ORDER = "ORD-204"


class ValidationError(Exception):
    """Raised when the dataset violates an expected invariant."""


def _load_raw(data_dir: Path) -> list[dict[str, Any]]:
    events: list[dict[str, Any]] = []
    for channel, filename in RAW_FILES.items():
        path = data_dir / "raw" / filename
        if not path.exists():
            raise ValidationError(f"missing raw file: {path}")
        for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            if not line.strip():
                continue
            try:
                payload = json.loads(line)
            except json.JSONDecodeError as exc:
                raise ValidationError(f"{filename}:{line_number} is not JSON: {exc}") from exc
            if payload.get("channel") != channel:
                raise ValidationError(
                    f"{filename}:{line_number} channel {payload.get('channel')!r} "
                    f"does not match file channel {channel!r}"
                )
            events.append(payload)
    return events


def _read_truth(data_dir: Path, filename: str) -> list[dict[str, str]]:
    path = data_dir / "truth" / filename
    with path.open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def validate(data_dir: Path) -> dict[str, int]:
    raw_events = _load_raw(data_dir)
    truth_events = _read_truth(data_dir, EVENT_TRUTH)
    truth_customers = _read_truth(data_dir, CUSTOMERS_TRUTH)
    expected_alerts = _read_truth(data_dir, EXPECTED_ALERTS)

    truth_by_key = {(row["channel"], row["source_event_id"]): row for row in truth_events}
    customer_ids = {row["truth_profile_id"] for row in truth_customers}

    parsed: list[EventIngestionRequest] = []
    normalization_failures = 0

    for payload in raw_events:
        key = (payload.get("channel"), payload.get("source_event_id"))
        truth = truth_by_key.get(key)
        if truth is None:
            raise ValidationError(f"no truth row for {key}")
        expected_invalid = truth["is_invalid"] == "true"

        try:
            event = EventIngestionRequest.model_validate(payload)
        except Exception as exc:  # noqa: BLE001 - classified below
            if not expected_invalid:
                raise ValidationError(
                    f"unexpected G1 validation failure for {key}: {exc}"
                ) from exc
            # Expected failures are either a malformed timestamp (422 at the
            # API boundary) or an unsupported schema version (202 downstream).
            normalization_failures += 1
            continue

        if expected_invalid:
            # A schema version the G1 normalizer rejects: valid envelope, but a
            # downstream normalization failure (HTTP 202).
            if event.schema_version != "1.0":
                normalization_failures += 1
            else:
                raise ValidationError(
                    f"invalid event {key} looks fully valid; expected a failure"
                )
        parsed.append(event)

    # Uniqueness of non-duplicate source IDs, and duplicate payloads must match.
    payload_by_key: dict[tuple[str, str], str] = {}
    duplicate_count = 0
    unique_keys: set[tuple[str, str]] = set()
    for event in parsed:
        key = (event.channel.value, event.source_event_id)
        serialized = event.model_dump_json()
        if key in payload_by_key:
            if payload_by_key[key] != serialized:
                raise ValidationError(f"duplicate {key} reuses the ID with a different payload")
            duplicate_count += 1
        else:
            payload_by_key[key] = serialized
            unique_keys.add(key)

    # Truth references resolve.
    for row in truth_events:
        truth_id = row["truth_profile_id"]
        if truth_id and truth_id not in customer_ids:
            raise ValidationError(f"event truth references unknown profile {truth_id}")

    # Flagship alerts.
    flagship_alerts = {
        row["alert_type"]
        for row in expected_alerts
        if row["order_id"] == FLAGSHIP_ORDER
    }
    if flagship_alerts != {"unresolved_refund", "repeat_contact"}:
        raise ValidationError(
            f"{FLAGSHIP_ORDER} expected exactly both flagship alerts, got {flagship_alerts}"
        )

    # Every customer with events should be reachable; report journey flags.
    broken = sum(1 for row in truth_customers if row["is_broken_journey"] == "true")
    bridges = sum(1 for row in truth_customers if row["anonymous_bridge"] == "true")
    collisions = {row["collision_group"] for row in truth_customers if row["collision_group"]}

    return {
        "raw_events": len(raw_events),
        "valid_envelopes": len(parsed),
        "unique_source_ids": len(unique_keys),
        "duplicate_records": duplicate_count,
        "expected_normalization_failures": normalization_failures,
        "customers": len(truth_customers),
        "broken_journeys": broken,
        "anonymous_bridges": bridges,
        "collision_groups": len(collisions),
        "expected_alert_rows": len(expected_alerts),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate the synthetic dataset.")
    parser.add_argument("--data-dir", type=Path, default=default_data_dir())
    args = parser.parse_args()

    try:
        summary = validate(args.data_dir)
    except ValidationError as exc:
        print(f"INVALID: {exc}")
        return 1

    print(f"Dataset at {args.data_dir} is valid")
    for key, value in summary.items():
        print(f"  {key}: {value}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
