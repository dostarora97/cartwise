import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict


class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    email: str
    name: str
    phone: str | None
    avatar_url: str | None
    oauth_provider: str
    splitwise_user_id: int | None
    is_active: bool
    created_at: datetime
    updated_at: datetime


class UserUpdate(BaseModel):
    name: str | None = None
    phone: str | None = None
    avatar_url: str | None = None


class OnboardRequest(BaseModel):
    name: str
    phone: str
    splitwise_user_id: int
