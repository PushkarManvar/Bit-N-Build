"""Gate G2 integration tests: identity pipeline through the live API.

Covers the flagship Riya bridge, the Aarav non-merge safety story, the
anonymous-to-known bridge, strong conflicts, and match persistence.
"""

import uuid

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.enums import IdentityOutcome
from app.db.models import (
    CanonicalEvent,
    CustomerProfile,
    MatchDecision,
    ProfileIdentifier,
)


def _count(db: Session, model) -> int:
    return int(db.scalar(select(func.count()).select_from(model)) or 0)


def test_riya_bridge_auto_links_web_to_mobile(
    client, db_session, riya_web_anonymous, riya_mobile_status
) -> None:
    first = client.post("/api/events", json=riya_web_anonymous)
    assert first.status_code == 201
    assert first.json()["match_decision"] == "new_profile"
    anonymous_profile = first.json()["profile_id"]
    assert anonymous_profile is not None

    second = client.post("/api/events", json=riya_mobile_status)
    assert second.status_code == 201
    body = second.json()
    assert body["match_decision"] == "auto_linked"
    assert body["profile_id"] == anonymous_profile
    assert body["match_score"] == 100

    evidence_fields = [item["field"] for item in _explanation(client, body)["evidence"]]
    assert "order_id" in evidence_fields
    assert "device_id" in evidence_fields

    profile = db_session.get(CustomerProfile, uuid.UUID(anonymous_profile))
    assert profile is not None
    identifiers = db_session.scalars(
        select(ProfileIdentifier).where(ProfileIdentifier.profile_id == profile.id)
    ).all()
    types = {row.type for row in identifiers}
    assert {"email", "order_id", "device_id"} <= types


def test_aarav_name_only_never_merges(client, aarav_name_only) -> None:
    first = client.post("/api/events", json=aarav_name_only)
    assert first.status_code == 201
    assert first.json()["match_decision"] == "new_profile"

    duplicate_name = dict(aarav_name_only)
    duplicate_name["source_event_id"] = "WEB-032"

    second = client.post("/api/events", json=duplicate_name)
    assert second.status_code == 201
    assert second.json()["match_decision"] == "new_profile"
    assert second.json()["profile_id"] != first.json()["profile_id"]


def test_anonymous_to_known_bridge_routes_to_review(
    client, db_session, id04_device_only, id04_email_plus_device
) -> None:
    first = client.post("/api/events", json=id04_device_only)
    assert first.status_code == 201
    assert first.json()["match_decision"] == "new_profile"
    anonymous_profile = first.json()["profile_id"]

    second = client.post("/api/events", json=id04_email_plus_device)
    assert second.status_code == 201
    body = second.json()
    assert body["match_decision"] == "review_required"
    assert body["profile_id"] is None
    assert body["match_score"] == 50

    canonical_id = body["canonical_event_id"]
    canonical = db_session.get(CanonicalEvent, uuid.UUID(canonical_id))
    assert canonical.profile_id is None

    decision = db_session.scalar(
        select(MatchDecision).where(MatchDecision.canonical_event_id == uuid.UUID(canonical_id))
    )
    assert decision is not None
    assert decision.outcome == IdentityOutcome.REVIEW_REQUIRED
    assert decision.candidates[0]["profile_id"] == anonymous_profile


def test_strong_conflict_routes_to_review(client) -> None:
    profile_a = {
        "source_event_id": "WEB-CONF-A",
        "channel": "web",
        "event_type": "product_viewed",
        "occurred_at": "2026-09-16T08:00:00Z",
        "schema_version": "1.0",
        "identifiers": [{"type": "email", "value": "alice@example.com"}],
        "entity_references": {},
        "attributes": {},
    }
    profile_b = {
        "source_event_id": "WEB-CONF-B",
        "channel": "web",
        "event_type": "product_viewed",
        "occurred_at": "2026-09-16T08:05:00Z",
        "schema_version": "1.0",
        "identifiers": [{"type": "phone", "value": "+919876543210"}],
        "entity_references": {},
        "attributes": {},
    }
    client.post("/api/events", json=profile_a)
    client.post("/api/events", json=profile_b)

    conflicting = {
        "source_event_id": "WEB-CONF-C",
        "channel": "web",
        "event_type": "support_contacted",
        "occurred_at": "2026-09-16T09:00:00Z",
        "schema_version": "1.0",
        "identifiers": [
            {"type": "email", "value": "alice@example.com"},
            {"type": "phone", "value": "+919876543210"},
        ],
        "entity_references": {},
        "attributes": {},
    }
    response = client.post("/api/events", json=conflicting)
    assert response.status_code == 201
    body = response.json()
    assert body["match_decision"] == "review_required"
    assert body["profile_id"] is None

    explanation = _explanation(client, body)
    assert len(explanation["conflicts"]) >= 1


def test_match_decision_persisted_for_every_event(
    client, db_session, riya_web_anonymous, riya_mobile_status
) -> None:
    client.post("/api/events", json=riya_web_anonymous)
    client.post("/api/events", json=riya_mobile_status)
    assert _count(db_session, MatchDecision) == 2
    assert _count(db_session, CustomerProfile) == 1


def test_id03_order_phone_auto_link_with_two_evidence(client) -> None:
    event1 = {
        "source_event_id": "WEB-ID03-1",
        "channel": "web",
        "event_type": "return_requested",
        "occurred_at": "2026-09-16T08:00:00Z",
        "schema_version": "1.0",
        "identifiers": [{"type": "phone", "value": "+91-98765-43210"}],
        "entity_references": {"order_id": "ord 204"},
        "attributes": {},
    }
    first = client.post("/api/events", json=event1)
    assert first.json()["match_decision"] == "new_profile"

    event2 = {
        "source_event_id": "WEB-ID03-2",
        "channel": "web",
        "event_type": "return_requested",
        "occurred_at": "2026-09-17T08:00:00Z",
        "schema_version": "1.0",
        "identifiers": [{"type": "phone", "value": "9876543210"}],
        "entity_references": {"order_id": "ORD-204"},
        "attributes": {},
    }
    second = client.post("/api/events", json=event2)
    body = second.json()
    assert body["match_decision"] == "auto_linked"
    assert body["profile_id"] == first.json()["profile_id"]
    assert body["match_score"] == 100
    fields = {item["field"] for item in _explanation(client, body)["evidence"]}
    assert fields == {"order_id", "phone"}


def _explanation(client, ingestion_body: dict) -> dict:
    canonical_id = ingestion_body["canonical_event_id"]
    response = client.get(f"/api/events/{canonical_id}/match-explanation")
    assert response.status_code == 200
    return response.json()