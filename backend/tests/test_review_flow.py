"""Gate G5 review queue and resolution tests."""

import uuid

from sqlalchemy import func, select

from app.core.enums import ReviewDecision, ReviewStatus
from app.db.models import (
    CanonicalEvent,
    CustomerProfile,
    JourneyAlert,
    MatchDecision,
    ProfileIdentifier,
    ReviewAction,
)


def _build_review_case(client, db_session) -> str:
    """Create an anonymous profile, then an email+device event routed to review."""
    anonymous = {
        "source_event_id": "WEB-G5-1",
        "channel": "web",
        "event_type": "app_login",
        "occurred_at": "2026-09-14T10:00:00Z",
        "schema_version": "1.0",
        "identifiers": [{"type": "device_id", "value": "dev-77"}],
        "entity_references": {},
        "attributes": {},
    }
    first = client.post("/api/events", json=anonymous)
    anonymous_profile = first.json()["profile_id"]

    ambiguous = {
        "source_event_id": "APP-G5-2",
        "channel": "mobile_app",
        "event_type": "support_contacted",
        "occurred_at": "2026-09-15T10:30:00Z",
        "schema_version": "1.0",
        "identifiers": [
            {"type": "email", "value": "PRIVA@EXAMPLE.COM"},
            {"type": "device_id", "value": "dev-77"},
        ],
        "entity_references": {},
        "attributes": {},
    }
    second = client.post("/api/events", json=ambiguous)
    assert second.json()["match_decision"] == "review_required"
    return second.json()["canonical_event_id"], anonymous_profile


def test_review_queue_lists_pending_decision(
    client, db_session
) -> None:
    canonical_id, anonymous_profile = _build_review_case(client, db_session)
    decision = db_session.scalar(
        select(MatchDecision).where(MatchDecision.canonical_event_id == uuid.UUID(canonical_id))
    )

    response = client.get("/api/reviews")
    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 1
    item = body["items"][0]
    assert item["match_decision_id"] == str(decision.id)
    assert item["event"]["channel"] == "mobile_app"
    assert item["best_candidate"]["profile_id"] == anonymous_profile
    assert item["best_candidate"]["score"] == 50
    assert set(item["missing_strong_identifiers"]) == {"phone", "order_id", "customer_id"}
    assert item["reason"] != ""


