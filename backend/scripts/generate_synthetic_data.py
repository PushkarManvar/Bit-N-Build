#!/usr/bin/env python3
"""Deterministic synthetic dataset generator for JourneyLens.

Visible source events are written as frozen G1 envelopes
(docs/05_API_CONTRACT.md) to ``data/raw/*.jsonl``. They can be posted to
``POST /api/events`` unchanged and contain no truth identifiers.

Hidden ground truth is written to ``data/truth/*.csv`` and must never be read
by runtime matching.

Composition targets come from docs/04_DATA_IDENTITY_AND_RULES.md section 11:

* 30-40 customers
* 180-250 source events
* 3-5 invalid records
* 3-8 duplicate records
* 5-10 manual-review candidates
* 5 broken journeys
* 2-3 same-name collision cases
* 5-8 anonymous-to-known transitions

Usage:
    python backend/scripts/generate_synthetic_data.py [--data-dir DIR]
"""

from __future__ import annotations

import argparse
import csv
import json
import os
from collections.abc import Iterable
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

SEED = 20260919
SCHEMA_VERSION = "1.0"
ANCHOR = datetime(2026, 9, 14, 8, 0, tzinfo=UTC)

RAW_FILES: dict[str, str] = {
    "web": "web_events.jsonl",
    "mobile_app": "mobile_events.jsonl",
    "call_center": "call_center_events.jsonl",
    "physical_store": "store_events.jsonl",
}

CUSTOMERS_TRUTH = "customers_truth.csv"
EVENT_TRUTH = "event_truth.csv"
EXPECTED_MATCHES = "expected_matches.csv"
EXPECTED_ALERTS = "expected_alerts.csv"

OUTCOMES = ("new_profile", "auto_link", "review_required", "duplicate", "failed")

# Sentinel so callers can distinguish "use the customer's truth id" from
# "this event's true owner is unknown" (explicit ``None``).
_UNSET: Any = object()

FIRST_NAMES = [
    "Aarav", "Vivaan", "Aditya", "Vihaan", "Arjun", "Sai", "Reyansh", "Ayaan",
    "Krishna", "Ishaan", "Neha", "Priya", "Ananya", "Diya", "Saanvi", "Aarohi",
    "Anika", "Navya", "Myra", "Sara", "Rohan", "Karan", "Vikram", "Meera",
    "Pooja", "Rahul", "Amit", "Sneha", "Kavya", "Nisha",
]
LAST_NAMES = [
    "Patel", "Sharma", "Gupta", "Singh", "Kumar", "Mehta", "Shah", "Reddy",
    "Nair", "Iyer", "Joshi", "Desai", "Rao", "Verma", "Mishra",
]
CITIES = [
    "mumbai", "pune", "bengaluru", "delhi", "hyderabad", "chennai",
    "ahmedabad", "kolkata", "jaipur", "surat",
]


def default_data_dir() -> Path:
    """Resolve the data directory for local runs and the compose container."""
    env = os.environ.get("JOURNEYLENS_DATA_DIR")
    if env:
        return Path(env)
    if Path("/data").is_dir():
        return Path("/data")
    return Path(__file__).resolve().parents[2] / "data"


@dataclass
class Customer:
    truth_id: str
    display_name: str
    email: str | None = None
    phone: str | None = None
    customer_id: str | None = None
    device_id: str | None = None
    city: str | None = None
    order_id: str | None = None
    is_flagship: bool = False
    collision_group: str | None = None
    has_return: bool = False
    has_refund_completed: bool = False
    support_contacts: int = 0
    is_broken_journey: bool = False
    anonymous_bridge: bool = False


@dataclass
class EventRecord:
    channel: str
    source_event_id: str
    payload: dict[str, Any]
    truth_profile_id: str | None
    expected_outcome: str
    order_id: str | None = None
    is_duplicate_of: str | None = None
    is_invalid: bool = False
    invalid_reason: str | None = None

    @property
    def is_duplicate(self) -> bool:
        return self.is_duplicate_of is not None


