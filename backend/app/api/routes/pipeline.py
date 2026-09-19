"""Data Pipeline read-model endpoints."""

from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.pipeline import PipelineOverviewResponse
from app.services.pipeline_read_model import get_pipeline_snapshot

router = APIRouter()

DbSession = Annotated[Session, Depends(get_db)]


@router.get("/pipeline/overview", response_model=PipelineOverviewResponse)
def pipeline_overview(
    db: DbSession,
    limit: Annotated[int, Query(ge=1, le=100)] = 25,
) -> PipelineOverviewResponse:
    """Return stage/channel counts and the latest persisted raw events."""
    return get_pipeline_snapshot(db, limit=limit)
