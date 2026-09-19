"""Data Pipeline read-model contract tests (docs/05 section 10)."""

from datetime import UTC, datetime

from sqlalchemy import update

from app.db.models import RawEvent


def test_pipeline_overview_empty_database_is_truthful(client) -> None:
    response = client.get("/api/pipeline/overview")

    assert response.status_code == 200
    body = response.json()
    datetime.fromisoformat(body.pop("as_of").replace("Z", "+00:00"))
    poll_cursor = body.pop("poll_cursor")
    assert isinstance(poll_cursor, str)
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
    assert normalized["event_summary"] == {
        "title": "Product viewed",
        "detail": None,
        "kind": "product_view",
    }
    assert normalized["has_order_reference"] is True
    assert normalized["profile_id"] is not None
    assert normalized["needs_review"] is False

    assert failed["canonical_event_id"] is None
    assert failed["processed_at"] is None
    assert failed["processing_status"] == "failed"
    assert failed["processing_error_code"] == "NORMALIZATION_FAILED"
    assert failed["identity_outcome"] is None
    assert failed["profile_id"] is None
    assert failed["needs_review"] is False
    assert failed["event_summary"] is None
    assert failed["has_order_reference"] is None


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


def test_pipeline_events_lists_only_the_requested_identity_outcome(
    client, id04_device_only, id04_email_plus_device
) -> None:
    assert client.post("/api/events", json=id04_device_only).status_code == 201
    review = client.post("/api/events", json=id04_email_plus_device)
    assert review.status_code == 201

    response = client.get("/api/pipeline/events?identity_outcome=review_required")

    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 1
    assert body["next_cursor"] is None
    assert len(body["items"]) == 1
    assert body["items"][0] == {
        "raw_event_id": review.json()["raw_event_id"],
        "canonical_event_id": review.json()["canonical_event_id"],
        "source_event_id": "APP-90099",
        "channel": "mobile_app",
        "event_type": "support_contacted",
        "event_summary": {
            "title": "Support contact",
            "detail": None,
            "kind": "support_contact",
        },
        "has_order_reference": False,
        "occurred_at": "2026-09-15T10:30:00Z",
        "received_at": body["items"][0]["received_at"],
        "processed_at": body["items"][0]["processed_at"],
        "processing_status": "normalized",
        "processing_error_code": None,
        "profile_id": None,
        "identity_outcome": "review_required",
        "identity_score": 50,
        "needs_review": True,
    }


def test_pipeline_events_paginates_without_loss_when_receipt_times_match(
    client, db_session, riya_web_valid
) -> None:
    source_ids = ["WEB-CURSOR-1", "WEB-CURSOR-2", "WEB-CURSOR-3"]
    for source_event_id in source_ids:
        response = client.post(
            "/api/events",
            json={**riya_web_valid, "source_event_id": source_event_id},
        )
        assert response.status_code == 201

    db_session.execute(
        update(RawEvent).values(received_at=datetime(2026, 9, 20, 12, 0, tzinfo=UTC))
    )
    db_session.commit()

    first = client.get("/api/pipeline/events?limit=2")
    assert first.status_code == 200
    first_body = first.json()
    assert first_body["total"] == 3
    assert len(first_body["items"]) == 2
    assert first_body["next_cursor"] is not None

    second = client.get(f"/api/pipeline/events?limit=2&cursor={first_body['next_cursor']}")
    assert second.status_code == 200
    second_body = second.json()
    assert second_body["total"] == 3
    assert second_body["next_cursor"] is None
    assert len(second_body["items"]) == 1

    first_sources = {item["source_event_id"] for item in first_body["items"]}
    second_sources = {item["source_event_id"] for item in second_body["items"]}
    assert first_sources.isdisjoint(second_sources)
    assert first_sources | second_sources == set(source_ids)


