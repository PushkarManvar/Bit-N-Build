"""Gate G6 analytics endpoint tests."""

from app.db.models import EvaluationRun


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