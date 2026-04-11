import uuid

from fastapi import APIRouter, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.auth.dependencies import CurrentUser
from app.database import SessionDep
from app.models.meal_plan import MealPlan, MealPlanItem
from app.models.menu_item import MenuItem
from app.schemas.meal_plan import MealPlanAddItem, MealPlanResponse, MealPlanSet

router = APIRouter(prefix="/meal-plans", tags=["meal-plans"])


async def _get_or_create_plan(session, user_id: uuid.UUID) -> MealPlan:
    result = await session.execute(
        select(MealPlan).where(MealPlan.user_id == user_id).options(selectinload(MealPlan.items))
    )
    plan = result.scalar_one_or_none()

    if plan is None:
        plan = MealPlan(user_id=user_id)
        session.add(plan)
        await session.flush()

    return plan


@router.get("/me", response_model=MealPlanResponse)
async def get_my_meal_plan(session: SessionDep, current_user: CurrentUser):
    plan = await _get_or_create_plan(session, current_user.id)
    await session.commit()
    return plan


@router.put("/me", response_model=MealPlanResponse)
async def set_my_meal_plan(
    data: MealPlanSet,
    session: SessionDep,
    current_user: CurrentUser,
):
    plan = await _get_or_create_plan(session, current_user.id)

    # Clear existing items
    plan.items.clear()

    # Add new items
    for menu_item_id in data.menu_item_ids:
        item = await session.get(MenuItem, menu_item_id)
        if not item:
            raise HTTPException(status_code=404, detail=f"Menu item {menu_item_id} not found")
        plan.items.append(MealPlanItem(menu_item_id=menu_item_id))

    await session.commit()

    # Reload with items
    result = await session.execute(
        select(MealPlan).where(MealPlan.id == plan.id).options(selectinload(MealPlan.items))
    )
    return result.scalar_one()


@router.post("/me/items", response_model=MealPlanResponse)
async def add_item_to_meal_plan(
    data: MealPlanAddItem,
    session: SessionDep,
    current_user: CurrentUser,
):
    plan = await _get_or_create_plan(session, current_user.id)

    # Check if already in plan
    existing = [i for i in plan.items if i.menu_item_id == data.menu_item_id]
    if existing:
        return plan

    # Verify menu item exists
    item = await session.get(MenuItem, data.menu_item_id)
    if not item:
        raise HTTPException(status_code=404, detail="Menu item not found")

    plan.items.append(MealPlanItem(menu_item_id=data.menu_item_id))
    await session.commit()

    result = await session.execute(
        select(MealPlan).where(MealPlan.id == plan.id).options(selectinload(MealPlan.items))
    )
    return result.scalar_one()


@router.delete("/me/items/{menu_item_id}", response_model=MealPlanResponse)
async def remove_item_from_meal_plan(
    menu_item_id: uuid.UUID,
    session: SessionDep,
    current_user: CurrentUser,
):
    plan = await _get_or_create_plan(session, current_user.id)

    plan.items = [i for i in plan.items if i.menu_item_id != menu_item_id]
    await session.commit()

    result = await session.execute(
        select(MealPlan).where(MealPlan.id == plan.id).options(selectinload(MealPlan.items))
    )
    return result.scalar_one()
