import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict


class OrderCreate(BaseModel):
    participant_ids: list[uuid.UUID]


class OrderParticipantResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    user_id: uuid.UUID


class SplitResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    amount: float
    grocery_items: list[dict]
    member_ids: list[str]
    status: str
    splitwise_expense_id: int | None


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
    splits: list[SplitResponse]


class SplitAssignment(BaseModel):
    """One grocery item's member assignment for the edit-splits endpoint."""

    upc: str
    member_ids: list[str]


class EditSplitsRequest(BaseModel):
    """Request body for PUT /orders/{id}/splits."""

    assignments: list[SplitAssignment]
