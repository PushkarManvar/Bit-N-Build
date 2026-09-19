"""Profile listing and journey-detail endpoints (Gate G2)."""

import uuid
from datetime import UTC
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.db.models import (
    CanonicalEvent,
    CustomerProfile,
    MatchDecision,
    ProfileIdentifier,
)
from app.db.session import get_db
from app.schemas.profiles import (
    ProfileJourneyResponse,
    ProfileListResponse,
    ProfileSummary,
    TimelineEventOut,
)

router = APIRouter()

DbSession = Annotated[Session, Depends(get_db)]


@router.get("/profiles", response_model=ProfileListResponse)
def list_profiles(
    db: DbSession,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    search: str | None = Query(None),
) -> ProfileListResponse:
    """List resolved profiles. Alerts counts arrive with Gate G4."""
    statement = select(CustomerProfile)
    if search:
        like = f"%{search.strip()}%"
        statement = statement.where(
            or_(
                CustomerProfile.display_name.ilike(like),
                CustomerProfile.id.in_(
                    select(ProfileIdentifier.profile_id).where(
                        ProfileIdentifier.value.ilike(like)
                    )
                ),
            )
        )

    total = db.scalar(select(func.count()).select_from(statement.subquery())) or 0
    profiles = db.scalars(
        statement.order_by(CustomerProfile.last_seen_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    ).all()

    items = [_profile_summary(db, p) for p in profiles]
    return ProfileListResponse(items=items, page=page, page_size=page_size, total=total)


@router.get("/profiles/{profile_id}", response_model=ProfileJourneyResponse)
def profile_journey(profile_id: str, db: DbSession) -> ProfileJourneyResponse:
    """Profile detail with chronological timeline (alerts land with Gate G4)."""
    try:
        profile_uuid = uuid.UUID(profile_id)
    except ValueError:
        raise HTTPException(status_code=404, detail="Profile not found") from None
    profile = db.get(CustomerProfile, profile_uuid)
    if profile is None:
        raise HTTPException(status_code=404, detail="Profile not found")

    identifiers = db.scalars(
        select(ProfileIdentifier)
        .where(ProfileIdentifier.profile_id == profile_uuid)
        .order_by(ProfileIdentifier.first_seen_at)
    ).all()

    timeline_rows = db.execute(
        select(CanonicalEvent, MatchDecision)
        .join(MatchDecision, MatchDecision.canonical_event_id == CanonicalEvent.id)
        .where(CanonicalEvent.profile_id == profile_uuid)
        .order_by(CanonicalEvent.occurred_at)
    ).all()

    timeline = [_timeline_event(canonical, decision) for canonical, decision in timeline_rows]

    return ProfileJourneyResponse(
        profile={
            "id": str(profile.id),
            "display_name": profile.display_name,
            "identifiers": [
                {
                    "type": id_row.type,
                    "display_value": id_row.value,
                    "first_seen_at": _to_utc(id_row.first_seen_at),
                }
                for id_row in identifiers
            ],
        },
        timeline=timeline,
        alerts=[],
        journey_summary=None,
    )


def _profile_summary(db: Session, profile: CustomerProfile) -> ProfileSummary:
    identifiers = db.scalars(
        select(ProfileIdentifier).where(ProfileIdentifier.profile_id == profile.id)
    ).all()
    by_type: dict[str, list[str]] = {}
    for row in identifiers:
        by_type.setdefault(row.type, []).append(row.value)

    channels = db.scalars(
        select(CanonicalEvent.channel)
        .where(CanonicalEvent.profile_id == profile.id)
        .distinct()
    ).all()
    event_count = db.scalar(
        select(func.count())
        .select_from(CanonicalEvent)
        .where(CanonicalEvent.profile_id == profile.id)
    ) or 0

    return ProfileSummary(
        profile_id=str(profile.id),
        display_name=profile.display_name,
        email=by_type.get("email", [None])[0],
        phone=by_type.get("phone", [None])[0],
        channels_used=sorted(channels, key=lambda c: c.value),
        event_count=event_count,
        open_alert_count=0,
        review_required=False,
        last_seen_at=_to_utc(profile.last_seen_at),
    )


def _timeline_event(
    canonical: CanonicalEvent, decision: MatchDecision
) -> TimelineEventOut:
    order_id = canonical.entity_references.get("order_id")
    return TimelineEventOut(
        event_id=str(canonical.id),
        channel=canonical.channel,
        event_type=canonical.event_type,
        occurred_at=_to_utc(canonical.occurred_at),
        order_id=str(order_id) if order_id else None,
        decision=decision.outcome,
        score=decision.score,
        evidence_summary=[item.get("message", "") for item in decision.evidence],
    )


def _to_utc(value):
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)