"""
Full end-to-end integration test — no mocks.

Tests every endpoint, every flow, happy path and error cases.
Real PostgreSQL, real Ollama, real PDF extraction.

Requires:
- Docker postgres-test running on port 5433
- Ollama running with qwen2.5:3b model
- Test PDF at ../data/ORD95806394221/invoice.pdf

Run: uv run pytest tests/test_integration.py -v -s
"""

import json
import uuid
from pathlib import Path

import httpx
import pytest
from httpx import AsyncClient

INVOICE_PDF = Path(__file__).parent / "fixtures" / "test_invoice.pdf"


def _auth(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


# ================================================================
# Prerequisite checks — skip entire module if infra is down
# ================================================================


def _check_postgres():
    """Check test PostgreSQL is reachable."""
    import asyncio

    import asyncpg

    async def _try():
        try:
            conn = await asyncpg.connect(
                "postgresql://postgres:postgres@localhost:5433/cartwise_test"
            )
            await conn.close()
            return True
        except Exception:
            return False

    return asyncio.run(_try())


def _check_ollama():
    """Check Ollama is running and has the model."""
    try:
        resp = httpx.get("http://localhost:11434/api/tags", timeout=5)
        models = [m["name"] for m in resp.json().get("models", [])]
        return any("qwen2.5:3b" in m for m in models)
    except Exception:
        return False


def _check_pdf():
    return INVOICE_PDF.exists()


# Run checks at module level — skip all tests if prereqs fail
_pg_ok = _check_postgres()
_ollama_ok = _check_ollama()
_pdf_ok = _check_pdf()

pytestmark = [
    pytest.mark.skipif(not _pg_ok, reason="PostgreSQL test DB not reachable on port 5433"),
    pytest.mark.skipif(not _ollama_ok, reason="Ollama not running or qwen2.5:3b not available"),
    pytest.mark.skipif(not _pdf_ok, reason=f"Test PDF not found at {INVOICE_PDF}"),
]


# ================================================================
# Helpers
# ================================================================


async def _login(client: AsyncClient, email: str, name: str) -> tuple[str, str]:
    """Dev-login, return (token, user_id)."""
    resp = await client.post("/api/v1/auth/dev-login", json={"email": email, "name": name})
    assert resp.status_code == 200, f"Dev login failed: {resp.text}"
    return resp.json()["access_token"], resp.json()["user"]["id"]


async def _create_menu_item(client: AsyncClient, token: str, name: str, body: str) -> str:
    """Create a menu item, return its ID."""
    resp = await client.post(
        "/api/v1/menu-items/",
        json={"name": name, "body": body},
        headers=_auth(token),
    )
    assert resp.status_code == 201
    return resp.json()["id"]


# ================================================================
# Tests — healthz
# ================================================================


async def test_healthz(client: AsyncClient):
    resp = await client.get("/healthz")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}


# ================================================================
# Tests — auth
# ================================================================


async def test_dev_login_creates_user(client: AsyncClient):
    resp = await client.post(
        "/api/v1/auth/dev-login",
        json={"email": "new@test.com", "name": "New User"},
    )
    assert resp.status_code == 200
    assert resp.json()["token_type"] == "bearer"
    assert resp.json()["user"]["email"] == "new@test.com"
    assert resp.json()["user"]["name"] == "New User"
    assert resp.json()["user"]["oauth_provider"] == "dev"


async def test_dev_login_idempotent(client: AsyncClient):
    """Logging in twice with same email returns the same user."""
    resp1 = await client.post(
        "/api/v1/auth/dev-login", json={"email": "same@test.com", "name": "Same"}
    )
    resp2 = await client.post(
        "/api/v1/auth/dev-login", json={"email": "same@test.com", "name": "Same"}
    )
    assert resp1.json()["user"]["id"] == resp2.json()["user"]["id"]


async def test_auth_me(client: AsyncClient):
    token, _ = await _login(client, "me@test.com", "Me")
    resp = await client.get("/api/v1/auth/me", headers=_auth(token))
    assert resp.status_code == 200
    assert resp.json()["email"] == "me@test.com"


async def test_auth_me_no_token(client: AsyncClient):
    resp = await client.get("/api/v1/auth/me")
    assert resp.status_code in (401, 403)


async def test_auth_me_invalid_token(client: AsyncClient):
    resp = await client.get("/api/v1/auth/me", headers=_auth("garbage.token.here"))
    assert resp.status_code == 401


# ================================================================
# Tests — users
# ================================================================


async def test_list_users(client: AsyncClient):
    await _login(client, "u1@test.com", "User1")
    await _login(client, "u2@test.com", "User2")
    resp = await client.get("/api/v1/users/")
    assert resp.status_code == 200
    emails = [u["email"] for u in resp.json()]
    assert "u1@test.com" in emails
    assert "u2@test.com" in emails


