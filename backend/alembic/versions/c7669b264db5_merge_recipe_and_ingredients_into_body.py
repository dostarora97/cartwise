"""merge recipe and ingredients into body

Revision ID: c7669b264db5
Revises: ed05092115ff
Create Date: 2026-04-12
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "c7669b264db5"
down_revision: str | None = "ed05092115ff"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Add body column with a temporary default
    op.add_column("menu_items", sa.Column("body", sa.Text(), nullable=False, server_default=""))

    # Backfill: merge recipe + ingredients into body
    op.execute("UPDATE menu_items SET body = recipe || E'\\n\\n' || ingredients")

    # Remove the server default now that data is backfilled
    op.alter_column("menu_items", "body", server_default=None)

    # Drop old columns
    op.drop_column("menu_items", "recipe")
    op.drop_column("menu_items", "ingredients")


def downgrade() -> None:
    # Re-add old columns
    op.add_column("menu_items", sa.Column("recipe", sa.Text(), nullable=False, server_default=""))
    op.add_column(
        "menu_items", sa.Column("ingredients", sa.Text(), nullable=False, server_default="")
    )

    # Best-effort split: put everything in recipe, leave ingredients empty
    op.execute("UPDATE menu_items SET recipe = body, ingredients = ''")

    # Remove server defaults
    op.alter_column("menu_items", "recipe", server_default=None)
    op.alter_column("menu_items", "ingredients", server_default=None)

    # Drop body
    op.drop_column("menu_items", "body")
