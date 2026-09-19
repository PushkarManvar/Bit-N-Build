"""Pydantic request/response schemas for event ingestion.

Shapes are frozen in docs/05_API_CONTRACT.md.
"""

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field

from app.core.enums import Channel, EventType, IdentityOutcome, ProcessingStatus

IdentifierType = Literal["email", "phone", "device_id", "session_id", "customer_id"]

IngestionResponseStatus = Literal["normalized", "duplicate", "failed"]


class IdentifierRef(BaseModel):
    type: IdentifierType
    value: str


class EventIngestionRequest(BaseModel):
    source_event_id: str = Field(min_length=1, max_length=200)
    channel: Channel
    event_type: EventType
    occurred_at: datetime
    schema_version: str = Field(min_length=1, max_length=20)
    identifiers: list[IdentifierRef] = Field(default_factory=list)
    entity_references: dict[str, Any] = Field(default_factory=dict)
    attributes: dict[str, Any] = Field(default_factory=dict)


class EventIngestionResponse(BaseModel):
    raw_event_id: str
    canonical_event_id: str | None = None
    channel: Channel
    event_type: EventType | None = None
    occurred_at: datetime | None = None
    processing_status: IngestionResponseStatus
    duplicate: bool = False
    match_decision: IdentityOutcome | None = None
    profile_id: str | None = None
    match_score: int | None = None


class RawEventDetail(BaseModel):
    id: str
    channel: Channel
    source_event_id: str
    schema_version: str
    occurred_at: datetime
    received_at: datetime
    payload: dict[str, Any]
    processing_status: ProcessingStatus
    processing_error: str | None = None


class CanonicalEventDetail(BaseModel):
    id: str
    raw_event_id: str
    channel: Channel
    event_type: EventType
    occurred_at: datetime
    profile_id: str | None = None
    identifiers: list[dict[str, Any]]
    entity_references: dict[str, Any]
    attributes: dict[str, Any]
    created_at: datetime


class EventRetrievalResponse(BaseModel):
    raw_event: RawEventDetail
    canonical_event: CanonicalEventDetail | None = None