async def test_get_user_by_id(client: AsyncClient):
    _, user_id = await _login(client, "getme@test.com", "GetMe")
    resp = await client.get(f"/api/v1/users/{user_id}")
    assert resp.status_code == 200
    assert resp.json()["name"] == "GetMe"


async def test_get_user_not_found(client: AsyncClient):
    fake_id = str(uuid.uuid4())
    resp = await client.get(f"/api/v1/users/{fake_id}")
    assert resp.status_code == 404


async def test_update_own_profile(client: AsyncClient):
    token, user_id = await _login(client, "update@test.com", "Before")
    resp = await client.patch(
        f"/api/v1/users/{user_id}",
        json={"name": "After", "phone": "+911234567890"},
        headers=_auth(token),
    )
    assert resp.status_code == 200
    assert resp.json()["name"] == "After"
    assert resp.json()["phone"] == "+911234567890"


async def test_update_other_user_forbidden(client: AsyncClient):
    token_a, _ = await _login(client, "a@test.com", "A")
    _, id_b = await _login(client, "b@test.com", "B")
    resp = await client.patch(
        f"/api/v1/users/{id_b}",
        json={"name": "Hacked"},
        headers=_auth(token_a),
    )
    assert resp.status_code == 403


# ================================================================
# Tests — menu items
# ================================================================


