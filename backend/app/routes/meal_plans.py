import uuid

from fastapi import APIRouter, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.auth.dependencies import CurrentUser
from app.database import SessionDep
from app.models.meal_plan import MealPlan, MealPlanItem
from app.models.menu_item import MenuItem
from app.schemas.meal_plan import MealPlanResponse, MealPlanSet
from app.schemas.menu_item import MenuItemResponse

router = APIRouter(prefix="/meal-plans", tags=["meal-plans"])


def _plan_response(plan: MealPlan) -> dict:
    """Build a MealPlanResponse dict from a loaded MealPlan with eager-loaded items + menu_items."""
    return {
        "id": plan.id,
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


@router.get("", response_model=MealPlanResponse)
async def get_meal_plan(session: SessionDep, current_user: CurrentUser):
    plan = await _get_or_create_plan(session, current_user.id)
    await session.commit()
    return _plan_response(plan)


@router.put("", response_model=MealPlanResponse)
async def set_meal_plan(
    data: MealPlanSet,
    session: SessionDep,
    current_user: CurrentUser,
):
    plan = await _get_or_create_plan(session, current_user.id)
    plan.items.clear()

    if data.menu_item_ids:
        stmt = select(MenuItem).where(MenuItem.id.in_(data.menu_item_ids))
        result = await session.execute(stmt)
        found_items = {item.id: item for item in result.scalars().all()}

        missing = [str(mid) for mid in data.menu_item_ids if mid not in found_items]
        if missing:
            raise HTTPException(
                status_code=400,
                detail=f"Menu items not found: {', '.join(missing)}",
            )

        archived = [str(mid) for mid in data.menu_item_ids if found_items[mid].status == "archived"]
        if archived:
            raise HTTPException(
                status_code=400,
                detail=f"Menu items are archived: {', '.join(archived)}",
            )

        for rank, menu_item_id in enumerate(data.menu_item_ids):
            plan.items.append(MealPlanItem(menu_item_id=menu_item_id, rank=rank))

    await session.commit()
    plan = await _reload_plan(session, plan.id)
    return _plan_response(plan)
