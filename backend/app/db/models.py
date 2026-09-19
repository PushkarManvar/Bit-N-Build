"""Database models for Gate G1: raw_events and canonical_events.

Gate G2 adds customer_profiles, profile_identifiers, and match_decisions.
"""

import uuid
from datetime import UTC, datetime

from sqlalchemy import JSON, DateTime, Enum, ForeignKey, Integer, String, UniqueConstraint, Uuid
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.core.enums import (
    AlertSeverity,
    AlertStatus,
    AlertType,
    Channel,
    EventType,
    IdentityOutcome,
    ProcessingStatus,
)
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


class CustomerProfile(Base):
    """A resolved customer. Owns identifiers; events link to it."""

    __tablename__ = "customer_profiles"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    display_name: Mapped[str | None] = mapped_column(String(200), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_now_utc
    )
    first_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    last_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class ProfileIdentifier(Base):
    """A single normalized identifier owned by one profile.

    ``(type, value)`` is globally unique: the same normalized identifier
    always resolves to the same profile.
    """

    __tablename__ = "profile_identifiers"
    __table_args__ = (
        UniqueConstraint("type", "value", name="uq_profile_identifiers_type_value"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    profile_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("customer_profiles.id"), nullable=False, index=True
    )
    type: Mapped[str] = mapped_column(String(50), nullable=False)
    value: Mapped[str] = mapped_column(String(200), nullable=False)
    first_seen_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_now_utc
    )


class MatchDecision(Base):
    """Explainable identity decision for one canonical event."""

    __tablename__ = "match_decisions"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    canonical_event_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("canonical_events.id"), unique=True, nullable=False
    )
    profile_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("customer_profiles.id"), nullable=True
    )
    outcome: Mapped[IdentityOutcome] = mapped_column(
        Enum(IdentityOutcome, native_enum=False), nullable=False
    )
    score: Mapped[int] = mapped_column(Integer, nullable=False)
    thresholds: Mapped[dict] = mapped_column(_jsonb(), nullable=False, default=dict)
    evidence: Mapped[list[dict]] = mapped_column(_jsonb(), nullable=False, default=list)
    conflicts: Mapped[list[dict]] = mapped_column(_jsonb(), nullable=False, default=list)
    candidates: Mapped[list[dict]] = mapped_column(_jsonb(), nullable=False, default=list)
    decision_reason: Mapped[str | None] = mapped_column(String(500), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_now_utc
    )


class JourneyAlert(Base):
    """A detected journey-level problem for one profile (Gate G4).

    Open alerts are deduplicated by (profile, order, type). Dedup is enforced
    in the journey analyzer (deterministic, tested) plus a partial unique
    index for Postgres.
    """

    __tablename__ = "journey_alerts"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    profile_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("customer_profiles.id"), nullable=True, index=True
    )
    order_id: Mapped[str | None] = mapped_column(String(200), nullable=True)
    type: Mapped[AlertType] = mapped_column(
        Enum(AlertType, native_enum=False), nullable=False
    )
    severity: Mapped[AlertSeverity] = mapped_column(
        Enum(AlertSeverity, native_enum=False), nullable=False
    )
    title: Mapped[str] = mapped_column(String(300), nullable=False)
    description: Mapped[str] = mapped_column(String(1000), nullable=False)
    recommended_action: Mapped[str] = mapped_column(String(500), nullable=False)
    status: Mapped[AlertStatus] = mapped_column(
        Enum(AlertStatus, native_enum=False), nullable=False, default=AlertStatus.OPEN
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_now_utc
    )
    resolved_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )