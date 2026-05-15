from __future__ import annotations

import asyncio
import json
from collections.abc import AsyncIterator
from itertools import count
from pathlib import Path
from uuid import UUID

import httpx
from pydantic import BaseModel, TypeAdapter

from ..items import MenuItemImportItem


class RawImportEntry(BaseModel):
    name: str
    body: str
    intents: list[str] = []


_entries_adapter = TypeAdapter(list[RawImportEntry])


class StaticJsonSupplier:
    def __init__(
        self,
        supplier_id: str,
        url: str,
        user_id: UUID,
        meal_plan_id: UUID | None,
        rank_counter: count,
    ):
        self._supplier_id = supplier_id
        self._url = url
        self._user_id = user_id
        self._meal_plan_id = meal_plan_id
        self._rank_counter = rank_counter

    @property
    def supplier_id(self) -> str:
        return self._supplier_id

    async def fetch(self) -> AsyncIterator[MenuItemImportItem]:
        raw_json = await self._fetch_json()
        entries = _entries_adapter.validate_python(raw_json)
        for entry in entries:
            yield MenuItemImportItem(
                name=entry.name,
                body=entry.body,
                intents_declared=entry.intents,
                user_id=self._user_id,
                meal_plan_id=self._meal_plan_id,
                rank_counter=self._rank_counter,
            )

    async def _fetch_json(self) -> list[dict]:
        if self._url.startswith("file://"):
            path = Path(self._url.removeprefix("file://"))
            content = await asyncio.to_thread(path.read_text)
            return json.loads(content)
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.get(self._url)
            resp.raise_for_status()
            return resp.json()
