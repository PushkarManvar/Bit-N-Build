"""Gate G6 analytics endpoint tests."""

from datetime import UTC, datetime, timedelta

from app.core.enums import (
    AlertSeverity,
    AlertStatus,
    AlertType,
    Channel,
    EventType,
    IdentityOutcome,
    ProcessingStatus,
    ReviewStatus,
)
from app.db.models import (
    CanonicalEvent,
    CustomerProfile,
    EvaluationRun,
    JourneyAlert,
    MatchDecision,
    RawEvent,
)


def _add_canonical_event(
    db_session,
    *,
    source_event_id: str,
    channel: Channel,
    event_type: EventType,
    occurred_at: datetime,
    profile_id=None,
    order_id: str | None = None,
) -> CanonicalEvent:
    raw_event = RawEvent(
        channel=channel,
        source_event_id=source_event_id,
        schema_version="1.0",
        occurred_at=occurred_at,
        received_at=occurred_at,
        payload={},
        payload_hash=f"hash-{source_event_id}",
        processing_status=ProcessingStatus.NORMALIZED,
    )
    db_session.add(raw_event)
    db_session.flush()
    event = CanonicalEvent(
        raw_event_id=raw_event.id,
        channel=channel,
        event_type=event_type,
        occurred_at=occurred_at,
        profile_id=profile_id,
        entity_references={"order_id": order_id} if order_id else {},
    )
    db_session.add(event)
    db_session.flush()
    return event


def test_overview_empty_db_returns_null_metrics(client, db_session) -> None:
    response = client.get("/api/analytics/overview")
    assert response.status_code == 200
    body = response.json()
    assert body["total_raw_events"] == 0
    assert body["unified_profiles"] == 0
    assert body["open_alerts"] == 0
    assert body["match_precision"] is None
    assert body["match_f1"] is None
    assert body["false_merge_rate"] is None
    assert body["average_processing_latency_ms"] is None


def test_overview_reflects_latest_evaluation_run(client, db_session) -> None:
    db_session.add(
        EvaluationRun(
            metrics={
                "match_precision": 0.96,
                "match_recall": 0.91,
                "match_f1": 0.93,
                "false_merge_rate": 0.02,
            },
            note="test",
        )
    )
    db_session.add(
        EvaluationRun(
            metrics={
                "match_precision": 0.99,
                "match_recall": 0.99,
                "match_f1": 0.99,
                "false_merge_rate": 0.0,
            },
            note="latest",
        )
    )
    db_session.commit()

    response = client.get("/api/analytics/overview")
    body = response.json()
    assert body["match_precision"] == 0.99
    assert body["match_recall"] == 0.99
    assert body["match_f1"] == 0.99
    assert body["false_merge_rate"] == 0.0


def test_overview_counts_open_alerts(
    client,
    db_session,
    riya_web_anonymous,
    riya_return_requested,
    riya_support_mobile,
    riya_support_call,
) -> None:
    client.post("/api/events", json=riya_web_anonymous)
    client.post("/api/events", json=riya_return_requested)
    client.post("/api/events", json=riya_support_mobile)
    client.post("/api/events", json=riya_support_call)

    response = client.get("/api/analytics/overview")
    body = response.json()
    assert body["open_alerts"] == 2
    assert body["total_raw_events"] == 4
    assert body["normalized_events"] == 4
    assert body["unified_profiles"] == 1


def test_channels_counts(
    client,
    db_session,
    riya_web_anonymous,
    riya_return_requested,
    riya_support_mobile,
    riya_support_call,
) -> None:
    client.post("/api/events", json=riya_web_anonymous)
    client.post("/api/events", json=riya_return_requested)
    client.post("/api/events", json=riya_support_mobile)
    client.post("/api/events", json=riya_support_call)

    response = client.get("/api/analytics/channels")
    body = response.json()
    assert body["web"] == 2
    assert body["mobile_app"] == 1
    assert body["call_center"] == 1
    assert body["physical_store"] == 0


def test_friction_radar_empty_db_is_an_honest_zero_snapshot(client, db_session) -> None:
    response = client.get("/api/analytics/friction-radar")

    assert response.status_code == 200
    body = response.json()
    assert body["score_version"] == "friction_v1"
    assert body["score_max"] == 60
    assert body["summary"] == {
        "attributable_open_refunds": 0,
        "unattributed_open_refunds": 0,
        "critical": 0,
        "elevated": 0,
        "watch": 0,
    }
    assert body["journeys"] == []
    assert sum(bucket["count"] for bucket in body["unresolved_age_distribution"]) == 0
    assert body["support_contact_channels"] == []


