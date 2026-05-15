from pydantic import BaseModel


class SupplierInfo(BaseModel):
    id: str
    name: str
    description: str


class ImportRequest(BaseModel):
    supplier_id: str


class ImportResultResponse(BaseModel):
    supplier_id: str
    intents_applied: dict[str, int]
