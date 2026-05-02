"""add order_sources table and swiggy columns

Revision ID: 4a5b6c7d8e9f
Revises: 3df8ef3688f7
Create Date: 2026-05-02 12:00:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "4a5b6c7d8e9f"
down_revision: Union[str, Sequence[str], None] = "3df8ef3688f7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create enum type using raw SQL (checkfirst doesn't work reliably with asyncpg)
    op.execute(
        "DO $$ BEGIN "
        "CREATE TYPE order_source_type AS ENUM ('invoice', 'swiggy_order'); "
        "EXCEPTION WHEN duplicate_object THEN NULL; "
        "END $$"
    )

    # Create order_sources table
    op.create_table(
        "order_sources",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column(
            "type",
            postgresql.ENUM("invoice", "swiggy_order", name="order_source_type", create_type=False),
            nullable=False,
        ),
        sa.Column("raw_data", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("items", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("created_by", sa.UUID(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )

    # Add source_id column to orders (nullable initially for data migration)
    op.add_column("orders", sa.Column("source_id", sa.UUID(), nullable=True))

    # Data migration: create source rows for existing orders
    conn = op.get_bind()
    orders = conn.execute(
        sa.text("SELECT id, paid_by, invoice_filename, created_at FROM orders")
    ).fetchall()

    for order in orders:
        source_id = conn.execute(
            sa.text(
                "INSERT INTO order_sources (id, type, raw_data, created_by, created_at) "
                "VALUES (gen_random_uuid(), 'invoice', "
                "jsonb_build_object('invoice_filename', :filename), :created_by, :created_at) "
                "RETURNING id"
            ),
            {
                "filename": order.invoice_filename,
                "created_by": order.paid_by,
                "created_at": order.created_at,
            },
        ).scalar_one()

        conn.execute(
            sa.text("UPDATE orders SET source_id = :source_id WHERE id = :order_id"),
            {"source_id": source_id, "order_id": order.id},
        )

    # Add unique constraint and FK on source_id
    op.create_unique_constraint("uq_orders_source_id", "orders", ["source_id"])
    op.create_foreign_key(
        "fk_orders_source_id",
        "orders",
        "order_sources",
        ["source_id"],
        ["id"],
        ondelete="SET NULL",
    )

    # Drop invoice_filename
    op.drop_column("orders", "invoice_filename")

    # Add swiggy columns to users
    op.add_column("users", sa.Column("swiggy_user_id", sa.String(length=50), nullable=True))
    op.add_column(
        "users", sa.Column("swiggy_connected_at", sa.DateTime(timezone=True), nullable=True)
    )


def downgrade() -> None:
    # Remove swiggy columns from users
    op.drop_column("users", "swiggy_connected_at")
    op.drop_column("users", "swiggy_user_id")

    # Re-add invoice_filename with a default for existing rows
    op.add_column(
        "orders",
        sa.Column(
            "invoice_filename",
            sa.String(length=500),
            nullable=False,
            server_default="unknown.pdf",
        ),
    )

    # Restore filenames from order_sources.raw_data
    conn = op.get_bind()
    conn.execute(
        sa.text(
            "UPDATE orders o SET invoice_filename = "
            "COALESCE((SELECT os.raw_data->>'invoice_filename' FROM order_sources os WHERE os.id = o.source_id), 'unknown.pdf')"
        )
    )

    # Remove the server default now that data is populated
    op.alter_column("orders", "invoice_filename", server_default=None)

    # Drop source_id FK and column
    op.drop_constraint("fk_orders_source_id", "orders", type_="foreignkey")
    op.drop_constraint("uq_orders_source_id", "orders", type_="unique")
    op.drop_column("orders", "source_id")

    # Drop order_sources table and enum
    op.drop_table("order_sources")
    postgresql.ENUM(name="order_source_type").drop(op.get_bind(), checkfirst=True)
