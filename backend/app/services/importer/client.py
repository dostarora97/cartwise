from __future__ import annotations

import httpx
from fastapi import HTTPException
from pydantic import BaseModel


class RawImportEntry(BaseModel):
    name: str
    body: str
    intents: list[str] = []


class PreviewItem(BaseModel):
    name: str


class PreviewResponse(BaseModel):
    name: str
    items: list[PreviewItem]
    total: int


class SupplierClient:
    def __init__(self, url: str, payload: str, internal_secret: str | None = None):
        self._url = url
        self._payload = payload
        self._secret = internal_secret

    async def preview(self) -> PreviewResponse:
        data = await self._post("preview")
        return PreviewResponse.model_validate(data)

    async def import_items(self) -> list[RawImportEntry]:
        data = await self._post("import")
        items = data.get("items", [])
        return [RawImportEntry.model_validate(item) for item in items]

    async def _post(self, action: str) -> dict:
        headers: dict[str, str] = {}
        if self._secret:
            headers["X-Internal-Secret"] = self._secret

        async with httpx.AsyncClient() as client:
            try:
                resp = await client.post(
                    self._url,
                    json={"action": action, "payload": self._payload},
                    headers=headers,
                )
                resp.raise_for_status()
            except httpx.HTTPError:
                raise HTTPException(502, "Supplier unavailable") from None
        return resp.json()
