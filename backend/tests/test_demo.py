"""Gate G7 demo control and dashboard polling tests."""

import json
from datetime import UTC, datetime, timedelta
from pathlib import Path

from sqlalchemy import func, select

from app.core.enums import AlertType, DemoRunStatus
from app.db.models import (
    CanonicalEvent,
    DemoRun,
    JourneyAlert,
    RawEvent,
)
from app.services.demo import get_demo_run, reset_demo, start_demo


def _write_scenario(tmp_path: Path, steps: list[dict]) -> Path:
    demo_dir = tmp_path / "demo"
    demo_dir.mkdir(exist_ok=True)
    scenario = demo_dir / "test_scenario.json"
    scenario.write_text(json.dumps({"scenario": "test_scenario", "steps": steps}), encoding="utf-8")
    return tmp_path


def _write_raw(tmp_path: Path, events: list[dict]) -> Path:
    raw_dir = tmp_path / "raw"
    raw_dir.mkdir(exist_ok=True)
    with (raw_dir / "web_events.jsonl").open("w", encoding="utf-8") as handle:
        for event in events:
            handle.write(json.dumps(event) + "\n")
    return tmp_path


def _riya_step(source_id: str, event_type: str, occurred_at: str) -> dict:
    return {
        "source_event_id": source_id,
        "channel": "web",
        "event_type": event_type,
        "occurred_at": occurred_at,
        "schema_version": "1.0",
        "identifiers": [{"type": "device_id", "value": "DEV-17"}],
        "entity_references": {"order_id": "ORD-204"},
        "attributes": {"customer_name": "Riya Shah"},
    }


def test_reset_wipes_and_reloads_base(db_session, tmp_path: Path) -> None:
    events = [
        _riya_step("WEB-00001", "product_viewed", "2026-09-14T08:00:00Z"),
        _riya_step("WEB-00002", "return_requested", "2026-09-15T08:00:00Z"),
    ]
    data_dir = _write_raw(tmp_path, events)

    loaded = reset_demo(db_session, data_dir)
    assert loaded["received"] == 2
    assert int(db_session.scalar(select(func.count()).select_from(RawEvent)) or 0) == 2
    assert int(db_session.scalar(select(func.count()).select_from(CanonicalEvent)) or 0) == 2


def test_reset_clears_existing_data(db_session, tmp_path: Path) -> None:
    events = [_riya_step("WEB-00001", "product_viewed", "2026-09-14T08:00:00Z")]
    data_dir = _write_raw(tmp_path, events)
    reset_demo(db_session, data_dir)

    reset_demo(db_session, data_dir)
    assert int(db_session.scalar(select(func.count()).select_from(RawEvent)) or 0) == 1


def test_start_ingests_first_step(db_session, tmp_path: Path) -> None:
    steps = [
        _riya_step("DEMO-WEB-01", "product_viewed", "2026-09-14T08:00:00Z"),
        _riya_step("DEMO-WEB-02", "return_requested", "2026-09-15T08:00:00Z"),
    ]
    data_dir = _write_scenario(tmp_path, steps)

    run = start_demo(db_session, scenario="test_scenario", interval_seconds=60, data_dir=data_dir)
    assert run.current_step == 1
    assert run.total_steps == 2
    assert run.status == DemoRunStatus.RUNNING.value
    assert run.last_event_id is not None


def test_status_advances_to_completion(db_session, tmp_path: Path) -> None:
    steps = [
        _riya_step("DEMO-WEB-01", "product_viewed", "2026-09-14T08:00:00Z"),
        _riya_step("DEMO-WEB-02", "return_requested", "2026-09-15T08:00:00Z"),
        _riya_step("DEMO-WEB-03", "support_contacted", "2026-09-15T09:00:00Z"),
    ]
    data_dir = _write_scenario(tmp_path, steps)
    start_demo(db_session, scenario="test_scenario", interval_seconds=60, data_dir=data_dir)

    run_row = db_session.scalar(select(DemoRun))
    run_row.started_at = datetime.now(UTC) - timedelta(seconds=300)
    db_session.commit()

    state = get_demo_run(db_session, run_row.run_id, data_dir)
    assert state.status == DemoRunStatus.COMPLETED.value
    assert state.current_step == 3
    assert state.last_event_id is not None


