"""Initial schema: personnel, weeks, duty_assignments.

Revision ID: 0001
Revises:
Create Date: 2026-08-06

"""
from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "personnel",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(length=100), nullable=False, unique=True),
        sa.Column("has_phone", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("remarks", sa.String(length=500), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_personnel_name", "personnel", ["name"])

    op.create_table(
        "weeks",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("week_number", sa.Integer(), nullable=False, unique=True),
        sa.Column("generated_date", sa.Date(), nullable=False),
        sa.Column("published", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_weeks_week_number", "weeks", ["week_number"])

    op.create_table(
        "duty_assignments",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "week_id",
            sa.Integer(),
            sa.ForeignKey("weeks.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("category", sa.String(length=32), nullable=False),
        sa.Column("meal", sa.String(length=16), nullable=False),
        sa.Column(
            "person_id",
            sa.Integer(),
            sa.ForeignKey("personnel.id", ondelete="CASCADE"),
            nullable=False,
        ),
    )
    op.create_index("ix_duty_assignments_week_id", "duty_assignments", ["week_id"])
    op.create_index("ix_duty_assignments_person_id", "duty_assignments", ["person_id"])


def downgrade() -> None:
    op.drop_index("ix_duty_assignments_person_id", table_name="duty_assignments")
    op.drop_index("ix_duty_assignments_week_id", table_name="duty_assignments")
    op.drop_table("duty_assignments")

    op.drop_index("ix_weeks_week_number", table_name="weeks")
    op.drop_table("weeks")

    op.drop_index("ix_personnel_name", table_name="personnel")
    op.drop_table("personnel")
