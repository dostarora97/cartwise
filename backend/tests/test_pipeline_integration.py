"""Pipeline integration tests — full order flows with mocked externals.

Exercises: source creation → extraction → correlate → splits → approve.
Real Postgres, real pdfplumber, real business logic. Only AI, Swiggy MCP,
and Splitwise HTTP are mocked.
"""

import json
import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.jwt import create_test_token
from app.errors import ProblemDetailError
from app.models.meal_plan import MealPlan, MealPlanItem
from app.models.menu_item import MenuItem
from app.models.order import Order, OrderParticipant
from app.models.order_source import OrderSource, OrderSourceType
from app.models.split import Split
from app.models.splitwise_audit import SplitwiseAuditLog
from app.models.user import User

# --- Fixtures ---


@pytest.fixture
async def alice(session: AsyncSession) -> User:
    user = User(
        email="alice@test.com",
        name="Alice",
        oauth_provider="google",
        oauth_id="alice-oauth",
        splitwise_user_id=99001,
    )
    session.add(user)
    await session.commit()
    await session.refresh(user)
    return user


@pytest.fixture
async def bob(session: AsyncSession) -> User:
    user = User(
        email="bob@test.com",
        name="Bob",
        oauth_provider="google",
        oauth_id="bob-oauth",
        splitwise_user_id=99002,
    )
    session.add(user)
    await session.commit()
    await session.refresh(user)
    return user


@pytest.fixture
def alice_headers(alice: User) -> dict[str, str]:
    token = create_test_token(alice.oauth_id, alice.email)
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
async def menu_items_and_plans(session: AsyncSession, alice: User, bob: User):
    """Create menu items and meal plans for bipartite graph testing.

    Alice: Chicken Curry, Green Salad
    Bob: Green Salad
    """
    chicken_curry = MenuItem(
        name="Chicken Curry",
        body="Chicken breast, onion, tomato, spices",
        created_by=alice.id,
        updated_by=alice.id,
    )
    green_salad = MenuItem(
        name="Green Salad",
        body="Cucumber, tomato, lemon",
        created_by=alice.id,
        updated_by=alice.id,
    )
    session.add_all([chicken_curry, green_salad])
    await session.flush()

    alice_plan = MealPlan(user_id=alice.id)
    bob_plan = MealPlan(user_id=bob.id)
    session.add_all([alice_plan, bob_plan])
    await session.flush()

    session.add_all(
        [
            MealPlanItem(meal_plan_id=alice_plan.id, menu_item_id=chicken_curry.id),
            MealPlanItem(meal_plan_id=alice_plan.id, menu_item_id=green_salad.id),
            MealPlanItem(meal_plan_id=bob_plan.id, menu_item_id=green_salad.id),
        ]
    )
    await session.commit()
    return {"chicken_curry": chicken_curry, "green_salad": green_salad}


# --- Helpers ---


def _mock_classify_response(prompt: str) -> dict:
    """Deterministic classify: known fees → 'fee', everything else → 'item'."""
    fee_keywords = ["delivery", "handling", "platform", "packing", "service fee"]
    prompt_lower = prompt.lower()
    for kw in fee_keywords:
        if kw in prompt_lower:
            return {"category": "fee"}
    return {"category": "item"}


def _mock_correlate_response(prompt: str, menu_items: dict) -> dict:
    """Deterministic correlate based on menu item name in the prompt."""
    if "Chicken Curry" in prompt:
        return {"matched_upcs": ["8906108191331"]}  # Chicken Breast
    if "Green Salad" in prompt:
        return {"matched_upcs": ["3600476005000"]}  # English Cucumber
    return {"matched_upcs": []}


def _make_mock_generate(menu_items: dict | None = None):
    """Build a mock for app.ai.client.generate that handles classify + correlate."""

    async def mock_generate(system: str, prompt: str, schema: dict) -> dict:
        if "classify" in system.lower():
            return _mock_classify_response(prompt)
        if "match" in system.lower() or "correlate" in system.lower():
            return _mock_correlate_response(prompt, menu_items or {})
        return {"category": "item"}

    return mock_generate


