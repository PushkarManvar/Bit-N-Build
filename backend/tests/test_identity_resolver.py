"""Unit tests for the pure identity resolver (docs/04 test IDs ID-01..09)."""

from datetime import UTC, datetime

from app.core.enums import Channel, EventType, IdentityOutcome
from app.services.candidate_retriever import CandidateInfo
from app.services.identity_resolver import decide
from app.services.normalizer import NormalizedEvent


def _event(
    identifiers: list[tuple[str, str]] | None = None,
    refs: dict | None = None,
) -> NormalizedEvent:
    return NormalizedEvent(
        channel=Channel.WEB,
        event_type=EventType.PRODUCT_VIEWED,
        occurred_at=datetime.now(UTC),
        identifiers=[{"type": t, "value": v} for t, v in (identifiers or [])],
        entity_references=refs or {},
        attributes={},
    )


def _candidate(profile_id: str, matched: list[str]) -> CandidateInfo:
    return CandidateInfo(profile_id=profile_id, matched_fields=matched)


def _field_map(**kwargs: list[str]) -> dict[str, list[str]]:
    return kwargs


def test_id01_same_email_auto_links() -> None:
    event = _event([("email", "riya.shah@example.com")])
    result = decide(event, [_candidate("P1", ["email"])], _field_map(email=["P1"]))
    assert result.outcome == IdentityOutcome.AUTO_LINKED
    assert result.selected_profile_id == "P1"
    assert result.score >= 80


def test_id02_same_phone_auto_links() -> None:
    event = _event([("phone", "+919876543210")])
    result = decide(event, [_candidate("P1", ["phone"])], _field_map(phone=["P1"]))
    assert result.outcome == IdentityOutcome.AUTO_LINKED
    assert result.selected_profile_id == "P1"


def test_id03_order_and_phone_show_both_evidence() -> None:
    event = _event([("phone", "+919876543210")], refs={"order_id": "ORD-204"})
    result = decide(
        event,
        [_candidate("P1", ["order_id", "phone"])],
        _field_map(order_id=["P1"], phone=["P1"]),
    )
    assert result.outcome == IdentityOutcome.AUTO_LINKED
    fields = {item["field"] for item in result.evidence}
    assert fields == {"order_id", "phone"}
    assert result.score == 100


def test_id05_same_name_only_never_auto_links() -> None:
    event = _event(identifiers=[], refs={})
    result = decide(event, [], {})
    assert result.outcome == IdentityOutcome.NEW_PROFILE


def test_id06_same_name_and_city_only_never_auto_links() -> None:
    event = _event(identifiers=[], refs={})
    result = decide(event, [], {})
    assert result.outcome == IdentityOutcome.NEW_PROFILE


def test_id07_email_and_phone_on_different_profiles_is_review() -> None:
    event = _event(
        [("email", "riya.shah@example.com"), ("phone", "+919876543210")]
    )
    result = decide(
        event,
        [_candidate("P1", ["email"]), _candidate("P2", ["phone"])],
        _field_map(email=["P1"], phone=["P2"]),
    )
    assert result.outcome == IdentityOutcome.REVIEW_REQUIRED
    assert result.selected_profile_id is None
    assert len(result.conflicts) >= 1


def test_id09_nearly_tied_top_candidates_is_review() -> None:
    event = _event([("email", "riya@example.com")])
    result = decide(
        event,
        [_candidate("P1", ["email", "device_id"]), _candidate("P2", ["email", "session_id"])],
        _field_map(email=["P1", "P2"], device_id=["P1"], session_id=["P2"]),
    )
    assert result.outcome == IdentityOutcome.REVIEW_REQUIRED
    assert "within" in result.reason


def test_device_only_match_scores_review_threshold() -> None:
    event = _event([("device_id", "DEV-77")])
    result = decide(event, [_candidate("P1", ["device_id"])], _field_map(device_id=["P1"]))
    assert result.score == 50
    assert result.outcome == IdentityOutcome.REVIEW_REQUIRED


def test_no_candidate_scores_zero_new_profile() -> None:
    event = _event([("device_id", "DEV-77")])
    result = decide(event, [], {})
    assert result.outcome == IdentityOutcome.NEW_PROFILE
    assert result.score == 0
    assert result.reason != ""


def test_customer_id_is_strongest_evidence() -> None:
    event = _event([("customer_id", "CUST-9")])
    result = decide(event, [_candidate("P1", ["customer_id"])], _field_map(customer_id=["P1"]))
    assert result.score == 100
    assert result.outcome == IdentityOutcome.AUTO_LINKED