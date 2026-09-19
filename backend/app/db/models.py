"""Database models for Gate G1: raw_events and canonical_events.

Only the tables required by Gate G1 are created here. Profiles, identifiers,
match decisions, and alerts arrive with their own gates.
"""

import uuid
from datetime import UTC, datetime

from sqlalchemy import JSON, DateTime, Enum, ForeignKey, String, UniqueConstraint, Uuid
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.core.enums import Channel, EventType, ProcessingStatus
from app.db.base import Base


def _now_utc() -> datetime:
    return datetime.now(UTC)


def _jsonb() -> JSON:
    return JSON().with_variant(JSONB, "postgresql")


class RawEvent(Base):
    """Immutable incoming evidence. Preserved before any downstream processing."""

    __tablename__ = "raw_events"
    __table_args__ = (
        UniqueConstraint(
            "channel",
            "source_event_id",
            name="uq_raw_events_channel_source_event_id",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    channel: Mapped[Channel] = mapped_column(Enum(Channel, native_enum=False), nullable=False)
    source_event_id: Mapped[str] = mapped_column(String(200), nullable=False)
    schema_version: Mapped[str] = mapped_column(String(20), nullable=False)
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    received_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_now_utc
    )
    payload: Mapped[dict] = mapped_column(_jsonb(), nullable=False)
    payload_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    processing_status: Mapped[ProcessingStatus] = mapped_column(
        Enum(ProcessingStatus, native_enum=False),
        nullable=False,
        default=ProcessingStatus.RECEIVED,
    )
    processing_error: Mapped[str | None] = mapped_column(String(500), nullable=True)


class CanonicalEvent(Base):
    """Normalized, channel-independent event record."""

    __tablename__ = "canonical_events"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    raw_event_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("raw_events.id"), unique=True, nullable=False
    )
    channel: Mapped[Channel] = mapped_column(Enum(Channel, native_enum=False), nullable=False)
    event_type: Mapped[EventType] = mapped_column(
        Enum(EventType, native_enum=False), nullable=False
    )
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    profile_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, nullable=True)
    identifiers: Mapped[list[dict]] = mapped_column(_jsonb(), nullable=False, default=list)
    entity_references: Mapped[dict] = mapped_column(_jsonb(), nullable=False, default=dict)
    attributes: Mapped[dict] = mapped_column(_jsonb(), nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_now_utc
    )