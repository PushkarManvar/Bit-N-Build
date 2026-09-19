"""Human review queue and resolution (Gate G5).

Resolution updates the canonical link, records an append-only audit action,
and reruns journey rules for the affected profile.
"""

import uuid
from dataclasses import dataclass
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.enums import IdentityOutcome, ReviewDecision, ReviewStatus
from app.core.errors import AppError
from app.db.models import (
    CanonicalEvent,
    CustomerProfile,
    MatchDecision,
    ReviewAction,
)
from app.services.journey_analyzer import analyze_profile
from app.services.profile_service import (
    attach_event_to_profile,
    create_profile_for_event,
)


class ReviewError(AppError):
    def __init__(
        self,
        *,
        code: str,
        message: str,
        http_status: int,
        details: dict | None = None,
    ) -> None:
        super().__init__(
            code=code,
            message=message,
            stage="review",
            raw_event_id=None,
            details=details or {},
            http_status=http_status,
        )


@dataclass(frozen=True)
class ReviewResolution:
    match_decision_id: str
    review_status: str
    action: ReviewDecision
    profile_id: str
    resolved_at: datetime


def list_pending_reviews(db: Session) -> list[MatchDecision]:
    return list(
        db.scalars(
            select(MatchDecision)
            .where(
                MatchDecision.outcome == IdentityOutcome.REVIEW_REQUIRED,
                MatchDecision.review_status == ReviewStatus.PENDING,
            )
            .order_by(MatchDecision.created_at)
        ).all()
    )


def _get_decision(db: Session, decision_id: str) -> MatchDecision:
    try:
        decision_uuid = uuid.UUID(decision_id)
    except ValueError:
        raise ReviewError(
            code="REVIEW_NOT_FOUND", message="Match decision not found.", http_status=404
        ) from None
    decision = db.get(MatchDecision, decision_uuid)
    if decision is None:
        raise ReviewError(
            code="REVIEW_NOT_FOUND", message="Match decision not found.", http_status=404
        )
    return decision


def _get_canonical(db: Session, decision: MatchDecision) -> CanonicalEvent:
    canonical = db.get(CanonicalEvent, decision.canonical_event_id)
    if canonical is None:
        raise ReviewError(
            code="REVIEW_INVALID",
            message="Canonical event for this decision is missing.",
            http_status=409,
        )
    return canonical


def _get_profile(db: Session, profile_id: str) -> CustomerProfile:
    try:
        profile_uuid = uuid.UUID(profile_id)
    except ValueError:
        raise ReviewError(
            code="VALIDATION_ERROR",
            message="selected_profile_id is not a valid profile.",
            http_status=422,
        ) from None
    profile = db.get(CustomerProfile, profile_uuid)
    if profile is None:
        raise ReviewError(
            code="VALIDATION_ERROR",
            message="selected_profile_id does not exist.",
            http_status=422,
        )
    return profile


def resolve_review(
    db: Session,
    decision_id: str,
    action: ReviewDecision,
    *,
    selected_profile_id: str | None,
    reviewer_name: str,
    note: str | None,
) -> ReviewResolution:
    decision = _get_decision(db, decision_id)
    if (
        decision.outcome != IdentityOutcome.REVIEW_REQUIRED
        or decision.review_status != ReviewStatus.PENDING
    ):
        raise ReviewError(
            code="REVIEW_ALREADY_RESOLVED",
            message="Match decision is not pending review.",
            http_status=409,
        )
    canonical = _get_canonical(db, decision)

    if action == ReviewDecision.APPROVE_LINK:
        if not selected_profile_id:
            raise ReviewError(
                code="VALIDATION_ERROR",
                message="approve_link requires selected_profile_id.",
                http_status=422,
            )
        profile = _get_profile(db, selected_profile_id)
        attach_event_to_profile(db, canonical, canonical, profile)
        decision.review_status = ReviewStatus.APPROVED
    elif action == ReviewDecision.REJECT_LINK:
        profile = create_profile_for_event(db, canonical, canonical)
        decision.review_status = ReviewStatus.REJECTED
    elif action == ReviewDecision.CREATE_PROFILE:
        profile = create_profile_for_event(db, canonical, canonical)
        decision.review_status = ReviewStatus.PROFILE_CREATED
    else:
        raise ReviewError(
            code="VALIDATION_ERROR",
            message=f"Unsupported review action: {action.value}.",
            http_status=422,
        )

    decision.profile_id = profile.id
    selected_uuid = uuid.UUID(selected_profile_id) if selected_profile_id else None
    db.add(
        ReviewAction(
            match_decision_id=decision.id,
            action=action,
            selected_profile_id=selected_uuid,
            reviewer_name=reviewer_name,
            note=note,
        )
    )
    # The session is created with autoflush=False, so flush the link before
    # the analyzer queries the profile's events.
    db.flush()
    analyze_profile(db, profile.id)
    db.commit()

    return ReviewResolution(
        match_decision_id=str(decision.id),
        review_status=decision.review_status.value,
        action=action,
        profile_id=str(profile.id),
        resolved_at=datetime.now(UTC),
    )