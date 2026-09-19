"""Computed analytics (docs/05_API_CONTRACT.md section 9).

Match metrics come from the latest persisted evaluation run (written only by
the evaluation script). Counts are computed live from the database. Metrics
that have never been computed return null, never invented defaults.
"""

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.enums import IdentityOutcome, ProcessingStatus
from app.db.models import (
    CanonicalEvent,
    CustomerProfile,
    EvaluationRun,
    JourneyAlert,
    MatchDecision,
    RawEvent,
)
from app.schemas.analytics import AnalyticsOverview, ChannelsResponse


def compute_overview(db: Session) -> AnalyticsOverview:
    total_raw = int(db.scalar(select(func.count()).select_from(RawEvent)) or 0)
    normalized = int(db.scalar(select(func.count()).select_from(CanonicalEvent)) or 0)
    failed = int(
        db.scalar(
            select(func.count())
            .select_from(RawEvent)
            .where(RawEvent.processing_status == ProcessingStatus.FAILED)
        )
        or 0
    )
    profiles = int(db.scalar(select(func.count()).select_from(CustomerProfile)) or 0)
    open_alerts = int(
        db.scalar(
            select(func.count())
            .select_from(JourneyAlert)
            .where(JourneyAlert.status == "open")
        )
        or 0
    )

    decisions_total = int(db.scalar(select(func.count()).select_from(MatchDecision)) or 0)
    auto = int(
        db.scalar(
            select(func.count())
            .select_from(MatchDecision)
            .where(MatchDecision.outcome == IdentityOutcome.AUTO_LINKED)
        )
        or 0
    )
    review = int(
        db.scalar(
            select(func.count())
            .select_from(MatchDecision)
            .where(MatchDecision.outcome == IdentityOutcome.REVIEW_REQUIRED)
        )
        or 0
    )
    auto_rate = round(auto / decisions_total * 100, 1) if decisions_total else None
    review_rate = round(review / decisions_total * 100, 1) if decisions_total else None

    latest = db.scalar(select(EvaluationRun).order_by(EvaluationRun.created_at.desc()))
    metrics = latest.metrics if latest else {}

    return AnalyticsOverview(
        total_raw_events=total_raw,
        normalized_events=normalized,
        failed_events=failed,
        duplicate_events=None,
        unified_profiles=profiles,
        auto_link_rate=auto_rate,
        review_required_rate=review_rate,
        open_alerts=open_alerts,
        match_precision=metrics.get("match_precision"),
        match_recall=metrics.get("match_recall"),
        match_f1=metrics.get("match_f1"),
        false_merge_rate=metrics.get("false_merge_rate"),
        average_processing_latency_ms=None,
    )


def compute_channels(db: Session) -> ChannelsResponse:
    rows = db.execute(
        select(CanonicalEvent.channel, func.count())
        .group_by(CanonicalEvent.channel)
    ).all()
    counts = {channel.value: count for channel, count in rows}
    return ChannelsResponse(
        web=counts.get("web", 0),
        mobile_app=counts.get("mobile_app", 0),
        call_center=counts.get("call_center", 0),
        physical_store=counts.get("physical_store", 0),
    )