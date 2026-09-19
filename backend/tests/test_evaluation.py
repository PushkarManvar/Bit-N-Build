"""Gate G6 evaluation logic tests (hidden truth is never read by runtime)."""

from datetime import UTC, datetime
from pathlib import Path

from app.core.enums import AlertSeverity, AlertStatus, AlertType
from app.db.models import CustomerProfile, JourneyAlert
from scripts.evaluate_matching import _alert_metrics, _pair_metrics


def _event(truth_id: str, profile: str | None) -> dict:
    return {"truth_id": truth_id, "runtime_profile": profile}


def test_pair_metrics_perfect() -> None:
    metrics = _pair_metrics(
        [
            _event("T1", "P1"),
            _event("T1", "P1"),
            _event("T2", "P2"),
            _event("T2", "P2"),
        ]
    )
    assert metrics["match_precision"] == 1.0
    assert metrics["match_recall"] == 1.0
    assert metrics["match_f1"] == 1.0
    assert metrics["false_merge_rate"] == 0.0


def test_pair_metrics_false_merge_detected() -> None:
    metrics = _pair_metrics(
        [
            _event("T1", "P1"),
            _event("T1", "P1"),
            _event("T2", "P1"),  # different customer merged into P1
        ]
    )
    assert metrics["fp"] >= 1
    assert metrics["false_merge_rate"] > 0.0
    assert metrics["match_precision"] < 1.0


def test_pair_metrics_false_split_detected() -> None:
    metrics = _pair_metrics(
        [
            _event("T1", "P1"),
            _event("T1", "P2"),  # same customer split into P1/P2
        ]
    )
    assert metrics["fn"] >= 1
    assert metrics["match_recall"] < 1.0


def test_alert_metrics_reports_found_missed_unexpected(
    client, db_session, tmp_path: Path
) -> None:
    profile = CustomerProfile(
        display_name="Riya Shah",
        first_seen_at=datetime.now(UTC),
        last_seen_at=datetime.now(UTC),
    )
    db_session.add(profile)
    db_session.flush()
    db_session.add(
        JourneyAlert(
            profile_id=profile.id,
            order_id="ORD-204",
            type=AlertType.UNRESOLVED_REFUND,
            severity=AlertSeverity.HIGH,
            title="t",
            description="d",
            recommended_action="a",
            status=AlertStatus.OPEN,
        )
    )
    db_session.commit()

    truth_dir = tmp_path / "truth"
    truth_dir.mkdir()
    expected = truth_dir / "expected_alerts.csv"
    expected.write_text(
        "truth_profile_id,order_id,alert_type,severity\n"
        "TRUTH-C001,ORD-204,unresolved_refund,high\n"
        "TRUTH-C001,ORD-204,repeat_contact,medium\n"
        "TRUTH-C002,ORD-999,unresolved_refund,high\n",
        encoding="utf-8",
    )

    event_rows = [
        {
            "_runtime_profile": str(profile.id),
            "truth_profile_id": "TRUTH-C001",
            "source_event_id": "WEB-1",
        },
        {
            "_runtime_profile": str(profile.id),
            "truth_profile_id": "TRUTH-C001",
            "source_event_id": "APP-1",
        },
    ]

    metrics = _alert_metrics(db_session, event_rows, tmp_path)
    assert metrics["alert_found"] == 1
    assert metrics["alert_missed"] == 2
    assert metrics["alert_unexpected"] == 0
    assert metrics["alert_duplicates"] == 0
    assert metrics["alert_precision"] == 1.0
    assert metrics["alert_recall"] == round(1 / 3, 4)


def test_alert_metrics_duplicates_counted(client, db_session, tmp_path: Path) -> None:
    profile = CustomerProfile(
        display_name="Riya Shah",
        first_seen_at=datetime.now(UTC),
        last_seen_at=datetime.now(UTC),
    )
    db_session.add(profile)
    db_session.flush()
    for _ in range(2):
        db_session.add(
            JourneyAlert(
                profile_id=profile.id,
                order_id="ORD-204",
                type=AlertType.REPEAT_CONTACT,
                severity=AlertSeverity.MEDIUM,
                title="t",
                description="d",
                recommended_action="a",
                status=AlertStatus.OPEN,
            )
        )
    db_session.commit()

    truth_dir = tmp_path / "truth"
    truth_dir.mkdir()
    expected = truth_dir / "expected_alerts.csv"
    expected.write_text(
        "truth_profile_id,order_id,alert_type,severity\n",
        encoding="utf-8",
    )
    event_rows = [{"_runtime_profile": str(profile.id), "truth_profile_id": "TRUTH-C001"}]
    metrics = _alert_metrics(db_session, event_rows, tmp_path)
    assert metrics["alert_duplicates"] >= 1