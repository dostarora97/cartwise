"""add splitwise_user_id to users

Revision ID: e37c2a1db4ce
Revises: 5d59acc1cbe5
Create Date: 2026-04-12
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "e37c2a1db4ce"
down_revision: str | None = "5d59acc1cbe5"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("users", sa.Column("splitwise_user_id", sa.Integer(), nullable=True))


def downgrade() -> None:
    op.drop_column("users", "splitwise_user_id")
