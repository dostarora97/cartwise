import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.schemas.menu_item import MenuItemResponse


class MealPlanSet(BaseModel):
    menu_item_ids: list[uuid.UUID]


class MealPlanAddItem(BaseModel):
    menu_item_id: uuid.UUID


class MealPlanItemResponse(BaseModel):
    rank: int
    menu_item: MenuItemResponse


class MealPlanResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    user_id: uuid.UUID
    updated_at: datetime
    items: list[MealPlanItemResponse]
