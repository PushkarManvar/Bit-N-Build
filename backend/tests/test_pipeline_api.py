"""Data Pipeline read-model contract tests (docs/05 section 10)."""

from datetime import datetime


def test_pipeline_overview_empty_database_is_truthful(client) -> None:
    response = client.get("/api/pipeline/overview")

    assert response.status_code == 200
    body = response.json()
    datetime.fromisoformat(body.pop("as_of").replace("Z", "+00:00"))
    assert body == {
        "stages": {
            "raw_accepted": 0,
            "normalization_succeeded": 0,
            "normalization_failed": 0,
            "identity_decided": 0,
            "profile_linked": 0,
            "review_required": 0,
        },
        "channels": {
            "web": {"raw": 0, "normalized": 0, "failed": 0},
            "mobile_app": {"raw": 0, "normalized": 0, "failed": 0},
            "call_center": {"raw": 0, "normalized": 0, "failed": 0},
            "physical_store": {"raw": 0, "normalized": 0, "failed": 0},
        },
        "events": [],
        "next_cursor": None,
        "poll_cursor": None,
        "duplicate_attempts": None,
        "duplicate_tracking_supported": False,
    }


def test_pipeline_overview_shows_normalized_and_failed_events(
    client, riya_web_valid
) -> None:
    normalized_response = client.post("/api/events", json=riya_web_valid)
    assert normalized_response.status_code == 201

    failed_event = {
        **riya_web_valid,
        "source_event_id": "WEB-BAD-SCHEMA",
        "schema_version": "9.9",
    }
    failed_response = client.post("/api/events", json=failed_event)
    assert failed_response.status_code == 202

    response = client.get("/api/pipeline/overview")
    assert response.status_code == 200
    body = response.json()

    assert body["stages"] == {
        "raw_accepted": 2,
        "normalization_succeeded": 1,
        "normalization_failed": 1,
        "identity_decided": 1,
        "profile_linked": 1,
        "review_required": 0,
    }
    assert body["channels"]["web"] == {"raw": 2, "normalized": 1, "failed": 1}

    events = {event["source_event_id"]: event for event in body["events"]}
    normalized = events[riya_web_valid["source_event_id"]]
    failed = events["WEB-BAD-SCHEMA"]

    detail = client.get(f"/api/events/{normalized['raw_event_id']}").json()
    assert normalized["canonical_event_id"] == detail["canonical_event"]["id"]
    assert normalized["processed_at"] == detail["canonical_event"]["created_at"]
    assert normalized["processing_status"] == "normalized"
    assert normalized["identity_outcome"] == "new_profile"
    assert normalized["identity_score"] == 0
    assert normalized["profile_id"] is not None
    assert normalized["needs_review"] is False

    assert failed["canonical_event_id"] is None
    assert failed["processed_at"] is None
    assert failed["processing_status"] == "failed"
    assert failed["processing_error_code"] == "NORMALIZATION_FAILED"
    assert failed["identity_outcome"] is None
    assert failed["profile_id"] is None
    assert failed["needs_review"] is False


def test_pipeline_overview_exposes_pending_review_without_claiming_a_profile(
    client, id04_device_only, id04_email_plus_device
) -> None:
    assert client.post("/api/events", json=id04_device_only).status_code == 201
    review_response = client.post("/api/events", json=id04_email_plus_device)
    assert review_response.status_code == 201
    assert review_response.json()["match_decision"] == "review_required"

    response = client.get("/api/pipeline/overview")
    assert response.status_code == 200
    body = response.json()

    assert body["stages"] == {
        "raw_accepted": 2,
        "normalization_succeeded": 2,
        "normalization_failed": 0,
        "identity_decided": 2,
        "profile_linked": 1,
        "review_required": 1,
    }
    review_event = next(
        event
        for event in body["events"]
        if event["source_event_id"] == id04_email_plus_device["source_event_id"]
    )
    assert review_event["identity_outcome"] == "review_required"
    assert review_event["identity_score"] == 50
    assert review_event["profile_id"] is None
    assert review_event["needs_review"] is True


def test_pipeline_overview_validates_and_applies_recent_event_limit(
    client, riya_web_valid
) -> None:
    assert client.post("/api/events", json=riya_web_valid).status_code == 201

    limited = client.get("/api/pipeline/overview?limit=1")
    assert limited.status_code == 200
    assert len(limited.json()["events"]) == 1

    invalid = client.get("/api/pipeline/overview?limit=0")
    assert invalid.status_code == 422
    assert invalid.json()["error"]["code"] == "VALIDATION_ERROR"