def test_friction_radar_ranks_persisted_refund_evidence(client, db_session) -> None:
    now = datetime.now(UTC)
    profile = CustomerProfile(
        display_name="Riya Shah",
        first_seen_at=now - timedelta(days=5),
        last_seen_at=now,
    )
    db_session.add(profile)
    db_session.flush()

    order_id = "ORD-RADAR-001"
    _add_canonical_event(
        db_session,
        source_event_id="return-radar-001",
        channel=Channel.WEB,
        event_type=EventType.RETURN_REQUESTED,
        occurred_at=now - timedelta(days=5),
        profile_id=profile.id,
        order_id=order_id,
    )
    for index, channel in enumerate(
        (Channel.WEB, Channel.MOBILE_APP, Channel.CALL_CENTER), start=1
    ):
        _add_canonical_event(
            db_session,
            source_event_id=f"support-radar-00{index}",
            channel=channel,
            event_type=EventType.SUPPORT_CONTACTED,
            occurred_at=now - timedelta(days=2, hours=index),
            profile_id=profile.id,
            order_id=order_id,
        )

    review_event = _add_canonical_event(
        db_session,
        source_event_id="review-radar-001",
        channel=Channel.MOBILE_APP,
        event_type=EventType.SUPPORT_CONTACTED,
        occurred_at=now - timedelta(days=1),
        order_id=order_id,
    )
    db_session.add(
        MatchDecision(
            canonical_event_id=review_event.id,
            outcome=IdentityOutcome.REVIEW_REQUIRED,
            score=50,
            candidates=[{"profile_id": str(profile.id), "score": 50}],
            review_status=ReviewStatus.PENDING,
        )
    )
    db_session.add_all(
        [
            JourneyAlert(
                profile_id=profile.id,
                order_id=order_id,
                type=AlertType.UNRESOLVED_REFUND,
                severity=AlertSeverity.HIGH,
                title="Refund remains unresolved",
                description="test",
                recommended_action="test",
                status=AlertStatus.OPEN,
            ),
            JourneyAlert(
                profile_id=profile.id,
                order_id=order_id,
                type=AlertType.REPEAT_CONTACT,
                severity=AlertSeverity.MEDIUM,
                title="Repeated support contact",
                description="test",
                recommended_action="test",
                status=AlertStatus.OPEN,
            ),
            JourneyAlert(
                order_id="ORD-UNATTRIBUTED",
                type=AlertType.UNRESOLVED_REFUND,
                severity=AlertSeverity.HIGH,
                title="Unattributed refund",
                description="test",
                recommended_action="test",
                status=AlertStatus.OPEN,
            ),
        ]
    )
    db_session.commit()

    response = client.get("/api/analytics/friction-radar?limit=1")

    assert response.status_code == 200
    body = response.json()
    assert body["summary"] == {
        "attributable_open_refunds": 1,
        "unattributed_open_refunds": 1,
        "critical": 1,
        "elevated": 0,
        "watch": 0,
    }
    journey = body["journeys"][0]
    assert journey["display_name"] == "Riya Shah"
    assert journey["order_id"] == order_id
    assert journey["friction_score"] == 57
    assert journey["band"] == "critical"
    assert journey["distinct_channel_count"] == 3
    assert journey["support_contact_count"] == 3
    assert journey["has_open_repeat_contact_alert"] is True
    assert journey["pending_candidate_review_count"] == 1
    assert journey["components"] == {
        "unresolved_age_points": 20,
        "channel_points": 9,
        "support_contact_points": 12,
        "repeat_contact_points": 10,
        "pending_candidate_review_points": 6,
    }
    assert sum(bucket["count"] for bucket in body["unresolved_age_distribution"]) == 1
    assert body["support_contact_channels"] == [
        {"channel": "call_center", "count": 1, "share_percent": 33.3},
        {"channel": "mobile_app", "count": 1, "share_percent": 33.3},
        {"channel": "web", "count": 1, "share_percent": 33.3},
    ]


def test_friction_radar_validates_its_limit(client, db_session) -> None:
    response = client.get("/api/analytics/friction-radar?limit=0")

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "VALIDATION_ERROR"
