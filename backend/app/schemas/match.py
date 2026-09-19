"""Pydantic schema for match explanations (docs/05_API_CONTRACT.md section 7)."""

from typing import Any

from pydantic import BaseModel

from app.core.enums import Channel, EventType, IdentityOutcome


class EventContext(BaseModel):
    channel: Channel
    event_type: EventType
    occurred_at: Any


class MatchExplanationResponse(BaseModel):
    event_id: str
    event_context: EventContext
    decision: IdentityOutcome
    selected_profile_id: str | None = None
    score: int
    thresholds: dict[str, int]
    evidence: list[dict]
    conflicts: list[dict]
    alternative_candidates: list[dict]
    raw_payload: dict[str, Any]
    normalized_fields: dict[str, Any]