async def test_create_menu_item(client: AsyncClient):
    token, _ = await _login(client, "chef@test.com", "Chef")
    resp = await client.post(
        "/api/v1/menu-items/",
        json={"name": "Pasta", "body": "Boil pasta.\n\npasta, sauce"},
        headers=_auth(token),
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["name"] == "Pasta"
    assert data["status"] == "active"


async def test_list_menu_items_with_filters(client: AsyncClient):
    token, user_id = await _login(client, "filter@test.com", "Filter")
    await _create_menu_item(client, token, "Active1", "body")
    id2 = await _create_menu_item(client, token, "Active2", "body")

    # Archive one
    await client.patch(f"/api/v1/menu-items/{id2}/archive", headers=_auth(token))

    # Default listing (active only)
    resp = await client.get("/api/v1/menu-items/")
    names = [i["name"] for i in resp.json()]
    assert "Active1" in names
    assert "Active2" not in names

    # Archived listing
    resp = await client.get("/api/v1/menu-items/?status=archived")
    names = [i["name"] for i in resp.json()]
    assert "Active2" in names

    # Filter by creator
    resp = await client.get(f"/api/v1/menu-items/?created_by={user_id}")
    assert len(resp.json()) >= 1


async def test_get_menu_item_by_id(client: AsyncClient):
    token, _ = await _login(client, "get@test.com", "Get")
    item_id = await _create_menu_item(client, token, "GetThis", "body")
    resp = await client.get(f"/api/v1/menu-items/{item_id}")
    assert resp.status_code == 200
    assert resp.json()["name"] == "GetThis"


async def test_get_menu_item_not_found(client: AsyncClient):
    resp = await client.get(f"/api/v1/menu-items/{uuid.uuid4()}")
    assert resp.status_code == 404


async def test_update_menu_item(client: AsyncClient):
    token, _ = await _login(client, "edit@test.com", "Editor")
    item_id = await _create_menu_item(client, token, "Original", "old body")
    resp = await client.patch(
        f"/api/v1/menu-items/{item_id}",
        json={"name": "Updated", "body": "new body"},
        headers=_auth(token),
    )
    assert resp.status_code == 200
    assert resp.json()["name"] == "Updated"
    assert resp.json()["body"] == "new body"


async def test_archive_menu_item(client: AsyncClient):
    token, _ = await _login(client, "archiver@test.com", "Archiver")
    item_id = await _create_menu_item(client, token, "ToArchive", "body")
    resp = await client.patch(f"/api/v1/menu-items/{item_id}/archive", headers=_auth(token))
    assert resp.status_code == 200
    assert resp.json()["status"] == "archived"


# ================================================================
# Tests — meal plans
# ================================================================


async def test_empty_meal_plan(client: AsyncClient):
    _, user_id = await _login(client, "empty_plan@test.com", "Empty")
    resp = await client.get(f"/api/v1/meal-plans/{user_id}")
    assert resp.status_code == 200
    assert resp.json()["items"] == []


async def test_set_meal_plan(client: AsyncClient):
    token, user_id = await _login(client, "set_plan@test.com", "Setter")
    id1 = await _create_menu_item(client, token, "Item1", "body")
    id2 = await _create_menu_item(client, token, "Item2", "body")

    resp = await client.put(
        f"/api/v1/meal-plans/{user_id}",
        json={"menu_item_ids": [id1, id2]},
        headers=_auth(token),
    )
    assert resp.status_code == 200
    assert len(resp.json()["items"]) == 2


async def test_set_meal_plan_nonexistent_item(client: AsyncClient):
    token, user_id = await _login(client, "bad_plan@test.com", "BadPlan")
    resp = await client.put(
        f"/api/v1/meal-plans/{user_id}",
        json={"menu_item_ids": [str(uuid.uuid4())]},
        headers=_auth(token),
    )
    assert resp.status_code == 404


async def test_add_item_to_plan(client: AsyncClient):
    token, user_id = await _login(client, "add_plan@test.com", "Adder")
    id1 = await _create_menu_item(client, token, "AddMe", "body")

    resp = await client.post(
        f"/api/v1/meal-plans/{user_id}/items",
        json={"menu_item_id": id1},
        headers=_auth(token),
    )
    assert resp.status_code == 200
    assert len(resp.json()["items"]) == 1


async def test_add_item_idempotent(client: AsyncClient):
    token, user_id = await _login(client, "idem@test.com", "Idem")
    item_id = await _create_menu_item(client, token, "Idem", "body")

    await client.post(
        f"/api/v1/meal-plans/{user_id}/items",
        json={"menu_item_id": item_id},
        headers=_auth(token),
    )
    resp = await client.post(
        f"/api/v1/meal-plans/{user_id}/items",
        json={"menu_item_id": item_id},
        headers=_auth(token),
    )
    assert len(resp.json()["items"]) == 1  # Not duplicated


async def test_add_nonexistent_item_to_plan(client: AsyncClient):
    token, user_id = await _login(client, "add404@test.com", "Add404")
    resp = await client.post(
        f"/api/v1/meal-plans/{user_id}/items",
        json={"menu_item_id": str(uuid.uuid4())},
        headers=_auth(token),
    )
    assert resp.status_code == 404


async def test_remove_item_from_plan(client: AsyncClient):
    token, user_id = await _login(client, "remove@test.com", "Remover")
    id1 = await _create_menu_item(client, token, "Keep", "body")
    id2 = await _create_menu_item(client, token, "Remove", "body")

    await client.put(
        f"/api/v1/meal-plans/{user_id}",
        json={"menu_item_ids": [id1, id2]},
        headers=_auth(token),
    )
    resp = await client.delete(f"/api/v1/meal-plans/{user_id}/items/{id2}", headers=_auth(token))
    assert resp.status_code == 200
    item_ids = [i["menu_item"]["id"] for i in resp.json()["items"]]
    assert id1 in item_ids
    assert id2 not in item_ids


async def test_replace_meal_plan(client: AsyncClient):
    """Setting a plan replaces the previous one entirely."""
    token, user_id = await _login(client, "replace@test.com", "Replacer")
    id1 = await _create_menu_item(client, token, "Old", "body")
    id2 = await _create_menu_item(client, token, "New", "body")

    await client.put(
        f"/api/v1/meal-plans/{user_id}",
        json={"menu_item_ids": [id1]},
        headers=_auth(token),
    )
    resp = await client.put(
        f"/api/v1/meal-plans/{user_id}",
        json={"menu_item_ids": [id2]},
        headers=_auth(token),
    )
    item_ids = [i["menu_item"]["id"] for i in resp.json()["items"]]
    assert id2 in item_ids
    assert id1 not in item_ids


# ================================================================
# Tests — orders (full pipeline with real Ollama)
# ================================================================


async def test_order_full_pipeline(client: AsyncClient):
    """The main event: upload PDF → extract → classify → correlate → split."""
    # Setup users
    alice_token, alice_id = await _login(client, "alice_order@test.com", "Alice")
    bob_token, bob_id = await _login(client, "bob_order@test.com", "Bob")
    carol_token, carol_id = await _login(client, "carol_order@test.com", "Carol")

    # Create menu items with ingredients that match the invoice
    chicken_id = await _create_menu_item(
        client,
        alice_token,
        "Chicken Curry",
        "Cook chicken with onions and spices, squeeze lemon.\n\nboneless chicken breast, onion, lemon, spices",
    )
    salad_id = await _create_menu_item(
        client,
        bob_token,
        "Green Salad",
        "Chop cucumber and cherry tomatoes, dress with lemon.\n\ncucumber, cherry tomato, lemon",
    )
    tea_id = await _create_menu_item(
        client, carol_token, "Milk Tea", "Boil milk with tea leaves.\n\nmilk"
    )

    # Set meal plans
    await client.put(
        f"/api/v1/meal-plans/{alice_id}",
        json={"menu_item_ids": [chicken_id, salad_id]},
        headers=_auth(alice_token),
    )
    await client.put(
        f"/api/v1/meal-plans/{bob_id}",
        json={"menu_item_ids": [salad_id]},
        headers=_auth(bob_token),
    )
    await client.put(
        f"/api/v1/meal-plans/{carol_id}",
        json={"menu_item_ids": [tea_id]},
        headers=_auth(carol_token),
    )

    # Upload invoice
    with open(INVOICE_PDF, "rb") as f:
        order_resp = await client.post(
            "/api/v1/orders/",
            files={"file": ("invoice.pdf", f, "application/pdf")},
            data={"participant_ids": json.dumps([alice_id, bob_id, carol_id])},
            headers=_auth(alice_token),
            timeout=120.0,
        )

    assert order_resp.status_code == 201, f"Order failed: {order_resp.text}"
    order = order_resp.json()

    # Verify result structure
    assert order["status"] == "draft"
    assert order["paid_by"] == alice_id
    assert len(order["participants"]) == 3
    assert order["result"] is not None
    assert order["result"]["paidBy"] == alice_id
    assert len(order["result"]["splits"]) > 0

    # Verify snapshot was saved
    assert order["snapshot"] is not None
    assert "members" in order["snapshot"]
    assert "uses" in order["snapshot"]

    # Verify split rows were created
    assert len(order["splits"]) > 0
    for s in order["splits"]:
        assert s["status"] == "pending"
        assert s["amount"] > 0
        assert len(s["member_ids"]) > 0

    # Every split has required fields
    for split in order["result"]["splits"]:
        assert "amount" in split
        assert "groceryItems" in split
        assert "splitEquallyAmong" in split
        assert split["amount"] > 0
        assert len(split["splitEquallyAmong"]) > 0

    # Fees should be split among all 3
    fee_splits = [s for s in order["result"]["splits"] if len(s["splitEquallyAmong"]) == 3]
    assert len(fee_splits) >= 1, "Expected at least one split among all 3 participants (fees)"

    order_id = order["id"]
    print(f"\n  Pipeline: {len(order['result']['splits'])} splits")
    for s in order["result"]["splits"]:
        print(f"    ₹{s['amount']:>8.2f} among {len(s['splitEquallyAmong'])} member(s)")

    # ---- List orders ----
    alice_orders = await client.get("/api/v1/orders/", headers=_auth(alice_token))
    assert alice_orders.status_code == 200
    assert any(o["id"] == order_id for o in alice_orders.json())

    bob_orders = await client.get("/api/v1/orders/", headers=_auth(bob_token))
    assert any(o["id"] == order_id for o in bob_orders.json())

    carol_orders = await client.get("/api/v1/orders/", headers=_auth(carol_token))
    assert any(o["id"] == order_id for o in carol_orders.json())

    # ---- Get order by ID ----
    detail = await client.get(f"/api/v1/orders/{order_id}", headers=_auth(bob_token))
    assert detail.status_code == 200
    assert detail.json()["id"] == order_id


async def test_order_bad_participant_ids(client: AsyncClient):
    token, _ = await _login(client, "bad_order@test.com", "BadOrder")
    with open(INVOICE_PDF, "rb") as f:
        resp = await client.post(
            "/api/v1/orders/",
            files={"file": ("invoice.pdf", f, "application/pdf")},
            data={"participant_ids": "not-valid-json"},
            headers=_auth(token),
        )
    assert resp.status_code == 400


async def test_order_visible_to_non_participant(client: AsyncClient):
    """Any authenticated user can view any order (open visibility)."""
    alice_token, alice_id = await _login(client, "alice_priv@test.com", "AlicePriv")
    bob_token, bob_id = await _login(client, "bob_priv@test.com", "BobPriv")
    outsider_token, _ = await _login(client, "outsider@test.com", "Outsider")

    # Create minimal menu item + plan so pipeline can run
    item_id = await _create_menu_item(client, alice_token, "Quick", "body")
    await client.put(
        f"/api/v1/meal-plans/{alice_id}",
        json={"menu_item_ids": [item_id]},
        headers=_auth(alice_token),
    )
    await client.put(
        f"/api/v1/meal-plans/{bob_id}",
        json={"menu_item_ids": [item_id]},
        headers=_auth(bob_token),
    )

    with open(INVOICE_PDF, "rb") as f:
        order_resp = await client.post(
            "/api/v1/orders/",
            files={"file": ("invoice.pdf", f, "application/pdf")},
            data={"participant_ids": json.dumps([alice_id, bob_id])},
            headers=_auth(alice_token),
            timeout=120.0,
        )
    assert order_resp.status_code == 201
    order_id = order_resp.json()["id"]

    # Outsider can view → 200
    resp = await client.get(f"/api/v1/orders/{order_id}", headers=_auth(outsider_token))
    assert resp.status_code == 200


async def test_order_not_found(client: AsyncClient):
    token, _ = await _login(client, "order404@test.com", "Order404")
    resp = await client.get(f"/api/v1/orders/{uuid.uuid4()}", headers=_auth(token))
    assert resp.status_code == 404
