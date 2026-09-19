"""Read model for the inspectable synchronous data pipeline."""

import base64
import binascii
import hashlib
import json
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime

from sqlalchemy import and_, func, or_, select, text
from sqlalchemy.orm import Session

from app.core.enums import Channel, IdentityOutcome, ProcessingStatus, ReviewStatus
from app.core.errors import AppError
from app.db.models import CanonicalEvent, MatchDecision, RawEvent
from app.schemas.events import CanonicalEventDetail, RawEventDetail
from app.schemas.pipeline import (
    PipelineChannelCounts,
    PipelineChannels,
    PipelineEventDetailResponse,
    PipelineEventListResponse,
    PipelineEventOut,
    PipelineEventSummary,
    PipelineIdentityDecisionOut,
    PipelineOverviewResponse,
    PipelineStageCounts,
    PipelineUpdatesResponse,
)
from app.services.event_presentation import present_event


@dataclass(frozen=True)
class PipelineEventFilters:
    channel: Channel | None = None
    processing_status: ProcessingStatus | None = None
    identity_outcome: IdentityOutcome | None = None
    source_event_id: str | None = None


@dataclass(frozen=True)
class PipelinePageCursor:
    received_at: datetime
    raw_event_id: uuid.UUID


_ORIGIN_CURSOR = PipelinePageCursor(
    received_at=datetime(1970, 1, 1, tzinfo=UTC),
    raw_event_id=uuid.UUID(int=0),
)


def _filters_fingerprint(filters: PipelineEventFilters) -> str:
    payload = {
        "channel": filters.channel.value if filters.channel else None,
        "identity_outcome": filters.identity_outcome.value if filters.identity_outcome else None,
        "processing_status": filters.processing_status.value if filters.processing_status else None,
        "source_event_id": filters.source_event_id.lower() if filters.source_event_id else None,
    }
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _encode_page_cursor(raw: RawEvent, filters: PipelineEventFilters) -> str:
    payload = {
        "filters": _filters_fingerprint(filters),
        "kind": "pipeline_events_v1",
        "raw_event_id": str(raw.id),
        "received_at": _to_utc(raw.received_at).isoformat(),
    }
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return base64.urlsafe_b64encode(encoded).decode("ascii").rstrip("=")


def _invalid_cursor() -> AppError:
    return AppError(
        code="VALIDATION_ERROR",
        message="Pipeline cursor is invalid or does not match the active filters.",
        stage="pipeline",
        http_status=422,
    )


def _decode_page_cursor(value: str, filters: PipelineEventFilters) -> PipelinePageCursor:
    try:
        padded = value + "=" * (-len(value) % 4)
        decoded = base64.urlsafe_b64decode(padded.encode("ascii"))
        payload = json.loads(decoded)
        if (
            payload.get("kind") != "pipeline_events_v1"
            or payload.get("filters") != _filters_fingerprint(filters)
        ):
            raise ValueError
        received_at = datetime.fromisoformat(payload["received_at"])
        raw_event_id = uuid.UUID(payload["raw_event_id"])
    except (
        binascii.Error,
        KeyError,
        TypeError,
        UnicodeDecodeError,
        ValueError,
        json.JSONDecodeError,
    ) as exc:
        raise _invalid_cursor() from exc
    return PipelinePageCursor(
        received_at=_to_utc(received_at),
        raw_event_id=raw_event_id,
    )


def _encode_update_cursor(cursor: PipelinePageCursor) -> str:
    payload = {
        "kind": "pipeline_updates_v1",
        "raw_event_id": str(cursor.raw_event_id),
        "received_at": cursor.received_at.isoformat(),
    }
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return base64.urlsafe_b64encode(encoded).decode("ascii").rstrip("=")


def _decode_update_cursor(value: str) -> PipelinePageCursor:
    try:
        padded = value + "=" * (-len(value) % 4)
        decoded = base64.urlsafe_b64decode(padded.encode("ascii"))
        payload = json.loads(decoded)
        if payload.get("kind") != "pipeline_updates_v1":
            raise ValueError
        received_at = datetime.fromisoformat(payload["received_at"])
        raw_event_id = uuid.UUID(payload["raw_event_id"])
    except (
        binascii.Error,
        KeyError,
        TypeError,
        UnicodeDecodeError,
        ValueError,
        json.JSONDecodeError,
    ) as exc:
        raise _invalid_cursor() from exc
    return PipelinePageCursor(
        received_at=_to_utc(received_at),
        raw_event_id=raw_event_id,
    )


def _at_or_before(cursor: PipelinePageCursor):
    return or_(
        RawEvent.received_at < cursor.received_at,
        and_(
            RawEvent.received_at == cursor.received_at,
            RawEvent.id <= cursor.raw_event_id,
        ),
    )