def _swiggy_orders_response(order_id: str) -> str:
    """Canned get_orders response."""
    return json.dumps(
        {
            "orders": [
                {
                    "orderId": order_id,
                    "items": [
                        {"itemId": "SW1", "name": "Paneer Tikka", "quantity": 1},
                        {"itemId": "SW2", "name": "Naan", "quantity": 2},
                        {"itemId": "SW3", "name": "Dal Makhani", "quantity": 1},
                    ],
                }
            ]
        }
    )


def _swiggy_track_response() -> str:
    """Canned track_order response."""
    return json.dumps(
        {
            "items": [
                {"name": "1 x Paneer Tikka", "total": 220},
                {"name": "2 x Naan", "total": 80},
                {"name": "1 x Dal Makhani", "total": 180},
            ],
            "billDetails": {
                "deliveryFee": 30,
                "handlingFee": 5,
                "platformFee": 0,
                "packagingCharges": 0,
                "surgeFee": 0,
            },
        }
    )


def _mock_call_tool_side_effect(order_id: str):
    """Side effect for call_tool that returns canned Swiggy MCP responses."""
    call_count = 0

    async def side_effect(token, tool_name, arguments):
        nonlocal call_count
        call_count += 1
        block = MagicMock()
        if tool_name == "get_orders":
            block.text = _swiggy_orders_response(order_id)
        else:
            block.text = _swiggy_track_response()
        return [block]

    return side_effect


def _mock_splitwise_post_success():
    """Mock httpx response for successful Splitwise create_expense."""
    call_count = [0]

    def post(url, **kwargs):
        call_count[0] += 1
        resp = MagicMock()
        resp.status_code = 200
        resp.raise_for_status = MagicMock()
        resp.json.return_value = {
            "expenses": [{"id": 10000 + call_count[0]}],
            "errors": [],
        }
        return resp

    return post


def _mock_splitwise_post_partial_failure():
    """First call succeeds, second call returns errors."""
    call_count = [0]

    def post(url, **kwargs):
        call_count[0] += 1
        resp = MagicMock()
        resp.status_code = 200
        resp.raise_for_status = MagicMock()
        if call_count[0] == 1:
            resp.json.return_value = {"expenses": [{"id": 20001}], "errors": []}
        else:
            resp.json.return_value = {"expenses": [{}], "errors": ["Invalid request"]}
        return resp

    return post


# --- Tests ---


async def test_swiggy_pipeline_happy_path(
    client: AsyncClient,
    alice_headers: dict,
    alice: User,
    bob: User,
    session: AsyncSession,
    menu_items_and_plans: dict,
):
    """Full Swiggy pipeline: source → extraction → correlate → splits."""
    # Create swiggy source
    source_resp = await client.post(
        "/api/v1/orders/sources/",
        headers=alice_headers,
        json={"type": "swiggy_order", "raw_data": {"swiggy_order_id": "SWG999"}},
    )
    assert source_resp.status_code == 201
    source_id = source_resp.json()["id"]

    with (
        patch(
            "app.services.swiggy.extract.get_valid_token",
            new_callable=AsyncMock,
            return_value="fake-token",
        ),
        patch(
            "app.services.swiggy.extract.call_tool",
            new_callable=AsyncMock,
            side_effect=_mock_call_tool_side_effect("SWG999"),
        ),
        patch(
            "app.services.classify.generate",
            side_effect=_make_mock_generate(menu_items_and_plans),
        ),
        patch(
            "app.services.correlate.generate",
            side_effect=_make_mock_generate(menu_items_and_plans),
        ),
    ):
        order_resp = await client.post(
            "/api/v1/orders/",
            headers=alice_headers,
            json={
                "source_id": source_id,
                "participant_ids": [str(alice.id), str(bob.id)],
            },
        )

    assert order_resp.status_code == 201
    data = order_resp.json()
    assert data["status"] == "draft"
    assert len(data["splits"]) > 0
    assert len(data["participants"]) == 2

    # Verify source was updated with raw API responses
    session.expire_all()
    source = await session.get(OrderSource, uuid.UUID(source_id))
    assert source.items is not None
    assert len(source.items) > 0
    assert "orders_response" in source.raw_data
    assert "track_response" in source.raw_data


