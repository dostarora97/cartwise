from __future__ import annotations

import uuid as uuid_mod
from dataclasses import dataclass
from itertools import count
from uuid import UUID

from app.models.meal_plan import MealPlanItem
from app.models.menu_item import MenuItem

from .intents import DbIntent, Persist, Skip
from .protocols import ReadContext


@dataclass
class MenuItemImportItem:
    name: str
    body: str
    intents_declared: list[str]
    user_id: UUID
    meal_plan_id: UUID | None
    rank_counter: count

    async def resolve_intents(self, ctx: ReadContext) -> list[DbIntent]:
        existing = await ctx.find_by(
            MenuItem, name=self.name, body=self.body, created_by=self.user_id
        )

        if existing:
            return [Skip(reason=f"'{self.name}' already exists")]

        menu_item_id = uuid_mod.uuid4()
        menu_item = MenuItem(
            id=menu_item_id,
            name=self.name,
            body=self.body,
            created_by=self.user_id,
            updated_by=self.user_id,
        )
        result: list[DbIntent] = [Persist(menu_item)]

        if "add_to_meal_plan" in self.intents_declared and self.meal_plan_id:
            result.append(
                Persist(
                    MealPlanItem(
                        meal_plan_id=self.meal_plan_id,
                        menu_item_id=menu_item_id,
                        rank=next(self.rank_counter),
                    )
                )
            )

        return result
