"""Local/test-only diagnostics for pipeline event composition.

The audit explains whether repetitive pipeline rows come from persisted event
composition, batched receipt times, or the frontend projection. It deliberately
returns aggregates only and is not exposed through an HTTP route.
"""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.enums import ContactReason, EventType
from app.db.models import CanonicalEvent, RawEvent

_RECOGNIZED_SUPPORT_NOTES = {"refund not received", "second follow-up"}
_RECOGNIZED_CONTACT_REASONS = {
    ContactReason.REFUND_NOT_RECEIVED.value,
    ContactReason.RETURN_STATUS.value,
}


@dataclass(frozen=True)
class PipelineCompositionAudit:
    """Aggregate composition of the newest receipt-ordered pipeline window."""

    window_size: int
    channel_counts: dict[str, int]
    event_type_counts: dict[str, int]
    processing_status_counts: dict[str, int]
    distinct_received_at_seconds: int
    distinct_occurred_at_seconds: int
    rows_with_order_reference: int
    rows_with_recognized_support_context: int
    rows_with_recognized_store_context: int


def audit_pipeline_composition(
    db: Session,
    *,
    limit: int = 25,
) -> PipelineCompositionAudit:
    """Measure the newest receipt-ordered page without exposing row-level data."""
    if limit < 1:
        raise ValueError("limit must be at least 1")

    rows = db.execute(
        select(RawEvent, CanonicalEvent)
        .outerjoin(CanonicalEvent, CanonicalEvent.raw_event_id == RawEvent.id)
        .order_by(RawEvent.received_at.desc(), RawEvent.id.desc())
        .limit(limit)
    ).all()

    channel_counts: Counter[str] = Counter()
    event_type_counts: Counter[str] = Counter()
    processing_status_counts: Counter[str] = Counter()
    received_seconds: set[datetime] = set()
    occurred_seconds: set[datetime] = set()
    rows_with_order_reference = 0
    rows_with_recognized_support_context = 0
    rows_with_recognized_store_context = 0

    for raw, canonical in rows:
        channel_counts[raw.channel.value] += 1
        processing_status_counts[raw.processing_status.value] += 1
        received_seconds.add(_at_second(raw.received_at))
        occurred_seconds.add(_at_second(raw.occurred_at))
        if canonical is None:
            continue

        event_type_counts[canonical.event_type.value] += 1
        if _has_order_reference(canonical):
            rows_with_order_reference += 1
        if _has_recognized_support_context(canonical):
            rows_with_recognized_support_context += 1
        if _has_recognized_store_context(canonical):
            rows_with_recognized_store_context += 1

    return PipelineCompositionAudit(
        window_size=len(rows),
        channel_counts=dict(sorted(channel_counts.items())),
        event_type_counts=dict(sorted(event_type_counts.items())),
        processing_status_counts=dict(sorted(processing_status_counts.items())),
        distinct_received_at_seconds=len(received_seconds),
        distinct_occurred_at_seconds=len(occurred_seconds),
        rows_with_order_reference=rows_with_order_reference,
        rows_with_recognized_support_context=rows_with_recognized_support_context,
        rows_with_recognized_store_context=rows_with_recognized_store_context,
    )


def _at_second(value: datetime) -> datetime:
    """Return a UTC timestamp with sub-second differences removed for the audit."""
    if value.tzinfo is None:
        value = value.replace(tzinfo=UTC)
    return value.astimezone(UTC).replace(microsecond=0)


def _has_order_reference(event: CanonicalEvent) -> bool:
    value = event.entity_references.get("order_id")
    return isinstance(value, str) and bool(value.strip())


def _has_recognized_support_context(event: CanonicalEvent) -> bool:
    if event.event_type != EventType.SUPPORT_CONTACTED:
        return False
    contact_reason = event.attributes.get("contact_reason")
    if contact_reason in _RECOGNIZED_CONTACT_REASONS:
        return True
    note = event.attributes.get("notes")
    return isinstance(note, str) and note.strip().lower() in _RECOGNIZED_SUPPORT_NOTES


def _has_recognized_store_context(event: CanonicalEvent) -> bool:
    if event.event_type != EventType.STORE_VISITED:
        return False
    city = event.attributes.get("store_city")
    return isinstance(city, str) and bool(city.strip())