async def test_swiggy_pipeline_token_expired(
    client: AsyncClient,
    alice_headers: dict,
    alice: User,
    session: AsyncSession,
):
    """Token expired → ProblemDetailError → 422 with problem+json."""
    source_resp = await client.post(
        "/api/v1/orders/sources/",
        headers=alice_headers,
        json={"type": "swiggy_order", "raw_data": {"swiggy_order_id": "SWG000"}},
    )
    source_id = source_resp.json()["id"]

    error = ProblemDetailError(
        type="tag:cartwise.app,2026:problem/provider-auth-required",
        title="External provider authentication required",
        status=422,
        detail="Your Swiggy connection has expired. Please reconnect.",
        provider="swiggy",
    )

    with patch(
        "app.services.swiggy.extract.get_valid_token",
        new_callable=AsyncMock,
        side_effect=error,
    ):
        resp = await client.post(
            "/api/v1/orders/",
            headers=alice_headers,
            json={"source_id": source_id, "participant_ids": [str(alice.id)]},
        )

    assert resp.status_code == 422
    body = resp.json()
    assert body["type"] == "tag:cartwise.app,2026:problem/provider-auth-required"
    assert body["provider"] == "swiggy"


async def test_invoice_pipeline_with_mocked_ai(
    client: AsyncClient,
    alice_headers: dict,
    alice: User,
    bob: User,
    session: AsyncSession,
    menu_items_and_plans: dict,
):
    """Invoice pipeline: real PDF → pdfplumber → mocked classify/correlate → splits."""
    # Upload real PDF
    with open("tests/fixtures/test_invoice.pdf", "rb") as f:
        pdf_content = f.read()

    upload_resp = await client.post(
        "/api/v1/orders/sources/upload",
        headers=alice_headers,
        files={"file": ("invoice.pdf", pdf_content, "application/pdf")},
    )
    assert upload_resp.status_code == 201
    source_id = upload_resp.json()["source_id"]

    with (
        patch(
            "app.services.classify.generate",
            side_effect=_make_mock_generate(menu_items_and_plans),
        ),
        patch(
            "app.services.correlate.generate",
            side_effect=_make_mock_generate(menu_items_and_plans),
        ),
    ):
        order_resp = await client.post(
            "/api/v1/orders/",
            headers=alice_headers,
            json={
                "source_id": source_id,
                "participant_ids": [str(alice.id), str(bob.id)],
            },
        )

    assert order_resp.status_code == 201
    data = order_resp.json()
    assert data["status"] == "draft"
    assert len(data["splits"]) >= 1

    # Verify items were classified (all should have category)
    session.expire_all()
    source = await session.get(OrderSource, uuid.UUID(source_id))
    assert source.items is not None
    assert all("category" in item for item in source.items)


async def test_approve_order_happy_path(
    client: AsyncClient,
    alice_headers: dict,
    alice: User,
    bob: User,
    session: AsyncSession,
):
    """Approve draft → Splitwise expenses created → order completed."""
    # Create order directly in DB with splits
    order = Order(
        paid_by=alice.id,
        snapshot={"members": {str(alice.id): [], str(bob.id): []}, "uses": {}, "menu_items": []},
        result={
            "paidBy": str(alice.id),
            "splits": [
                {
                    "amount": 100.0,
                    "groceryItems": [{"upc": "A1", "description": "Chicken", "total": 100.0}],
                    "splitEquallyAmong": [str(alice.id), str(bob.id)],
                }
            ],
        },
    )
    session.add(order)
    await session.flush()

    session.add(OrderParticipant(order_id=order.id, user_id=alice.id))
    session.add(OrderParticipant(order_id=order.id, user_id=bob.id))
    session.add(
        Split(
            order_id=order.id,
            amount=100.0,
            grocery_items=[{"upc": "A1", "description": "Chicken", "total": 100.0}],
            member_ids=[str(alice.id), str(bob.id)],
        )
    )
    await session.commit()

    mock_http = MagicMock()
    mock_http.post = _mock_splitwise_post_success()

    with (
        patch("app.services.splitwise._http", mock_http),
        patch(
            "app.services.vault.get_secret",
            new_callable=AsyncMock,
            return_value="fake-sw-token",
        ),
    ):
        resp = await client.post(f"/api/v1/orders/{order.id}/approve", headers=alice_headers)

    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "completed"

    # Verify audit rows exist
    result = await session.execute(
        select(SplitwiseAuditLog).where(SplitwiseAuditLog.order_id == order.id)
    )
    audits = result.scalars().all()
    assert len(audits) == 1
    assert audits[0].status == "success"
    assert audits[0].splitwise_expense_id is not None


