from datetime import UTC, datetime

import pytest

from app.core.enums import Channel, EventType
from app.core.errors import NormalizationError
from app.schemas.events import EventIngestionRequest
from app.services.normalizer import (
    normalize_device_id,
    normalize_email,
    normalize_for_channel,
    normalize_order_id,
    normalize_phone,
)


def _web_event(
    *,
    source_event_id: str = "WEB-001",
    occurred_at: str = "2026-09-19T08:30:00Z",
    schema_version: str = "1.0",
    identifiers: list[dict] | None = None,
    entity_references: dict | None = None,
) -> EventIngestionRequest:
    return EventIngestionRequest(
        source_event_id=source_event_id,
        channel=Channel.WEB,
        event_type=EventType.PRODUCT_VIEWED,
        occurred_at=datetime.fromisoformat(occurred_at.replace("Z", "+00:00")),
        schema_version=schema_version,
        identifiers=identifiers or [],
        entity_references=entity_references or {},
        attributes={},
    )


def test_normalize_email() -> None:
    assert normalize_email("  RIYA.SHAH@EXAMPLE.COM ") == "riya.shah@example.com"


def test_normalize_device_id() -> None:
    assert normalize_device_id(" dev-17 ") == "DEV-17"


def test_normalize_order_id() -> None:
    assert normalize_order_id("ord 204") == "ORD-204"
    assert normalize_order_id("ord_204") == "ORD-204"


def test_normalize_phone() -> None:
    assert normalize_phone("98765 43210") == "+919876543210"
    assert normalize_phone("+91-98765-43210") == "+919876543210"


def test_web_event_normalization() -> None:
    event = _web_event(
        identifiers=[
            {"type": "email", "value": "RIYA.SHAH@EXAMPLE.COM"},
            {"type": "device_id", "value": " dev-17 "},
            {"type": "session_id", "value": " sess-1001 "},
        ],
        entity_references={"order_id": "ord 204"},
    )
    normalized = normalize_for_channel(event)

    assert normalized.channel == Channel.WEB
    assert normalized.event_type == EventType.PRODUCT_VIEWED
    assert normalized.occurred_at.tzinfo is not None
    assert normalized.identifiers == [
        {"type": "email", "value": "riya.shah@example.com"},
        {"type": "device_id", "value": "DEV-17"},
        {"type": "session_id", "value": "sess-1001"},
    ]
    assert normalized.entity_references == {"order_id": "ORD-204"}


def test_naive_timestamp_normalized_to_utc() -> None:
    event = _web_event()
    event.occurred_at = datetime(2026, 9, 19, 8, 30)
    normalized = normalize_for_channel(event)
    assert normalized.occurred_at.tzinfo is UTC


def test_unsupported_schema_version_raises() -> None:
    event = _web_event(schema_version="9.9")
    with pytest.raises(NormalizationError):
        normalize_for_channel(event)


def test_unsupported_channel_raises() -> None:
    event = _web_event()
    event.channel = Channel.PHYSICAL_STORE
    with pytest.raises(NormalizationError):
        normalize_for_channel(event)