def _strictly_before(cursor: PipelinePageCursor):
    return or_(
        RawEvent.received_at < cursor.received_at,
        and_(
            RawEvent.received_at == cursor.received_at,
            RawEvent.id < cursor.raw_event_id,
        ),
    )


def _strictly_after(cursor: PipelinePageCursor):
    return or_(
        RawEvent.received_at > cursor.received_at,
        and_(
            RawEvent.received_at == cursor.received_at,
            RawEvent.id > cursor.raw_event_id,
        ),
    )


def _capture_high_water(db: Session) -> PipelinePageCursor:
    row = db.execute(
        select(RawEvent.received_at, RawEvent.id)
        .order_by(RawEvent.received_at.desc(), RawEvent.id.desc())
        .limit(1)
    ).first()
    if row is None:
        return _ORIGIN_CURSOR
    received_at, raw_event_id = row
    return PipelinePageCursor(
        received_at=_to_utc(received_at),
        raw_event_id=raw_event_id,
    )


def _prepare_snapshot(db: Session) -> None:
    if db.get_bind().dialect.name == "postgresql":
        db.execute(text("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ"))


def _to_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


def _count(db: Session, model) -> int:
    return int(db.scalar(select(func.count()).select_from(model)) or 0)


def _channel_counts(
    db: Session,
    high_water: PipelinePageCursor | None = None,
) -> PipelineChannels:
    counts = {
        channel: {"raw": 0, "normalized": 0, "failed": 0}
        for channel in Channel
    }

    raw_statement = select(RawEvent.channel, func.count())
    if high_water is not None:
        raw_statement = raw_statement.where(_at_or_before(high_water))
    for channel, count in db.execute(raw_statement.group_by(RawEvent.channel)).all():
        counts[channel]["raw"] = int(count)

    canonical_statement = select(CanonicalEvent.channel, func.count()).join(
        RawEvent,
        RawEvent.id == CanonicalEvent.raw_event_id,
    )
    if high_water is not None:
        canonical_statement = canonical_statement.where(_at_or_before(high_water))
    for channel, count in db.execute(canonical_statement.group_by(CanonicalEvent.channel)).all():
        counts[channel]["normalized"] = int(count)

    failed_statement = select(RawEvent.channel, func.count()).where(
        RawEvent.processing_status == ProcessingStatus.FAILED
    )
    if high_water is not None:
        failed_statement = failed_statement.where(_at_or_before(high_water))
    for channel, count in db.execute(failed_statement.group_by(RawEvent.channel)).all():
        counts[channel]["failed"] = int(count)

    return PipelineChannels(
        web=PipelineChannelCounts(**counts[Channel.WEB]),
        mobile_app=PipelineChannelCounts(**counts[Channel.MOBILE_APP]),
        call_center=PipelineChannelCounts(**counts[Channel.CALL_CENTER]),
        physical_store=PipelineChannelCounts(**counts[Channel.PHYSICAL_STORE]),
    )


def _stage_counts(
    db: Session,
    high_water: PipelinePageCursor | None = None,
) -> PipelineStageCounts:
    raw_scope = _at_or_before(high_water) if high_water is not None else None
    raw_count_statement = select(func.count()).select_from(RawEvent)
    if raw_scope is not None:
        raw_count_statement = raw_count_statement.where(raw_scope)
    failed_statement = select(func.count()).select_from(RawEvent).where(
        RawEvent.processing_status == ProcessingStatus.FAILED
    )
    if raw_scope is not None:
        failed_statement = failed_statement.where(raw_scope)
    canonical_count_statement = select(func.count()).select_from(CanonicalEvent).join(
        RawEvent,
        RawEvent.id == CanonicalEvent.raw_event_id,
    )
    if raw_scope is not None:
        canonical_count_statement = canonical_count_statement.where(raw_scope)
    linked_statement = (
        select(func.count())
        .select_from(CanonicalEvent)
        .join(RawEvent, RawEvent.id == CanonicalEvent.raw_event_id)
        .where(CanonicalEvent.profile_id.is_not(None))
    )
    if raw_scope is not None:
        linked_statement = linked_statement.where(raw_scope)
    review_statement = (
        select(func.count())
        .select_from(MatchDecision)
        .join(CanonicalEvent, CanonicalEvent.id == MatchDecision.canonical_event_id)
        .join(RawEvent, RawEvent.id == CanonicalEvent.raw_event_id)
        .where(
            MatchDecision.outcome == IdentityOutcome.REVIEW_REQUIRED,
            MatchDecision.review_status == ReviewStatus.PENDING,
        )
    )
    if raw_scope is not None:
        review_statement = review_statement.where(raw_scope)
    identity_statement = (
        select(func.count())
        .select_from(MatchDecision)
        .join(CanonicalEvent, CanonicalEvent.id == MatchDecision.canonical_event_id)
        .join(RawEvent, RawEvent.id == CanonicalEvent.raw_event_id)
    )
    if raw_scope is not None:
        identity_statement = identity_statement.where(raw_scope)
    return PipelineStageCounts(
        raw_accepted=int(db.scalar(raw_count_statement) or 0),
        normalization_succeeded=int(db.scalar(canonical_count_statement) or 0),
        normalization_failed=int(db.scalar(failed_statement) or 0),
        identity_decided=int(db.scalar(identity_statement) or 0),
        profile_linked=int(db.scalar(linked_statement) or 0),
        review_required=int(db.scalar(review_statement) or 0),
    )


