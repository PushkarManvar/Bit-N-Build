"""Deterministic demo controls (Gate G7).

Playback is timer-driven without background workers: the status endpoint
advances the run based on elapsed time and lazily ingests due steps. Reset
wipes operational data and reloads the synthetic base fixtures so the
dashboard and metrics are populated for the presentation.
"""

import json
import os
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from app.core.enums import DemoRunStatus
from app.core.errors import AppError
from app.db.models import (
    CanonicalEvent,
    CustomerProfile,
    DemoRun,
    EvaluationRun,
    JourneyAlert,
    MatchDecision,
    ProfileIdentifier,
    RawEvent,
    ReviewAction,
)
from app.schemas.events import EventIngestionRequest
from app.services.event_ingestion import ingest_event

_DELETE_ORDER = [
    ReviewAction,
    JourneyAlert,
    MatchDecision,
    CanonicalEvent,
    ProfileIdentifier,
    CustomerProfile,
    RawEvent,
    EvaluationRun,
    DemoRun,
]

RAW_FILES = [
    "web_events.jsonl",
    "mobile_events.jsonl",
    "call_center_events.jsonl",
    "store_events.jsonl",
]


class DemoError(AppError):
    def __init__(
        self, *, code: str, message: str, http_status: int, details: dict | None = None
    ) -> None:
        super().__init__(
            code=code,
            message=message,
            stage="demo",
            raw_event_id=None,
            details=details or {},
            http_status=http_status,
        )


@dataclass(frozen=True)
class DemoRunState:
    run_id: str
    status: str
    current_step: int
    total_steps: int
    last_event_id: str | None = None
    error: str | None = None


def default_data_dir() -> Path:
    env = os.environ.get("JOURNEYLENS_DATA_DIR")
    if env:
        return Path(env)
    if Path("/data").is_dir():
        return Path("/data")
    return Path(__file__).resolve().parents[2] / "data"


def _load_baseline(db: Session, data_dir: Path) -> dict[str, int]:
    """Ingest the synthetic base fixtures after a reset."""
    counts = {"received": 0, "duplicates": 0, "failed": 0, "invalid": 0}
    for filename in RAW_FILES:
        path = data_dir / "raw" / filename
        if not path.exists():
            continue
        with path.open("r", encoding="utf-8") as handle:
            for line in handle:
                line = line.strip()
                if not line:
                    continue
                try:
                    envelope = EventIngestionRequest.model_validate_json(line)
                except Exception:
                    counts["invalid"] += 1
                    continue
                result = ingest_event(db, envelope)
                if result.http_status == 201:
                    counts["received"] += 1
                elif result.http_status == 200:
                    counts["duplicates"] += 1
                else:
                    counts["failed"] += 1
    db.commit()
    return counts


def reset_demo(db: Session, data_dir: Path | None = None) -> dict[str, int]:
    """Wipe all operational data and reload the synthetic base fixtures."""
    for model in _DELETE_ORDER:
        db.execute(delete(model))
    db.commit()
    return _load_baseline(db, data_dir or default_data_dir())


def _load_scenario(data_dir: Path, scenario: str) -> list[dict]:
    path = data_dir / "demo" / f"{scenario}.json"
    if not path.exists():
        raise DemoError(
            code="DEMO_SCENARIO_NOT_FOUND",
            message=f"Demo scenario '{scenario}' not found.",
            http_status=404,
        )
    with path.open("r", encoding="utf-8") as handle:
        payload = json.load(handle)
    return payload.get("steps", [])


def _next_run_id(db: Session) -> str:
    count = int(db.scalar(select(func.count()).select_from(DemoRun)) or 0)
    return f"demo-run-{count + 1:02d}"


def _ingest_step(db: Session, envelope: dict) -> str:
    event = EventIngestionRequest.model_validate(envelope)
    result = ingest_event(db, event)
    response = result.response
    return response.canonical_event_id or response.raw_event_id


def start_demo(
    db: Session,
    *,
    scenario: str,
    interval_seconds: float,
    data_dir: Path | None = None,
) -> DemoRunState:
    data = data_dir or default_data_dir()
    steps = _load_scenario(data, scenario)
    if not steps:
        raise DemoError(
            code="DEMO_EMPTY_SCENARIO",
            message=f"Demo scenario '{scenario}' has no steps.",
            http_status=422,
        )

    run = DemoRun(
        run_id=_next_run_id(db),
        scenario=scenario,
        total_steps=len(steps),
        interval_seconds=interval_seconds,
        status=DemoRunStatus.RUNNING,
        current_step=0,
        started_at=datetime.now(UTC),
    )
    db.add(run)
    db.flush()

    try:
        last_event_id = _ingest_step(db, steps[0])
        run.current_step = 1
        run.last_event_id = last_event_id
    except Exception as exc:  # noqa: BLE001
        run.status = DemoRunStatus.FAILED
        run.error = str(exc)
    db.commit()
    return _to_state(run)


def get_demo_run(db: Session, run_id: str, data_dir: Path | None = None) -> DemoRunState:
    run = db.scalar(select(DemoRun).where(DemoRun.run_id == run_id))
    if run is None:
        raise DemoError(
            code="DEMO_RUN_NOT_FOUND",
            message=f"Demo run '{run_id}' not found.",
            http_status=404,
        )
    if run.status == DemoRunStatus.RUNNING:
        steps = _load_scenario(data_dir or default_data_dir(), run.scenario)
        elapsed = (datetime.now(UTC) - _to_utc(run.started_at)).total_seconds()
        target = min(run.total_steps, 1 + int(elapsed // run.interval_seconds))
        try:
            while run.current_step < target:
                last_event_id = _ingest_step(db, steps[run.current_step])
                run.current_step += 1
                run.last_event_id = last_event_id
            if run.current_step >= run.total_steps:
                run.status = DemoRunStatus.COMPLETED
        except Exception as exc:  # noqa: BLE001
            run.status = DemoRunStatus.FAILED
            run.error = str(exc)
        db.commit()
    return _to_state(run)


def latest_run(db: Session) -> DemoRunState | None:
    run = db.scalar(select(DemoRun).order_by(DemoRun.started_at.desc()))
    return _to_state(run) if run else None


def _to_state(run: DemoRun) -> DemoRunState:
    return DemoRunState(
        run_id=run.run_id,
        status=run.status.value,
        current_step=run.current_step,
        total_steps=run.total_steps,
        last_event_id=run.last_event_id,
        error=run.error,
    )


def _to_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)