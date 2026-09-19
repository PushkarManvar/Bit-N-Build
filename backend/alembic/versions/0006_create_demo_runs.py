"""create demo_runs table

Revision ID: 0006
Revises: 0005
Create Date: 2026-09-19

Gate G7 deterministic demo playback state.
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0006"
down_revision: Union[str, None] = "0005"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "demo_runs",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("run_id", sa.String(length=100), nullable=False),
        sa.Column("scenario", sa.String(length=100), nullable=False),
        sa.Column("total_steps", sa.Integer(), nullable=False),
        sa.Column("interval_seconds", sa.Float(), nullable=False),
        sa.Column(
            "status",
            sa.Enum("RUNNING", "COMPLETED", "FAILED", name="demo_run_status", native_enum=False),
            nullable=False,
        ),
        sa.Column("current_step", sa.Integer(), nullable=False),
        sa.Column("last_event_id", sa.String(length=100), nullable=True),
        sa.Column("error", sa.String(length=500), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("run_id", name="uq_demo_runs_run_id"),
    )


def downgrade() -> None:
    op.drop_table("demo_runs")