def _error_code(processing_error: str | None) -> str | None:
    if not processing_error:
        return None
    code, _, _ = processing_error.partition(":")
    return code.strip() or None


def _source_prefix_pattern(value: str) -> str:
    escaped = value.lower().replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
    return f"{escaped}%"


def _apply_event_filters(statement, filters: PipelineEventFilters):
    if filters.channel is not None:
        statement = statement.where(RawEvent.channel == filters.channel)
    if filters.processing_status is not None:
        statement = statement.where(RawEvent.processing_status == filters.processing_status)
    if filters.identity_outcome is not None:
        statement = statement.where(MatchDecision.outcome == filters.identity_outcome)
    if filters.source_event_id:
        statement = statement.where(
            func.lower(RawEvent.source_event_id).like(
                _source_prefix_pattern(filters.source_event_id),
                escape="\\",
            )
        )
    return statement


def _event_statement(filters: PipelineEventFilters):
    statement = (
        select(RawEvent, CanonicalEvent, MatchDecision)
        .outerjoin(CanonicalEvent, CanonicalEvent.raw_event_id == RawEvent.id)
        .outerjoin(
            MatchDecision,
            MatchDecision.canonical_event_id == CanonicalEvent.id,
        )
    )
    return _apply_event_filters(statement, filters)


def _event_count(db: Session, filters: PipelineEventFilters) -> int:
    statement = (
        select(func.count())
        .select_from(RawEvent)
        .outerjoin(CanonicalEvent, CanonicalEvent.raw_event_id == RawEvent.id)
        .outerjoin(
            MatchDecision,
            MatchDecision.canonical_event_id == CanonicalEvent.id,
        )
    )
    return int(db.scalar(_apply_event_filters(statement, filters)) or 0)


def _event_out(
    raw: RawEvent,
    canonical: CanonicalEvent | None,
    decision: MatchDecision | None,
) -> PipelineEventOut:
    needs_review = bool(
        decision
        and decision.outcome == IdentityOutcome.REVIEW_REQUIRED
        and decision.review_status == ReviewStatus.PENDING
    )
    presentation = (
        present_event(canonical.event_type, canonical.entity_references, canonical.attributes)
        if canonical
        else None
    )
    return PipelineEventOut(
        raw_event_id=str(raw.id),
        canonical_event_id=str(canonical.id) if canonical else None,
        source_event_id=raw.source_event_id,
        channel=raw.channel,
        event_type=canonical.event_type if canonical else None,
        event_summary=(
            PipelineEventSummary(
                title=presentation.title,
                detail=presentation.detail,
                kind=presentation.kind,
            )
            if presentation
            else None
        ),
        has_order_reference=presentation.has_order_reference if presentation else None,
        occurred_at=_to_utc(raw.occurred_at),
        received_at=_to_utc(raw.received_at),
        processed_at=_to_utc(canonical.created_at) if canonical else None,
        processing_status=raw.processing_status,
        processing_error_code=_error_code(raw.processing_error),
        profile_id=(
            str(canonical.profile_id)
            if canonical and canonical.profile_id is not None
            else None
        ),
        identity_outcome=decision.outcome if decision else None,
        identity_score=decision.score if decision else None,
        needs_review=needs_review,
    )


def _fetch_events(
    db: Session,
    filters: PipelineEventFilters,
    limit: int,
    cursor: PipelinePageCursor | None = None,
    high_water: PipelinePageCursor | None = None,
) -> tuple[list[PipelineEventOut], str | None]:
    statement = _event_statement(filters)
    if cursor is not None:
        statement = statement.where(_strictly_before(cursor))
    if high_water is not None:
        statement = statement.where(_at_or_before(high_water))
    rows = db.execute(
        statement.order_by(RawEvent.received_at.desc(), RawEvent.id.desc()).limit(limit + 1)
    ).all()
    has_more = len(rows) > limit
    visible_rows = rows[:limit]

    events: list[PipelineEventOut] = []
    for raw, canonical, decision in visible_rows:
        events.append(_event_out(raw, canonical, decision))
    next_cursor = (
        _encode_page_cursor(visible_rows[-1][0], filters) if has_more and visible_rows else None
    )
    return events, next_cursor


