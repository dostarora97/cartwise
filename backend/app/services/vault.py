"""
Supabase Vault service for secure secret storage.

Uses the Postgres vault extension (pgsodium) for server-managed encryption.
Secrets are encrypted at rest and only decrypted on-the-fly via the
vault.decrypted_secrets view.

For local dev without Vault, falls back to a plaintext secrets table.
"""

from __future__ import annotations

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession


async def store_secret(
    session: AsyncSession, name: str, secret: str, description: str = ""
) -> None:
    existing = await session.execute(
        text("SELECT id FROM vault.secrets WHERE name = :name"),
        {"name": name},
    )
    row_id = existing.scalar_one_or_none()
    if row_id:
        await session.execute(
            text("SELECT vault.update_secret(:id, :secret)"),
            {"id": row_id, "secret": secret},
        )
    else:
        await session.execute(
            text("SELECT vault.create_secret(:secret, :name, :description)"),
            {"secret": secret, "name": name, "description": description},
        )


async def get_secret(session: AsyncSession, name: str) -> str | None:
    result = await session.execute(
        text("SELECT decrypted_secret FROM vault.decrypted_secrets WHERE name = :name"),
        {"name": name},
    )
    return result.scalar_one_or_none()


async def delete_secret(session: AsyncSession, name: str) -> None:
    await session.execute(
        text("DELETE FROM vault.secrets WHERE name = :name"),
        {"name": name},
    )