class DatasetBuilder:
    """Accumulates source events and per-channel id counters."""

    def __init__(self) -> None:
        self._counters: dict[str, int] = {}
        self.records: list[EventRecord] = []

    def next_id(self, channel: str) -> str:
        count = self._counters.get(channel, 0) + 1
        self._counters[channel] = count
        return f"{channel.upper().replace('_', '')}-{count:05d}"

    def emit(
        self,
        payload: dict[str, Any],
        *,
        truth_profile_id: str | None,
        expected_outcome: str,
        order_id: str | None = None,
        is_invalid: bool = False,
        invalid_reason: str | None = None,
    ) -> EventRecord:
        assert expected_outcome in OUTCOMES, expected_outcome
        record = EventRecord(
            channel=payload["channel"],
            source_event_id=payload["source_event_id"],
            payload=payload,
            truth_profile_id=truth_profile_id,
            expected_outcome=expected_outcome,
            order_id=order_id,
            is_invalid=is_invalid,
            invalid_reason=invalid_reason,
        )
        self.records.append(record)
        return record

    def duplicate(self, record: EventRecord) -> EventRecord:
        clone = EventRecord(
            channel=record.channel,
            source_event_id=record.source_event_id,
            payload=json.loads(json.dumps(record.payload)),
            truth_profile_id=record.truth_profile_id,
            expected_outcome="duplicate",
            order_id=record.order_id,
            is_duplicate_of=record.source_event_id,
        )
        self.records.append(clone)
        return clone


def emit_event(
    builder: DatasetBuilder,
    customer: Customer,
    *,
    channel: str,
    event_type: str,
    include: Iterable[str] = (),
    day: int = 0,
    minute: int = 0,
    order_id: str | None = None,
    session_id: str | None = None,
    issue_id: str | None = None,
    attributes: dict[str, Any] | None = None,
    expected_outcome: str = "auto_link",
    schema_version: str = SCHEMA_VERSION,
    occurred_at_override: str | None = None,
    truth_profile_id: Any = _UNSET,
    is_invalid: bool = False,
    invalid_reason: str | None = None,
) -> EventRecord:
    include = set(include)
    identifiers: list[dict[str, str]] = []
    if "email" in include and customer.email:
        identifiers.append({"type": "email", "value": customer.email})
    if "phone" in include and customer.phone:
        identifiers.append({"type": "phone", "value": customer.phone})
    if "customer_id" in include and customer.customer_id:
        identifiers.append({"type": "customer_id", "value": customer.customer_id})
    if "device_id" in include and customer.device_id:
        identifiers.append({"type": "device_id", "value": customer.device_id})
    if "session_id" in include and session_id:
        identifiers.append({"type": "session_id", "value": session_id})

    entity_references: dict[str, Any] = {}
    if order_id:
        entity_references["order_id"] = order_id
    if issue_id:
        entity_references["issue_id"] = issue_id

    resolved_attributes: dict[str, Any] = {"customer_name": customer.display_name}
    if customer.city:
        resolved_attributes["city"] = customer.city
    if attributes:
        resolved_attributes.update(attributes)

    if occurred_at_override is not None:
        occurred_at = occurred_at_override
    else:
        occurred_at = (ANCHOR + timedelta(days=day, minutes=minute)).strftime(
            "%Y-%m-%dT%H:%M:%SZ"
        )

    payload: dict[str, Any] = {
        "source_event_id": builder.next_id(channel),
        "channel": channel,
        "event_type": event_type,
        "occurred_at": occurred_at,
        "schema_version": schema_version,
        "identifiers": identifiers,
        "entity_references": entity_references,
        "attributes": resolved_attributes,
    }
    resolved_truth = customer.truth_id if truth_profile_id is _UNSET else truth_profile_id
    return builder.emit(
        payload,
        truth_profile_id=resolved_truth,
        expected_outcome=expected_outcome,
        order_id=order_id,
        is_invalid=is_invalid,
        invalid_reason=invalid_reason,
    )


