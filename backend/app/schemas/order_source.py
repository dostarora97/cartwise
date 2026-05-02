import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.models.order_source import OrderSourceType


class OrderSourceCreate(BaseModel):
    type: OrderSourceType
    raw_data: dict | None = None


class OrderSourceResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    type: OrderSourceType
    raw_data: dict | None
    items: list | None
    created_by: uuid.UUID
    created_at: datetime


class UploadResponse(BaseModel):
    source_id: uuid.UUID
    storage_path: str
