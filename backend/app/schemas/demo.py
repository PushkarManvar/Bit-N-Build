"""Pydantic schemas for demo controls and dashboard polling."""

from datetime import datetime

from pydantic import BaseModel, Field

from app.core.enums import Channel, EventType, IdentityOutcome
from app.schemas.profiles import AlertOut


class DemoStartRequest(BaseModel):
    scenario: str = Field(min_length=1)
    interval_seconds: float = Field(default=1.5, gt=0)


class DemoStartResponse(BaseModel):
    run_id: str
    status: str
    total_steps: int
    current_step: int


class DemoRunResponse(BaseModel):
    run_id: str
    status: str
    current_step: int
    total_steps: int
    last_event_id: str | None = None
    error: str | None = None


class DemoResetResponse(BaseModel):
    status: str
    loaded: dict[str, int]


class DashboardEventOut(BaseModel):
    event_id: str
    channel: Channel
    event_type: EventType
    occurred_at: datetime
    profile_id: str | None = None
    match_decision: IdentityOutcome | None = None


class DashboardUpdatesResponse(BaseModel):
    events: list[DashboardEventOut]
    new_alerts: list[AlertOut]
    open_alerts: int
    pending_reviews: int
    demo: DemoRunResponse | None = None