def test_pipeline_events_rejects_invalid_or_filter_mismatched_cursors(
    client, riya_web_valid
) -> None:
    for source_event_id in ("WEB-FILTER-1", "WEB-FILTER-2"):
        assert (
            client.post(
                "/api/events",
                json={**riya_web_valid, "source_event_id": source_event_id},
            ).status_code
            == 201
        )

    first = client.get("/api/pipeline/events?channel=web&limit=1")
    assert first.status_code == 200
    cursor = first.json()["next_cursor"]
    assert cursor is not None

    mismatched = client.get(
        f"/api/pipeline/events?channel=mobile_app&cursor={cursor}"
    )
    assert mismatched.status_code == 422
    assert mismatched.json()["error"] == {
        "code": "VALIDATION_ERROR",
        "message": "Pipeline cursor is invalid or does not match the active filters.",
        "stage": "pipeline",
        "raw_event_id": None,
        "details": {},
    }

    invalid = client.get("/api/pipeline/events?cursor=not-a-cursor")
    assert invalid.status_code == 422
    assert invalid.json()["error"]["code"] == "VALIDATION_ERROR"


def test_pipeline_event_detail_keeps_raw_canonical_and_decision_data_together(
    client, riya_web_valid
) -> None:
    normalized = client.post("/api/events", json=riya_web_valid)
    assert normalized.status_code == 201

    response = client.get(f"/api/pipeline/events/{normalized.json()['raw_event_id']}")

    assert response.status_code == 200
    body = response.json()
    assert body["event"]["raw_event_id"] == normalized.json()["raw_event_id"]
    assert body["event"]["canonical_event_id"] == normalized.json()["canonical_event_id"]
    assert body["raw_event"]["id"] == normalized.json()["raw_event_id"]
    assert body["raw_event"]["payload"] == riya_web_valid
    assert body["canonical_event"]["id"] == normalized.json()["canonical_event_id"]
    assert body["canonical_event"]["raw_event_id"] == normalized.json()["raw_event_id"]
    assert body["identity_decision"] == {
        "canonical_event_id": normalized.json()["canonical_event_id"],
        "selected_profile_id": normalized.json()["profile_id"],
        "outcome": "new_profile",
        "score": 0,
        "thresholds": {"auto_link": 80, "review_required": 50},
        "evidence": [],
        "conflicts": [],
        "candidates": [],
        "reason": "No candidate profile shares an identifier with this event.",
        "review_status": None,
    }


def test_pipeline_event_detail_keeps_failed_event_fields_null(client, riya_web_valid) -> None:
    failed = client.post(
        "/api/events",
        json={
            **riya_web_valid,
            "source_event_id": "WEB-DETAIL-FAILED",
            "schema_version": "9.9",
        },
    )
    assert failed.status_code == 202

    response = client.get(f"/api/pipeline/events/{failed.json()['raw_event_id']}")

    assert response.status_code == 200
    body = response.json()
    assert body["event"]["processing_status"] == "failed"
    assert body["raw_event"]["processing_error"].startswith("NORMALIZATION_FAILED:")
    assert body["canonical_event"] is None
    assert body["identity_decision"] is None


def test_pipeline_event_detail_includes_pending_review_state(
    client, id04_device_only, id04_email_plus_device
) -> None:
    assert client.post("/api/events", json=id04_device_only).status_code == 201
    review = client.post("/api/events", json=id04_email_plus_device)
    assert review.status_code == 201

    response = client.get(f"/api/pipeline/events/{review.json()['raw_event_id']}")

    assert response.status_code == 200
    decision = response.json()["identity_decision"]
    assert decision is not None
    assert decision["outcome"] == "review_required"
    assert decision["review_status"] == "pending"
    assert response.json()["event"]["needs_review"] is True


def test_pipeline_event_detail_uses_shared_not_found_error(client) -> None:
    for raw_event_id in ("not-a-uuid", "00000000-0000-0000-0000-000000000000"):
        response = client.get(f"/api/pipeline/events/{raw_event_id}")

        assert response.status_code == 404
        assert response.json()["error"] == {
            "code": "PIPELINE_EVENT_NOT_FOUND",
            "message": "Pipeline event not found.",
            "stage": "pipeline",
            "raw_event_id": None,
            "details": {},
        }


