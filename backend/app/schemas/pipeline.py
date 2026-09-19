"""Data Pipeline read-model schemas (docs/05_API_CONTRACT.md section 10)."""

from datetime import datetime
from typing import Any

from pydantic import BaseModel

from app.core.enums import Channel, EventType, IdentityOutcome, ProcessingStatus, ReviewStatus
from app.schemas.events import CanonicalEventDetail, RawEventDetail


class PipelineStageCounts(BaseModel):
    raw_accepted: int
    normalization_succeeded: int
    normalization_failed: int
    identity_decided: int
    profile_linked: int
    review_required: int


class PipelineChannelCounts(BaseModel):
    raw: int
    normalized: int
    failed: int


class PipelineChannels(BaseModel):
    web: PipelineChannelCounts
    mobile_app: PipelineChannelCounts
    call_center: PipelineChannelCounts
    physical_store: PipelineChannelCounts


class PipelineEventOut(BaseModel):
    raw_event_id: str
    canonical_event_id: str | None = None
    source_event_id: str
    channel: Channel
    event_type: EventType | None = None
    occurred_at: datetime
    received_at: datetime
    processed_at: datetime | None = None
    processing_status: ProcessingStatus
    processing_error_code: str | None = None
    profile_id: str | None = None
    identity_outcome: IdentityOutcome | None = None
    identity_score: int | None = None
    needs_review: bool


class PipelineEventListResponse(BaseModel):
    items: list[PipelineEventOut]
    total: int
    next_cursor: str | None = None


class PipelineIdentityDecisionOut(BaseModel):
    canonical_event_id: str
    selected_profile_id: str | None = None
    outcome: IdentityOutcome
    score: int
    thresholds: dict[str, int]
    evidence: list[dict[str, Any]]
    conflicts: list[dict[str, Any]]
    candidates: list[dict[str, Any]]
    reason: str | None = None
    review_status: ReviewStatus | None = None


class PipelineEventDetailResponse(BaseModel):
    event: PipelineEventOut
    raw_event: RawEventDetail
    canonical_event: CanonicalEventDetail | None = None
    identity_decision: PipelineIdentityDecisionOut | None = None


class PipelineUpdatesResponse(BaseModel):
    as_of: datetime
    stages: PipelineStageCounts
    channels: PipelineChannels
    events: list[PipelineEventOut]
    next_cursor: str
    upper_bound_cursor: str
    has_more: bool


class PipelineOverviewResponse(BaseModel):
    as_of: datetime
    stages: PipelineStageCounts
    channels: PipelineChannels
    events: list[PipelineEventOut]
    next_cursor: str | None = None
    poll_cursor: str | None = None
    duplicate_attempts: int | None = None
    duplicate_tracking_supported: bool = False