async def test_approve_order_partial_failure(
    client: AsyncClient,
    alice_headers: dict,
    alice: User,
    bob: User,
    session: AsyncSession,
):
    """One split succeeds, one fails → order stays draft."""
    order = Order(
        paid_by=alice.id,
        snapshot={"members": {str(alice.id): [], str(bob.id): []}, "uses": {}, "menu_items": []},
        result={
            "paidBy": str(alice.id),
            "splits": [
                {
                    "amount": 80.0,
                    "groceryItems": [{"upc": "B1", "description": "Rice", "total": 80.0}],
                    "splitEquallyAmong": [str(alice.id), str(bob.id)],
                },
                {
                    "amount": 20.0,
                    "groceryItems": [{"upc": "B2", "description": "Delivery Fee", "total": 20.0}],
                    "splitEquallyAmong": [str(alice.id), str(bob.id)],
                },
            ],
        },
    )
    session.add(order)
    await session.flush()

    session.add(OrderParticipant(order_id=order.id, user_id=alice.id))
    session.add(OrderParticipant(order_id=order.id, user_id=bob.id))
    session.add(
        Split(
            order_id=order.id,
            amount=80.0,
            grocery_items=[{"upc": "B1", "description": "Rice", "total": 80.0}],
            member_ids=[str(alice.id), str(bob.id)],
        )
    )
    session.add(
        Split(
            order_id=order.id,
            amount=20.0,
            grocery_items=[{"upc": "B2", "description": "Delivery Fee", "total": 20.0}],
            member_ids=[str(alice.id), str(bob.id)],
        )
    )
    await session.commit()

    mock_http = MagicMock()
    mock_http.post = _mock_splitwise_post_partial_failure()

    with (
        patch("app.services.splitwise._http", mock_http),
        patch(
            "app.services.vault.get_secret",
            new_callable=AsyncMock,
            return_value="fake-sw-token",
        ),
    ):
        resp = await client.post(f"/api/v1/orders/{order.id}/approve", headers=alice_headers)

    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "draft"

    statuses = {s["status"] for s in data["splits"]}
    assert "success" in statuses
    assert "failed" in statuses


async def test_edit_splits_recomputes(
    client: AsyncClient,
    alice_headers: dict,
    alice: User,
    bob: User,
    session: AsyncSession,
):
    """PUT /orders/{id}/splits reassigns items and recomputes amounts."""
    order = Order(
        paid_by=alice.id,
        snapshot={"members": {str(alice.id): [], str(bob.id): []}, "uses": {}, "menu_items": []},
        result={
            "paidBy": str(alice.id),
            "splits": [
                {
                    "amount": 150.0,
                    "groceryItems": [
                        {"upc": "C1", "description": "Milk", "total": 50.0},
                        {"upc": "C2", "description": "Bread", "total": 100.0},
                    ],
                    "splitEquallyAmong": [str(alice.id)],
                }
            ],
        },
    )
    session.add(order)
    await session.flush()

    session.add(OrderParticipant(order_id=order.id, user_id=alice.id))
    session.add(OrderParticipant(order_id=order.id, user_id=bob.id))
    session.add(
        Split(
            order_id=order.id,
            amount=150.0,
            grocery_items=[
                {"upc": "C1", "description": "Milk", "total": 50.0},
                {"upc": "C2", "description": "Bread", "total": 100.0},
            ],
            member_ids=[str(alice.id)],
        )
    )
    await session.commit()

    # Reassign: Milk to alice only, Bread to alice+bob
    resp = await client.put(
        f"/api/v1/orders/{order.id}/splits",
        headers=alice_headers,
        json={
            "assignments": [
                {"upc": "C1", "member_ids": [str(alice.id)]},
                {"upc": "C2", "member_ids": [str(alice.id), str(bob.id)]},
            ]
        },
    )

    assert resp.status_code == 200
    splits = resp.json()["splits"]
    total_amount = sum(s["amount"] for s in splits)
    assert total_amount == 150.0


