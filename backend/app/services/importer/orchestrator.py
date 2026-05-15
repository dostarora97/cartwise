from __future__ import annotations

from dataclasses import dataclass, field

from sqlalchemy.ext.asyncio import AsyncSession

from .intents import Delete, Persist, Skip
from .protocols import DataSupplier
from .read_context import ReadContext


@dataclass
class ImportResult:
    supplier_id: str
    intents_applied: dict[str, int] = field(
        default_factory=lambda: {"persist": 0, "skip": 0, "delete": 0}
    )


class ImportOrchestrator:
    def __init__(self, session: AsyncSession, read_ctx: ReadContext):
        self._session = session
        self._read_ctx = read_ctx

    async def run(self, supplier: DataSupplier) -> ImportResult:
        result = ImportResult(supplier_id=supplier.supplier_id)

        async for item in supplier.fetch():
            intents = await item.resolve_intents(self._read_ctx)
            for intent in intents:
                match intent:
                    case Persist(entity=e):
                        self._session.add(e)
                        result.intents_applied["persist"] += 1
                    case Delete(entity_type=t, id=i):
                        obj = await self._session.get(t, i)
                        if obj:
                            await self._session.delete(obj)
                        result.intents_applied["delete"] += 1
                    case Skip():
                        result.intents_applied["skip"] += 1

        await self._session.commit()
        return result
