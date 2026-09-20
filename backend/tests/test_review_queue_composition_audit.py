"""Aggregate diagnostics for the pending-review data baseline."""

from app.services.demo import reset_demo
from app.services.review_queue_composition_audit import audit_pending_review_composition


def test_review_composition_audit_reports_persisted_evidence_groups(
    client, db_session, id04_device_only, id04_email_plus_device
) -> None:
    assert client.post("/api/events", json=id04_device_only).status_code == 201
    assert client.post("/api/events", json=id04_email_plus_device).status_code == 201

    audit = audit_pending_review_composition(db_session)

    assert audit.pending_count == 1
    assert len(audit.groups) == 1
    group = audit.groups[0]
    assert group.channel == "mobile_app"
    assert group.score == 50
    assert group.has_conflicts is False
    assert group.evidence_fields == ("device_id",)
    assert group.decision_reason == (
        "best candidate score 50 is between review and auto-link thresholds."
    )
    assert group.count == 1


def test_clean_demo_seed_has_an_explainable_pending_review_total(db_session) -> None:
    loaded = reset_demo(db_session, seed="full")

    audit = audit_pending_review_composition(db_session)

    assert loaded == {"received": 189, "duplicates": 6, "failed": 2, "invalid": 2}
    assert audit.pending_count == 67
    assert [
        (
            group.channel,
            group.score,
            group.has_conflicts,
            group.evidence_fields,
            group.decision_reason,
            group.count,
        )
        for group in audit.groups
    ] == [
        (
            "mobile_app",
            50,
            False,
            ("device_id",),
            "best candidate score 50 is between review and auto-link thresholds.",
            35,
        ),
        (
            "web",
            50,
            False,
            ("device_id", "session_id"),
            "best candidate score 50 is between review and auto-link thresholds.",
            21,
        ),
        (
            "web",
            50,
            False,
            ("device_id",),
            "best candidate score 50 is between review and auto-link thresholds.",
            6,
        ),
        (
            "call_center",
            0,
            False,
            (),
            "a matching name exists, but no identifier evidence supports a link.",
            2,
        ),
        (
            "physical_store",
            0,
            False,
            (),
            "a matching name exists, but no identifier evidence supports a link.",
            2,
        ),
        (
            "call_center",
            100,
            True,
            ("email", "order_id"),
            "strong identifiers point to different profiles; a human must decide.",
            1,
        ),
    ]


def test_curated_demo_seed_exposes_exactly_three_review_archetypes(
    client, db_session
) -> None:
    loaded = reset_demo(db_session, seed="curated")

    audit = audit_pending_review_composition(db_session)
    queue = client.get("/api/reviews")

    assert loaded == {"received": 8, "duplicates": 0, "failed": 0, "invalid": 0}
    assert audit.pending_count == 3
    assert [
        (group.channel, group.score, group.has_conflicts, group.evidence_fields, group.count)
        for group in audit.groups
    ] == [
        ("call_center", 90, True, ("email",), 1),
        ("mobile_app", 50, False, ("device_id",), 1),
        ("physical_store", 0, False, (), 1),
    ]
    assert queue.status_code == 200
    assert queue.json()["total"] == 3
