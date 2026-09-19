"""Gate G4 journey alert tests (docs/04 §12 JR-01..JR-04, idempotency, API)."""

import uuid

from sqlalchemy import func, select

from app.core.enums import AlertStatus, AlertType
from app.db.models import CustomerProfile, JourneyAlert
from app.services.journey_analyzer import analyze_profile


def _count_alerts(db, profile_id: str, alert_type: AlertType) -> int:
    return int(
        db.scalar(
            select(func.count())
            .select_from(JourneyAlert)
            .where(
                JourneyAlert.profile_id == uuid.UUID(profile_id),
                JourneyAlert.type == alert_type,
                JourneyAlert.status == AlertStatus.OPEN,
            )
        )
        or 0
    )


def _build_riya_journey(
    client,
    riya_web_anonymous,
    riya_return_requested,
    riya_support_mobile,
    riya_support_call,
) -> str:
    first = client.post("/api/events", json=riya_web_anonymous)
    client.post("/api/events", json=riya_return_requested)
    client.post("/api/events", json=riya_support_mobile)
    client.post("/api/events", json=riya_support_call)
    return first.json()["profile_id"]


def test_jr01_unresolved_refund_and_jr04_repeat_contact_created(
    client,
    db_session,
    riya_web_anonymous,
    riya_return_requested,
    riya_support_mobile,
    riya_support_call,
) -> None:
    profile_id = _build_riya_journey(
        client, riya_web_anonymous, riya_return_requested, riya_support_mobile, riya_support_call
    )

    assert _count_alerts(db_session, profile_id, AlertType.UNRESOLVED_REFUND) == 1
    assert _count_alerts(db_session, profile_id, AlertType.REPEAT_CONTACT) == 1
    total = int(db_session.scalar(select(func.count()).select_from(JourneyAlert)) or 0)
    assert total == 2


def test_jr01_requires_two_support_contacts(
    client, db_session, riya_web_anonymous, riya_return_requested, riya_support_mobile
) -> None:
    first = client.post("/api/events", json=riya_web_anonymous)
    client.post("/api/events", json=riya_return_requested)
    client.post("/api/events", json=riya_support_mobile)
    profile_id = first.json()["profile_id"]

    assert _count_alerts(db_session, profile_id, AlertType.UNRESOLVED_REFUND) == 0
    assert _count_alerts(db_session, profile_id, AlertType.REPEAT_CONTACT) == 0


def test_jr02_refund_completion_prevents_new_unresolved_alert(
    client,
    db_session,
    riya_web_anonymous,
    riya_return_requested,
    riya_support_mobile,
    riya_support_call,
    riya_refund_completed,
) -> None:
    profile_id = _build_riya_journey(
        client, riya_web_anonymous, riya_return_requested, riya_support_mobile, riya_support_call
    )
    before = _count_alerts(db_session, profile_id, AlertType.UNRESOLVED_REFUND)

    client.post("/api/events", json=riya_refund_completed)
    after = _count_alerts(db_session, profile_id, AlertType.UNRESOLVED_REFUND)

    assert before == 1
    assert after == before  # no new unresolved alert


def test_jr03_analyzer_is_idempotent(
    client,
    db_session,
    riya_web_anonymous,
    riya_return_requested,
    riya_support_mobile,
    riya_support_call,
) -> None:
    profile_id = _build_riya_journey(
        client, riya_web_anonymous, riya_return_requested, riya_support_mobile, riya_support_call
    )
    profile = db_session.get(CustomerProfile, uuid.UUID(profile_id))

    analyze_profile(db_session, profile.id)
    db_session.commit()
    analyze_profile(db_session, profile.id)
    db_session.commit()

    total = int(db_session.scalar(select(func.count()).select_from(JourneyAlert)) or 0)
    assert total == 2


def test_jr04_support_outside_72h_no_repeat_alert(
    client, db_session, riya_web_anonymous
) -> None:
    first = client.post("/api/events", json=riya_web_anonymous)
    profile_id = first.json()["profile_id"]

    support_a = {
        "source_event_id": "WEB-SUPA",
        "channel": "web",
        "event_type": "support_contacted",
        "occurred_at": "2026-09-14T08:30:00Z",
        "schema_version": "1.0",
        "identifiers": [],
        "entity_references": {"order_id": "ORD-204"},
        "attributes": {},
    }
    support_b = {
        "source_event_id": "WEB-SUPB",
        "channel": "web",
        "event_type": "support_contacted",
        "occurred_at": "2026-09-20T08:30:00Z",
        "schema_version": "1.0",
        "identifiers": [],
        "entity_references": {"order_id": "ORD-204"},
        "attributes": {},
    }
    client.post("/api/events", json=support_a)
    client.post("/api/events", json=support_b)

    assert _count_alerts(db_session, profile_id, AlertType.REPEAT_CONTACT) == 0


def test_profile_journey_exposes_open_alerts(
    client, riya_web_anonymous, riya_return_requested, riya_support_mobile, riya_support_call
) -> None:
    profile_id = _build_riya_journey(
        client, riya_web_anonymous, riya_return_requested, riya_support_mobile, riya_support_call
    )
    response = client.get(f"/api/profiles/{profile_id}")
    assert response.status_code == 200
    alerts = response.json()["alerts"]
    assert len(alerts) == 2

    by_type = {alert["type"]: alert for alert in alerts}
    unresolved = by_type["unresolved_refund"]
    assert unresolved["severity"] == "high"
    assert unresolved["order_id"] == "ORD-204"
    assert unresolved["status"] == "open"
    assert unresolved["title"] == "Refund ORD-204 remains unresolved"
    assert unresolved["recommended_action"] != ""

    repeat = by_type["repeat_contact"]
    assert repeat["severity"] == "medium"
    assert repeat["status"] == "open"


def test_alerts_list_endpoint(
    client, riya_web_anonymous, riya_return_requested, riya_support_mobile, riya_support_call
) -> None:
    _build_riya_journey(
        client, riya_web_anonymous, riya_return_requested, riya_support_mobile, riya_support_call
    )
    response = client.get("/api/alerts")
    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 2
    types = {item["type"] for item in body["items"]}
    assert types == {"unresolved_refund", "repeat_contact"}