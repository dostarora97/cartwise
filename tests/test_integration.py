"""
Full end-to-end integration test — no mocks.

Tests the complete user journey against real services:
- Real PostgreSQL test database
- Real Ollama (qwen2.5:3b) for classify + correlate
- Real PDF extraction

Requires:
- Docker postgres-test running on port 5433
- Ollama running with qwen2.5:3b model

Run: uv run pytest tests/test_integration.py -v -s
"""

import json
from pathlib import Path

from httpx import AsyncClient

# Path to the test invoice PDF (from the prototype data)
INVOICE_PDF = Path(__file__).parent.parent.parent / "data" / "ORD95806394221" / "invoice.pdf"


def _auth(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


async def test_full_end_to_end(client: AsyncClient):
    """Complete flow: users → menu items → meal plans → order pipeline → splits."""

    # ============================================================
    # 1. Create users via dev-login
    # ============================================================
    alice_resp = await client.post(
        "/api/v1/auth/dev-login",
        json={"email": "alice@test.com", "name": "Alice"},
    )
    assert alice_resp.status_code == 200
    alice_token = alice_resp.json()["access_token"]
    alice_id = alice_resp.json()["user"]["id"]

    bob_resp = await client.post(
        "/api/v1/auth/dev-login",
        json={"email": "bob@test.com", "name": "Bob"},
    )
    bob_token = bob_resp.json()["access_token"]
    bob_id = bob_resp.json()["user"]["id"]

    carol_resp = await client.post(
        "/api/v1/auth/dev-login",
        json={"email": "carol@test.com", "name": "Carol"},
    )
    carol_token = carol_resp.json()["access_token"]
    carol_id = carol_resp.json()["user"]["id"]

    print(f"\n  Users: Alice={alice_id[:8]}, Bob={bob_id[:8]}, Carol={carol_id[:8]}")

    # ============================================================
    # 2. Verify auth
    # ============================================================
    me = await client.get("/api/v1/auth/me", headers=_auth(alice_token))
    assert me.status_code == 200
    assert me.json()["name"] == "Alice"

    # ============================================================
    # 3. Create menu items
    # ============================================================
    chicken = await client.post(
        "/api/v1/menu-items/",
        json={
            "name": "Chicken Curry",
            "recipe": "Cook chicken with onions and spices, squeeze lemon.",
            "ingredients": "boneless chicken breast, onion, lemon, spices",
        },
        headers=_auth(alice_token),
    )
    assert chicken.status_code == 201
    chicken_id = chicken.json()["id"]

    salad = await client.post(
        "/api/v1/menu-items/",
        json={
            "name": "Green Salad",
            "recipe": "Chop cucumber and cherry tomatoes, dress with lemon.",
            "ingredients": "cucumber, cherry tomato, lemon",
        },
        headers=_auth(bob_token),
    )
    assert salad.status_code == 201
    salad_id = salad.json()["id"]

    tea = await client.post(
        "/api/v1/menu-items/",
        json={
            "name": "Milk Tea",
            "recipe": "Boil milk with tea leaves.",
            "ingredients": "milk",
        },
        headers=_auth(carol_token),
    )
    assert tea.status_code == 201
    tea_id = tea.json()["id"]

    print(f"  Menu items: Chicken={chicken_id[:8]}, Salad={salad_id[:8]}, Tea={tea_id[:8]}")

    # ============================================================
    # 4. Fork + update
    # ============================================================
    forked = await client.post(
        f"/api/v1/menu-items/{chicken_id}/fork",
        headers=_auth(carol_token),
    )
    assert forked.status_code == 201
    forked_id = forked.json()["id"]

    updated = await client.patch(
        f"/api/v1/menu-items/{forked_id}",
        json={"name": "Spicy Chicken", "ingredients": "chicken, onion, extra chilli"},
        headers=_auth(carol_token),
    )
    assert updated.json()["name"] == "Spicy Chicken"

    # ============================================================
    # 5. Set meal plans
    # ============================================================
    await client.put(
        "/api/v1/meal-plans/me",
        json={"menu_item_ids": [chicken_id, salad_id]},
        headers=_auth(alice_token),
    )
    await client.put(
        "/api/v1/meal-plans/me",
        json={"menu_item_ids": [salad_id]},
        headers=_auth(bob_token),
    )
    await client.put(
        "/api/v1/meal-plans/me",
        json={"menu_item_ids": [forked_id, tea_id]},
        headers=_auth(carol_token),
    )

    # Verify plans
    alice_plan = await client.get("/api/v1/meal-plans/me", headers=_auth(alice_token))
    assert len(alice_plan.json()["items"]) == 2
    print("  Meal plans set: Alice=2, Bob=1, Carol=2")

    # ============================================================
    # 6. Upload invoice → full pipeline (real Ollama!)
    # ============================================================
    assert INVOICE_PDF.exists(), f"Test PDF not found at {INVOICE_PDF}"

    with open(INVOICE_PDF, "rb") as f:
        order_resp = await client.post(
            "/api/v1/orders/",
            files={"file": ("invoice.pdf", f, "application/pdf")},
            data={"participant_ids": json.dumps([alice_id, bob_id, carol_id])},
            headers=_auth(alice_token),
            timeout=120.0,  # LLM calls take time
        )

    assert order_resp.status_code == 201, f"Order failed: {order_resp.text}"
    order = order_resp.json()
    order_id = order["id"]

    print(f"  Order created: {order_id[:8]}")
    print(f"  Status: {order['status']}")
    print(f"  Participants: {len(order['participants'])}")

    # ============================================================
    # 7. Verify order result
    # ============================================================
    assert order["status"] == "completed"
    assert order["result"] is not None
    assert order["result"]["paidBy"] == alice_id
    assert len(order["result"]["splits"]) > 0

    print(f"  Splits: {len(order['result']['splits'])}")
    total = 0
    for s in order["result"]["splits"]:
        print(f"    ₹{s['amount']:>8.2f} among {s['splitEquallyAmong'][:3]}...")
        total += s["amount"]
    print(f"  Total split: ₹{total:.2f}")

    # ============================================================
    # 8. List orders
    # ============================================================
    orders = await client.get("/api/v1/orders/", headers=_auth(alice_token))
    assert orders.status_code == 200
    assert len(orders.json()) == 1

    # Bob can see the order too (he's a participant)
    bob_orders = await client.get("/api/v1/orders/", headers=_auth(bob_token))
    assert len(bob_orders.json()) == 1

    # ============================================================
    # 9. Get order by ID
    # ============================================================
    detail = await client.get(f"/api/v1/orders/{order_id}", headers=_auth(alice_token))
    assert detail.status_code == 200
    assert detail.json()["result"]["paidBy"] == alice_id

    # ============================================================
    # 10. Security checks
    # ============================================================
    # Unauthenticated → 401 (no token) or 403 (HTTPBearer returns 403 when no header)
    no_auth = await client.get("/api/v1/auth/me")
    assert no_auth.status_code in (401, 403)

    # Can't edit someone else's profile
    not_mine = await client.patch(
        f"/api/v1/users/{bob_id}",
        json={"name": "Hacked"},
        headers=_auth(alice_token),
    )
    assert not_mine.status_code == 403

    print("\n  All assertions passed!")
