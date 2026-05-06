"""Tests for the full create_order pipeline (POST /orders/)."""

import uuid
from unittest.mock import AsyncMock, patch

from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.order import Order
from app.models.order_source import OrderSource, OrderSourceType
from app.models.user import User


async def _make_source(session: AsyncSession, user_id: uuid.UUID) -> OrderSource:
    source = OrderSource(
        type=OrderSourceType.invoice,
        raw_data={"storage_path": "/fake/path"},
        created_by=user_id,
    )
    session.add(source)
    await session.commit()
    await session.refresh(source)
    return source


async def test_create_order_pipeline(
    client: AsyncClient, auth_headers: dict, test_user, session: AsyncSession
):
    """Full pipeline: extraction → correlate → compute_splits → order created."""
    source = await _make_source(session, test_user.id)

    mock_items = [
        {"id": "I1", "name": "Milk", "quantity": 1, "total": 50.0, "category": "item"},
        {"id": "FEE_DEL", "name": "Delivery", "quantity": 1, "total": 10.0, "category": "fee"},
    ]
    mock_uses = {}
    mock_result = {
        "paidBy": str(test_user.id),
        "noSplit": True,
        "splits": [
            {
                "amount": 60.0,
                "groceryItems": [
                    {"upc": "I1", "description": "Milk", "total": 50.0, "category": "item"},
                    {"upc": "FEE_DEL", "description": "Delivery", "total": 10.0, "category": "fee"},
                ],
                "splitEquallyAmong": [str(test_user.id)],
            }
        ],
    }

    with (
        patch(
            "app.routes.orders.run_extraction",
            new_callable=AsyncMock,
            return_value=mock_items,
        ),
        patch(
            "app.routes.orders.correlate",
            new_callable=AsyncMock,
            return_value=mock_uses,
        ),
        patch("app.routes.orders.compute_splits", return_value=mock_result),
    ):
        resp = await client.post(
            "/api/v1/orders/",
            headers=auth_headers,
            json={
                "source_id": str(source.id),
                "participant_ids": [str(test_user.id)],
            },
        )

    assert resp.status_code == 201
    data = resp.json()
    assert data["source_id"] == str(source.id)
    assert data["status"] == "no_split"
    assert len(data["splits"]) == 0  # noSplit=True → no Split rows created


async def test_create_order_idempotent(
    client: AsyncClient, auth_headers: dict, test_user, session: AsyncSession
):
    """Second POST with same source_id returns the existing order."""
    source = await _make_source(session, test_user.id)

    # Create the first order directly in DB
    order = Order(
        paid_by=test_user.id,
        source_id=source.id,
        snapshot={"members": {}, "uses": {}, "menu_items": []},
        result={"paidBy": str(test_user.id), "splits": []},
    )
    session.add(order)
    await session.commit()
    await session.refresh(order)

    resp = await client.post(
        "/api/v1/orders/",
        headers=auth_headers,
        json={
            "source_id": str(source.id),
            "participant_ids": [str(test_user.id)],
        },
    )

    assert resp.status_code == 201
    assert resp.json()["id"] == str(order.id)


async def test_create_order_adds_current_user_to_participants(
    client: AsyncClient, auth_headers: dict, test_user, session: AsyncSession
):
    """Current user is added to participants even if not in the list."""
    other = User(email="p2@x.com", name="P2", oauth_provider="google", oauth_id="p2-oauth")
    session.add(other)
    await session.flush()

    source = await _make_source(session, test_user.id)

    mock_items = [
        {"id": "I1", "name": "Rice", "quantity": 1, "total": 80.0, "category": "item"},
    ]
    mock_result = {
        "paidBy": str(test_user.id),
        "noSplit": False,
        "splits": [
            {
                "amount": 80.0,
                "groceryItems": [
                    {"upc": "I1", "description": "Rice", "total": 80.0, "category": "item"},
                ],
                "splitEquallyAmong": [str(test_user.id), str(other.id)],
            }
        ],
    }

    with (
        patch(
            "app.routes.orders.run_extraction",
            new_callable=AsyncMock,
            return_value=mock_items,
        ),
        patch(
            "app.routes.orders.correlate",
            new_callable=AsyncMock,
            return_value={},
        ),
        patch("app.routes.orders.compute_splits", return_value=mock_result),
    ):
        resp = await client.post(
            "/api/v1/orders/",
            headers=auth_headers,
            json={
                "source_id": str(source.id),
                "participant_ids": [str(other.id)],
            },
        )

    assert resp.status_code == 201
    participant_ids = [p["user_id"] for p in resp.json()["participants"]]
    assert str(test_user.id) in participant_ids
    assert str(other.id) in participant_ids


