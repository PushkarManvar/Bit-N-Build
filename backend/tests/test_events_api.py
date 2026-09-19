"""Gate G1 API tests.

Run against an in-memory SQLite database via dependency override. Each test
asserts real database row counts, never hard-coded pass markers.
"""

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.db.models import CanonicalEvent, RawEvent


def _counts(db: Session) -> tuple[int, int]:
    raw = db.scalar(select(func.count()).select_from(RawEvent))
    canonical = db.scalar(select(func.count()).select_from(CanonicalEvent))
    return int(raw or 0), int(canonical or 0)


def test_valid_web_event_creates_one_raw_and_one_canonical(
    client, db_session, riya_web_valid
) -> None:
    response = client.post("/api/events", json=riya_web_valid)

    assert response.status_code == 201
    body = response.json()
    assert body["processing_status"] == "normalized"
    assert body["duplicate"] is False
    assert body["canonical_event_id"] is not None

    raw_count, canonical_count = _counts(db_session)
    assert raw_count == 1
    assert canonical_count == 1


def test_canonical_matches_expected_normalized_fixture(
    client, riya_web_valid, riya_web_canonical_expected
) -> None:
    response = client.post("/api/events", json=riya_web_valid)
    assert response.status_code == 201
    body = response.json()
    assert body["channel"] == riya_web_canonical_expected["channel"]
    assert body["event_type"] == riya_web_canonical_expected["event_type"]

    retrieval = client.get(f"/api/events/{body['raw_event_id']}")
    assert retrieval.status_code == 200
    canonical = retrieval.json()["canonical_event"]
    assert canonical["identifiers"] == riya_web_canonical_expected["identifiers"]
    assert (
        canonical["entity_references"] == riya_web_canonical_expected["entity_references"]
    )
    assert canonical["attributes"] == riya_web_canonical_expected["attributes"]


def test_canonical_links_back_to_raw_event(client, riya_web_valid) -> None:
    response = client.post("/api/events", json=riya_web_valid)
    assert response.status_code == 201
    body = response.json()

    retrieval = client.get(f"/api/events/{body['raw_event_id']}")
    assert retrieval.status_code == 200
    data = retrieval.json()
    assert data["canonical_event"]["raw_event_id"] == body["raw_event_id"]
    assert data["raw_event"]["payload"]["source_event_id"] == "WEB-001"


def test_support_note_is_preserved_raw_but_bounded_in_canonical(client) -> None:
    event = {
        "source_event_id": "CALL-204-CONTEXT",
        "channel": "call_center",
        "event_type": "support_contacted",
        "occurred_at": "2026-09-20T12:00:00Z",
        "schema_version": "1.0",
        "identifiers": [],
        "entity_references": {"order_id": "ORD-204"},
        "attributes": {"notes": "Refund not received"},
    }
    response = client.post("/api/events", json=event)

    assert response.status_code == 201
    detail = client.get(f"/api/events/{response.json()['raw_event_id']}")
    assert detail.status_code == 200
    body = detail.json()
    assert body["raw_event"]["payload"]["attributes"] == {
        "notes": "Refund not received"
    }
    assert body["canonical_event"]["attributes"] == {
        "contact_reason": "refund_not_received"
    }


def test_identical_replay_creates_no_additional_rows(
    client, db_session, riya_web_valid, riya_web_duplicate
) -> None:
    first = client.post("/api/events", json=riya_web_valid)
    assert first.status_code == 201

    replay = client.post("/api/events", json=riya_web_duplicate)
    assert replay.status_code == 200
    assert replay.json()["processing_status"] == "duplicate"
    assert replay.json()["duplicate"] is True
    assert replay.json()["raw_event_id"] == first.json()["raw_event_id"]

    raw_count, canonical_count = _counts(db_session)
    assert raw_count == 1
    assert canonical_count == 1


def test_reused_source_id_with_different_payload_returns_conflict(
    client, riya_web_valid
) -> None:
    client.post("/api/events", json=riya_web_valid)

    changed = dict(riya_web_valid)
    changed["attributes"] = {"page": "/products/99", "product_id": "PROD-99"}

    response = client.post("/api/events", json=changed)
    assert response.status_code == 409
    body = response.json()
    assert body["error"]["code"] == "EVENT_ID_REUSED"
    assert body["error"]["stage"] == "ingestion"


def test_missing_required_field_returns_422(client, web_invalid_missing_timestamp) -> None:
    response = client.post("/api/events", json=web_invalid_missing_timestamp)
    assert response.status_code == 422
    body = response.json()
    assert body["error"]["code"] == "VALIDATION_ERROR"


def test_unsupported_channel_rejected(client, riya_web_valid) -> None:
    unsupported = dict(riya_web_valid)
    unsupported["channel"] = "sms"
    response = client.post("/api/events", json=unsupported)
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "VALIDATION_ERROR"


def test_unsupported_event_type_rejected(client, riya_web_valid) -> None:
    unsupported = dict(riya_web_valid)
    unsupported["event_type"] = "dance_party"
    response = client.post("/api/events", json=unsupported)
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "VALIDATION_ERROR"


def test_normalization_failure_retains_failed_raw_event(client, db_session) -> None:
    unsupported_schema = {
        "source_event_id": "WEB-BAD-SCHEMA",
        "channel": "web",
        "event_type": "product_viewed",
        "occurred_at": "2026-09-19T08:30:00Z",
        "schema_version": "9.9",
        "identifiers": [],
        "entity_references": {},
        "attributes": {},
    }
    response = client.post("/api/events", json=unsupported_schema)
    assert response.status_code == 202
    body = response.json()
    assert body["processing_status"] == "failed"
    assert body["canonical_event_id"] is None

    raw_count, canonical_count = _counts(db_session)
    assert raw_count == 1
    assert canonical_count == 0

    raw = db_session.scalar(select(RawEvent))
    assert raw is not None
    assert raw.processing_status.value == "failed"
    assert "NORMALIZATION_FAILED" in (raw.processing_error or "")


def test_retrieval_returns_404_for_unknown_event(client) -> None:
    response = client.get("/api/events/00000000-0000-0000-0000-000000000000")
    assert response.status_code == 404
