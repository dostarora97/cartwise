"""Unit tests for order cancel, visibility, and list endpoints."""

import uuid

from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.order import Order, OrderParticipant
from app.models.split import Split
from app.models.user import User


async def _create_draft_order(session: AsyncSession, payer_id: uuid.UUID) -> Order:
    """Create a draft order directly in the DB for testing."""
    order = Order(
        paid_by=payer_id,
        invoice_filename="test.pdf",
        result={"paidBy": str(payer_id), "splits": []},
        snapshot={"members": {}, "uses": {}, "menu_items": []},
    )
    session.add(order)
    await session.flush()

    session.add(OrderParticipant(order_id=order.id, user_id=payer_id))
    await session.flush()

    session.add(
        Split(
            order_id=order.id,
            amount=100.00,
            grocery_items=[{"upc": "AAA", "description": "Chicken", "total": 100.0}],
            member_ids=[str(payer_id)],
        )
    )
    await session.commit()
    await session.refresh(order)
    return order


async def test_cancel_draft_order(
    client: AsyncClient, auth_headers: dict, test_user, session: AsyncSession
):
    order = await _create_draft_order(session, test_user.id)

    resp = await client.patch(f"/api/v1/orders/{order.id}/cancel", headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json()["status"] == "cancelled"


async def test_cancel_non_draft_fails(
    client: AsyncClient, auth_headers: dict, test_user, session: AsyncSession
):
    order = await _create_draft_order(session, test_user.id)
    order.status = "completed"
    await session.commit()

    resp = await client.patch(f"/api/v1/orders/{order.id}/cancel", headers=auth_headers)
    assert resp.status_code == 400


async def test_cancel_not_payer_forbidden(
    client: AsyncClient, auth_headers: dict, test_user, session: AsyncSession
):
    """Another user created the order — test_user can't cancel it."""
    other_user = User(
        email="other@test.com", name="Other", oauth_provider="google", oauth_id="other-oauth"
    )
    session.add(other_user)
    await session.flush()

    order = await _create_draft_order(session, other_user.id)

    resp = await client.patch(f"/api/v1/orders/{order.id}/cancel", headers=auth_headers)
    assert resp.status_code == 403


async def test_order_visible_to_anyone(
    client: AsyncClient, auth_headers: dict, test_user, session: AsyncSession
):
    """GET /orders/{id} is open — no participant check."""
    other_user = User(
        email="other2@test.com", name="Other2", oauth_provider="google", oauth_id="other-oauth-2"
    )
    session.add(other_user)
    await session.flush()

    order = await _create_draft_order(session, other_user.id)

    resp = await client.get(f"/api/v1/orders/{order.id}", headers=auth_headers)
    assert resp.status_code == 200


async def test_order_not_found(client: AsyncClient, auth_headers: dict):
    resp = await client.get(f"/api/v1/orders/{uuid.uuid4()}", headers=auth_headers)
    assert resp.status_code == 404


async def test_list_orders_default(
    client: AsyncClient, auth_headers: dict, test_user, session: AsyncSession
):
    """Default list returns orders where current user is participant."""
    order = await _create_draft_order(session, test_user.id)

    resp = await client.get("/api/v1/orders/", headers=auth_headers)
    assert resp.status_code == 200
    order_ids = [o["id"] for o in resp.json()]
    assert str(order.id) in order_ids


async def test_list_orders_by_user_id(
    client: AsyncClient, auth_headers: dict, test_user, session: AsyncSession
):
    """?user_id= lists orders where that user is the payer."""
    order = await _create_draft_order(session, test_user.id)

    resp = await client.get(f"/api/v1/orders/?user_id={test_user.id}", headers=auth_headers)
    assert resp.status_code == 200
    order_ids = [o["id"] for o in resp.json()]
    assert str(order.id) in order_ids


async def test_list_orders_by_status(
    client: AsyncClient, auth_headers: dict, test_user, session: AsyncSession
):
    """?status= filters orders by status."""
    order = await _create_draft_order(session, test_user.id)

    resp = await client.get("/api/v1/orders/?status=draft", headers=auth_headers)
    assert resp.status_code == 200
    assert all(o["status"] == "draft" for o in resp.json())
    assert any(o["id"] == str(order.id) for o in resp.json())

    resp2 = await client.get("/api/v1/orders/?status=completed", headers=auth_headers)
    assert all(o["status"] == "completed" for o in resp2.json())


async def test_order_has_splits(
    client: AsyncClient, auth_headers: dict, test_user, session: AsyncSession
):
    """Order response includes split rows."""
    order = await _create_draft_order(session, test_user.id)

    resp = await client.get(f"/api/v1/orders/{order.id}", headers=auth_headers)
    assert resp.status_code == 200
    splits = resp.json()["splits"]
    assert len(splits) == 1
    assert splits[0]["amount"] == 100.0
    assert splits[0]["status"] == "pending"


async def test_archive_removes_from_meal_plan(client: AsyncClient, auth_headers: dict, test_user):
    """Archiving a MenuItem auto-removes it from the user's meal plan."""
    # Create item and add to plan
    item_resp = await client.post(
        "/api/v1/menu-items/",
        json={"name": "ToArchive", "body": "body"},
        headers=auth_headers,
    )
    item_id = item_resp.json()["id"]

    await client.put(
        f"/api/v1/meal-plans/{test_user.id}",
        json={"menu_item_ids": [item_id]},
        headers=auth_headers,
    )

    # Verify it's in the plan
    plan_resp = await client.get(f"/api/v1/meal-plans/{test_user.id}")
    assert len(plan_resp.json()["items"]) == 1

    # Archive it
    await client.patch(f"/api/v1/menu-items/{item_id}/archive", headers=auth_headers)

    # Verify it's removed from plan
    plan_resp2 = await client.get(f"/api/v1/meal-plans/{test_user.id}")
    assert len(plan_resp2.json()["items"]) == 0