def emit_mixed_identifier_event(
    builder: DatasetBuilder,
    *,
    channel: str,
    event_type: str,
    identifiers: list[dict[str, str]],
    display_name: str,
    city: str | None,
    order_id: str | None,
    day: int,
    minute: int,
) -> EventRecord:
    """Emit a deliberately conflicting event (strong identifiers disagree)."""
    entity_references: dict[str, Any] = {}
    if order_id:
        entity_references["order_id"] = order_id
    attributes = {"customer_name": display_name}
    if city:
        attributes["city"] = city
    payload = {
        "source_event_id": builder.next_id(channel),
        "channel": channel,
        "event_type": event_type,
        "occurred_at": (ANCHOR + timedelta(days=day, minutes=minute)).strftime(
            "%Y-%m-%dT%H:%M:%SZ"
        ),
        "schema_version": SCHEMA_VERSION,
        "identifiers": identifiers,
        "entity_references": entity_references,
        "attributes": attributes,
    }
    return builder.emit(
        payload,
        truth_profile_id=None,
        expected_outcome="review_required",
        order_id=order_id,
    )


def _filler_customer(index: int) -> Customer:
    first = FIRST_NAMES[index % len(FIRST_NAMES)]
    last = LAST_NAMES[(index * 7) % len(LAST_NAMES)]
    city = CITIES[(index * 3) % len(CITIES)]
    digits = f"{index:08d}"
    return Customer(
        truth_id=f"TRUTH-F{index:03d}",
        display_name=f"{first} {last}",
        email=f"{first}.{last}{index}@example.com".lower(),
        phone=f"+9198{digits}",
        customer_id=f"CUST-{1000 + index}",
        device_id=f"DEV-{100 + index}",
        city=city,
        order_id=f"ORD-{300 + index}",
    )


def _normal_journey(builder: DatasetBuilder, customer: Customer, index: int) -> None:
    assert customer.order_id is not None
    order = customer.order_id
    session = f"SESS-{2000 + index}"
    emit_event(
        builder, customer, channel="web", event_type="product_viewed",
        include=("device_id", "session_id"), session_id=session, day=0, minute=index,
        expected_outcome="new_profile",
    )
    emit_event(
        builder, customer, channel="mobile_app", event_type="app_login",
        include=("email", "device_id"), day=0, minute=30 + index,
    )
    emit_event(
        builder, customer, channel="mobile_app", event_type="order_placed",
        include=("email", "customer_id"), order_id=order, day=0, minute=60 + index,
    )
    emit_event(
        builder, customer, channel="mobile_app", event_type="refund_completed",
        include=("email",), order_id=order, day=5, minute=index,
    )
    emit_event(
        builder, customer, channel="web", event_type="product_viewed",
        include=("device_id", "session_id"), session_id=session, day=6, minute=index,
    )
    emit_event(
        builder, customer, channel="physical_store", event_type="store_visited",
        include=("phone",), order_id=order, day=7, minute=index,
        attributes={"store_city": customer.city or ""},
    )
    customer.has_refund_completed = True


def _bridge_journey(builder: DatasetBuilder, customer: Customer, index: int) -> None:
    assert customer.order_id is not None
    order = customer.order_id
    session = f"SESS-{3000 + index}"
    emit_event(
        builder, customer, channel="web", event_type="product_viewed",
        include=("device_id", "session_id"), session_id=session, day=0, minute=index,
        expected_outcome="new_profile",
    )
    emit_event(
        builder, customer, channel="mobile_app", event_type="app_login",
        include=("email", "device_id"), day=0, minute=45 + index,
    )
    emit_event(
        builder, customer, channel="web", event_type="order_placed",
        include=("device_id", "customer_id"), order_id=order, day=0, minute=90 + index,
    )
    emit_event(
        builder, customer, channel="physical_store", event_type="store_visited",
        include=("phone",), order_id=order, day=3, minute=index,
        attributes={"store_city": customer.city or ""},
    )
    customer.anonymous_bridge = True


