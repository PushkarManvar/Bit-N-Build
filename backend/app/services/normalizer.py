import re
from collections.abc import Mapping
from typing import Any

from app.schemas.events import CanonicalEvent, EventIngestionRequest

EVENT_TYPE_MAP = {
    "return_initiated": "return_started",
    "return_request": "return_requested",
    "return_requested": "return_requested",
    "refund_pending": "refund_status_checked",
    "refund_not_received": "support_call",
    "customer_call": "support_call",
    "order_confirmed": "order_placed",
    "checkout_begin": "checkout_started",
}

SOURCE_FIELDS: dict[str, dict[str, tuple[str, ...]]] = {
    "web": {
        "event_type": ("event", "type"),
        "device_id": ("deviceId",),
        "session_id": ("sessionId",),
        "order_id": ("order_id",),
        "customer_id": ("customer_id",),
    },
    "mobile_app": {
        "event_type": ("action",),
        "email": ("email_address", "userEmail"),
        "device_id": ("device",),
        "order_id": ("orderNumber",),
        "customer_name": ("customerName",),
        "customer_id": ("customer_id",),
    },
    "call_centre": {
        "event_type": ("reason",),
        "email": ("caller_email",),
        "phone": ("caller_phone",),
        "order_id": ("order_ref",),
        "customer_name": ("caller_name",),
        "issue_id": ("ticket_id",),
        "city": ("city",),
    },
    "physical_store": {
        "event_type": ("activity",),
        "phone": ("phoneNumber",),
        "order_id": ("return_order",),
        "customer_name": ("customer",),
        "issue_id": ("rma_id",),
        "city": ("store_city",),
    },
}


def first_value(payload: Mapping[str, Any], keys: tuple[str, ...]) -> Any | None:
    for key in keys:
        value = payload.get(key)
        if value not in (None, ""):
            return value
    return None


def normalize_email(value: Any | None) -> str | None:
    if value is None:
        return None
    normalized = str(value).strip().lower()
    return normalized if "@" in normalized else None


def normalize_phone(value: Any | None) -> str | None:
    if value is None:
        return None
    digits = re.sub(r"\D", "", str(value))
    if len(digits) == 10:
        return f"+91{digits}"
    if len(digits) == 12 and digits.startswith("91"):
        return f"+{digits}"
    return f"+{digits}" if digits else None


def normalize_order_id(value: Any | None) -> str | None:
    if value is None:
        return None
    normalized = re.sub(r"[\s_]+", "-", str(value).strip().upper())
    normalized = re.sub(r"-+", "-", normalized)
    return normalized or None


def normalize_name(value: Any | None) -> str | None:
    if value is None:
        return None
    normalized = " ".join(str(value).strip().split())
    return normalized or None


def normalize_event_type(value: Any | None) -> str:
    if value is None:
        return "other"
    raw_value = str(value).strip().lower()
    return EVENT_TYPE_MAP.get(raw_value, raw_value or "other")


def normalize_event(event: EventIngestionRequest) -> CanonicalEvent:
    mapping = SOURCE_FIELDS[event.source]
    payload = event.payload

    consumed_keys = {key for keys in mapping.values() for key in keys}
    attributes = {key: value for key, value in payload.items() if key not in consumed_keys}

    return CanonicalEvent(
        channel=event.source,
        event_type=normalize_event_type(first_value(payload, mapping["event_type"])),
        occurred_at=event.occurred_at,
        email=normalize_email(first_value(payload, mapping.get("email", ()))),
        phone=normalize_phone(first_value(payload, mapping.get("phone", ()))),
        device_id=first_value(payload, mapping.get("device_id", ())),
        session_id=first_value(payload, mapping.get("session_id", ())),
        customer_id=first_value(payload, mapping.get("customer_id", ())),
        order_id=normalize_order_id(first_value(payload, mapping.get("order_id", ()))),
        issue_id=first_value(payload, mapping.get("issue_id", ())),
        customer_name=normalize_name(first_value(payload, mapping.get("customer_name", ()))),
        city=normalize_name(first_value(payload, mapping.get("city", ()))),
        attributes=attributes,
    )
