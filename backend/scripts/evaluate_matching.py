#!/usr/bin/env python3
"""Evaluate identity resolution and alerts against hidden ground truth (Gate G6).

Reads ``data/truth/*.csv`` (gitignored; never read by runtime matching) and
compares against the current database state. Writes a persisted
``evaluation_runs`` row consumed by ``GET /api/analytics/overview``.

Usage:
    docker compose run --rm backend python scripts/evaluate_matching.py
"""

from __future__ import annotations

import argparse
import csv
import os
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.db.models import (  # noqa: E402
    CanonicalEvent,
    EvaluationRun,
    JourneyAlert,
    MatchDecision,
    RawEvent,
)
from app.db.session import SessionLocal  # noqa: E402

EVENT_TRUTH = "event_truth.csv"
EXPECTED_ALERTS = "expected_alerts.csv"
CUSTOMERS_TRUTH = "customers_truth.csv"

_EVALUATABLE_OUTCOMES = {"new_profile", "auto_link", "review_required"}


def default_data_dir() -> Path:
    env = os.environ.get("JOURNEYLENS_DATA_DIR")
    if env:
        return Path(env)
    if Path("/data").is_dir():
        return Path("/data")
    return Path(__file__).resolve().parents[2] / "data"


def _read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def _event_assignments(db) -> dict[tuple[str, str], str | None]:
    """Map (channel, source_event_id) -> runtime profile id (or None)."""
    rows = db.execute(
        RawEvent.__table__.select()
        .outerjoin(CanonicalEvent, CanonicalEvent.raw_event_id == RawEvent.id)
        .with_only_columns(
            RawEvent.channel,
            RawEvent.source_event_id,
            CanonicalEvent.profile_id,
        )
    ).all()
    return {(channel, source_id): str(pid) if pid else None for channel, source_id, pid in rows}


def _pair_metrics(events: list[dict[str, Any]]) -> dict[str, Any]:
    """Pair-level precision/recall over assigned events with truth ids."""
    eligible = [
        e for e in events if e["truth_id"] and e["runtime_profile"] is not None
    ]
    tp = fp = fn = tn = 0
    for i in range(len(eligible)):
        for j in range(i + 1, len(eligible)):
            a, b = eligible[i], eligible[j]
            same_truth = a["truth_id"] == b["truth_id"]
            same_profile = a["runtime_profile"] == b["runtime_profile"]
            if same_truth:
                if same_profile:
                    tp += 1
                else:
                    fn += 1
            elif same_profile:
                fp += 1
            else:
                tn += 1

    precision = tp / (tp + fp) if (tp + fp) else 0.0
    recall = tp / (tp + fn) if (tp + fn) else 0.0
    f1 = 2 * precision * recall / (precision + recall) if (precision + recall) else 0.0
    false_merge = fp / (tp + fp) if (tp + fp) else 0.0

    return {
        "tp": tp,
        "fp": fp,
        "fn": fn,
        "tn": tn,
        "match_precision": round(precision, 4),
        "match_recall": round(recall, 4),
        "match_f1": round(f1, 4),
        "false_merge_rate": round(false_merge, 4),
        "assigned_events": len(eligible),
    }


def _alert_metrics(db, event_rows: list[dict[str, str]], data_dir: Path) -> dict[str, Any]:
    """Compare runtime open alerts to expected_alerts.csv tuples."""
    profile_truth: dict[str, set[str]] = {}
    for row in event_rows:
        runtime = row.get("_runtime_profile")
        truth = row.get("truth_profile_id")
        if runtime and truth:
            profile_truth.setdefault(runtime, set()).add(truth)

    expected = {
        (row["truth_profile_id"], row["order_id"], row["alert_type"])
        for row in _read_csv(data_dir / "truth" / EXPECTED_ALERTS)
        if row.get("alert_type")
    }
    actual: set[tuple[str, str, str]] = set()
    alert_keys: dict[tuple[str, str, str], int] = {}
    for alert in db.query(JourneyAlert).filter(JourneyAlert.status == "open").all():
        key = (str(alert.profile_id), alert.order_id or "", alert.type.value)
        alert_keys[key] = alert_keys.get(key, 0) + 1
        for truth_id in profile_truth.get(str(alert.profile_id), set()):
            actual.add((truth_id, alert.order_id or "", alert.type.value))

    duplicates = sum(1 for count in alert_keys.values() if count > 1)

    found = expected & actual
    missed = expected - actual
    unexpected = actual - expected

    denom_p = len(found) + len(unexpected)
    denom_r = len(found) + len(missed)
    precision = len(found) / denom_p if denom_p else 0.0
    recall = len(found) / denom_r if denom_r else 0.0

    return {
        "alert_found": len(found),
        "alert_missed": len(missed),
        "alert_unexpected": len(unexpected),
        "alert_duplicates": duplicates,
        "alert_precision": round(precision, 4),
        "alert_recall": round(recall, 4),
    }


def _outcome_rates(db) -> dict[str, Any]:
    total = db.query(MatchDecision).count()
    if total == 0:
        return {"auto_link_rate": None, "review_required_rate": None}
    auto = db.query(MatchDecision).filter(MatchDecision.outcome == "auto_linked").count()
    review = db.query(MatchDecision).filter(MatchDecision.outcome == "review_required").count()
    return {
        "auto_link_rate": round(auto / total * 100, 1),
        "review_required_rate": round(review / total * 100, 1),
    }


def evaluate(data_dir: Path) -> dict[str, Any]:
    truth_dir = data_dir / "truth"
    event_rows = _read_csv(truth_dir / EVENT_TRUTH)
    customers = _read_csv(truth_dir / CUSTOMERS_TRUTH)

    db = SessionLocal()
    try:
        assignments = _event_assignments(db)

        evaluatable: list[dict[str, Any]] = []
        for row in event_rows:
            if row.get("is_duplicate_of"):
                continue
            if row.get("is_invalid") == "true":
                continue
            if row.get("expected_outcome") not in _EVALUATABLE_OUTCOMES:
                continue
            key = (row["channel"], row["source_event_id"])
            runtime = assignments.get(key)
            row["_runtime_profile"] = runtime
            evaluatable.append(
                {
                    "truth_id": row.get("truth_profile_id") or "",
                    "runtime_profile": runtime,
                }
            )

        metrics: dict[str, Any] = {}
        metrics.update(_pair_metrics(evaluatable))
        metrics.update(_alert_metrics(db, event_rows, data_dir))
        metrics.update(_outcome_rates(db))

        unassigned = sum(1 for e in evaluatable if e["runtime_profile"] is None)
        metrics["unassigned_events"] = unassigned
        metrics["truth_customers"] = sum(1 for c in customers if c.get("truth_profile_id"))
        metrics["truth_events"] = len(evaluatable)
        metrics["evaluated_at"] = datetime.now(UTC).isoformat()

        run = EvaluationRun(metrics=metrics, note="evaluate_matching.py")
        db.add(run)
        db.commit()
        return metrics
    finally:
        db.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-dir", type=Path, default=None)
    args = parser.parse_args()

    _data_dir = args.data_dir or default_data_dir()
    result = evaluate(_data_dir)
    for key, value in result.items():
        print(f"{key}: {value}")