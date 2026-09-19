from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_event_ingestion_returns_canonical_event() -> None:
    response = client.post(
        "/api/events",
        json={
            "source": "web",
            "source_record_id": "WEB-001",
            "occurred_at": "2026-09-14T08:00:00Z",
            "payload": {
                "event": "return_initiated",
                "deviceId": "DEV-17",
                "sessionId": "SESS-1001",
                "order_id": "ord 204",
            },
        },
    )

    assert response.status_code == 201
    body = response.json()
    assert body["status"] == "normalized"
    assert body["canonical_event"]["event_type"] == "return_started"
    assert body["canonical_event"]["device_id"] == "DEV-17"
    assert body["canonical_event"]["order_id"] == "ORD-204"