def test_demo_run_produces_alerts_and_review(
    client, db_session, tmp_path: Path
) -> None:
    steps = [
        {
            "source_event_id": "DEMO-WEB-01",
            "channel": "web",
            "event_type": "product_viewed",
            "occurred_at": "2026-09-14T08:00:00Z",
            "schema_version": "1.0",
            "identifiers": [
                {"type": "device_id", "value": "DEV-17"},
                {"type": "session_id", "value": "SESS-1"},
            ],
            "entity_references": {"order_id": "ORD-204"},
            "attributes": {"customer_name": "Riya Shah"},
        },
        {
            "source_event_id": "DEMO-APP-01",
            "channel": "mobile_app",
            "event_type": "support_contacted",
            "occurred_at": "2026-09-15T09:00:00Z",
            "schema_version": "1.0",
            "identifiers": [
                {"type": "email", "value": "RIYA@EXAMPLE.COM"},
                {"type": "device_id", "value": "dev-17"},
            ],
            "entity_references": {"order_id": "ORD-204"},
            "attributes": {},
        },
        {
            "source_event_id": "DEMO-CC-01",
            "channel": "call_center",
            "event_type": "support_contacted",
            "occurred_at": "2026-09-15T11:00:00Z",
            "schema_version": "1.0",
            "identifiers": [
                {"type": "phone", "value": "+91-98765-43210"},
                {"type": "email", "value": "RIYA@EXAMPLE.COM"},
            ],
            "entity_references": {"order_id": "ORD-204"},
            "attributes": {},
        },
        {
            "source_event_id": "DEMO-STORE-01",
            "channel": "physical_store",
            "event_type": "return_requested",
            "occurred_at": "2026-09-16T12:00:00Z",
            "schema_version": "1.0",
            "identifiers": [{"type": "phone", "value": "9876543210"}],
            "entity_references": {"order_id": "ORD-204"},
            "attributes": {},
        },
    ]
    data_dir = _write_scenario(tmp_path, steps)
    run = start_demo(db_session, scenario="test_scenario", interval_seconds=60, data_dir=data_dir)
    run_row = db_session.scalar(select(DemoRun))
    run_row.started_at = datetime.now(UTC) - timedelta(seconds=300)
    db_session.commit()
    get_demo_run(db_session, run.run_id, data_dir)

    alert_types = set(
        db_session.scalars(
            select(JourneyAlert.type).where(JourneyAlert.status == "open")
        ).all()
    )
    assert alert_types == {AlertType.UNRESOLVED_REFUND, AlertType.REPEAT_CONTACT}


def test_dashboard_updates_endpoint(
    client,
    riya_web_anonymous,
    riya_return_requested,
    riya_support_mobile,
    riya_support_call,
) -> None:
    client.post("/api/events", json=riya_web_anonymous)
    client.post("/api/events", json=riya_return_requested)
    client.post("/api/events", json=riya_support_mobile)
    client.post("/api/events", json=riya_support_call)

    response = client.get("/api/dashboard/updates")
    assert response.status_code == 200
    body = response.json()
    assert len(body["events"]) == 4
    assert body["open_alerts"] == 2
    assert body["new_alerts"] is not None


def test_demo_start_and_status_via_api(client, db_session) -> None:
    start = client.post(
        "/api/demo/start",
        json={"scenario": "unresolved_refund_riya", "interval_seconds": 0.0001},
    )
    assert start.status_code == 200
    body = start.json()
    assert body["status"] == "running"
    assert body["total_steps"] == 6
    assert body["current_step"] == 1

    row = db_session.scalar(select(DemoRun))
    row.started_at = datetime.now(UTC) - timedelta(seconds=60)
    db_session.commit()

    status = client.get(f"/api/demo/{body['run_id']}")
    assert status.status_code == 200
    assert status.json()["status"] == "completed"
    assert status.json()["current_step"] == 6