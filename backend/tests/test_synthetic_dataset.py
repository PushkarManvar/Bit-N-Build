"""Tests for the generated synthetic dataset.

These tests are hermetic: if ``data/raw`` or ``data/truth`` are absent or
empty, the generator is invoked into a temporary directory so CI and fresh
clones do not depend on committed data. Runtime matching never reads truth
files; only evaluation tests do.
"""

from __future__ import annotations

import csv
import json
from pathlib import Path

import pytest
from generate_synthetic_data import (
    EVENT_TRUTH,
    EXPECTED_ALERTS,
    RAW_FILES,
    generate,
)
from validate_synthetic_data import validate

from app.schemas.events import EventIngestionRequest

REPO_ROOT = Path(__file__).resolve().parents[2]
DATA_ROOT = REPO_ROOT / "data"


@pytest.fixture(scope="module")
def dataset_dir(tmp_path_factory: pytest.TempPathFactory) -> Path:
    """Use committed data when present, otherwise generate a fresh copy."""
    committed_raw = DATA_ROOT / "raw" / RAW_FILES["web"]
    committed_truth = DATA_ROOT / "truth" / EVENT_TRUTH
    if (
        committed_raw.exists()
        and committed_raw.stat().st_size > 0
        and committed_truth.exists()
        and committed_truth.stat().st_size > 0
    ):
        return DATA_ROOT

    target = tmp_path_factory.mktemp("synthetic")
    generate(target)
    return target


def _read_raw(data_dir: Path) -> list[dict]:
    events: list[dict] = []
    for filename in RAW_FILES.values():
        lines = (data_dir / "raw" / filename).read_text(encoding="utf-8").splitlines()
        events.extend(json.loads(line) for line in lines if line.strip())
    return events


def _read_truth(data_dir: Path, filename: str) -> list[dict[str, str]]:
    with (data_dir / "truth" / filename).open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def test_dataset_passes_validation(dataset_dir: Path) -> None:
    summary = validate(dataset_dir)

    assert summary["raw_events"] >= 180
    assert summary["raw_events"] <= 250
    assert summary["customers"] >= 30
    assert summary["customers"] <= 40
    assert summary["duplicate_records"] >= 3
    assert summary["duplicate_records"] <= 8


def test_composition_targets(dataset_dir: Path) -> None:
    summary = validate(dataset_dir)

    assert 3 <= summary["expected_normalization_failures"] <= 5
    assert 5 <= summary["broken_journeys"] <= 10
    assert 5 <= summary["anonymous_bridges"] <= 8
    assert 2 <= summary["collision_groups"] <= 3


def test_every_constructor_accepted_or_intentionally_failed(dataset_dir: Path) -> None:
    truth = _read_truth(dataset_dir, EVENT_TRUTH)
    truth_by_key = {(row["channel"], row["source_event_id"]): row for row in truth}

    for payload in _read_raw(dataset_dir):
        key = (payload["channel"], payload["source_event_id"])
        row = truth_by_key[key]
        if row["is_invalid"] == "true":
            continue
        # Valid envelopes must construct without error.
        EventIngestionRequest.model_validate(payload)


def test_duplicate_payloads_are_identical(dataset_dir: Path) -> None:
    seen: dict[tuple[str, str], str] = {}
    for payload in _read_raw(dataset_dir):
        key = (payload["channel"], payload["source_event_id"])
        serialized = json.dumps(payload, sort_keys=True)
        if key in seen:
            assert seen[key] == serialized
        else:
            seen[key] = serialized


def test_flagship_order_has_both_expected_alerts(dataset_dir: Path) -> None:
    alerts = _read_truth(dataset_dir, EXPECTED_ALERTS)
    flagship = {row["alert_type"] for row in alerts if row["order_id"] == "ORD-204"}
    assert flagship == {"unresolved_refund", "repeat_contact"}


def test_no_truth_identifiers_in_raw_events(dataset_dir: Path) -> None:
    raw_text = "".join(
        (dataset_dir / "raw" / filename).read_text(encoding="utf-8")
        for filename in RAW_FILES.values()
    )
    assert "TRUTH-" not in raw_text
    assert "expected_outcome" not in raw_text


def test_generator_is_deterministic(tmp_path: Path) -> None:
    first = tmp_path / "first"
    second = tmp_path / "second"
    generate(first)
    generate(second)

    for filename in RAW_FILES.values():
        assert (first / "raw" / filename).read_text(encoding="utf-8") == (
            second / "raw" / filename
        ).read_text(encoding="utf-8")

    for filename in (EVENT_TRUTH, EXPECTED_ALERTS):
        assert (first / "truth" / filename).read_text(encoding="utf-8") == (
            second / "truth" / filename
        ).read_text(encoding="utf-8")
