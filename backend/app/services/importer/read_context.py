from __future__ import annotations

from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession


class ReadContext:
    def __init__(self, session: AsyncSession):
        self._session = session

    async def find_by_id(self, entity_type: type, id: Any) -> Any | None:
        return await self._session.get(entity_type, id)

    async def find_by(self, entity_type: type, **filters: Any) -> list[Any]:
        stmt = select(entity_type).filter_by(**filters)
        result = await self._session.execute(stmt)
        return list(result.scalars().all())
