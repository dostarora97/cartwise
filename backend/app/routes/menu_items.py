import uuid

from fastapi import APIRouter, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.auth.dependencies import CurrentUser
from app.database import SessionDep
from app.models.meal_plan import MealPlan
from app.models.menu_item import MenuItem
from app.schemas.menu_item import MenuItemCreate, MenuItemResponse, MenuItemUpdate

router = APIRouter(prefix="/menu-items", tags=["menu-items"])

VALID_STATUSES = {"active", "archived"}


async def _get_item_or_404(session, item_id: uuid.UUID) -> MenuItem:
    item = await session.get(MenuItem, item_id)
    if not item:
        raise HTTPException(status_code=404, detail="Menu item not found")
    return item


def _check_owner(item: MenuItem, user_id: uuid.UUID):
    if item.created_by != user_id:
        raise HTTPException(status_code=403, detail="Not allowed to modify this item")


@router.post("/", response_model=MenuItemResponse, status_code=201)
async def create_menu_item(
    data: MenuItemCreate,
    session: SessionDep,
    current_user: CurrentUser,
):
    item = MenuItem(
        name=data.name,
        body=data.body,
        created_by=current_user.id,
        updated_by=current_user.id,
    )
    session.add(item)
    await session.commit()
    await session.refresh(item)
    return item


@router.get("/", response_model=list[MenuItemResponse])
async def list_menu_items(
    session: SessionDep,
    current_user: CurrentUser,
    status: str = Query(default="active"),
):
    statuses = [s.strip() for s in status.split(",")]
    invalid = [s for s in statuses if s not in VALID_STATUSES]
    if invalid:
        raise HTTPException(status_code=400, detail=f"Invalid status: {', '.join(invalid)}")

    stmt = select(MenuItem).where(
        MenuItem.created_by == current_user.id,
        MenuItem.status.in_(statuses),
    )
    result = await session.execute(stmt)
    return result.scalars().all()


@router.get("/{item_id}", response_model=MenuItemResponse)
async def get_menu_item(item_id: uuid.UUID, session: SessionDep):
    return await _get_item_or_404(session, item_id)


@router.patch("/{item_id}", response_model=MenuItemResponse)
async def update_menu_item(
    item_id: uuid.UUID,
    data: MenuItemUpdate,
    session: SessionDep,
    current_user: CurrentUser,
):
    item = await _get_item_or_404(session, item_id)
    _check_owner(item, current_user.id)

    update_data = data.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(item, key, value)
    item.updated_by = current_user.id

    await session.commit()
    await session.refresh(item)
    return item


@router.patch("/{item_id}/archive", response_model=MenuItemResponse)
async def archive_menu_item(
    item_id: uuid.UUID,
    session: SessionDep,
    current_user: CurrentUser,
):
    item = await _get_item_or_404(session, item_id)
    _check_owner(item, current_user.id)

    item.status = "archived"
    item.updated_by = current_user.id

    result = await session.execute(
        select(MealPlan)
        .where(MealPlan.user_id == current_user.id)
        .options(selectinload(MealPlan.items))
    )
    plan = result.scalar_one_or_none()
    if plan:
        plan.items = [i for i in plan.items if i.menu_item_id != item_id]

    await session.commit()
    await session.refresh(item)
    return item


@router.patch("/{item_id}/unarchive", response_model=MenuItemResponse)
async def unarchive_menu_item(
    item_id: uuid.UUID,
    session: SessionDep,
    current_user: CurrentUser,
):
    item = await _get_item_or_404(session, item_id)
    _check_owner(item, current_user.id)

    item.status = "active"
    item.updated_by = current_user.id
    await session.commit()
    await session.refresh(item)
    return item
