"""Pydantic schemas for the review queue (docs/05_API_CONTRACT.md section 8)."""

from datetime import datetime

from pydantic import BaseModel, Field

from app.core.enums import (
    Channel,
    EventType,
    ReviewDecision,
    ReviewQueueKind,
    ReviewQueuePriority,
)


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


class ReviewQueueCandidateOut(BaseModel):
    profile_id: str
    display_name: str | None = None
    score: int
    matched_fields: list[str]


class ReviewQueueEvidenceOut(BaseModel):
    field: str
    result: str
    weight: int
    message: str


class ReviewQueueConflictOut(BaseModel):
    fields: list[str]
    message: str


class ReviewQueueItem(BaseModel):
    match_decision_id: str
    created_at: datetime
    review_kind: ReviewQueueKind
    priority: ReviewQueuePriority
    event: ReviewEventOut
    candidates: list[ReviewQueueCandidateOut]
    evidence: list[ReviewQueueEvidenceOut]
    conflicts: list[ReviewQueueConflictOut]
    missing_strong_identifiers: list[str]
    reason_code: str
    reason: str


class ReviewQueueSummary(BaseModel):
    pending: int
    critical_conflicts: int
    incomplete_evidence: int
    same_name_collisions: int
    ambiguous_moderate_matches: int


class ReviewQueueListResponse(BaseModel):
    items: list[ReviewQueueItem]
    total: int
    next_cursor: str | None = None
    summary: ReviewQueueSummary


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
