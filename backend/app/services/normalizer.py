"""Channel normalizers: source envelope -> canonical, channel-independent fields.

The event envelope (docs/05_API_CONTRACT.md) is uniform across channels;
channels differ in which identifiers they expose and in value formatting.
Each channel has an adapter declaring its identifier normalizers. Only the
``web`` adapter is implemented for Gate G1.

Normalization is pure and deterministic.
"""

import re
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

from app.core.enums import Channel, EventType
from app.core.errors import NormalizationError
from app.schemas.events import EventIngestionRequest, IdentifierRef

SUPPORTED_SCHEMA_VERSIONS: frozenset[str] = frozenset({"1.0"})


@dataclass(frozen=True)
class NormalizedEvent:
    channel: Channel
    event_type: EventType
    occurred_at: datetime
    identifiers: list[dict[str, str]] = field(default_factory=list)
    entity_references: dict[str, Any] = field(default_factory=dict)
    attributes: dict[str, Any] = field(default_factory=dict)


def normalize_email(value: str) -> str:
    return value.strip().lower()


def normalize_phone(value: str) -> str:
    digits = re.sub(r"\D", "", value)
    if len(digits) == 10:
        return f"+91{digits}"
    if len(digits) == 12 and digits.startswith("91"):
        return f"+{digits}"
    return f"+{digits}" if digits else ""


def normalize_device_id(value: str) -> str:
    return value.strip().upper()


def normalize_session_id(value: str) -> str:
    return value.strip()


def normalize_customer_id(value: str) -> str:
    return value.strip().upper()


def normalize_order_id(value: str) -> str:
    normalized = re.sub(r"[\s_]+", "-", value.strip().upper())
    normalized = re.sub(r"-+", "-", normalized)
    return normalized


_IDENTIFIER_NORMALIZERS: dict[str, Callable[[str], str]] = {
    "email": normalize_email,
    "phone": normalize_phone,
    "device_id": normalize_device_id,
    "session_id": normalize_session_id,
    "customer_id": normalize_customer_id,
}


class ChannelAdapter:
    """Declares how one channel normalizes identifiers and references."""

    def __init__(
        self,
        *,
        identifier_types: set[str],
        reference_normalizers: dict[str, Callable[[str], str]],
    ) -> None:
        self.identifier_types = identifier_types
        self.reference_normalizers = reference_normalizers

    def normalize_identifier(self, ref: IdentifierRef) -> dict[str, str]:
        normalizer = _IDENTIFIER_NORMALIZERS.get(ref.type)
        value = normalizer(ref.value) if normalizer else ref.value.strip()
        return {"type": ref.type, "value": value}

    def normalize_references(self, refs: dict[str, Any]) -> dict[str, Any]:
        normalized: dict[str, Any] = {}
        for key, value in refs.items():
            if value is None:
                normalized[key] = None
            elif key in self.reference_normalizers:
                normalized[key] = self.reference_normalizers[key](str(value))
            else:
                normalized[key] = str(value).strip()
        return normalized


WEB_ADAPTER = ChannelAdapter(
    identifier_types={"email", "phone", "device_id", "session_id", "customer_id"},
    reference_normalizers={"order_id": normalize_order_id},
)

CHANNEL_ADAPTERS: dict[Channel, ChannelAdapter] = {
    Channel.WEB: WEB_ADAPTER,
}


def normalize_for_channel(envelope: EventIngestionRequest) -> NormalizedEvent:
    """Normalize a validated envelope for its channel.

    Raises NormalizationError if the channel adapter is unavailable or the
    schema version is unsupported. The caller is responsible for persisting
    the raw event before invoking this function.
    """
    adapter = CHANNEL_ADAPTERS.get(envelope.channel)
    if adapter is None:
        raise NormalizationError(
            message=f"No normalizer implemented for channel '{envelope.channel.value}'.",
            raw_event_id="",
            channel=envelope.channel.value,
            details={"channel": envelope.channel.value},
        )
    if envelope.schema_version not in SUPPORTED_SCHEMA_VERSIONS:
        raise NormalizationError(
            message=f"Unsupported schema version '{envelope.schema_version}'.",
            raw_event_id="",
            channel=envelope.channel.value,
            details={"schema_version": envelope.schema_version},
        )

    occurred_at = envelope.occurred_at
    if occurred_at.tzinfo is None:
        occurred_at = occurred_at.replace(tzinfo=UTC)
    else:
        occurred_at = occurred_at.astimezone(UTC)

    identifiers = [adapter.normalize_identifier(ref) for ref in envelope.identifiers]

    return NormalizedEvent(
        channel=envelope.channel,
        event_type=envelope.event_type,
        occurred_at=occurred_at,
        identifiers=identifiers,
        entity_references=adapter.normalize_references(envelope.entity_references),
        attributes=dict(envelope.attributes),
    )