async def test_create_order_edit_splits(
    client: AsyncClient, auth_headers: dict, test_user, session: AsyncSession
):
    """PUT /orders/{id}/splits recomputes split amounts from reassignments."""
    source = await _make_source(session, test_user.id)

    other = User(email="o@x.com", name="O", oauth_provider="google", oauth_id="o-oauth")
    session.add(other)
    await session.flush()

    mock_items = [
        {"id": "I1", "name": "Milk", "quantity": 1, "total": 50.0, "category": "item"},
        {"id": "I2", "name": "Bread", "quantity": 1, "total": 30.0, "category": "item"},
        {"id": "FEE", "name": "Delivery", "quantity": 1, "total": 10.0, "category": "fee"},
    ]
    mock_result = {
        "paidBy": str(test_user.id),
        "noSplit": True,
        "splits": [
            {
                "amount": 90.0,
                "groceryItems": [
                    {"upc": "I1", "description": "Milk", "total": 50.0, "category": "item"},
                    {"upc": "I2", "description": "Bread", "total": 30.0, "category": "item"},
                    {"upc": "FEE", "description": "Delivery", "total": 10.0, "category": "fee"},
                ],
                "splitEquallyAmong": [str(test_user.id)],
            }
        ],
    }

    with (
        patch(
            "app.routes.orders.run_extraction",
            new_callable=AsyncMock,
            return_value=mock_items,
        ),
        patch("app.routes.orders.correlate", new_callable=AsyncMock, return_value={}),
        patch("app.routes.orders.compute_splits", return_value=mock_result),
    ):
        create_resp = await client.post(
            "/api/v1/orders/",
            headers=auth_headers,
            json={
                "source_id": str(source.id),
                "participant_ids": [str(test_user.id), str(other.id)],
            },
        )

    assert create_resp.status_code == 201
    assert create_resp.json()["status"] == "no_split"
    order_id = create_resp.json()["id"]

    # Reassign Milk to other user — should transition to draft
    edit_resp = await client.put(
        f"/api/v1/orders/{order_id}/splits",
        headers=auth_headers,
        json={
            "assignments": [
                {"upc": "I1", "member_ids": [str(other.id)]},
                {"upc": "I2", "member_ids": [str(test_user.id)]},
            ]
        },
    )
    assert edit_resp.status_code == 200
    assert edit_resp.json()["status"] == "draft"
    splits = edit_resp.json()["splits"]
    # Two groups: other (Milk=50 + fee share) and payer (Bread=30 + fee share)
    # Actually fees go to both members since both have items
    total = sum(s["amount"] for s in splits)
    assert total == 90.0


async def test_create_order_no_split_status(
    client: AsyncClient, auth_headers: dict, test_user, session: AsyncSession
):
    """Order with noSplit=False gets status='draft' and Split rows."""
    source = await _make_source(session, test_user.id)

    other = User(email="ns@x.com", name="NS", oauth_provider="google", oauth_id="ns-oauth")
    session.add(other)
    await session.flush()

    mock_items = [
        {"id": "I1", "name": "Milk", "quantity": 1, "total": 50.0, "category": "item"},
    ]
    mock_result = {
        "paidBy": str(test_user.id),
        "noSplit": False,
        "splits": [
            {
                "amount": 50.0,
                "groceryItems": [
                    {"upc": "I1", "description": "Milk", "total": 50.0, "category": "item"},
                ],
                "splitEquallyAmong": [str(test_user.id), str(other.id)],
            }
        ],
    }

    with (
        patch(
            "app.routes.orders.run_extraction",
            new_callable=AsyncMock,
            return_value=mock_items,
        ),
        patch("app.routes.orders.correlate", new_callable=AsyncMock, return_value={}),
        patch("app.routes.orders.compute_splits", return_value=mock_result),
    ):
        resp = await client.post(
            "/api/v1/orders/",
            headers=auth_headers,
            json={
                "source_id": str(source.id),
                "participant_ids": [str(test_user.id), str(other.id)],
            },
        )

    assert resp.status_code == 201
    assert resp.json()["status"] == "draft"
    assert len(resp.json()["splits"]) == 1
    assert resp.json()["splits"][0]["amount"] == 50.0


