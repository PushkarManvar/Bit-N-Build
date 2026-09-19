"""Data Pipeline read-model schemas (docs/05_API_CONTRACT.md section 10)."""

from datetime import datetime

from pydantic import BaseModel

from app.core.enums import Channel, EventType, IdentityOutcome, ProcessingStatus


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


class PipelineOverviewResponse(BaseModel):
    as_of: datetime
    stages: PipelineStageCounts
    channels: PipelineChannels
    events: list[PipelineEventOut]
    next_cursor: str | None = None
    poll_cursor: str | None = None
    duplicate_attempts: int | None = None
    duplicate_tracking_supported: bool = False
