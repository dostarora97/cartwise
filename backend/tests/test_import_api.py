from __future__ import annotations

import os

from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

os.environ.setdefault("CARTWISE_ENV", "testing")

from app.models.meal_plan import MealPlan, MealPlanItem
from app.models.menu_item import MenuItem


class TestImportAPI:
    async def test_list_suppliers(self, client: AsyncClient, auth_headers: dict):
        resp = await client.get("/api/v1/imports/suppliers", headers=auth_headers)

        assert resp.status_code == 200
        data = resp.json()
        assert len(data) >= 1
        supplier = data[0]
        assert supplier["id"] == "cartwise/starter"
        assert "name" in supplier
        assert "description" in supplier

    async def test_list_suppliers_unauthenticated(self, client: AsyncClient):
        resp = await client.get("/api/v1/imports/suppliers")

        assert resp.status_code in (401, 403)

    async def test_run_import_creates_items(
        self, client: AsyncClient, session: AsyncSession, auth_headers: dict, test_user
    ):
        resp = await client.post(
            "/api/v1/imports/",
            json={"supplier_id": "cartwise/starter"},
            headers=auth_headers,
        )

        assert resp.status_code == 200
        data = resp.json()
        assert data["supplier_id"] == "cartwise/starter"
        assert data["intents_applied"]["persist"] > 0
        assert data["intents_applied"]["skip"] == 0

        result = await session.execute(select(MenuItem).where(MenuItem.created_by == test_user.id))
        menu_items = list(result.scalars().all())
        assert len(menu_items) == 10

    async def test_run_import_idempotent(self, client: AsyncClient, auth_headers: dict, test_user):
        await client.post(
            "/api/v1/imports/",
            json={"supplier_id": "cartwise/starter"},
            headers=auth_headers,
        )

        resp = await client.post(
            "/api/v1/imports/",
            json={"supplier_id": "cartwise/starter"},
            headers=auth_headers,
        )

        assert resp.status_code == 200
        data = resp.json()
        assert data["intents_applied"]["persist"] == 0
        assert data["intents_applied"]["skip"] == 10

    async def test_run_import_creates_meal_plan_items(
        self, client: AsyncClient, session: AsyncSession, auth_headers: dict, test_user
    ):
        resp = await client.post(
            "/api/v1/imports/",
            json={"supplier_id": "cartwise/starter"},
            headers=auth_headers,
        )

        assert resp.status_code == 200

        result = await session.execute(select(MealPlan).where(MealPlan.user_id == test_user.id))
        plan = result.scalar_one()

        result = await session.execute(
            select(MealPlanItem).where(MealPlanItem.meal_plan_id == plan.id)
        )
        meal_plan_items = list(result.scalars().all())
        assert len(meal_plan_items) == 8  # 8 items have add_to_meal_plan intent

    async def test_run_import_ranks_sequential(
        self, client: AsyncClient, session: AsyncSession, auth_headers: dict, test_user
    ):
        await client.post(
            "/api/v1/imports/",
            json={"supplier_id": "cartwise/starter"},
            headers=auth_headers,
        )

        result = await session.execute(select(MealPlan).where(MealPlan.user_id == test_user.id))
        plan = result.scalar_one()

        result = await session.execute(
            select(MealPlanItem)
            .where(MealPlanItem.meal_plan_id == plan.id)
            .order_by(MealPlanItem.rank)
        )
        items = list(result.scalars().all())
        ranks = [i.rank for i in items]
        assert ranks == list(range(len(ranks)))

    async def test_run_import_unknown_supplier(self, client: AsyncClient, auth_headers: dict):
        resp = await client.post(
            "/api/v1/imports/",
            json={"supplier_id": "nonexistent/supplier"},
            headers=auth_headers,
        )

        assert resp.status_code == 404
        assert "Supplier not found" in resp.json()["detail"]

    async def test_run_import_unauthenticated(self, client: AsyncClient):
        resp = await client.post(
            "/api/v1/imports/",
            json={"supplier_id": "cartwise/starter"},
        )

        assert resp.status_code in (401, 403)
