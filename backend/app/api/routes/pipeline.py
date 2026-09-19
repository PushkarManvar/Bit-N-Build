"""Data Pipeline read-model endpoints."""

from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.enums import Channel, IdentityOutcome, ProcessingStatus
from app.core.errors import AppError
from app.db.session import get_db
from app.schemas.pipeline import (
    PipelineEventDetailResponse,
    PipelineEventListResponse,
    PipelineOverviewResponse,
    PipelineUpdatesResponse,
)
from app.services.pipeline_read_model import (
    PipelineEventFilters,
    get_pipeline_event_detail,
    get_pipeline_snapshot,
    get_pipeline_updates,
    list_pipeline_events,
)

router = APIRouter()

DbSession = Annotated[Session, Depends(get_db)]


@router.get("/pipeline/overview", response_model=PipelineOverviewResponse)
def pipeline_overview(
    db: DbSession,
    limit: Annotated[int, Query(ge=1, le=100)] = 25,
) -> PipelineOverviewResponse:
    """Return stage/channel counts and the latest persisted raw events."""
    return get_pipeline_snapshot(db, limit=limit)


@router.get("/pipeline/events", response_model=PipelineEventListResponse)
def pipeline_events(
    db: DbSession,
    limit: Annotated[int, Query(ge=1, le=100)] = 25,
    cursor: Annotated[str | None, Query(min_length=1, max_length=1000)] = None,
    channel: Channel | None = None,
    processing_status: ProcessingStatus | None = None,
    identity_outcome: IdentityOutcome | None = None,
    source_event_id: Annotated[str | None, Query(min_length=1, max_length=200)] = None,
) -> PipelineEventListResponse:
    """Return a filtered, list-safe page of raw pipeline events."""
    return list_pipeline_events(
        db,
        filters=PipelineEventFilters(
            channel=channel,
            processing_status=processing_status,
            identity_outcome=identity_outcome,
            source_event_id=source_event_id,
        ),
        limit=limit,
        cursor=cursor,
    )


@router.get("/pipeline/events/{raw_event_id}", response_model=PipelineEventDetailResponse)
def pipeline_event_detail(
    raw_event_id: str,
    db: DbSession,
) -> PipelineEventDetailResponse:
    """Return raw, canonical, and identity records for one pipeline event."""
    detail = get_pipeline_event_detail(db, raw_event_id)
    if detail is None:
        raise AppError(
            code="PIPELINE_EVENT_NOT_FOUND",
            message="Pipeline event not found.",
            stage="pipeline",
            http_status=404,
        )
    return detail


@router.get("/pipeline/updates", response_model=PipelineUpdatesResponse)
def pipeline_updates(
    db: DbSession,
    cursor: Annotated[str, Query(min_length=1, max_length=1000)],
    limit: Annotated[int, Query(ge=1, le=100)] = 100,
    upper_bound_cursor: Annotated[str | None, Query(min_length=1, max_length=1000)] = None,
) -> PipelineUpdatesResponse:
    """Return newly persisted events after one opaque high-water cursor."""
    return get_pipeline_updates(
        db,
        cursor=cursor,
        limit=limit,
        upper_bound_cursor=upper_bound_cursor,
    )
