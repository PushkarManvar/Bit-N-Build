"""Event ingestion orchestration for Gate G1.

Flow (docs/00_START_HERE.md G1):
POST /api/events -> validate -> duplicate check -> save raw ->
normalize -> save canonical -> respond.

Raw persistence always happens before normalization so failures are
recoverable. The (channel, source_event_id) pair is the idempotency key.
"""

import hashlib
import json
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.enums import ProcessingStatus
from app.core.errors import EventConflictError, NormalizationError
from app.db.models import CanonicalEvent, RawEvent
from app.schemas.events import (
    CanonicalEventDetail,
    EventIngestionRequest,
    EventIngestionResponse,
    EventRetrievalResponse,
    RawEventDetail,
)
from app.services.normalizer import NormalizedEvent, normalize_for_channel


@dataclass(frozen=True)
class IngestionResult:
    response: EventIngestionResponse
    http_status: int


def _payload_hash(envelope: EventIngestionRequest) -> str:
    canonical_json = json.dumps(
        envelope.model_dump(mode="json"),
        sort_keys=True,
        separators=(",", ":"),
    )
    return hashlib.sha256(canonical_json.encode("utf-8")).hexdigest()


def _to_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


def ingest_event(db: Session, envelope: EventIngestionRequest) -> IngestionResult:
    payload_hash = _payload_hash(envelope)

    existing = db.scalar(
        select(RawEvent).where(
            RawEvent.channel == envelope.channel,
            RawEvent.source_event_id == envelope.source_event_id,
        )
    )
    if existing is not None:
        if existing.payload_hash == payload_hash:
            canonical_id = db.scalar(
                select(CanonicalEvent.id).where(CanonicalEvent.raw_event_id == existing.id)
            )
            return IngestionResult(
                response=EventIngestionResponse(
                    raw_event_id=str(existing.id),
                    canonical_event_id=str(canonical_id) if canonical_id else None,
                    channel=existing.channel,
                    event_type=None,
                    occurred_at=_to_utc(existing.occurred_at),
                    processing_status="duplicate",
                    duplicate=True,
                ),
                http_status=200,
            )
        raise EventConflictError(
            channel=envelope.channel.value,
            source_event_id=envelope.source_event_id,
            raw_event_id=str(existing.id),
        )

    raw = RawEvent(
        channel=envelope.channel,
        source_event_id=envelope.source_event_id,
        schema_version=envelope.schema_version,
        occurred_at=_to_utc(envelope.occurred_at),
        payload=envelope.model_dump(mode="json"),
        payload_hash=payload_hash,
        processing_status=ProcessingStatus.RECEIVED,
    )
    db.add(raw)
    db.flush()

    try:
        normalized = normalize_for_channel(envelope)
    except NormalizationError as exc:
        raw.processing_status = ProcessingStatus.FAILED
        raw.processing_error = f"{exc.code}: {exc.message}"
        db.commit()
        return IngestionResult(
            response=EventIngestionResponse(
                raw_event_id=str(raw.id),
                canonical_event_id=None,
                channel=envelope.channel,
                event_type=None,
                occurred_at=_to_utc(raw.occurred_at),
                processing_status=ProcessingStatus.FAILED,
                duplicate=False,
            ),
            http_status=202,
        )

    canonical = _persist_canonical(db, raw, normalized)
    raw.processing_status = ProcessingStatus.NORMALIZED
    db.commit()

    return IngestionResult(
        response=EventIngestionResponse(
            raw_event_id=str(raw.id),
            canonical_event_id=str(canonical.id),
            channel=normalized.channel,
            event_type=normalized.event_type,
            occurred_at=normalized.occurred_at,
            processing_status=ProcessingStatus.NORMALIZED,
            duplicate=False,
        ),
        http_status=201,
    )


def _persist_canonical(
    db: Session, raw: RawEvent, normalized: NormalizedEvent
) -> CanonicalEvent:
    canonical = CanonicalEvent(
        raw_event_id=raw.id,
        channel=normalized.channel,
        event_type=normalized.event_type,
        occurred_at=normalized.occurred_at,
        identifiers=normalized.identifiers,
        entity_references=normalized.entity_references,
        attributes=normalized.attributes,
    )
    db.add(canonical)
    db.flush()
    return canonical


def retrieve_event(db: Session, raw_event_id: str) -> EventRetrievalResponse | None:
    try:
        raw_id = uuid.UUID(raw_event_id)
    except ValueError:
        return None
    raw = db.get(RawEvent, raw_id)
    if raw is None:
        return None
    canonical = db.scalar(
        select(CanonicalEvent).where(CanonicalEvent.raw_event_id == raw.id)
    )
    return EventRetrievalResponse(
        raw_event=_to_raw_detail(raw),
        canonical_event=_to_canonical_detail(canonical) if canonical else None,
    )


def _to_raw_detail(raw: RawEvent) -> RawEventDetail:
    return RawEventDetail(
        id=str(raw.id),
        channel=raw.channel,
        source_event_id=raw.source_event_id,
        schema_version=raw.schema_version,
        occurred_at=_to_utc(raw.occurred_at),
        received_at=_to_utc(raw.received_at),
        payload=raw.payload,
        processing_status=raw.processing_status,
        processing_error=raw.processing_error,
    )


def _to_canonical_detail(canonical: CanonicalEvent) -> CanonicalEventDetail:
    return CanonicalEventDetail(
        id=str(canonical.id),
        raw_event_id=str(canonical.raw_event_id),
        channel=canonical.channel,
        event_type=canonical.event_type,
        occurred_at=_to_utc(canonical.occurred_at),
        profile_id=str(canonical.profile_id) if canonical.profile_id else None,
        identifiers=canonical.identifiers,
        entity_references=canonical.entity_references,
        attributes=canonical.attributes,
        created_at=_to_utc(canonical.created_at),
    )