def test_approve_link_attaches_event_and_reruns_rules(
    client, db_session
) -> None:
    canonical_id, anonymous_profile = _build_review_case(client, db_session)
    decision = db_session.scalar(
        select(MatchDecision).where(MatchDecision.canonical_event_id == uuid.UUID(canonical_id))
    )

    response = client.post(
        f"/api/reviews/{decision.id}/resolve",
        json={
            "action": "approve_link",
            "selected_profile_id": anonymous_profile,
            "reviewer_name": "Demo Reviewer",
            "note": "Email belongs to this customer.",
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert body["review_status"] == "approved"
    assert body["action"] == "approve_link"
    assert body["profile_id"] == anonymous_profile

    canonical = db_session.get(CanonicalEvent, uuid.UUID(canonical_id))
    assert canonical.profile_id is not None
    identifiers = db_session.scalars(
        select(ProfileIdentifier).where(
            ProfileIdentifier.profile_id == uuid.UUID(anonymous_profile)
        )
    ).all()
    types = {row.type for row in identifiers}
    assert "email" in types

    audit = db_session.scalars(
        select(ReviewAction).where(ReviewAction.match_decision_id == decision.id)
    ).all()
    assert len(audit) == 1
    assert audit[0].action == ReviewDecision.APPROVE_LINK
    assert audit[0].reviewer_name == "Demo Reviewer"

    db_session.refresh(decision)
    assert decision.review_status == ReviewStatus.APPROVED


def test_approve_link_triggers_repeat_contact_alert(
    client, db_session
) -> None:
    """Approving links joins support events, so two contacts within 72h fire JR-002."""
    anonymous = {
        "source_event_id": "WEB-G5-3",
        "channel": "web",
        "event_type": "app_login",
        "occurred_at": "2026-09-14T10:00:00Z",
        "schema_version": "1.0",
        "identifiers": [{"type": "device_id", "value": "dev-88"}],
        "entity_references": {},
        "attributes": {},
    }
    first = client.post("/api/events", json=anonymous)
    anonymous_profile = first.json()["profile_id"]

    support_a = {
        "source_event_id": "WEB-G5-4",
        "channel": "web",
        "event_type": "support_contacted",
        "occurred_at": "2026-09-15T09:00:00Z",
        "schema_version": "1.0",
        "identifiers": [
            {"type": "email", "value": "A@EXAMPLE.COM"},
            {"type": "device_id", "value": "dev-88"},
        ],
        "entity_references": {},
        "attributes": {},
    }
    support_b = {
        "source_event_id": "WEB-G5-5",
        "channel": "web",
        "event_type": "support_contacted",
        "occurred_at": "2026-09-15T10:30:00Z",
        "schema_version": "1.0",
        "identifiers": [
            {"type": "email", "value": "B@EXAMPLE.COM"},
            {"type": "device_id", "value": "dev-88"},
        ],
        "entity_references": {},
        "attributes": {},
    }
    decision_ids = []
    for event in (support_a, support_b):
        response = client.post("/api/events", json=event)
        assert response.json()["match_decision"] == "review_required"
        canonical_id = response.json()["canonical_event_id"]
        decision = db_session.scalar(
            select(MatchDecision).where(
                MatchDecision.canonical_event_id == uuid.UUID(canonical_id)
            )
        )
        decision_ids.append(str(decision.id))

    for decision_id in decision_ids:
        response = client.post(
            f"/api/reviews/{decision_id}/resolve",
            json={
                "action": "approve_link",
                "selected_profile_id": anonymous_profile,
                "reviewer_name": "Demo Reviewer",
                "note": "Same device.",
            },
        )
        assert response.status_code == 200

    repeat_alerts = int(
        db_session.scalar(
            select(func.count())
            .select_from(JourneyAlert)
            .where(JourneyAlert.type == "repeat_contact")
        )
    )
    assert repeat_alerts == 1


def test_reject_link_leaves_event_unlinked_without_new_profile(
    client, db_session
) -> None:
    """Rejecting a candidate must not create a profile or claim identifiers.

    docs/02_USER_WORKFLOWS_AND_UX.md §5: "Candidate is rejected; event remains
    unresolved or another candidate is considered."
    """
    canonical_id, anonymous_profile = _build_review_case(client, db_session)
    decision = db_session.scalar(
        select(MatchDecision).where(MatchDecision.canonical_event_id == uuid.UUID(canonical_id))
    )
    profiles_before = int(
        db_session.scalar(select(func.count()).select_from(CustomerProfile)) or 0
    )

    response = client.post(
        f"/api/reviews/{decision.id}/resolve",
        json={
            "action": "reject_link",
            "selected_profile_id": None,
            "reviewer_name": "Demo Reviewer",
            "note": "Different customer on shared device.",
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert body["action"] == "reject_link"
    assert body["review_status"] == "rejected"
    assert body["profile_id"] is None

    # No new profile, and the event is not attached to the rejected candidate.
    profiles_after = int(
        db_session.scalar(select(func.count()).select_from(CustomerProfile)) or 0
    )
    assert profiles_after == profiles_before

    canonical = db_session.get(CanonicalEvent, uuid.UUID(canonical_id))
    assert canonical.profile_id is None

    # The rejected candidate keeps its identifiers.
    candidate_identifiers = db_session.scalars(
        select(ProfileIdentifier).where(
            ProfileIdentifier.profile_id == uuid.UUID(anonymous_profile)
        )
    ).all()
    assert {(row.type, row.value) for row in candidate_identifiers} == {("device_id", "DEV-77")}

    db_session.refresh(decision)
    assert decision.review_status == ReviewStatus.REJECTED
    assert decision.profile_id is None

    # Audit record still written.
    audit = db_session.scalars(
        select(ReviewAction).where(ReviewAction.match_decision_id == decision.id)
    ).all()
    assert len(audit) == 1
    assert audit[0].action == ReviewDecision.REJECT_LINK


def test_create_profile_action(client, db_session) -> None:
    canonical_id, anonymous_profile = _build_review_case(client, db_session)
    decision = db_session.scalar(
        select(MatchDecision).where(MatchDecision.canonical_event_id == uuid.UUID(canonical_id))
    )

    response = client.post(
        f"/api/reviews/{decision.id}/resolve",
        json={
            "action": "create_profile",
            "selected_profile_id": None,
            "reviewer_name": "Demo Reviewer",
            "note": "New customer.",
        },
    )
    assert response.status_code == 200
    assert response.json()["review_status"] == "profile_created"
    assert response.json()["profile_id"] != anonymous_profile


def test_approve_without_selected_profile_is_422(client, db_session) -> None:
    canonical_id, _ = _build_review_case(client, db_session)
    decision = db_session.scalar(
        select(MatchDecision).where(MatchDecision.canonical_event_id == uuid.UUID(canonical_id))
    )

    response = client.post(
        f"/api/reviews/{decision.id}/resolve",
        json={
            "action": "approve_link",
            "selected_profile_id": None,
            "reviewer_name": "Demo Reviewer",
        },
    )
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "VALIDATION_ERROR"


def test_resolve_unknown_decision_is_404(client) -> None:
    response = client.post(
        "/api/reviews/00000000-0000-0000-0000-000000000000/resolve",
        json={
            "action": "create_profile",
            "selected_profile_id": None,
            "reviewer_name": "Demo Reviewer",
        },
    )
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "REVIEW_NOT_FOUND"


def test_resolve_twice_is_409(client, db_session) -> None:
    canonical_id, anonymous_profile = _build_review_case(client, db_session)
    decision = db_session.scalar(
        select(MatchDecision).where(MatchDecision.canonical_event_id == uuid.UUID(canonical_id))
    )
    payload = {
        "action": "create_profile",
        "selected_profile_id": None,
        "reviewer_name": "Demo Reviewer",
    }
    first = client.post(f"/api/reviews/{decision.id}/resolve", json=payload)
    assert first.status_code == 200

    second = client.post(f"/api/reviews/{decision.id}/resolve", json=payload)
    assert second.status_code == 409
    assert second.json()["error"]["code"] == "REVIEW_ALREADY_RESOLVED"


def test_review_queue_empty_after_resolution(client, db_session) -> None:
    canonical_id, anonymous_profile = _build_review_case(client, db_session)
    decision = db_session.scalar(
        select(MatchDecision).where(MatchDecision.canonical_event_id == uuid.UUID(canonical_id))
    )
    client.post(
        f"/api/reviews/{decision.id}/resolve",
        json={
            "action": "create_profile",
            "selected_profile_id": None,
            "reviewer_name": "Demo Reviewer",
        },
    )
    response = client.get("/api/reviews")
    assert response.json()["total"] == 0