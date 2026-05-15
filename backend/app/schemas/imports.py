from pydantic import BaseModel


class PreviewItem(BaseModel):
    name: str


class PreviewResponse(BaseModel):
    name: str
    items: list[PreviewItem]
    total: int


class ImportRequest(BaseModel):
    supplier_id: str


class ImportResultResponse(BaseModel):
    supplier_id: str
    intents_applied: dict[str, int]
