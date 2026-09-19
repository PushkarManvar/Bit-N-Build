"""Read model for the inspectable synchronous data pipeline."""

from datetime import UTC, datetime

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.enums import Channel, IdentityOutcome, ProcessingStatus, ReviewStatus
from app.db.models import CanonicalEvent, MatchDecision, RawEvent
from app.schemas.pipeline import (
    PipelineChannelCounts,
    PipelineChannels,
    PipelineEventOut,
    PipelineOverviewResponse,
    PipelineStageCounts,
)


def _to_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


def _count(db: Session, model) -> int:
    return int(db.scalar(select(func.count()).select_from(model)) or 0)


def _channel_counts(db: Session) -> PipelineChannels:
    counts = {
        channel: {"raw": 0, "normalized": 0, "failed": 0}
        for channel in Channel
    }

    for channel, count in db.execute(
        select(RawEvent.channel, func.count()).group_by(RawEvent.channel)
    ).all():
        counts[channel]["raw"] = int(count)

    for channel, count in db.execute(
        select(CanonicalEvent.channel, func.count()).group_by(CanonicalEvent.channel)
    ).all():
        counts[channel]["normalized"] = int(count)

    for channel, count in db.execute(
        select(RawEvent.channel, func.count())
        .where(RawEvent.processing_status == ProcessingStatus.FAILED)
        .group_by(RawEvent.channel)
    ).all():
        counts[channel]["failed"] = int(count)

    return PipelineChannels(
        web=PipelineChannelCounts(**counts[Channel.WEB]),
        mobile_app=PipelineChannelCounts(**counts[Channel.MOBILE_APP]),
        call_center=PipelineChannelCounts(**counts[Channel.CALL_CENTER]),
        physical_store=PipelineChannelCounts(**counts[Channel.PHYSICAL_STORE]),
    )


def _stage_counts(db: Session) -> PipelineStageCounts:
    failed = int(
        db.scalar(
            select(func.count())
            .select_from(RawEvent)
            .where(RawEvent.processing_status == ProcessingStatus.FAILED)
        )
        or 0
    )
    linked = int(
        db.scalar(
            select(func.count())
            .select_from(CanonicalEvent)
            .where(CanonicalEvent.profile_id.is_not(None))
        )
        or 0
    )
    review = int(
        db.scalar(
            select(func.count())
            .select_from(MatchDecision)
            .where(
                MatchDecision.outcome == IdentityOutcome.REVIEW_REQUIRED,
                MatchDecision.review_status == ReviewStatus.PENDING,
            )
        )
        or 0
    )
    return PipelineStageCounts(
        raw_accepted=_count(db, RawEvent),
        normalization_succeeded=_count(db, CanonicalEvent),
        normalization_failed=failed,
        identity_decided=_count(db, MatchDecision),
        profile_linked=linked,
        review_required=review,
    )


def _error_code(processing_error: str | None) -> str | None:
    if not processing_error:
        return None
    code, _, _ = processing_error.partition(":")
    return code.strip() or None


def _recent_events(db: Session, limit: int) -> list[PipelineEventOut]:
    statement = (
        select(RawEvent, CanonicalEvent, MatchDecision)
        .outerjoin(CanonicalEvent, CanonicalEvent.raw_event_id == RawEvent.id)
        .outerjoin(
            MatchDecision,
            MatchDecision.canonical_event_id == CanonicalEvent.id,
        )
        .order_by(RawEvent.received_at.desc(), RawEvent.id.desc())
        .limit(limit)
    )

    events: list[PipelineEventOut] = []
    for raw, canonical, decision in db.execute(statement).all():
        needs_review = bool(
            decision
            and decision.outcome == IdentityOutcome.REVIEW_REQUIRED
            and decision.review_status == ReviewStatus.PENDING
        )
        events.append(
            PipelineEventOut(
                raw_event_id=str(raw.id),
                canonical_event_id=str(canonical.id) if canonical else None,
                source_event_id=raw.source_event_id,
                channel=raw.channel,
                event_type=canonical.event_type if canonical else None,
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
        )
    return events


def get_pipeline_snapshot(db: Session, limit: int = 25) -> PipelineOverviewResponse:
    """Return the unfiltered pipeline snapshot used for initial page load."""
    as_of = datetime.now(UTC)
    return PipelineOverviewResponse(
        as_of=as_of,
        stages=_stage_counts(db),
        channels=_channel_counts(db),
        events=_recent_events(db, limit),
        next_cursor=None,
        poll_cursor=None,
        duplicate_attempts=None,
        duplicate_tracking_supported=False,
    )
