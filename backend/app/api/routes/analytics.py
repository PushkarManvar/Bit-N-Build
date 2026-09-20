"""Analytics endpoints (Gate G6)."""

from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.analytics import AnalyticsOverview, ChannelsResponse, FrictionRadarResponse
from app.services.analytics import compute_channels, compute_overview
from app.services.friction_radar_read_model import compute_friction_radar

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


@router.get("/analytics/friction-radar", response_model=FrictionRadarResponse)
def friction_radar(
    db: DbSession,
    limit: int = Query(default=5, ge=1, le=50),
) -> FrictionRadarResponse:
    """Rank open, attributable unresolved-refund journeys by persisted friction."""
    return compute_friction_radar(db, limit=limit)
