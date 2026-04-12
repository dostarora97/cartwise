import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict


class MenuItemCreate(BaseModel):
    name: str
    recipe: str
    ingredients: str


class MenuItemUpdate(BaseModel):
    name: str | None = None
    recipe: str | None = None
    ingredients: str | None = None


class MenuItemResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    recipe: str
    ingredients: str
    created_by: uuid.UUID
    updated_by: uuid.UUID
    status: str
    created_at: datetime
    updated_at: datetime
