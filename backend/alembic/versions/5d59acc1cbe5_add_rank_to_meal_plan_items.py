"""add rank to meal_plan_items

Revision ID: 5d59acc1cbe5
Revises: c7669b264db5
Create Date: 2026-04-12
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "5d59acc1cbe5"
down_revision: str | None = "c7669b264db5"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "meal_plan_items", sa.Column("rank", sa.Integer(), nullable=False, server_default="0")
    )

    # Backfill: assign sequential ranks per meal plan
    op.execute(
        """
        UPDATE meal_plan_items mpi
        SET rank = sub.rn
        FROM (
            SELECT meal_plan_id, menu_item_id,
                   ROW_NUMBER() OVER (PARTITION BY meal_plan_id ORDER BY menu_item_id) - 1 AS rn
            FROM meal_plan_items
        ) sub
        WHERE mpi.meal_plan_id = sub.meal_plan_id
          AND mpi.menu_item_id = sub.menu_item_id
        """
    )

    op.alter_column("meal_plan_items", "rank", server_default=None)


def downgrade() -> None:
    op.drop_column("meal_plan_items", "rank")
