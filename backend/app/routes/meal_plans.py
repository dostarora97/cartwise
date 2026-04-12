import uuid

from fastapi import APIRouter, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.auth.dependencies import CurrentUser
from app.database import SessionDep
from app.models.meal_plan import MealPlan, MealPlanItem
from app.models.menu_item import MenuItem
from app.schemas.meal_plan import (
    MealPlanAddItem,
    MealPlanResponse,
    MealPlanSet,
)
from app.schemas.menu_item import MenuItemResponse

router = APIRouter(prefix="/meal-plans", tags=["meal-plans"])


def _plan_response(plan: MealPlan) -> dict:
    """Build a MealPlanResponse dict from a loaded MealPlan with eager-loaded items + menu_items."""
    return {
        "id": plan.id,
        "user_id": plan.user_id,
        "updated_at": plan.updated_at,
        "items": [
            {
                "rank": item.rank,
                "menu_item": MenuItemResponse.model_validate(item.menu_item),
            }
            for item in plan.items
        ],
    }


def _load_options():
    """Eager-load options for MealPlan queries: items sorted by rank, with menu_item joined."""
    return selectinload(MealPlan.items).selectinload(MealPlanItem.menu_item)


async def _get_or_create_plan(session, user_id: uuid.UUID) -> MealPlan:
    result = await session.execute(
        select(MealPlan).where(MealPlan.user_id == user_id).options(_load_options())
    )
    plan = result.scalar_one_or_none()

    if plan is None:
        plan = MealPlan(user_id=user_id)
        session.add(plan)
        await session.flush()
        result = await session.execute(
            select(MealPlan).where(MealPlan.id == plan.id).options(_load_options())
        )
        plan = result.scalar_one()

    return plan


async def _reload_plan(session, plan_id: uuid.UUID) -> MealPlan:
    result = await session.execute(
        select(MealPlan).where(MealPlan.id == plan_id).options(_load_options())
    )
    return result.scalar_one()


def _check_ownership(user_id: uuid.UUID, current_user_id: uuid.UUID) -> None:
    if user_id != current_user_id:
        raise HTTPException(status_code=403, detail="Cannot modify another user's meal plan")


@router.get("/{user_id}", response_model=MealPlanResponse)
async def get_meal_plan(user_id: uuid.UUID, session: SessionDep):
    plan = await _get_or_create_plan(session, user_id)
    await session.commit()
    return _plan_response(plan)


@router.put("/{user_id}", response_model=MealPlanResponse)
async def set_meal_plan(
    user_id: uuid.UUID,
    data: MealPlanSet,
    session: SessionDep,
    current_user: CurrentUser,
):
    _check_ownership(user_id, current_user.id)
    plan = await _get_or_create_plan(session, user_id)

    plan.items.clear()

    for rank, menu_item_id in enumerate(data.menu_item_ids):
        item = await session.get(MenuItem, menu_item_id)
        if not item:
            raise HTTPException(status_code=404, detail=f"Menu item {menu_item_id} not found")
        plan.items.append(MealPlanItem(menu_item_id=menu_item_id, rank=rank))

    await session.commit()
    plan = await _reload_plan(session, plan.id)
    return _plan_response(plan)


@router.post("/{user_id}/items", response_model=MealPlanResponse)
async def add_item_to_meal_plan(
    user_id: uuid.UUID,
    data: MealPlanAddItem,
    session: SessionDep,
    current_user: CurrentUser,
):
    _check_ownership(user_id, current_user.id)
    plan = await _get_or_create_plan(session, user_id)

    existing = [i for i in plan.items if i.menu_item_id == data.menu_item_id]
    if existing:
        return _plan_response(plan)

    item = await session.get(MenuItem, data.menu_item_id)
    if not item:
        raise HTTPException(status_code=404, detail="Menu item not found")

    next_rank = max((i.rank for i in plan.items), default=-1) + 1
    plan.items.append(MealPlanItem(menu_item_id=data.menu_item_id, rank=next_rank))
    await session.commit()

    plan = await _reload_plan(session, plan.id)
    return _plan_response(plan)


@router.delete("/{user_id}/items/{menu_item_id}", response_model=MealPlanResponse)
async def remove_item_from_meal_plan(
    user_id: uuid.UUID,
    menu_item_id: uuid.UUID,
    session: SessionDep,
    current_user: CurrentUser,
):
    _check_ownership(user_id, current_user.id)
    plan = await _get_or_create_plan(session, user_id)

    plan.items = [i for i in plan.items if i.menu_item_id != menu_item_id]
    await session.commit()

    plan = await _reload_plan(session, plan.id)
    return _plan_response(plan)
