"""Tests for the split service — pure computation, no mocks needed."""

from app.services.split import compute_splits


async def test_compute_splits_groups_by_member_set():
    classified = {
        "summary": {"item_total": 100, "fee_total": 10, "grand_total": 110},
        "items": [
            {"upc": "AAA", "description": "Item A", "total": 50.0, "category": "item"},
            {"upc": "BBB", "description": "Item B", "total": 50.0, "category": "item"},
            {"upc": "-", "description": "Delivery", "total": 10.0, "category": "fee"},
        ],
    }
    members = {
        "user-1": ["menu-a"],
        "user-2": ["menu-b"],
    }
    uses = {
        "menu-a": ["AAA"],
        "menu-b": ["AAA", "BBB"],
    }

    result = compute_splits(classified, members, uses, "user-1")

    assert result["paidBy"] == "user-1"
    # AAA is shared by both users, fee also goes to both → same group
    # BBB is only user-2 → separate group
    assert len(result["splits"]) == 2

    splits_by_members = {tuple(s["splitEquallyAmong"]): s for s in result["splits"]}

    # AAA + fee grouped together (same member set: both users)
    shared = splits_by_members[("user-1", "user-2")]
    assert shared["amount"] == 60.0  # 50 (AAA) + 10 (delivery)
    descriptions = [g["description"] for g in shared["groceryItems"]]
    assert "Item A" in descriptions
    assert "Delivery" in descriptions

    # BBB only used by user-2
    solo = splits_by_members[("user-2",)]
    assert solo["amount"] == 50.0


async def test_compute_splits_ignores_unmatched_items():
    classified = {
        "items": [
            {"upc": "AAA", "description": "Matched", "total": 30.0, "category": "item"},
            {"upc": "ZZZ", "description": "Unmatched", "total": 20.0, "category": "item"},
        ],
    }
    members = {"user-1": ["menu-a"]}
    uses = {"menu-a": ["AAA"]}

    result = compute_splits(classified, members, uses, "user-1")

    all_upcs = [g["upc"] for s in result["splits"] for g in s["groceryItems"]]
    assert "AAA" in all_upcs
    assert "ZZZ" not in all_upcs
