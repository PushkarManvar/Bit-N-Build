"""create journey_alerts table

Revision ID: 0003
Revises: 0002
Create Date: 2026-09-19

Gate G4 journey alerts. Open-alert dedup enforced via partial unique index
(Postgres) and in the analyzer (SQLite tests).
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0003"
down_revision: Union[str, None] = "0002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "journey_alerts",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("profile_id", sa.Uuid(), nullable=True),
        sa.Column("order_id", sa.String(length=200), nullable=True),
        sa.Column(
            "type",
            sa.Enum("UNRESOLVED_REFUND", "REPEAT_CONTACT", name="alert_type", native_enum=False),
            nullable=False,
        ),
        sa.Column(
            "severity",
            sa.Enum("LOW", "MEDIUM", "HIGH", "CRITICAL", name="alert_severity", native_enum=False),
            nullable=False,
        ),
        sa.Column("title", sa.String(length=300), nullable=False),
        sa.Column("description", sa.String(length=1000), nullable=False),
        sa.Column("recommended_action", sa.String(length=500), nullable=False),
        sa.Column(
            "status",
            sa.Enum("OPEN", "RESOLVED", name="alert_status", native_enum=False),
            nullable=False,
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["profile_id"], ["customer_profiles.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_journey_alerts_profile_id"),
        "journey_alerts",
        ["profile_id"],
    )
    op.execute(
        "CREATE UNIQUE INDEX uq_journey_alerts_open_profile_order_type "
        "ON journey_alerts (profile_id, order_id, type) WHERE status = 'open'"
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS uq_journey_alerts_open_profile_order_type")
    op.drop_index(op.f("ix_journey_alerts_profile_id"), table_name="journey_alerts")
    op.drop_table("journey_alerts")