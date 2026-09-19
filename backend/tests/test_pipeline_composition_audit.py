"""Composition diagnostics for the truthful Data Pipeline narrative plan."""

from datetime import UTC, datetime

from sqlalchemy import update

from app.db.models import RawEvent
from app.services.pipeline_composition_audit import audit_pipeline_composition


def test_pipeline_composition_audit_measures_a_batched_mixed_page(
    client, db_session, riya_return_requested, riya_support_call, riya_web_valid
) -> None:
    fixtures = [
        riya_web_valid,
        riya_return_requested,
        {
            **riya_support_call,
            "attributes": {"notes": "Refund not received"},
        },
        {
            **riya_return_requested,
            "source_event_id": "STORE-204-01",
            "channel": "physical_store",
            "event_type": "store_visited",
            "occurred_at": "2026-09-16T12:00:00Z",
            "attributes": {"store_city": "Mumbai"},
        },
    ]
    for fixture in fixtures:
        assert client.post("/api/events", json=fixture).status_code == 201

    failed = client.post(
        "/api/events",
        json={
            **riya_web_valid,
            "source_event_id": "WEB-AUDIT-FAILED",
            "schema_version": "9.9",
        },
    )
    assert failed.status_code == 202

    db_session.execute(
        update(RawEvent).values(received_at=datetime(2026, 9, 20, 12, 0, tzinfo=UTC))
    )
    db_session.commit()

    audit = audit_pipeline_composition(db_session, limit=25)

    assert audit.window_size == 5
    assert audit.channel_counts == {
        "web": 3,
        "call_center": 1,
        "physical_store": 1,
    }
    assert audit.event_type_counts == {
        "product_viewed": 1,
        "return_requested": 1,
        "support_contacted": 1,
        "store_visited": 1,
    }
    assert audit.processing_status_counts == {"normalized": 4, "failed": 1}
    assert audit.distinct_received_at_seconds == 1
    assert audit.distinct_occurred_at_seconds == 4
    assert audit.rows_with_order_reference == 4
    assert audit.rows_with_recognized_support_context == 1
    assert audit.rows_with_recognized_store_context == 1

    overview = client.get("/api/pipeline/overview?limit=25")
    assert overview.status_code == 200
    prohibited_fields = {
        "attributes",
        "identifiers",
        "evidence",
        "candidates",
        "processing_error",
    }
    assert all(prohibited_fields.isdisjoint(event) for event in overview.json()["events"])
