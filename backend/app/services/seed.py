from __future__ import annotations

import json
import uuid
from pathlib import Path

import structlog
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import async_session
from app.models.meal_plan import MealPlan, MealPlanItem
from app.models.menu_item import MenuItem
from app.models.user import User

logger = structlog.get_logger()

FIXTURES_PATH = Path(__file__).resolve().parent.parent.parent / "fixtures" / "starter-users.json"


async def reconcile_fixtures() -> None:
    if not FIXTURES_PATH.exists():
        return

    desired_users = json.loads(FIXTURES_PATH.read_text())
    desired_ids = {uuid.UUID(u["id"]) for u in desired_users}

    async with async_session() as session:
        current_users = (
            (await session.execute(select(User).where(User.oauth_provider == "system")))
            .scalars()
            .all()
        )
        current_ids = {u.id for u in current_users}

        # Delete users no longer in fixture
        removed_ids = current_ids - desired_ids
        for uid in removed_ids:
            await _delete_system_user(session, uid)
            logger.info("seed.user_removed", user_id=str(uid))

        # Create or update users in fixture
        for spec in desired_users:
            user_id = uuid.UUID(spec["id"])
            existing = next((u for u in current_users if u.id == user_id), None)

            if existing is None:
                await _create_system_user(session, spec)
                logger.info("seed.user_created", user_id=spec["id"], name=spec["name"])
            else:
                changed = await _update_system_user(session, existing, spec)
                if changed:
                    logger.info("seed.user_updated", user_id=spec["id"])

        await session.commit()


async def _create_system_user(session: AsyncSession, spec: dict) -> None:
    user_id = uuid.UUID(spec["id"])

    user = User(
        id=user_id,
        email=spec["email"],
        name=spec["name"],
        oauth_provider="system",
        oauth_id=f"system:{spec['id']}",
    )
    session.add(user)
    await session.flush()

    plan = MealPlan(user_id=user_id)
    session.add(plan)
    await session.flush()

    for rank, item_spec in enumerate(spec["items"]):
        menu_item = MenuItem(
            name=item_spec["name"],
            body=item_spec["body"],
            created_by=user_id,
            updated_by=user_id,
        )
        session.add(menu_item)
        await session.flush()

        session.add(MealPlanItem(meal_plan_id=plan.id, menu_item_id=menu_item.id, rank=rank))


async def _update_system_user(session: AsyncSession, user: User, spec: dict) -> bool:
    changed = False

    if user.name != spec["name"]:
        user.name = spec["name"]
        changed = True
    if user.email != spec["email"]:
        user.email = spec["email"]
        changed = True

    desired_items = {(i["name"], i["body"]) for i in spec["items"]}
    current_items_result = await session.execute(
        select(MenuItem).where(MenuItem.created_by == user.id)
    )
    current_items = current_items_result.scalars().all()
    current_item_set = {(i.name, i.body) for i in current_items}

    if desired_items != current_item_set:
        await _replace_items(session, user.id, spec["items"])
        changed = True

    return changed


async def _replace_items(session: AsyncSession, user_id: uuid.UUID, items: list[dict]) -> None:
    plan_result = await session.execute(select(MealPlan).where(MealPlan.user_id == user_id))
    plan = plan_result.scalar_one()

    await session.execute(delete(MealPlanItem).where(MealPlanItem.meal_plan_id == plan.id))
    await session.execute(delete(MenuItem).where(MenuItem.created_by == user_id))

    for rank, item_spec in enumerate(items):
        menu_item = MenuItem(
            name=item_spec["name"],
            body=item_spec["body"],
            created_by=user_id,
            updated_by=user_id,
        )
        session.add(menu_item)
        await session.flush()

        session.add(MealPlanItem(meal_plan_id=plan.id, menu_item_id=menu_item.id, rank=rank))


async def _delete_system_user(session: AsyncSession, user_id: uuid.UUID) -> None:
    await session.execute(delete(User).where(User.id == user_id))
