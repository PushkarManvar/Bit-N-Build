"""Pydantic schemas for the review queue (docs/05_API_CONTRACT.md section 8)."""

from datetime import datetime

from pydantic import BaseModel, Field

from app.core.enums import Channel, EventType, ReviewDecision


class ReviewEventOut(BaseModel):
    channel: Channel | None = None
    event_type: EventType | None = None
    customer_name: str | None = None
    occurred_at: datetime | None = None


class BestCandidateOut(BaseModel):
    profile_id: str
    display_name: str | None = None
    score: int


class ReviewItem(BaseModel):
    match_decision_id: str
    event: ReviewEventOut
    best_candidate: BestCandidateOut | None = None
    evidence: list[str]
    conflicts: list[dict]
    missing_strong_identifiers: list[str]
    reason: str


class ReviewListResponse(BaseModel):
    items: list[ReviewItem]
    total: int


class ResolveReviewRequest(BaseModel):
    action: ReviewDecision
    selected_profile_id: str | None = None
    reviewer_name: str = Field(min_length=1, max_length=200)
    note: str | None = Field(default=None, max_length=500)


class ResolveReviewResponse(BaseModel):
    match_decision_id: str
    review_status: str
    action: ReviewDecision
    profile_id: str | None = None
    resolved_at: datetime