def list_pipeline_events(
    db: Session,
    filters: PipelineEventFilters,
    limit: int = 25,
    cursor: str | None = None,
) -> PipelineEventListResponse:
    """Return a filtered, list-safe page of persisted raw events."""
    page_cursor = _decode_page_cursor(cursor, filters) if cursor else None
    items, next_cursor = _fetch_events(db, filters, limit, cursor=page_cursor)
    return PipelineEventListResponse(
        items=items,
        total=_event_count(db, filters),
        next_cursor=next_cursor,
    )


def _raw_event_detail(raw: RawEvent) -> RawEventDetail:
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


def _canonical_event_detail(canonical: CanonicalEvent) -> CanonicalEventDetail:
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


def get_pipeline_event_detail(
    db: Session,
    raw_event_id: str,
) -> PipelineEventDetailResponse | None:
    """Return one raw event and all persisted pipeline records derived from it."""
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
    decision = (
        db.scalar(
            select(MatchDecision).where(MatchDecision.canonical_event_id == canonical.id)
        )
        if canonical
        else None
    )
    identity_decision = (
        PipelineIdentityDecisionOut(
            canonical_event_id=str(decision.canonical_event_id),
            selected_profile_id=str(decision.profile_id) if decision.profile_id else None,
            outcome=decision.outcome,
            score=decision.score,
            thresholds=decision.thresholds,
            evidence=decision.evidence,
            conflicts=decision.conflicts,
            candidates=decision.candidates,
            reason=decision.decision_reason,
            review_status=decision.review_status,
        )
        if decision
        else None
    )
    return PipelineEventDetailResponse(
        event=_event_out(raw, canonical, decision),
        raw_event=_raw_event_detail(raw),
        canonical_event=_canonical_event_detail(canonical) if canonical else None,
        identity_decision=identity_decision,
    )


def get_pipeline_updates(
    db: Session,
    cursor: str,
    limit: int = 100,
    upper_bound_cursor: str | None = None,
) -> PipelineUpdatesResponse:
    """Return events processed after a cursor, bounded by one high-water mark."""
    _prepare_snapshot(db)
    as_of = datetime.now(UTC)
    lower_bound = _decode_update_cursor(cursor)
    upper_bound = (
        _decode_update_cursor(upper_bound_cursor)
        if upper_bound_cursor
        else _capture_high_water(db)
    )
    if (lower_bound.received_at, str(lower_bound.raw_event_id)) > (
        upper_bound.received_at,
        str(upper_bound.raw_event_id),
    ):
        raise _invalid_cursor()

    rows = db.execute(
        _event_statement(PipelineEventFilters())
        .where(_strictly_after(lower_bound), _at_or_before(upper_bound))
        .order_by(RawEvent.received_at.asc(), RawEvent.id.asc())
        .limit(limit + 1)
    ).all()
    has_more = len(rows) > limit
    visible_rows = rows[:limit]
    events = [_event_out(raw, canonical, decision) for raw, canonical, decision in visible_rows]
    next_position = (
        PipelinePageCursor(
            received_at=_to_utc(visible_rows[-1][0].received_at),
            raw_event_id=visible_rows[-1][0].id,
        )
        if has_more and visible_rows
        else upper_bound
    )
    return PipelineUpdatesResponse(
        as_of=as_of,
        stages=_stage_counts(db, high_water=upper_bound),
        channels=_channel_counts(db, high_water=upper_bound),
        events=events,
        next_cursor=_encode_update_cursor(next_position),
        upper_bound_cursor=_encode_update_cursor(upper_bound),
        has_more=has_more,
    )


def get_pipeline_snapshot(db: Session, limit: int = 25) -> PipelineOverviewResponse:
    """Return the unfiltered pipeline snapshot used for initial page load."""
    _prepare_snapshot(db)
    as_of = datetime.now(UTC)
    high_water = _capture_high_water(db)
    events, next_cursor = _fetch_events(
        db,
        PipelineEventFilters(),
        limit,
        high_water=high_water,
    )
    return PipelineOverviewResponse(
        as_of=as_of,
        stages=_stage_counts(db, high_water=high_water),
        channels=_channel_counts(db, high_water=high_water),
        events=events,
        next_cursor=next_cursor,
        poll_cursor=_encode_update_cursor(high_water),
        duplicate_attempts=None,
        duplicate_tracking_supported=False,
    )
