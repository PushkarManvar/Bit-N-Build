"""Pydantic schemas for profile and journey views (docs/05_API_CONTRACT.md)."""

from datetime import datetime

from pydantic import BaseModel

from app.core.enums import (
    AlertSeverity,
    AlertStatus,
    AlertType,
    Channel,
    EventType,
    IdentityOutcome,
)


class AlertOut(BaseModel):
    id: str
    type: AlertType
    severity: AlertSeverity
    title: str
    description: str
    recommended_action: str
    status: AlertStatus
    order_id: str | None = None
    created_at: datetime


class ProfileIdentifierOut(BaseModel):
    type: str
    display_value: str
    first_seen_at: datetime


class ProfileSummary(BaseModel):
    profile_id: str
    display_name: str | None = None
    email: str | None = None
    phone: str | None = None
    channels_used: list[Channel]
    event_count: int
    open_alert_count: int = 0
    review_required: bool
    last_seen_at: datetime


class ProfileListResponse(BaseModel):
    items: list[ProfileSummary]
    page: int
    page_size: int
    total: int


class TimelineEventOut(BaseModel):
    event_id: str
    channel: Channel
    event_type: EventType
    occurred_at: datetime
    order_id: str | None = None
    decision: IdentityOutcome
    score: int
    evidence_summary: list[str]


class ProfileJourneyResponse(BaseModel):
    profile: dict
    timeline: list[TimelineEventOut]
    alerts: list[AlertOut] = []
    journey_summary: dict | None = None


class AlertListResponse(BaseModel):
    items: list[AlertOut]
    total: int