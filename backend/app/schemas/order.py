import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict


class OrderCreate(BaseModel):
    participant_ids: list[uuid.UUID]


class OrderParticipantResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    user_id: uuid.UUID


class OrderResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    paid_by: uuid.UUID
    invoice_filename: str
    status: str
    snapshot: dict | None
    result: dict | None
    created_at: datetime
    participants: list[OrderParticipantResponse]
