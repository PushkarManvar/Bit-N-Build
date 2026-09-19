"""Event ingestion and retrieval endpoints.

HTTP concerns only; processing lives in app.services.event_ingestion.
"""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.events import (
    EventIngestionRequest,
    EventIngestionResponse,
    EventRetrievalResponse,
)
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
    """Ingest one channel event: validate, save raw, normalize, save canonical.

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