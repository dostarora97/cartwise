from __future__ import annotations

from collections.abc import AsyncIterator
from typing import Any, Protocol

from .intents import DbIntent


class ReadContext(Protocol):
    async def find_by_id(self, entity_type: type, id: Any) -> Any | None: ...
    async def find_by(self, entity_type: type, **filters: Any) -> list[Any]: ...


class ImportItem(Protocol):
    async def resolve_intents(self, ctx: ReadContext) -> list[DbIntent]: ...


class DataSupplier(Protocol):
    @property
    def supplier_id(self) -> str: ...
    async def fetch(self) -> AsyncIterator[ImportItem]: ...
