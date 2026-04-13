"""create splits table

Revision ID: 048ccd693969
Revises: e37c2a1db4ce
Create Date: 2026-04-12
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "048ccd693969"
down_revision: str | None = "e37c2a1db4ce"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "splits",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("order_id", sa.UUID(), nullable=False),
        sa.Column("amount", sa.Numeric(precision=10, scale=2), nullable=False),
        sa.Column("grocery_items", sa.dialects.postgresql.JSONB(), nullable=False),
        sa.Column("member_ids", sa.dialects.postgresql.JSONB(), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="pending"),
        sa.Column("splitwise_expense_id", sa.BigInteger(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["order_id"], ["orders.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_splits_order_id", "splits", ["order_id"])


def downgrade() -> None:
    op.drop_index("ix_splits_order_id", table_name="splits")
    op.drop_table("splits")
