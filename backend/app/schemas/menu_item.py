import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict


class MenuItemCreate(BaseModel):
    name: str
    body: str


class MenuItemUpdate(BaseModel):
    name: str | None = None
    body: str | None = None


class MenuItemResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    body: str
    status: str
    created_at: datetime
    updated_at: datetime
