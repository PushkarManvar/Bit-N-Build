"""create raw_events and canonical_events tables

Revision ID: 0001
Revises:
Create Date: 2026-09-19

Gate G1 tables only. Profiles, identifiers, match decisions, and alerts
arrive with later gates.
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _jsonb() -> sa.JSON:
    return sa.JSON().with_variant(postgresql.JSONB(), "postgresql")


def upgrade() -> None:
    op.create_table(
        "raw_events",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column(
            "channel",
            sa.Enum("WEB", "MOBILE_APP", "CALL_CENTER", "PHYSICAL_STORE", name="channel", native_enum=False),
            nullable=False,
        ),
        sa.Column("source_event_id", sa.String(length=200), nullable=False),
        sa.Column("schema_version", sa.String(length=20), nullable=False),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("received_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("payload", _jsonb(), nullable=False),
        sa.Column("payload_hash", sa.String(length=64), nullable=False),
        sa.Column(
            "processing_status",
            sa.Enum("RECEIVED", "NORMALIZED", "FAILED", name="processing_status", native_enum=False),
            nullable=False,
        ),
        sa.Column("processing_error", sa.String(length=500), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "channel", "source_event_id", name="uq_raw_events_channel_source_event_id"
        ),
    )
    op.create_table(
        "canonical_events",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("raw_event_id", sa.Uuid(), nullable=False),
        sa.Column(
            "channel",
            sa.Enum("WEB", "MOBILE_APP", "CALL_CENTER", "PHYSICAL_STORE", name="channel", native_enum=False),
            nullable=False,
        ),
        sa.Column(
            "event_type",
            sa.Enum(
                "PRODUCT_VIEWED",
                "APP_LOGIN",
                "ORDER_PLACED",
                "RETURN_REQUESTED",
                "SUPPORT_CONTACTED",
                "STORE_VISITED",
                "REFUND_COMPLETED",
                name="event_type",
                native_enum=False,
            ),
            nullable=False,
        ),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("profile_id", sa.Uuid(), nullable=True),
        sa.Column("identifiers", _jsonb(), nullable=False),
        sa.Column("entity_references", _jsonb(), nullable=False),
        sa.Column("attributes", _jsonb(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["raw_event_id"], ["raw_events.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("raw_event_id", name="uq_canonical_events_raw_event_id"),
    )


def downgrade() -> None:
    op.drop_table("canonical_events")
    op.drop_table("raw_events")