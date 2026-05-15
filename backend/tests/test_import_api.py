from __future__ import annotations

import base64
import json
import os
from unittest.mock import AsyncMock, patch

from httpx import AsyncClient, Request, Response
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

os.environ.setdefault("CARTWISE_ENV", "testing")

import pytest

from app.models.meal_plan import MealPlan, MealPlanItem
from app.models.menu_item import MenuItem
from app.models.user import User
from app.services.importer.token import encode_token


@pytest.fixture
async def starter_user(session: AsyncSession) -> User:
    """Create the starter user with meal plan items for the export endpoint."""
    user = User(
        id="00000000-0000-0000-0000-000000000000",
        email="user_1@cartwise.app",
        name="User 1",
        oauth_provider="system",
        oauth_id="system:00000000-0000-0000-0000-000000000000",
    )
    session.add(user)
    await session.flush()

    items = [
        MenuItem(
            name="Chicken Breast", body="500g boneless pack", created_by=user.id, updated_by=user.id
        ),
        MenuItem(
            name="Basmati Rice", body="1kg aged basmati", created_by=user.id, updated_by=user.id
        ),
    ]
    session.add_all(items)
    await session.flush()

    plan = MealPlan(user_id=user.id)
    session.add(plan)
    await session.flush()

    for i, item in enumerate(items):
        session.add(MealPlanItem(meal_plan_id=plan.id, menu_item_id=item.id, rank=i))
    await session.commit()

    return user


def _make_cartwise_token(user_id: str) -> str:
    payload_json = json.dumps({"type": "user", "id": user_id})
    payload_b64 = base64.urlsafe_b64encode(payload_json.encode()).rstrip(b"=").decode()
    return encode_token("cartwise", payload_b64)


def _mock_supplier_preview(name: str, items: list[dict], total: int):
    """Create a mock for httpx.AsyncClient that returns a preview response."""
    mock_response = Response(
        200,
        json={"name": name, "items": items, "total": total},
        request=Request("POST", "http://test/internal/export"),
    )
    mock_client = AsyncMock()
    mock_client.post = AsyncMock(return_value=mock_response)
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)
    return mock_client


def _mock_supplier_import(items: list[dict]):
    """Create a mock for httpx.AsyncClient that returns an import response."""
    mock_response = Response(
        200,
        json={"items": items},
        request=Request("POST", "http://test/internal/export"),
    )
    mock_client = AsyncMock()
    mock_client.post = AsyncMock(return_value=mock_response)
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)
    return mock_client


class TestPreviewImport:
    async def test_preview_success(
        self, client: AsyncClient, auth_headers: dict, test_user, starter_user
    ):
        token = _make_cartwise_token(str(starter_user.id))
        mock_client = _mock_supplier_preview(
            "User 1's Meal Plan",
            [{"name": "Chicken Breast"}, {"name": "Basmati Rice"}],
            2,
        )
        with patch("app.services.importer.client.httpx.AsyncClient", return_value=mock_client):
            resp = await client.get(
                "/api/v1/imports/preview",
                params={"supplier_id": token},
                headers=auth_headers,
            )

        assert resp.status_code == 200
        data = resp.json()
        assert data["name"] == "User 1's Meal Plan"
        assert data["total"] == 2
        assert len(data["items"]) == 2

    async def test_preview_invalid_token(self, client: AsyncClient, auth_headers: dict, test_user):
        resp = await client.get(
            "/api/v1/imports/preview",
            params={"supplier_id": "invalid-garbage"},
            headers=auth_headers,
        )

        assert resp.status_code == 404

    async def test_preview_unknown_supplier(
        self, client: AsyncClient, auth_headers: dict, test_user
    ):
        inner = json.dumps({"supplier": "unknown", "payload": "abc"})
        token = base64.urlsafe_b64encode(inner.encode()).rstrip(b"=").decode()

        resp = await client.get(
            "/api/v1/imports/preview",
            params={"supplier_id": token},
            headers=auth_headers,
        )

        assert resp.status_code == 404

    async def test_preview_unauthenticated(self, client: AsyncClient, starter_user):
        token = _make_cartwise_token(str(starter_user.id))
        resp = await client.get(
            "/api/v1/imports/preview",
            params={"supplier_id": token},
        )

        assert resp.status_code in (401, 403)


