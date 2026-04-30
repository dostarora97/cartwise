"""add cascade delete on user fks

Revision ID: 3df8ef3688f7
Revises: b2c3d4e5f6a7
Create Date: 2026-05-01 02:56:40.076120

"""

from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "3df8ef3688f7"
down_revision: Union[str, Sequence[str], None] = "b2c3d4e5f6a7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add ON DELETE CASCADE to all foreign keys referencing users.id."""
    fks = [
        ("meal_plans", "meal_plans_user_id_fkey", "user_id"),
        ("menu_items", "menu_items_created_by_fkey", "created_by"),
        ("menu_items", "menu_items_updated_by_fkey", "updated_by"),
        ("order_participants", "order_participants_user_id_fkey", "user_id"),
        ("orders", "orders_paid_by_fkey", "paid_by"),
    ]
    for table, constraint, column in fks:
        op.drop_constraint(constraint, table, type_="foreignkey")
        op.create_foreign_key(constraint, table, "users", [column], ["id"], ondelete="CASCADE")


def downgrade() -> None:
    """Remove ON DELETE CASCADE (revert to default RESTRICT)."""
    fks = [
        ("meal_plans", "meal_plans_user_id_fkey", "user_id"),
        ("menu_items", "menu_items_created_by_fkey", "created_by"),
        ("menu_items", "menu_items_updated_by_fkey", "updated_by"),
        ("order_participants", "order_participants_user_id_fkey", "user_id"),
        ("orders", "orders_paid_by_fkey", "paid_by"),
    ]
    for table, constraint, column in fks:
        op.drop_constraint(constraint, table, type_="foreignkey")
        op.create_foreign_key(constraint, table, "users", [column], ["id"])
