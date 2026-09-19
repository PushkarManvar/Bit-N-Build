"""Gate G2 profile API tests: list, detail, timeline, search."""


def _build_riya(client, riya_web_anonymous, riya_mobile_status) -> str:
    first = client.post("/api/events", json=riya_web_anonymous)
    client.post("/api/events", json=riya_mobile_status)
    return first.json()["profile_id"]


def test_profiles_list_reflects_resolved_customer(
    client, db_session, riya_web_anonymous, riya_mobile_status
) -> None:
    _build_riya(client, riya_web_anonymous, riya_mobile_status)

    response = client.get("/api/profiles")
    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 1
    summary = body["items"][0]
    assert summary["email"] == "riya.shah@example.com"
    assert summary["event_count"] == 2
    assert set(summary["channels_used"]) == {"web", "mobile_app"}
    assert summary["open_alert_count"] == 0


def test_profile_journey_timeline_is_chronological(
    client, db_session, riya_web_anonymous, riya_mobile_status
) -> None:
    profile_id = _build_riya(client, riya_web_anonymous, riya_mobile_status)

    response = client.get(f"/api/profiles/{profile_id}")
    assert response.status_code == 200
    body = response.json()
    assert len(body["timeline"]) == 2
    times = [event["occurred_at"] for event in body["timeline"]]
    assert times == sorted(times)
    assert body["timeline"][0]["decision"] == "new_profile"
    assert body["timeline"][1]["decision"] == "auto_linked"
    assert body["timeline"][1]["order_id"] == "ORD-204"
    identifier_types = {item["type"] for item in body["profile"]["identifiers"]}
    assert {"email", "order_id", "device_id"} <= identifier_types


def test_profile_search_by_name_and_identifier(
    client, riya_web_anonymous, riya_mobile_status
) -> None:
    profile_id = _build_riya(client, riya_web_anonymous, riya_mobile_status)

    by_name = client.get("/api/profiles", params={"search": "riya"}).json()
    assert by_name["total"] == 1
    assert by_name["items"][0]["profile_id"] == profile_id

    by_email = client.get("/api/profiles", params={"search": "riya.shah"}).json()
    assert by_email["total"] == 1


def test_unknown_profile_returns_404(client) -> None:
    response = client.get("/api/profiles/00000000-0000-0000-0000-000000000000")
    assert response.status_code == 404