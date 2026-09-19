"""create customer_profiles, profile_identifiers, match_decisions

Revision ID: 0002
Revises: 0001
Create Date: 2026-09-19

Gate G2 identity tables. Adds FK from canonical_events.profile_id to
customer_profiles.
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0002"
down_revision: Union[str, None] = "0001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _jsonb() -> sa.JSON:
    return sa.JSON().with_variant(postgresql.JSONB(), "postgresql")


def upgrade() -> None:
    op.create_table(
        "customer_profiles",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("display_name", sa.String(length=200), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("first_seen_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_seen_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "profile_identifiers",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("profile_id", sa.Uuid(), nullable=False),
        sa.Column("type", sa.String(length=50), nullable=False),
        sa.Column("value", sa.String(length=200), nullable=False),
        sa.Column("first_seen_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["profile_id"], ["customer_profiles.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("type", "value", name="uq_profile_identifiers_type_value"),
    )
    op.create_index(
        op.f("ix_profile_identifiers_profile_id"),
        "profile_identifiers",
        ["profile_id"],
    )
    op.create_table(
        "match_decisions",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("canonical_event_id", sa.Uuid(), nullable=False),
        sa.Column("profile_id", sa.Uuid(), nullable=True),
        sa.Column(
            "outcome",
            sa.Enum("AUTO_LINKED", "REVIEW_REQUIRED", "NEW_PROFILE", name="identity_outcome", native_enum=False),
            nullable=False,
        ),
        sa.Column("score", sa.Integer(), nullable=False),
        sa.Column("thresholds", _jsonb(), nullable=False),
        sa.Column("evidence", _jsonb(), nullable=False),
        sa.Column("conflicts", _jsonb(), nullable=False),
        sa.Column("candidates", _jsonb(), nullable=False),
        sa.Column("decision_reason", sa.String(length=500), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["canonical_event_id"], ["canonical_events.id"]),
        sa.ForeignKeyConstraint(["profile_id"], ["customer_profiles.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("canonical_event_id", name="uq_match_decisions_canonical_event_id"),
    )
    op.create_foreign_key(
        "fk_canonical_events_profile_id",
        "canonical_events",
        "customer_profiles",
        ["profile_id"],
        ["id"],
    )


def downgrade() -> None:
    op.drop_constraint("fk_canonical_events_profile_id", "canonical_events", type_="foreignkey")
    op.drop_table("match_decisions")
    op.drop_index(op.f("ix_profile_identifiers_profile_id"), table_name="profile_identifiers")
    op.drop_table("profile_identifiers")
    op.drop_table("customer_profiles")