"""Demo controls and dashboard polling endpoints (Gate G7)."""

from datetime import UTC, datetime
from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.demo import (
    DashboardUpdatesResponse,
    DemoResetResponse,
    DemoRunResponse,
    DemoStartRequest,
    DemoStartResponse,
)
from app.services.dashboard import dashboard_updates
from app.services.demo import get_demo_run, reset_demo, start_demo

router = APIRouter()

DbSession = Annotated[Session, Depends(get_db)]


@router.post("/demo/reset", response_model=DemoResetResponse)
def demo_reset(db: DbSession) -> DemoResetResponse:
    """Wipe operational data and reload synthetic base fixtures (demo only)."""
    loaded = reset_demo(db)
    return DemoResetResponse(status="reset", loaded=loaded)


@router.post("/demo/start", response_model=DemoStartResponse)
def demo_start(request: DemoStartRequest, db: DbSession) -> DemoStartResponse:
    """Start deterministic scenario playback; the first step ingests immediately."""
    run = start_demo(
        db,
        scenario=request.scenario,
        interval_seconds=request.interval_seconds,
    )
    return DemoStartResponse(
        run_id=run.run_id,
        status=run.status,
        total_steps=run.total_steps,
        current_step=run.current_step,
    )


@router.get("/demo/{run_id}", response_model=DemoRunResponse)
def demo_status(run_id: str, db: DbSession) -> DemoRunResponse:
    """Playback status; advances due steps based on elapsed time."""
    run = get_demo_run(db, run_id)
    return DemoRunResponse(
        run_id=run.run_id,
        status=run.status,
        current_step=run.current_step,
        total_steps=run.total_steps,
        last_event_id=run.last_event_id,
        error=run.error,
    )


@router.get("/dashboard/updates", response_model=DashboardUpdatesResponse)
def dashboard_updates_endpoint(
    db: DbSession,
    since: Annotated[datetime | None, Query()] = None,
) -> DashboardUpdatesResponse:
    """Recent events, new alerts, review count, and demo state for polling."""
    if since is not None:
        since = since.astimezone(UTC) if since.tzinfo else since.replace(tzinfo=UTC)
    return dashboard_updates(db, since)