async def test_cancel_no_split_order(
    client: AsyncClient, auth_headers: dict, test_user, session: AsyncSession
):
    """Can cancel an order with status='no_split'."""
    source = await _make_source(session, test_user.id)

    mock_items = [
        {"id": "I1", "name": "Milk", "quantity": 1, "total": 50.0, "category": "item"},
    ]
    mock_result = {
        "paidBy": str(test_user.id),
        "noSplit": True,
        "splits": [
            {
                "amount": 50.0,
                "groceryItems": [
                    {"upc": "I1", "description": "Milk", "total": 50.0, "category": "item"},
                ],
                "splitEquallyAmong": [str(test_user.id)],
            }
        ],
    }

    with (
        patch(
            "app.routes.orders.run_extraction",
            new_callable=AsyncMock,
            return_value=mock_items,
        ),
        patch("app.routes.orders.correlate", new_callable=AsyncMock, return_value={}),
        patch("app.routes.orders.compute_splits", return_value=mock_result),
    ):
        create_resp = await client.post(
            "/api/v1/orders/",
            headers=auth_headers,
            json={
                "source_id": str(source.id),
                "participant_ids": [str(test_user.id)],
            },
        )

    assert create_resp.json()["status"] == "no_split"
    order_id = create_resp.json()["id"]

    cancel_resp = await client.patch(f"/api/v1/orders/{order_id}/cancel", headers=auth_headers)
    assert cancel_resp.status_code == 200
    assert cancel_resp.json()["status"] == "cancelled"


async def test_edit_splits_rejects_fee_upc(
    client: AsyncClient, auth_headers: dict, test_user, session: AsyncSession
):
    """Sending a fee UPC in assignments returns 400."""
    source = await _make_source(session, test_user.id)

    mock_items = [
        {"id": "I1", "name": "Milk", "quantity": 1, "total": 50.0, "category": "item"},
        {"id": "FEE", "name": "Delivery", "quantity": 1, "total": 10.0, "category": "fee"},
    ]
    mock_result = {
        "paidBy": str(test_user.id),
        "noSplit": True,
        "splits": [
            {
                "amount": 60.0,
                "groceryItems": [
                    {"upc": "I1", "description": "Milk", "total": 50.0, "category": "item"},
                    {"upc": "FEE", "description": "Delivery", "total": 10.0, "category": "fee"},
                ],
                "splitEquallyAmong": [str(test_user.id)],
            }
        ],
    }

    with (
        patch(
            "app.routes.orders.run_extraction",
            new_callable=AsyncMock,
            return_value=mock_items,
        ),
        patch("app.routes.orders.correlate", new_callable=AsyncMock, return_value={}),
        patch("app.routes.orders.compute_splits", return_value=mock_result),
    ):
        create_resp = await client.post(
            "/api/v1/orders/",
            headers=auth_headers,
            json={
                "source_id": str(source.id),
                "participant_ids": [str(test_user.id)],
            },
        )

    order_id = create_resp.json()["id"]

    edit_resp = await client.put(
        f"/api/v1/orders/{order_id}/splits",
        headers=auth_headers,
        json={
            "assignments": [
                {"upc": "I1", "member_ids": [str(test_user.id)]},
                {"upc": "FEE", "member_ids": [str(test_user.id)]},
            ]
        },
    )
    assert edit_resp.status_code == 400
    assert "fee" in edit_resp.json()["detail"].lower()


async def test_edit_splits_requires_all_non_fee_upcs(
    client: AsyncClient, auth_headers: dict, test_user, session: AsyncSession
):
    """Omitting a non-fee UPC from assignments returns 400."""
    source = await _make_source(session, test_user.id)

    mock_items = [
        {"id": "I1", "name": "Milk", "quantity": 1, "total": 50.0, "category": "item"},
        {"id": "I2", "name": "Bread", "quantity": 1, "total": 30.0, "category": "item"},
    ]
    mock_result = {
        "paidBy": str(test_user.id),
        "noSplit": True,
        "splits": [
            {
                "amount": 80.0,
                "groceryItems": [
                    {"upc": "I1", "description": "Milk", "total": 50.0, "category": "item"},
                    {"upc": "I2", "description": "Bread", "total": 30.0, "category": "item"},
                ],
                "splitEquallyAmong": [str(test_user.id)],
            }
        ],
    }

    with (
        patch(
            "app.routes.orders.run_extraction",
            new_callable=AsyncMock,
            return_value=mock_items,
        ),
        patch("app.routes.orders.correlate", new_callable=AsyncMock, return_value={}),
        patch("app.routes.orders.compute_splits", return_value=mock_result),
    ):
        create_resp = await client.post(
            "/api/v1/orders/",
            headers=auth_headers,
            json={
                "source_id": str(source.id),
                "participant_ids": [str(test_user.id)],
            },
        )

    order_id = create_resp.json()["id"]

    # Only send I1, missing I2
    edit_resp = await client.put(
        f"/api/v1/orders/{order_id}/splits",
        headers=auth_headers,
        json={
            "assignments": [
                {"upc": "I1", "member_ids": [str(test_user.id)]},
            ]
        },
    )
    assert edit_resp.status_code == 400
    assert "Missing" in edit_resp.json()["detail"]
