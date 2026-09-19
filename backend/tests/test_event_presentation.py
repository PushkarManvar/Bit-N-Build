"""Pure, list-safe event narrative tests."""

from app.core.enums import EventType
from app.services.event_presentation import EventPresentation, present_event


def test_present_event_uses_bounded_support_context() -> None:
    presentation = present_event(
        EventType.SUPPORT_CONTACTED,
        {"order_id": "ORD-204"},
        {"contact_reason": "refund_not_received"},
    )

    assert presentation == EventPresentation(
        title="Support contact",
        detail="Refund not received",
        kind="support_refund_follow_up",
        has_order_reference=True,
    )


def test_present_event_omits_unrecognized_support_note_context() -> None:
    presentation = present_event(
        EventType.SUPPORT_CONTACTED,
        {},
        {"contact_reason": "other"},
    )

    assert presentation == EventPresentation(
        title="Support contact",
        detail=None,
        kind="support_contact",
        has_order_reference=False,
    )


def test_present_event_marks_order_reference_without_exposing_its_value() -> None:
    presentation = present_event(
        EventType.RETURN_REQUESTED,
        {"order_id": "ORD-204"},
        {},
    )

    assert presentation == EventPresentation(
        title="Return requested",
        detail="Order reference recorded",
        kind="return_requested",
        has_order_reference=True,
    )
