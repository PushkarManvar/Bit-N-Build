"""create review_actions table and add review_status to match_decisions

Revision ID: 0004
Revises: 0003
Create Date: 2026-09-19

Gate G5 human review: append-only audit trail + review state on decisions.
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0004"
down_revision: Union[str, None] = "0003"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "match_decisions",
        sa.Column(
            "review_status",
            sa.Enum("PENDING", "APPROVED", "REJECTED", "PROFILE_CREATED", name="review_status", native_enum=False),
            nullable=True,
        ),
    )
    op.create_table(
        "review_actions",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("match_decision_id", sa.Uuid(), nullable=False),
        sa.Column(
            "action",
            sa.Enum("APPROVE_LINK", "REJECT_LINK", "CREATE_PROFILE", name="review_decision", native_enum=False),
            nullable=False,
        ),
        sa.Column("selected_profile_id", sa.Uuid(), nullable=True),
        sa.Column("reviewer_name", sa.String(length=200), nullable=False),
        sa.Column("note", sa.String(length=500), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["match_decision_id"], ["match_decisions.id"]),
        sa.ForeignKeyConstraint(["selected_profile_id"], ["customer_profiles.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_review_actions_match_decision_id"),
        "review_actions",
        ["match_decision_id"],
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_review_actions_match_decision_id"), table_name="review_actions")
    op.drop_table("review_actions")
    op.drop_column("match_decisions", "review_status")