def test_pipeline_updates_delivers_events_after_the_overview_cursor(
    client, riya_web_valid
) -> None:
    overview = client.get("/api/pipeline/overview")
    assert overview.status_code == 200
    cursor = overview.json()["poll_cursor"]
    assert cursor is not None

    ingested = client.post(
        "/api/events",
        json={**riya_web_valid, "source_event_id": "WEB-POLL-1"},
    )
    assert ingested.status_code == 201

    updates = client.get(f"/api/pipeline/updates?cursor={cursor}")

    assert updates.status_code == 200
    body = updates.json()
    assert [event["raw_event_id"] for event in body["events"]] == [
        ingested.json()["raw_event_id"]
    ]
    assert body["has_more"] is False
    assert body["next_cursor"] == body["upper_bound_cursor"]
    assert body["stages"]["raw_accepted"] == 1


def test_pipeline_summary_is_identical_across_read_endpoints(client) -> None:
    cursor = client.get("/api/pipeline/overview").json()["poll_cursor"]
    event = {
        "source_event_id": "CALL-SUMMARY-01",
        "channel": "call_center",
        "event_type": "support_contacted",
        "occurred_at": "2026-09-20T12:00:00Z",
        "schema_version": "1.0",
        "identifiers": [],
        "entity_references": {"order_id": "ORD-204"},
        "attributes": {"notes": "Refund not received"},
    }
    ingested = client.post("/api/events", json=event)
    assert ingested.status_code == 201

    overview_event = client.get("/api/pipeline/overview").json()["events"][0]
    listed_response = client.get("/api/pipeline/events?source_event_id=CALL-SUMMARY-01")
    listed_event = listed_response.json()["items"][0]
    update_event = client.get(f"/api/pipeline/updates?cursor={cursor}").json()["events"][0]
    detail_response = client.get(f"/api/pipeline/events/{ingested.json()['raw_event_id']}")
    detail_event = detail_response.json()["event"]

    expected_summary = {
        "title": "Support contact",
        "detail": "Refund not received",
        "kind": "support_refund_follow_up",
    }
    for pipeline_event in (overview_event, listed_event, update_event, detail_event):
        assert pipeline_event["event_summary"] == expected_summary
        assert pipeline_event["has_order_reference"] is True


def test_pipeline_updates_drains_a_101_event_burst_without_loss_or_duplicates(
    client, riya_web_valid
) -> None:
    origin = client.get("/api/pipeline/overview").json()["poll_cursor"]
    ingested_ids: set[str] = set()
    for number in range(101):
        response = client.post(
            "/api/events",
            json={
                **riya_web_valid,
                "source_event_id": f"WEB-BURST-{number:03}",
            },
        )
        assert response.status_code == 201
        ingested_ids.add(response.json()["raw_event_id"])

    first = client.get(f"/api/pipeline/updates?cursor={origin}&limit=100")
    assert first.status_code == 200
    first_body = first.json()
    assert first_body["has_more"] is True
    assert len(first_body["events"]) == 100

    second = client.get(
        "/api/pipeline/updates"
        f"?cursor={first_body['next_cursor']}"
        f"&upper_bound_cursor={first_body['upper_bound_cursor']}"
        "&limit=100"
    )
    assert second.status_code == 200
    second_body = second.json()
    assert second_body["has_more"] is False
    assert len(second_body["events"]) == 1
    assert second_body["next_cursor"] == first_body["upper_bound_cursor"]

    first_ids = {event["raw_event_id"] for event in first_body["events"]}
    second_ids = {event["raw_event_id"] for event in second_body["events"]}
    assert first_ids.isdisjoint(second_ids)
    assert first_ids | second_ids == ingested_ids
