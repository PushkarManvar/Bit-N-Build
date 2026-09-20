"""Review queue and resolution endpoints (Gate G5)."""

import uuid
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.enums import Channel, ReviewQueueKind, ReviewQueuePriority
from app.db.models import CanonicalEvent, CustomerProfile, MatchDecision
from app.db.session import get_db
from app.schemas.reviews import (
    BestCandidateOut,
    ResolveReviewRequest,
    ResolveReviewResponse,
    ReviewEventOut,
    ReviewItem,
    ReviewListResponse,
    ReviewQueueListResponse,
)
from app.services.review_queue_read_model import ReviewQueueFilters, list_review_queue
from app.services.review_service import list_pending_reviews, resolve_review

router = APIRouter()

DbSession = Annotated[Session, Depends(get_db)]

STRONG_IDENTIFIER_TYPES: frozenset[str] = frozenset({"email", "phone", "customer_id", "order_id"})


@router.get("/reviews", response_model=ReviewListResponse)
def list_reviews(db: DbSession) -> ReviewListResponse:
    """Pending review decisions with candidate context."""
    decisions = list_pending_reviews(db)
    items = [_review_item(db, decision) for decision in decisions]
    return ReviewListResponse(items=items, total=len(items))


@router.get("/review-queue", response_model=ReviewQueueListResponse)
def review_queue(
    db: DbSession,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    cursor: Annotated[str | None, Query(min_length=1, max_length=1000)] = None,
    status: Literal["pending"] = "pending",
    channel: Channel | None = None,
    kind: ReviewQueueKind | None = None,
    priority: ReviewQueuePriority | None = None,
) -> ReviewQueueListResponse:
    """Return a server-classified, operator-safe page of pending reviews."""
    return list_review_queue(
        db,
        ReviewQueueFilters(
            status=status,
            channel=channel,
            kind=kind,
            priority=priority,
        ),
        limit=limit,
        cursor=cursor,
    )


@router.post("/reviews/{match_decision_id}/resolve", response_model=ResolveReviewResponse)
def resolve_review_endpoint(
    match_decision_id: str,
    request: ResolveReviewRequest,
    db: DbSession,
) -> ResolveReviewResponse:
    """Resolve a pending review: approve link, reject, or create a profile."""
    result = resolve_review(
        db,
        match_decision_id,
        request.action,
        selected_profile_id=request.selected_profile_id,
        reviewer_name=request.reviewer_name,
        note=request.note,
    )
    return ResolveReviewResponse(
        match_decision_id=result.match_decision_id,
        review_status=result.review_status,
        action=result.action,
        profile_id=result.profile_id,
        resolved_at=result.resolved_at,
    )


def _review_item(db: Session, decision: MatchDecision) -> ReviewItem:
    event = _review_event(db, decision)

    candidates = sorted(decision.candidates, key=lambda c: c.get("score", 0), reverse=True)
    best = candidates[0] if candidates else None
    best_candidate = None
    if best is not None:
        try:
            candidate_uuid = uuid.UUID(best.get("profile_id"))
        except (TypeError, ValueError):
            candidate_uuid = None
        profile = db.get(CustomerProfile, candidate_uuid) if candidate_uuid else None
        best_candidate = BestCandidateOut(
            profile_id=best.get("profile_id"),
            display_name=profile.display_name if profile else None,
            score=best.get("score", 0),
        )

    present = _present_identifiers(db, decision)
    missing = [strong for strong in STRONG_IDENTIFIER_TYPES if strong not in present]

    return ReviewItem(
        match_decision_id=str(decision.id),
        event=event,
        best_candidate=best_candidate,
        evidence=[item.get("message", item.get("field", "")) for item in decision.evidence],
        conflicts=decision.conflicts,
        missing_strong_identifiers=missing,
        reason=decision.decision_reason or "",
    )


def _review_event(db: Session, decision: MatchDecision) -> ReviewEventOut:
    canonical = db.scalar(
        select(CanonicalEvent).where(CanonicalEvent.id == decision.canonical_event_id)
    )
    attributes = canonical.attributes if canonical else {}
    return ReviewEventOut(
        channel=canonical.channel if canonical else None,
        event_type=canonical.event_type if canonical else None,
        customer_name=attributes.get("customer_name"),
        occurred_at=canonical.occurred_at if canonical else None,
    )


def _present_identifiers(db: Session, decision: MatchDecision) -> set[str]:
    canonical = db.scalar(
        select(CanonicalEvent).where(CanonicalEvent.id == decision.canonical_event_id)
    )
    if canonical is None:
        return set()
    present = {item["type"] for item in canonical.identifiers}
    order_id = canonical.entity_references.get("order_id")
    if order_id:
        present.add("order_id")
    return present
