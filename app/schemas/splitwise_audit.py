import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict


class SplitwiseAuditResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    order_id: uuid.UUID | None
    action: str
    status: str
    request_payload: dict
    response_payload: dict | None
    splitwise_expense_id: int | None
    error_message: str | None
    created_at: datetime
    completed_at: datetime | None
