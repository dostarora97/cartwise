from __future__ import annotations

from collections.abc import AsyncIterator
from itertools import count
from uuid import UUID

from ..client import SupplierClient
from ..items import MenuItemImportItem


class ConnectorSupplier:
    def __init__(
        self,
        supplier_id: str,
        client: SupplierClient,
        user_id: UUID,
        meal_plan_id: UUID | None,
        rank_counter: count,
    ):
        self._supplier_id = supplier_id
        self._client = client
        self._user_id = user_id
        self._meal_plan_id = meal_plan_id
        self._rank_counter = rank_counter

    @property
    def supplier_id(self) -> str:
        return self._supplier_id

    async def fetch(self) -> AsyncIterator[MenuItemImportItem]:
        items = await self._client.import_items()
        for entry in items:
            yield MenuItemImportItem(
                name=entry.name,
                body=entry.body,
                intents_declared=entry.intents,
                user_id=self._user_id,
                meal_plan_id=self._meal_plan_id,
                rank_counter=self._rank_counter,
            )
