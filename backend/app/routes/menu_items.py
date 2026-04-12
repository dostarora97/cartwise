import uuid

from fastapi import APIRouter, HTTPException, Query
from sqlalchemy import select

from app.auth.dependencies import CurrentUser
from app.database import SessionDep
from app.models.menu_item import MenuItem
from app.schemas.menu_item import MenuItemCreate, MenuItemResponse, MenuItemUpdate

router = APIRouter(prefix="/menu-items", tags=["menu-items"])


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
    status: str = Query(default="active"),
    created_by: uuid.UUID | None = Query(default=None),
):
    stmt = select(MenuItem).where(MenuItem.status == status)
    if created_by:
        stmt = stmt.where(MenuItem.created_by == created_by)
    result = await session.execute(stmt)
    return result.scalars().all()


@router.get("/{item_id}", response_model=MenuItemResponse)
async def get_menu_item(item_id: uuid.UUID, session: SessionDep):
    item = await session.get(MenuItem, item_id)
    if not item:
        raise HTTPException(status_code=404, detail="Menu item not found")
    return item


@router.patch("/{item_id}", response_model=MenuItemResponse)
async def update_menu_item(
    item_id: uuid.UUID,
    data: MenuItemUpdate,
    session: SessionDep,
    current_user: CurrentUser,
):
    item = await session.get(MenuItem, item_id)
    if not item:
        raise HTTPException(status_code=404, detail="Menu item not found")

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
    item = await session.get(MenuItem, item_id)
    if not item:
        raise HTTPException(status_code=404, detail="Menu item not found")

    item.status = "archived"
    item.updated_by = current_user.id
    await session.commit()
    await session.refresh(item)
    return item


@router.patch("/{item_id}/unarchive", response_model=MenuItemResponse)
async def unarchive_menu_item(
    item_id: uuid.UUID,
    session: SessionDep,
    current_user: CurrentUser,
):
    item = await session.get(MenuItem, item_id)
    if not item:
        raise HTTPException(status_code=404, detail="Menu item not found")

    item.status = "active"
    item.updated_by = current_user.id
    await session.commit()
    await session.refresh(item)
    return item