def _broken_journey(builder: DatasetBuilder, customer: Customer, index: int) -> None:
    assert customer.order_id is not None
    order = customer.order_id
    session = f"SESS-{4000 + index}"
    emit_event(
        builder, customer, channel="web", event_type="product_viewed",
        include=("device_id", "session_id"), session_id=session, day=0, minute=index,
        expected_outcome="new_profile",
    )
    emit_event(
        builder, customer, channel="mobile_app", event_type="app_login",
        include=("email", "device_id"), day=0, minute=40 + index,
    )
    emit_event(
        builder, customer, channel="mobile_app", event_type="return_requested",
        include=("email", "customer_id"), order_id=order, day=1, minute=index,
    )
    emit_event(
        builder, customer, channel="call_center", event_type="support_contacted",
        include=("phone",), order_id=order, day=1, minute=120 + index,
        attributes={"notes": "Refund not received"},
    )
    emit_event(
        builder, customer, channel="call_center", event_type="support_contacted",
        include=("phone",), order_id=order, day=2, minute=index,
        attributes={"notes": "Second follow-up"},
    )
    emit_event(
        builder, customer, channel="physical_store", event_type="store_visited",
        include=("phone",), order_id=order, day=2, minute=240 + index,
        attributes={"store_city": customer.city or ""},
    )
    customer.has_return = True
    customer.support_contacts = 2
    customer.is_broken_journey = True


def _inject_invalid(
    builder: DatasetBuilder, customer: Customer, channel: str, event_type: str, index: int
) -> None:
    reason = "unsupported schema_version" if index % 2 == 0 else "malformed occurred_at"
    if index % 2 == 0:
        emit_event(
            builder, customer, channel=channel, event_type=event_type,
            include=("device_id",), day=1, minute=index * 11,
            expected_outcome="failed", schema_version="9.9",
            is_invalid=True, invalid_reason=reason,
        )
    else:
        emit_event(
            builder, customer, channel=channel, event_type=event_type,
            include=("device_id",), occurred_at_override="not-a-timestamp",
            expected_outcome="failed", is_invalid=True, invalid_reason=reason,
        )


