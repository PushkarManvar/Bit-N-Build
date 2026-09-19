from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field

Channel = Literal["web", "mobile_app", "call_centre", "physical_store"]
ProcessingStatus = Literal["received", "normalized", "matched", "failed", "duplicate"]


class EventIngestionRequest(BaseModel):
    source: Channel
    source_record_id: str = Field(min_length=1, max_length=200)
    occurred_at: datetime
    payload: dict[str, Any]


class CanonicalEvent(BaseModel):
    channel: Channel
    event_type: str
    occurred_at: datetime
    email: str | None = None
    phone: str | None = None
    device_id: str | None = None
    session_id: str | None = None
    customer_id: str | None = None
    order_id: str | None = None
    issue_id: str | None = None
    customer_name: str | None = None
    city: str | None = None
    attributes: dict[str, Any] = Field(default_factory=dict)


class EventIngestionResponse(BaseModel):
    source_record_id: str
    status: ProcessingStatus
    canonical_event: CanonicalEvent
    message: str
