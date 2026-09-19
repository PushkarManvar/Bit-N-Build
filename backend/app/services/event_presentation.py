"""Deterministic, list-safe narratives for canonical events."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

from app.core.enums import ContactReason, EventType


@dataclass(frozen=True)
class EventPresentation:
    """Safe event copy derived from canonical type and bounded context only."""

    title: str
    detail: str | None
    kind: str
    has_order_reference: bool


def present_event(
    event_type: EventType,
    entity_references: Mapping[str, Any],
    attributes: Mapping[str, Any],
) -> EventPresentation:
    """Create one factual presentation without exposing source values."""
    has_order_reference = _has_order_reference(entity_references)
    order_detail = "Order reference recorded" if has_order_reference else None

    if event_type == EventType.PRODUCT_VIEWED:
        return EventPresentation("Product viewed", None, "product_view", has_order_reference)
    if event_type == EventType.APP_LOGIN:
        return EventPresentation("Mobile app sign-in", None, "app_sign_in", has_order_reference)
    if event_type == EventType.ORDER_PLACED:
        return EventPresentation("Order placed", order_detail, "order_placed", has_order_reference)
    if event_type == EventType.RETURN_REQUESTED:
        return EventPresentation(
            "Return requested", order_detail, "return_requested", has_order_reference
        )
    if event_type == EventType.SUPPORT_CONTACTED:
        return _support_presentation(attributes, has_order_reference)
    if event_type == EventType.STORE_VISITED:
        return EventPresentation("Store visit", order_detail, "store_visit", has_order_reference)
    if event_type == EventType.REFUND_COMPLETED:
        return EventPresentation(
            "Refund completed", order_detail, "refund_completed", has_order_reference
        )
    return EventPresentation("Other event", None, "other", has_order_reference)


def _has_order_reference(entity_references: Mapping[str, Any]) -> bool:
    value = entity_references.get("order_id")
    return isinstance(value, str) and bool(value.strip())


def _support_presentation(
    attributes: Mapping[str, Any], has_order_reference: bool
) -> EventPresentation:
    contact_reason = attributes.get("contact_reason")
    if contact_reason == ContactReason.REFUND_NOT_RECEIVED.value:
        return EventPresentation(
            "Support contact",
            "Refund not received",
            "support_refund_follow_up",
            has_order_reference,
        )
    if contact_reason == ContactReason.RETURN_STATUS.value:
        return EventPresentation(
            "Support contact",
            "Return-status follow-up",
            "support_return_status",
            has_order_reference,
        )
    return EventPresentation("Support contact", None, "support_contact", has_order_reference)
