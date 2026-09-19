from datetime import UTC, datetime

from app.schemas.events import EventIngestionRequest
from app.services.normalizer import normalize_event, normalize_order_id, normalize_phone


def test_phone_normalization() -> None:
    assert normalize_phone("98765 43210") == "+919876543210"
    assert normalize_phone("+91-98765-43210") == "+919876543210"


def test_order_normalization() -> None:
    assert normalize_order_id("ord 204") == "ORD-204"
    assert normalize_order_id("ord_204") == "ORD-204"


def test_mobile_event_normalization() -> None:
    event = EventIngestionRequest(
        source="mobile_app",
        source_record_id="APP-001",
        occurred_at=datetime(2026, 9, 19, 9, 15, tzinfo=UTC),
        payload={
            "action": "refund_pending",
            "email_address": " RIYA.SHAH@EXAMPLE.COM ",
            "device": "DEV-17",
            "orderNumber": "ord 204",
            "customerName": "Riya  Shah",
        },
    )

    canonical = normalize_event(event)

    assert canonical.event_type == "refund_status_checked"
    assert canonical.email == "riya.shah@example.com"
    assert canonical.device_id == "DEV-17"
    assert canonical.order_id == "ORD-204"
    assert canonical.customer_name == "Riya Shah"
