"""Tests for the split service — pure computation, no mocks needed."""

from app.services.split import build_grocery_to_members, compute_splits

# --- build_grocery_to_members ---


def test_build_grocery_to_members_basic():
    members = {"alice": ["curry"], "bob": ["salad"]}
    uses = {"curry": ["chicken", "onion"], "salad": ["cucumber", "onion"]}

    result = build_grocery_to_members(members, uses)

    assert result["chicken"] == {"alice"}
    assert result["onion"] == {"alice", "bob"}
    assert result["cucumber"] == {"bob"}


def test_build_grocery_to_members_empty():
    assert build_grocery_to_members({}, {}) == {}
    assert build_grocery_to_members({"alice": ["curry"]}, {}) == {}
    assert build_grocery_to_members({"alice": []}, {"curry": ["x"]}) == {}


def test_build_grocery_to_members_menu_item_not_in_uses():
    members = {"alice": ["nonexistent"]}
    uses = {"curry": ["chicken"]}
    assert build_grocery_to_members(members, uses) == {}


# --- compute_splits ---


async def test_compute_splits_groups_by_member_set():
    classified = {
        "items": [
            {"upc": "AAA", "description": "Item A", "total": 50.0, "category": "item"},
            {"upc": "BBB", "description": "Item B", "total": 50.0, "category": "item"},
            {"upc": "-", "description": "Delivery", "total": 10.0, "category": "fee"},
        ],
    }
    members = {"user-1": ["menu-a"], "user-2": ["menu-b"]}
    uses = {"menu-a": ["AAA"], "menu-b": ["AAA", "BBB"]}

    result = compute_splits(classified, members, uses, "user-1")

    assert result["paidBy"] == "user-1"
    assert len(result["splits"]) == 2

    splits_by_members = {tuple(s["splitEquallyAmong"]): s for s in result["splits"]}

    shared = splits_by_members[("user-1", "user-2")]
    assert shared["amount"] == 60.0  # 50 (AAA) + 10 (fee)

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


async def test_compute_splits_single_member():
    classified = {
        "items": [
            {"upc": "A", "description": "X", "total": 100.0, "category": "item"},
            {"upc": "-", "description": "Fee", "total": 5.0, "category": "fee"},
        ],
    }
    members = {"solo": ["m1"]}
    uses = {"m1": ["A"]}

    result = compute_splits(classified, members, uses, "solo")

    assert len(result["splits"]) == 1  # item + fee merge (same member set)
    assert result["splits"][0]["amount"] == 105.0
    assert result["splits"][0]["splitEquallyAmong"] == ["solo"]


async def test_compute_splits_fees_only():
    """When no items match, only fee splits remain."""
    classified = {
        "items": [
            {"upc": "A", "description": "Unmatched", "total": 100.0, "category": "item"},
            {"upc": "-", "description": "Fee", "total": 5.0, "category": "fee"},
        ],
    }
    members = {"u1": [], "u2": []}
    uses = {}

    result = compute_splits(classified, members, uses, "u1")

    assert len(result["splits"]) == 1
    assert result["splits"][0]["amount"] == 5.0
    assert sorted(result["splits"][0]["splitEquallyAmong"]) == ["u1", "u2"]


async def test_compute_splits_empty_items():
    classified = {"items": []}
    members = {"u1": ["m1"]}
    uses = {"m1": ["A"]}

    result = compute_splits(classified, members, uses, "u1")
    assert result["splits"] == []


async def test_compute_splits_all_fees():
    """All items are fees — single split among everyone."""
    classified = {
        "items": [
            {"upc": "-", "description": "Delivery", "total": 5.0, "category": "fee"},
            {"upc": "-", "description": "Handling", "total": 3.0, "category": "fee"},
        ],
    }
    members = {"u1": [], "u2": [], "u3": []}
    uses = {}

    result = compute_splits(classified, members, uses, "u1")

    assert len(result["splits"]) == 1
    assert result["splits"][0]["amount"] == 8.0
    assert len(result["splits"][0]["splitEquallyAmong"]) == 3


async def test_compute_splits_three_way_different_groups():
    """Three members, each with unique items + shared items."""
    classified = {
        "items": [
            {"upc": "A", "description": "Alice Only", "total": 10.0, "category": "item"},
            {"upc": "B", "description": "Bob Only", "total": 20.0, "category": "item"},
            {"upc": "C", "description": "Shared AB", "total": 30.0, "category": "item"},
            {"upc": "D", "description": "All Three", "total": 40.0, "category": "item"},
            {"upc": "-", "description": "Fee", "total": 6.0, "category": "fee"},
        ],
    }
    members = {
        "alice": ["m1", "m3", "m4"],
        "bob": ["m2", "m3", "m4"],
        "carol": ["m4"],
    }
    uses = {
        "m1": ["A"],
        "m2": ["B"],
        "m3": ["C"],
        "m4": ["D"],
    }

    result = compute_splits(classified, members, uses, "alice")

    splits_by_members = {tuple(s["splitEquallyAmong"]): s for s in result["splits"]}

    assert splits_by_members[("alice",)]["amount"] == 10.0
    assert splits_by_members[("bob",)]["amount"] == 20.0
    assert splits_by_members[("alice", "bob")]["amount"] == 30.0
    # D (all 3) + fee (all 3) merge
    assert splits_by_members[("alice", "bob", "carol")]["amount"] == 46.0


async def test_compute_splits_rounding():
    """Amounts are rounded to 2 decimal places."""
    classified = {
        "items": [
            {"upc": "A", "description": "X", "total": 10.333, "category": "item"},
            {"upc": "B", "description": "Y", "total": 20.667, "category": "item"},
        ],
    }
    members = {"u1": ["m1"]}
    uses = {"m1": ["A", "B"]}

    result = compute_splits(classified, members, uses, "u1")
    assert result["splits"][0]["amount"] == 31.0
