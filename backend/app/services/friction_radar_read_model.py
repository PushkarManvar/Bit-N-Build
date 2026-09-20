"""Deterministic read model for the Journey Friction Radar.

The radar ranks persisted, attributable open unresolved-refund alerts. It does
not predict churn, infer payment status, or make identity decisions. See
``docs/18_JOURNEY_FRICTION_RADAR_PLAN.md`` for the score contract.
"""

from collections import Counter
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.enums import AlertStatus, AlertType, EventType, ReviewStatus
from app.db.models import CanonicalEvent, CustomerProfile, JourneyAlert, MatchDecision
from app.schemas.analytics import (
    FrictionAgeDistributionBucket,
    FrictionJourney,
    FrictionRadarResponse,
    FrictionRadarSummary,
    FrictionScoreComponents,
    FrictionSupportContactChannel,
)

SCORE_VERSION = "friction_v1"
SCORE_MAX = 60
AGE_BUCKETS: tuple[tuple[str, int | None, int | None], ...] = (
    ("0 days", 0, 0),
    ("1–3 days", 1, 3),
    ("4–7 days", 4, 7),
    ("8+ days", 8, None),
)


def _utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


def _order_id(event: CanonicalEvent) -> str | None:
    value = event.entity_references.get("order_id")
    return str(value) if value else None


def _candidate_references_profile(candidates: list[dict[str, Any]], profile_id: str) -> bool:
    return any(str(candidate.get("profile_id")) == profile_id for candidate in candidates)


def _band(score: int) -> str:
    if score >= 45:
        return "critical"
    if score >= 30:
        return "elevated"
    if score >= 1:
        return "watch"
    return "none"


def _age_bucket(age_days: int) -> str:
    for label, minimum, maximum in AGE_BUCKETS:
        if age_days >= minimum and (maximum is None or age_days <= maximum):
            return label
    raise ValueError("Unreachable age bucket")


def compute_friction_radar(db: Session, *, limit: int) -> FrictionRadarResponse:
    """Return a deterministic ranking of persisted open refund-friction evidence."""
    as_of = datetime.now(UTC)
    open_alerts = list(
        db.scalars(
            select(JourneyAlert).where(JourneyAlert.status == AlertStatus.OPEN)
        ).all()
    )
    unresolved_alerts = [
        alert for alert in open_alerts if alert.type == AlertType.UNRESOLVED_REFUND
    ]
    attributable_alerts = [
        alert
        for alert in unresolved_alerts
        if alert.profile_id is not None and alert.order_id is not None
    ]
    unattributed_count = len(unresolved_alerts) - len(attributable_alerts)

    profile_ids = {alert.profile_id for alert in attributable_alerts if alert.profile_id}
    profiles = {
        str(profile.id): profile
        for profile in db.scalars(
            select(CustomerProfile).where(CustomerProfile.id.in_(profile_ids))
        ).all()
    } if profile_ids else {}
    events = list(db.scalars(select(CanonicalEvent)).all())
    pending_decisions = list(
        db.execute(
            select(MatchDecision, CanonicalEvent)
            .join(CanonicalEvent, CanonicalEvent.id == MatchDecision.canonical_event_id)
            .where(MatchDecision.review_status == ReviewStatus.PENDING)
        ).all()
    )
    repeat_contact_pairs = {
        (str(alert.profile_id), alert.order_id)
        for alert in open_alerts
        if (
            alert.type == AlertType.REPEAT_CONTACT
            and alert.profile_id is not None
            and alert.order_id is not None
        )
    }

    all_journeys: list[FrictionJourney] = []
    age_distribution = Counter[str]()
    support_channels = Counter[str]()
    total_support_contacts = 0

    for alert in attributable_alerts:
        assert alert.profile_id is not None
        assert alert.order_id is not None
        profile_id = str(alert.profile_id)
        order_id = alert.order_id
        journey_events = [
            event
            for event in events
            if str(event.profile_id) == profile_id and _order_id(event) == order_id
        ]
        returns = [
            event for event in journey_events if event.event_type == EventType.RETURN_REQUESTED
        ]
        earliest_return = min((_utc(event.occurred_at) for event in returns), default=None)
        age_days = max(0, (as_of - earliest_return).days) if earliest_return else 0
        support_events = [
            event for event in journey_events if event.event_type == EventType.SUPPORT_CONTACTED
        ]
        channel_count = len({event.channel.value for event in support_events})
        support_count = len(support_events)
        candidate_review_count = sum(
            1
            for decision, event in pending_decisions
            if (
                _order_id(event) == order_id
                and _candidate_references_profile(decision.candidates, profile_id)
            )
        )
        has_repeat_contact = (profile_id, order_id) in repeat_contact_pairs
        components = FrictionScoreComponents(
            unresolved_age_points=min(30, 4 * age_days),
            channel_points=min(12, 3 * channel_count),
            support_contact_points=min(12, 4 * support_count),
            repeat_contact_points=10 if has_repeat_contact else 0,
            pending_candidate_review_points=min(6, 6 * candidate_review_count),
        )
        score = sum(components.model_dump().values())
        profile = profiles.get(profile_id)
        all_journeys.append(
            FrictionJourney(
                alert_id=str(alert.id),
                profile_id=profile_id,
                display_name=profile.display_name if profile else None,
                order_id=order_id,
                friction_score=score,
                band=_band(score),
                unresolved_age_days=age_days,
                distinct_channel_count=channel_count,
                support_contact_count=support_count,
                has_open_repeat_contact_alert=has_repeat_contact,
                pending_candidate_review_count=candidate_review_count,
                components=components,
            )
        )
        age_distribution[_age_bucket(age_days)] += 1
        support_channels.update(event.channel.value for event in support_events)
        total_support_contacts += support_count

    all_journeys.sort(
        key=lambda journey: (
            -journey.friction_score,
            -journey.unresolved_age_days,
            journey.alert_id,
        )
    )
    summary = FrictionRadarSummary(
        attributable_open_refunds=len(all_journeys),
        unattributed_open_refunds=unattributed_count,
        critical=sum(journey.band == "critical" for journey in all_journeys),
        elevated=sum(journey.band == "elevated" for journey in all_journeys),
        watch=sum(journey.band == "watch" for journey in all_journeys),
    )
    distribution = [
        FrictionAgeDistributionBucket(bucket=label, count=age_distribution[label])
        for label, _, _ in AGE_BUCKETS
    ]
    channel_rows = [
        FrictionSupportContactChannel(
            channel=channel,
            count=count,
            share_percent=round((count / total_support_contacts) * 100, 1)
            if total_support_contacts
            else None,
        )
        for channel, count in sorted(support_channels.items())
    ]
    return FrictionRadarResponse(
        as_of=as_of,
        score_version=SCORE_VERSION,
        score_max=SCORE_MAX,
        summary=summary,
        journeys=all_journeys[:limit],
        unresolved_age_distribution=distribution,
        support_contact_channels=channel_rows,
    )
