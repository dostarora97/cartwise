from pydantic import BaseModel


class PreviewItem(BaseModel):
    name: str


class PreviewResponse(BaseModel):
    name: str
    items: list[PreviewItem]
    total: int


class ImportRequest(BaseModel):
    supplier: str


class ImportResultResponse(BaseModel):
    supplier: str
    intents_applied: dict[str, int]
