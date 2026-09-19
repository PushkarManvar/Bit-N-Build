"""Analytics endpoints (Gate G6)."""

from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.analytics import AnalyticsOverview, ChannelsResponse
from app.services.analytics import compute_channels, compute_overview

router = APIRouter()

DbSession = Annotated[Session, Depends(get_db)]


@router.get("/analytics/overview", response_model=AnalyticsOverview)
def analytics_overview(db: DbSession) -> AnalyticsOverview:
    """Computed overview metrics; null for anything not yet evaluated."""
    return compute_overview(db)


@router.get("/analytics/channels", response_model=ChannelsResponse)
def analytics_channels(db: DbSession) -> ChannelsResponse:
    """Canonical event counts per channel."""
    return compute_channels(db)