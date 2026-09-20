"""Public contract tests for the additive Review Queue read model."""


def _reset_curated_demo(client) -> None:
    response = client.post("/api/demo/reset?seed=curated")
    assert response.status_code == 200
    assert response.json()["loaded"]["received"] == 8


def test_review_queue_classifies_the_curated_cases_without_identifier_values(client) -> None:
    _reset_curated_demo(client)

    response = client.get("/api/review-queue")

    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 3
    assert body["summary"] == {
        "pending": 3,
        "critical_conflicts": 1,
        "incomplete_evidence": 1,
        "same_name_collisions": 1,
        "ambiguous_moderate_matches": 0,
    }
    assert [item["review_kind"] for item in body["items"]] == [
        "strong_identifier_conflict",
        "incomplete_evidence",
        "same_name_collision",
    ]
    assert [item["priority"] for item in body["items"]] == [
        "critical",
        "standard",
        "standard",
    ]

    conflict = body["items"][0]
    assert conflict["event"] == {
        "channel": "call_center",
        "event_type": "support_contacted",
        "customer_name": "Conflict Case",
        "occurred_at": "2026-09-14T09:00:00Z",
    }
    assert conflict["reason_code"] == "strong_identifier_conflict"
    assert conflict["conflicts"] == [
        {
            "fields": ["email", "phone"],
            "message": "Email and phone resolve to different profiles.",
        }
    ]
    assert [candidate["matched_fields"] for candidate in conflict["candidates"]] == [
        ["email"],
        ["phone"],
    ]
    assert conflict["evidence"] == [
        {
            "field": "email",
            "result": "exact_match",
            "weight": 90,
            "message": "Same email matches the profile.",
        }
    ]

    bridge = body["items"][1]
    assert bridge["missing_strong_identifiers"] == [
        "customer_id",
        "order_id",
        "phone",
    ]
    assert bridge["evidence"][0]["field"] == "device_id"
    assert bridge["evidence"][0]["weight"] == 45

    same_name = body["items"][2]
    assert same_name["candidates"] == []
    assert same_name["evidence"] == []
    assert same_name["conflicts"] == []

    rendered = str(body)
    assert "conflict.a@example.com" not in rendered
    assert "9876500000" not in rendered
    assert "DEV-CURATED-BRIDGE" not in rendered


def test_review_queue_filters_paginate_and_reject_a_mismatched_cursor(client) -> None:
    _reset_curated_demo(client)

    first = client.get("/api/review-queue?limit=1")
    assert first.status_code == 200
    first_body = first.json()
    assert first_body["total"] == 3
    assert first_body["next_cursor"]
    assert first_body["items"][0]["priority"] == "critical"

    second = client.get(f"/api/review-queue?limit=1&cursor={first_body['next_cursor']}")
    assert second.status_code == 200
    assert second.json()["items"][0]["review_kind"] == "incomplete_evidence"

    filtered = client.get("/api/review-queue?kind=same_name_collision")
    assert filtered.status_code == 200
    assert filtered.json()["total"] == 1
    assert filtered.json()["summary"] == {
        "pending": 1,
        "critical_conflicts": 0,
        "incomplete_evidence": 0,
        "same_name_collisions": 1,
        "ambiguous_moderate_matches": 0,
    }
    assert filtered.json()["items"][0]["event"]["channel"] == "physical_store"

    mismatched = client.get(
        f"/api/review-queue?kind=same_name_collision&cursor={first_body['next_cursor']}"
    )
    assert mismatched.status_code == 422
    assert mismatched.json()["error"]["code"] == "VALIDATION_ERROR"

    invalid = client.get("/api/review-queue?priority=urgent")
    assert invalid.status_code == 422
    assert invalid.json()["error"]["code"] == "VALIDATION_ERROR"


def test_review_queue_classifies_every_pending_full_seed_case(client) -> None:
    reset = client.post("/api/demo/reset?seed=full")
    assert reset.status_code == 200

    response = client.get("/api/review-queue?limit=100")

    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 67
    assert body["summary"]["critical_conflicts"] == 1
    assert all(item["review_kind"] in {
        "strong_identifier_conflict",
        "same_name_collision",
        "incomplete_evidence",
    } for item in body["items"])
