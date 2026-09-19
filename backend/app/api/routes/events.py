from fastapi import APIRouter, status

from app.schemas.events import EventIngestionRequest, EventIngestionResponse
from app.services.normalizer import normalize_event

router = APIRouter()


@router.post(
    "/events",
    response_model=EventIngestionResponse,
    status_code=status.HTTP_201_CREATED,
)
def ingest_event(event: EventIngestionRequest) -> EventIngestionResponse:
    """Normalize one event.

    Raw/canonical persistence and identity resolution are the next vertical-slice tasks.
    The response is intentionally explicit about the scaffold state.
    """
    canonical = normalize_event(event)
    return EventIngestionResponse(
        source_record_id=event.source_record_id,
        status="normalized",
        canonical_event=canonical,
        message="Event normalized; persistence and identity resolution are pending.",
    )
