import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict


class MealPlanSet(BaseModel):
    menu_item_ids: list[uuid.UUID]


class MealPlanAddItem(BaseModel):
    menu_item_id: uuid.UUID


class MealPlanItemResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    menu_item_id: uuid.UUID


class MealPlanResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    user_id: uuid.UUID
    updated_at: datetime
    items: list[MealPlanItemResponse]
