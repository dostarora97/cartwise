"""Tests for Supabase Vault service (app/services/vault.py).

Uses a fake vault schema (no pgsodium encryption) to test the actual SQL
queries that store_secret, get_secret, and delete_secret execute.
"""

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.vault import delete_secret, get_secret, store_secret

_VAULT_STATEMENTS = [
    "CREATE SCHEMA IF NOT EXISTS vault",
    """CREATE TABLE IF NOT EXISTS vault.secrets (
        id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
        name TEXT UNIQUE NOT NULL,
        secret TEXT,
        description TEXT DEFAULT ''
    )""",
    """CREATE OR REPLACE VIEW vault.decrypted_secrets AS
        SELECT id, name, secret AS decrypted_secret FROM vault.secrets""",
    """CREATE OR REPLACE FUNCTION vault.create_secret(secret TEXT, name TEXT, description TEXT DEFAULT '')
    RETURNS UUID LANGUAGE sql AS $$
        INSERT INTO vault.secrets(secret, name, description) VALUES ($1, $2, $3) RETURNING id
    $$""",
    """CREATE OR REPLACE FUNCTION vault.update_secret(secret_id UUID, new_secret TEXT)
    RETURNS VOID LANGUAGE sql AS $$
        UPDATE vault.secrets SET secret = $2 WHERE id = $1
    $$""",
]


@pytest.fixture(autouse=True)
async def vault_schema(session: AsyncSession):
    """Create fake vault schema before each test in this module."""
    for stmt in _VAULT_STATEMENTS:
        await session.execute(text(stmt))
    await session.commit()
    yield
    await session.execute(text("DROP SCHEMA IF EXISTS vault CASCADE"))
    await session.commit()


async def test_store_and_get_secret(session: AsyncSession):
    """store_secret inserts, get_secret retrieves."""
    await store_secret(session, "my_key", "my_value", "test description")
    await session.commit()

    result = await get_secret(session, "my_key")
    assert result == "my_value"


async def test_update_existing_secret(session: AsyncSession):
    """Calling store_secret with same name updates the value."""
    await store_secret(session, "token:user1", "original", "first store")
    await session.commit()

    await store_secret(session, "token:user1", "updated", "second store")
    await session.commit()

    result = await get_secret(session, "token:user1")
    assert result == "updated"


async def test_get_nonexistent_returns_none(session: AsyncSession):
    """get_secret returns None for unknown key."""
    result = await get_secret(session, "does_not_exist")
    assert result is None


async def test_delete_secret(session: AsyncSession):
    """delete_secret removes the row."""
    await store_secret(session, "to_delete", "value", "will be deleted")
    await session.commit()

    await delete_secret(session, "to_delete")
    await session.commit()

    result = await get_secret(session, "to_delete")
    assert result is None