async def test_create_order_idempotent(
    client: AsyncClient,
    alice_headers: dict,
    alice: User,
    session: AsyncSession,
):
    """Second POST with same source_id returns existing order."""
    source = OrderSource(
        type=OrderSourceType.invoice,
        raw_data={"storage_path": "/fake"},
        items=[{"id": "X", "name": "Eggs", "quantity": 6, "total": 78.0, "category": "item"}],
        created_by=alice.id,
    )
    session.add(source)
    await session.flush()

    order = Order(
        paid_by=alice.id,
        source_id=source.id,
        snapshot={"members": {}, "uses": {}, "menu_items": []},
        result={"paidBy": str(alice.id), "splits": []},
    )
    session.add(order)
    await session.flush()
    session.add(OrderParticipant(order_id=order.id, user_id=alice.id))
    await session.commit()

    resp = await client.post(
        "/api/v1/orders/",
        headers=alice_headers,
        json={"source_id": str(source.id), "participant_ids": [str(alice.id)]},
    )

    assert resp.status_code == 201
    assert resp.json()["id"] == str(order.id)


async def test_approve_missing_splitwise_user_id(
    client: AsyncClient,
    alice_headers: dict,
    alice: User,
    session: AsyncSession,
):
    """Approve fails if a participant has no splitwise_user_id."""
    # Create a user without splitwise_user_id
    carol = User(
        email="carol@test.com",
        name="Carol",
        oauth_provider="google",
        oauth_id="carol-oauth",
    )
    session.add(carol)
    await session.flush()

    order = Order(
        paid_by=alice.id,
        snapshot={"members": {}, "uses": {}, "menu_items": []},
        result={
            "paidBy": str(alice.id),
            "splits": [
                {
                    "amount": 50.0,
                    "groceryItems": [{"upc": "D1", "description": "Item", "total": 50.0}],
                    "splitEquallyAmong": [str(alice.id), str(carol.id)],
                }
            ],
        },
    )
    session.add(order)
    await session.flush()

    session.add(OrderParticipant(order_id=order.id, user_id=alice.id))
    session.add(OrderParticipant(order_id=order.id, user_id=carol.id))
    session.add(
        Split(
            order_id=order.id,
            amount=50.0,
            grocery_items=[{"upc": "D1", "description": "Item", "total": 50.0}],
            member_ids=[str(alice.id), str(carol.id)],
        )
    )
    await session.commit()

    resp = await client.post(f"/api/v1/orders/{order.id}/approve", headers=alice_headers)

    assert resp.status_code == 400
    assert "Splitwise user ID" in resp.json()["detail"]


async def test_approve_non_draft_rejected(
    client: AsyncClient,
    alice_headers: dict,
    alice: User,
    session: AsyncSession,
):
    """Cannot approve an order that is not in draft status."""
    order = Order(
        paid_by=alice.id,
        status="completed",
        snapshot={"members": {}, "uses": {}, "menu_items": []},
        result={"paidBy": str(alice.id), "splits": []},
    )
    session.add(order)
    await session.flush()
    session.add(OrderParticipant(order_id=order.id, user_id=alice.id))
    await session.commit()

    resp = await client.post(f"/api/v1/orders/{order.id}/approve", headers=alice_headers)

    assert resp.status_code == 400
    assert "status" in resp.json()["detail"].lower()