class TestRunImport:
    async def test_import_creates_items(
        self,
        client: AsyncClient,
        session: AsyncSession,
        auth_headers: dict,
        test_user,
        starter_user,
    ):
        token = _make_cartwise_token(str(starter_user.id))
        mock_client = _mock_supplier_import(
            [
                {
                    "name": "Chicken Breast",
                    "body": "500g boneless pack",
                    "intents": ["add_to_meal_plan"],
                },
                {
                    "name": "Basmati Rice",
                    "body": "1kg aged basmati",
                    "intents": ["add_to_meal_plan"],
                },
            ]
        )
        with patch("app.services.importer.client.httpx.AsyncClient", return_value=mock_client):
            resp = await client.post(
                "/api/v1/imports/",
                json={"supplier_id": token},
                headers=auth_headers,
            )

        assert resp.status_code == 200
        data = resp.json()
        assert data["intents_applied"]["persist"] > 0
        assert data["intents_applied"]["skip"] == 0

        result = await session.execute(select(MenuItem).where(MenuItem.created_by == test_user.id))
        items = list(result.scalars().all())
        assert len(items) == 2

    async def test_import_idempotent(
        self, client: AsyncClient, auth_headers: dict, test_user, starter_user
    ):
        token = _make_cartwise_token(str(starter_user.id))
        mock_client = _mock_supplier_import(
            [
                {
                    "name": "Chicken Breast",
                    "body": "500g boneless pack",
                    "intents": ["add_to_meal_plan"],
                },
                {
                    "name": "Basmati Rice",
                    "body": "1kg aged basmati",
                    "intents": ["add_to_meal_plan"],
                },
            ]
        )
        with patch("app.services.importer.client.httpx.AsyncClient", return_value=mock_client):
            await client.post(
                "/api/v1/imports/",
                json={"supplier_id": token},
                headers=auth_headers,
            )

        with patch("app.services.importer.client.httpx.AsyncClient", return_value=mock_client):
            resp = await client.post(
                "/api/v1/imports/",
                json={"supplier_id": token},
                headers=auth_headers,
            )

        assert resp.status_code == 200
        data = resp.json()
        assert data["intents_applied"]["persist"] == 0
        assert data["intents_applied"]["skip"] == 2

    async def test_import_creates_meal_plan_items(
        self,
        client: AsyncClient,
        session: AsyncSession,
        auth_headers: dict,
        test_user,
        starter_user,
    ):
        token = _make_cartwise_token(str(starter_user.id))
        mock_client = _mock_supplier_import(
            [
                {
                    "name": "Chicken Breast",
                    "body": "500g boneless pack",
                    "intents": ["add_to_meal_plan"],
                },
                {
                    "name": "Basmati Rice",
                    "body": "1kg aged basmati",
                    "intents": ["add_to_meal_plan"],
                },
            ]
        )
        with patch("app.services.importer.client.httpx.AsyncClient", return_value=mock_client):
            resp = await client.post(
                "/api/v1/imports/",
                json={"supplier_id": token},
                headers=auth_headers,
            )

        assert resp.status_code == 200

        result = await session.execute(select(MealPlan).where(MealPlan.user_id == test_user.id))
        plan = result.scalar_one()

        result = await session.execute(
            select(MealPlanItem).where(MealPlanItem.meal_plan_id == plan.id)
        )
        meal_plan_items = list(result.scalars().all())
        assert len(meal_plan_items) == 2

    async def test_import_unknown_token(self, client: AsyncClient, auth_headers: dict, test_user):
        resp = await client.post(
            "/api/v1/imports/",
            json={"supplier_id": "garbage-token"},
            headers=auth_headers,
        )

        assert resp.status_code == 404

    async def test_import_unauthenticated(self, client: AsyncClient, starter_user):
        token = _make_cartwise_token(str(starter_user.id))
        resp = await client.post(
            "/api/v1/imports/",
            json={"supplier_id": token},
        )

        assert resp.status_code in (401, 403)


class TestInternalExportEndpoint:
    async def test_export_preview_and_import(
        self, client: AsyncClient, session: AsyncSession, starter_user
    ):
        from app.config import settings

        payload_json = json.dumps({"type": "user", "id": str(starter_user.id)})
        payload_b64 = base64.urlsafe_b64encode(payload_json.encode()).rstrip(b"=").decode()

        resp = await client.post(
            "/internal/export",
            json={"action": "preview", "payload": payload_b64},
            headers={"X-Internal-Secret": settings.INTERNAL_API_SECRET},
        )

        assert resp.status_code == 200
        data = resp.json()
        assert data["name"] == "User 1's Meal Plan"
        assert data["total"] == 2

        resp = await client.post(
            "/internal/export",
            json={"action": "import", "payload": payload_b64},
            headers={"X-Internal-Secret": settings.INTERNAL_API_SECRET},
        )

        assert resp.status_code == 200
        data = resp.json()
        assert len(data["items"]) == 2
        assert data["items"][0]["name"] == "Chicken Breast"
        assert data["items"][0]["intents"] == ["add_to_meal_plan"]

    async def test_export_rejected_without_secret(self, client: AsyncClient, starter_user):
        payload_json = json.dumps({"type": "user", "id": str(starter_user.id)})
        payload_b64 = base64.urlsafe_b64encode(payload_json.encode()).rstrip(b"=").decode()

        resp = await client.post(
            "/internal/export",
            json={"action": "preview", "payload": payload_b64},
        )

        assert resp.status_code == 404

    async def test_export_rejected_wrong_secret(self, client: AsyncClient, starter_user):
        payload_json = json.dumps({"type": "user", "id": str(starter_user.id)})
        payload_b64 = base64.urlsafe_b64encode(payload_json.encode()).rstrip(b"=").decode()

        resp = await client.post(
            "/internal/export",
            json={"action": "preview", "payload": payload_b64},
            headers={"X-Internal-Secret": "wrong-secret"},
        )

        assert resp.status_code == 404
