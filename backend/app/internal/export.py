from __future__ import annotations

import base64
import json
from uuid import UUID

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.database import SessionDep
from app.models.meal_plan import MealPlan, MealPlanItem
from app.models.menu_item import MenuItem
from app.models.user import User

router = APIRouter()


class ExportRequest(BaseModel):
    action: str
    payload: str


class CartwisePayload(BaseModel):
    type: str
    id: UUID


def _decode_cartwise_payload(raw: str) -> CartwisePayload:
    try:
        decoded = base64.urlsafe_b64decode(raw + "==")
        data = json.loads(decoded)
    except (ValueError, json.JSONDecodeError) as exc:
        raise HTTPException(400, "Invalid payload") from exc
    return CartwisePayload.model_validate(data)


async def _get_user_meal_plan_items(
    session: SessionDep, user_id: UUID
) -> tuple[User, list[MenuItem]]:
    user = await session.get(User, user_id)
    if user is None or not user.is_active:
        raise HTTPException(404, "User not found")

    result = await session.execute(
        select(MealPlan)
        .where(MealPlan.user_id == user_id)
        .options(selectinload(MealPlan.items).selectinload(MealPlanItem.menu_item))
    )
    plan = result.scalar_one_or_none()
    if plan is None:
        return user, []

    items = [mpi.menu_item for mpi in plan.items]
    return user, items


@router.post("/export")
async def handle_export(body: ExportRequest, session: SessionDep):
    payload = _decode_cartwise_payload(body.payload)

    if payload.type == "user":
        user, items = await _get_user_meal_plan_items(session, payload.id)

        if body.action == "preview":
            return {
                "name": f"{user.name}'s Meal Plan",
                "items": [{"name": i.name} for i in items],
                "total": len(items),
            }

        if body.action == "import":
            return {
                "items": [
                    {"name": i.name, "body": i.body or "", "intents": ["add_to_meal_plan"]}
                    for i in items
                ]
            }

    raise HTTPException(400, "Unsupported payload type")