def generate(data_dir: Path) -> dict[str, int]:
    """Generate the dataset under ``data_dir`` and return composition counts."""
    builder = DatasetBuilder()
    customers: list[Customer] = []

    # --- Flagship: Riya Shah (four channels, ORD-204, broken refund) ---
    riya = Customer(
        truth_id="TRUTH-C001", display_name="Riya Shah",
        email="riya.shah@example.com", phone="+919876543210",
        customer_id="CUST-RIYA-001", device_id="DEV-17", city="mumbai",
        order_id="ORD-204", is_flagship=True, is_broken_journey=True,
        anonymous_bridge=True, has_return=True, support_contacts=2,
    )
    customers.append(riya)
    emit_event(
        builder, riya, channel="web", event_type="product_viewed",
        include=("device_id", "session_id"), session_id="SESS-1001", day=0, minute=0,
        expected_outcome="new_profile",
    )
    emit_event(
        builder, riya, channel="mobile_app", event_type="app_login",
        include=("email", "device_id"), order_id="ORD-204", day=0, minute=75,
    )
    emit_event(
        builder, riya, channel="web", event_type="return_requested",
        include=("device_id", "session_id"), session_id="SESS-1001", order_id="ORD-204",
        day=1, minute=0,
    )
    emit_event(
        builder, riya, channel="call_center", event_type="support_contacted",
        include=("phone",), order_id="ORD-204", day=1, minute=150,
        attributes={"notes": "Refund not received"},
    )
    emit_event(
        builder, riya, channel="call_center", event_type="support_contacted",
        include=("phone",), order_id="ORD-204", day=2, minute=60,
        attributes={"notes": "Second follow-up"},
    )
    emit_event(
        builder, riya, channel="physical_store", event_type="store_visited",
        include=("phone",), order_id="ORD-204", day=2, minute=300,
        attributes={"store_city": "mumbai"},
    )

    # --- Same-name collision groups (must never auto-link on name alone) ---
    aarav_a = Customer(
        truth_id="TRUTH-AARAV-A", display_name="Aarav Patel",
        email="aarav.patel.a@example.com", phone="+919000000001",
        customer_id="CUST-AARAV-A", device_id="DEV-701", city="pune",
        order_id="ORD-701", collision_group="aarav_patel",
    )
    aarav_b = Customer(
        truth_id="TRUTH-AARAV-B", display_name="Aarav Patel",
        email="aarav.patel.b@example.com", phone="+919000000002",
        customer_id="CUST-AARAV-B", device_id="DEV-702", city="pune",
        order_id="ORD-702", collision_group="aarav_patel",
    )
    neha_a = Customer(
        truth_id="TRUTH-NEHA-A", display_name="Neha Gupta",
        email="neha.gupta.a@example.com", phone="+919000000003",
        customer_id="CUST-NEHA-A", device_id="DEV-703", city="delhi",
        order_id="ORD-703", collision_group="neha_gupta",
    )
    neha_b = Customer(
        truth_id="TRUTH-NEHA-B", display_name="Neha Gupta",
        email="neha.gupta.b@example.com", phone="+919000000004",
        customer_id="CUST-NEHA-B", device_id="DEV-704", city="delhi",
        order_id="ORD-704", collision_group="neha_gupta",
    )
    for offset, member in enumerate((aarav_a, aarav_b, neha_a, neha_b)):
        customers.append(member)
        emit_event(
            builder, member, channel="web", event_type="product_viewed",
            include=("device_id",), day=3, minute=offset,
            expected_outcome="new_profile",
        )
        emit_event(
            builder, member, channel="mobile_app", event_type="app_login",
            include=("email", "device_id"), order_id=member.order_id, day=3, minute=30 + offset,
        )

    # Ambiguous same-name events: name + city only, no strong identifier.
    ambiguous = [
        Customer("TRUTH-AMB-AARAV", "Aarav Patel", city="pune"),
        Customer("TRUTH-AMB-NEHA", "Neha Gupta", city="delhi"),
    ]
    for offset, shadow in enumerate(ambiguous):
        emit_event(
            builder, shadow, channel="physical_store", event_type="store_visited",
            include=(), day=4, minute=offset, expected_outcome="review_required",
            truth_profile_id=None, attributes={"store_city": shadow.city or ""},
        )

    # Strong-conflict events: email points to one profile, phone to another.
    emit_mixed_identifier_event(
        builder, channel="call_center", event_type="support_contacted",
        identifiers=[
            {"type": "email", "value": aarav_a.email or ""},
            {"type": "phone", "value": aarav_b.phone or ""},
        ],
        display_name="Aarav Patel", city="pune", order_id="ORD-701", day=5, minute=0,
    )
    emit_mixed_identifier_event(
        builder, channel="call_center", event_type="support_contacted",
        identifiers=[
            {"type": "email", "value": neha_a.email or ""},
            {"type": "phone", "value": neha_b.phone or ""},
        ],
        display_name="Neha Gupta", city="delhi", order_id="ORD-703", day=5, minute=30,
    )

    # --- Filler: 4 broken journeys, 6 anonymous bridges, 20 normal journeys ---
    broken_count = 4
    bridge_count = 6
    normal_count = 20

    filler_customers: list[Customer] = []
    for i in range(1, broken_count + 1):
        customer = _filler_customer(i)
        filler_customers.append(customer)
        customers.append(customer)
        _broken_journey(builder, customer, i)

    for i in range(broken_count + 1, broken_count + bridge_count + 1):
        customer = _filler_customer(i)
        filler_customers.append(customer)
        customers.append(customer)
        _bridge_journey(builder, customer, i)

    for i in range(broken_count + bridge_count + 1, broken_count + bridge_count + normal_count + 1):
        customer = _filler_customer(i)
        filler_customers.append(customer)
        customers.append(customer)
        _normal_journey(builder, customer, i)

    # Two extra strong conflicts between profiles that already have events,
    # so email and phone genuinely resolve to different known profiles.
    conflict_x = filler_customers[0]
    conflict_y = filler_customers[1]
    emit_mixed_identifier_event(
        builder, channel="call_center", event_type="support_contacted",
        identifiers=[
            {"type": "email", "value": conflict_x.email or ""},
            {"type": "phone", "value": conflict_y.phone or ""},
        ],
        display_name=conflict_x.display_name, city=conflict_x.city,
        order_id=conflict_x.order_id, day=8, minute=0,
    )
    conflict_p = filler_customers[4]
    conflict_q = filler_customers[5]
    emit_mixed_identifier_event(
        builder, channel="call_center", event_type="support_contacted",
        identifiers=[
            {"type": "customer_id", "value": conflict_p.customer_id or ""},
            {"type": "email", "value": conflict_q.email or ""},
        ],
        display_name=conflict_q.display_name, city=conflict_q.city,
        order_id=conflict_q.order_id, day=8, minute=30,
    )

    # Near-tie same-name + same-city, no strong identifier (not a known profile).
    near_tie_shadow = Customer("TRUTH-AMB-TIE", "Vikram Mehta", city="jaipur")
    emit_event(
        builder, near_tie_shadow, channel="physical_store", event_type="store_visited",
        include=(), day=4, minute=10, expected_outcome="review_required",
        truth_profile_id=None, attributes={"store_city": near_tie_shadow.city or ""},
    )

    # --- Invalid records (raw is preserved, normalization fails) ---
    invalid_specs = [
        ("web", "product_viewed"),
        ("mobile_app", "app_login"),
        ("call_center", "support_contacted"),
        ("web", "product_viewed"),
    ]
    for idx, (channel, event_type) in enumerate(invalid_specs):
        owner = customers[idx % len(customers)]
        _inject_invalid(builder, owner, channel, event_type, idx)

    # --- Duplicate records (identical replay of an existing envelope) ---
    duplicate_sources = [
        r for r in builder.records
        if not r.is_invalid and r.expected_outcome == "auto_link"
    ]
    step = max(1, len(duplicate_sources) // 6)
    for source in duplicate_sources[::step][:6]:
        builder.duplicate(source)

    _write_raw(data_dir, builder.records)
    _write_truth(data_dir, customers, builder.records)

    unique_events = [r for r in builder.records if not r.is_duplicate]
    duplicates = [r for r in builder.records if r.is_duplicate]
    invalid = [r for r in builder.records if r.is_invalid]
    review = [r for r in builder.records if r.expected_outcome == "review_required"]
    broken = [c for c in customers if c.is_broken_journey]
    bridges = [c for c in customers if c.anonymous_bridge]
    collisions = {c.collision_group for c in customers if c.collision_group}

    return {
        "customers": len(customers),
        "unique_source_events": len(unique_events),
        "total_source_events": len(builder.records),
        "invalid_records": len(invalid),
        "duplicate_records": len(duplicates),
        "manual_review_candidates": len(review),
        "broken_journeys": len(broken),
        "anonymous_to_known": len(bridges),
        "same_name_collisions": len(collisions),
    }


def _write_raw(data_dir: Path, records: list[EventRecord]) -> None:
    raw_dir = data_dir / "raw"
    raw_dir.mkdir(parents=True, exist_ok=True)
    for channel, filename in RAW_FILES.items():
        lines = [
            json.dumps(r.payload, separators=(",", ":"))
            for r in records
            if r.channel == channel
        ]
        (raw_dir / filename).write_text("\n".join(lines) + "\n", encoding="utf-8")


def _write_truth(
    data_dir: Path,
    customers: list[Customer],
    records: list[EventRecord],
) -> None:
    truth_dir = data_dir / "truth"
    truth_dir.mkdir(parents=True, exist_ok=True)

    _write_csv(
        truth_dir / CUSTOMERS_TRUTH,
        [
            "truth_profile_id", "display_name", "canonical_email", "canonical_phone",
            "customer_id", "device_id", "city", "is_flagship", "collision_group",
            "has_return", "has_refund_completed", "support_contacts", "is_broken_journey",
            "anonymous_bridge", "order_id",
        ],
        [
            {
                "truth_profile_id": c.truth_id,
                "display_name": c.display_name,
                "canonical_email": c.email or "",
                "canonical_phone": c.phone or "",
                "customer_id": c.customer_id or "",
                "device_id": c.device_id or "",
                "city": c.city or "",
                "is_flagship": str(c.is_flagship).lower(),
                "collision_group": c.collision_group or "",
                "has_return": str(c.has_return).lower(),
                "has_refund_completed": str(c.has_refund_completed).lower(),
                "support_contacts": c.support_contacts,
                "is_broken_journey": str(c.is_broken_journey).lower(),
                "anonymous_bridge": str(c.anonymous_bridge).lower(),
                "order_id": c.order_id or "",
            }
            for c in customers
        ],
    )

    _write_csv(
        truth_dir / EVENT_TRUTH,
        [
            "channel", "source_event_id", "truth_profile_id", "expected_outcome",
            "order_id", "is_duplicate_of", "is_invalid", "invalid_reason",
        ],
        [
            {
                "channel": r.channel,
                "source_event_id": r.source_event_id,
                "truth_profile_id": r.truth_profile_id or "",
                "expected_outcome": r.expected_outcome,
                "order_id": r.order_id or "",
                "is_duplicate_of": r.is_duplicate_of or "",
                "is_invalid": str(r.is_invalid).lower(),
                "invalid_reason": r.invalid_reason or "",
            }
            for r in records
        ],
    )

    _write_csv(
        truth_dir / EXPECTED_MATCHES,
        ["channel", "source_event_id", "expected_truth_profile_id", "expected_outcome"],
        [
            {
                "channel": r.channel,
                "source_event_id": r.source_event_id,
                "expected_truth_profile_id": r.truth_profile_id or "",
                "expected_outcome": r.expected_outcome,
            }
            for r in records
            if not r.is_duplicate
        ],
    )

    alert_rows: list[dict[str, Any]] = []
    for customer in customers:
        if not customer.is_broken_journey or not customer.order_id:
            continue
        alert_rows.append({
            "truth_profile_id": customer.truth_id,
            "order_id": customer.order_id,
            "alert_type": "unresolved_refund",
            "severity": "high",
        })
        alert_rows.append({
            "truth_profile_id": customer.truth_id,
            "order_id": customer.order_id,
            "alert_type": "repeat_contact",
            "severity": "medium",
        })
    _write_csv(
        truth_dir / EXPECTED_ALERTS,
        ["truth_profile_id", "order_id", "alert_type", "severity"],
        alert_rows,
    )


def _write_csv(path: Path, fieldnames: list[str], rows: list[dict[str, Any]]) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate the JourneyLens synthetic dataset.")
    parser.add_argument("--data-dir", type=Path, default=default_data_dir())
    args = parser.parse_args()

    summary = generate(args.data_dir)
    print(f"Wrote dataset to {args.data_dir}")
    for key, value in summary.items():
        print(f"  {key}: {value}")


if __name__ == "__main__":
    main()
