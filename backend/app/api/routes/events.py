"""Event ingestion and retrieval endpoints.

HTTP concerns only; processing lives in app.services.event_ingestion.
"""

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import CanonicalEvent, MatchDecision, RawEvent
from app.db.session import get_db
from app.schemas.events import (
    EventIngestionRequest,
    EventIngestionResponse,
    EventRetrievalResponse,
)
from app.schemas.match import EventContext, MatchExplanationResponse
from app.services.event_ingestion import ingest_event, retrieve_event

router = APIRouter()

DbSession = Annotated[Session, Depends(get_db)]


@router.post(
    "/events",
    response_model=EventIngestionResponse,
)
def create_event(
    envelope: EventIngestionRequest,
    response: Response,
    db: DbSession,
) -> EventIngestionResponse:
    """Ingest one channel event: validate, save raw, normalize, resolve, save.

    Status codes: 201 new, 200 idempotent duplicate, 202 normalization failed.
    """
    result = ingest_event(db, envelope)
    response.status_code = result.http_status
    return result.response


@router.get(
    "/events/{raw_event_id}",
    response_model=EventRetrievalResponse,
)
def get_event(
    raw_event_id: str,
    db: DbSession,
) -> EventRetrievalResponse:
    """Retrieve a raw event and its canonical event (if normalization succeeded)."""
    result = retrieve_event(db, raw_event_id)
    if result is None:
        raise HTTPException(status_code=404, detail="Event not found")
    return result


@router.get(
    "/events/{canonical_event_id}/match-explanation",
    response_model=MatchExplanationResponse,
)
def get_match_explanation(
    canonical_event_id: str,
    db: DbSession,
) -> MatchExplanationResponse:
    """Explainable identity decision for a canonical event (Gate G2)."""
    try:
        event_uuid = uuid.UUID(canonical_event_id)
    except ValueError:
        raise HTTPException(status_code=404, detail="Match decision not found") from None
    decision = db.scalar(
        select(MatchDecision).where(MatchDecision.canonical_event_id == event_uuid)
    )
    if decision is None:
        raise HTTPException(status_code=404, detail="Match decision not found")

    canonical = db.get(CanonicalEvent, event_uuid)
    if canonical is None:
        raise HTTPException(status_code=404, detail="Canonical event not found")

    raw = db.get(RawEvent, canonical.raw_event_id)
    alternatives = [
        candidate
        for candidate in decision.candidates
        if candidate.get("profile_id") != decision.profile_id
    ]
    return MatchExplanationResponse(
        event_id=str(canonical.id),
        event_context=EventContext(
            channel=canonical.channel,
            event_type=canonical.event_type,
            occurred_at=canonical.occurred_at,
        ),
        decision=decision.outcome,
        selected_profile_id=str(decision.profile_id) if decision.profile_id else None,
        score=decision.score,
        thresholds=decision.thresholds,
        evidence=decision.evidence,
        conflicts=decision.conflicts,
        alternative_candidates=alternatives,
        raw_payload=raw.payload if raw else {},
        normalized_fields={
            "identifiers": canonical.identifiers,
            "entity_references": canonical.entity_references,
            "attributes": canonical.attributes,
        },
    )