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


async def test_compute_splits_unmatched_items_go_to_payer():
    """Unmatched items are assigned to the payer, not dropped."""
    classified = {
        "items": [
            {"upc": "AAA", "description": "Matched", "total": 30.0, "category": "item"},
            {"upc": "ZZZ", "description": "Unmatched", "total": 20.0, "category": "item"},
        ],
    }
    members = {"user-1": ["menu-a"], "user-2": []}
    uses = {"menu-a": ["AAA"]}

    result = compute_splits(classified, members, uses, "user-1")

    splits_by_members = {tuple(s["splitEquallyAmong"]): s for s in result["splits"]}

    # Matched item goes to user-1
    assert splits_by_members[("user-1",)]["amount"] == 50.0  # 30 matched + 20 unmatched
    # Both items land on user-1 (matched via menu, unmatched as payer)
    upcs = [g["upc"] for g in splits_by_members[("user-1",)]["groceryItems"]]
    assert "AAA" in upcs
    assert "ZZZ" in upcs


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


async def test_compute_splits_unmatched_plus_fees():
    """Unmatched items go to payer, fees go to everyone."""
    classified = {
        "items": [
            {"upc": "A", "description": "Unmatched", "total": 100.0, "category": "item"},
            {"upc": "-", "description": "Fee", "total": 5.0, "category": "fee"},
        ],
    }
    members = {"u1": [], "u2": []}
    uses = {}

    result = compute_splits(classified, members, uses, "u1")

    splits_by_members = {tuple(s["splitEquallyAmong"]): s for s in result["splits"]}

    # Unmatched item → payer only
    assert splits_by_members[("u1",)]["amount"] == 100.0

    # Fee → everyone
    assert splits_by_members[("u1", "u2")]["amount"] == 5.0

    # Total equals invoice
    total = sum(s["amount"] for s in result["splits"])
    assert total == 105.0


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
    """Amounts are rounded to 2 decimal places.

    Use totals whose binary float sum is not exactly the mathematical sum
    (e.g. 10.1 + 20.2 != 30.3 in IEEE-754) so the test fails if rounding is removed.
    """
    classified = {
        "items": [
            {"upc": "A", "description": "X", "total": 10.1, "category": "item"},
            {"upc": "B", "description": "Y", "total": 20.2, "category": "item"},
        ],
    }
    members = {"u1": ["m1"]}
    uses = {"m1": ["A", "B"]}

    result = compute_splits(classified, members, uses, "u1")
    assert result["splits"][0]["amount"] == 30.3


# --- Total invariant: sum of splits == sum of all classified items ---


async def test_total_invariant_all_matched():
    """When all items match, split total equals invoice total."""
    classified = {
        "items": [
            {"upc": "A", "description": "X", "total": 50.0, "category": "item"},
            {"upc": "B", "description": "Y", "total": 30.0, "category": "item"},
            {"upc": "-", "description": "Fee", "total": 10.0, "category": "fee"},
        ],
    }
    members = {"u1": ["m1"], "u2": ["m2"]}
    uses = {"m1": ["A"], "m2": ["B"]}

    result = compute_splits(classified, members, uses, "u1")

    invoice_total = sum(i["total"] for i in classified["items"])
    split_total = sum(s["amount"] for s in result["splits"])
    assert split_total == invoice_total  # 90 == 90


async def test_total_invariant_some_unmatched():
    """Unmatched items go to payer, so total still balances."""
    classified = {
        "items": [
            {"upc": "A", "description": "Matched", "total": 40.0, "category": "item"},
            {"upc": "X", "description": "Unmatched1", "total": 25.0, "category": "item"},
            {"upc": "Y", "description": "Unmatched2", "total": 15.0, "category": "item"},
            {"upc": "-", "description": "Fee", "total": 8.0, "category": "fee"},
        ],
    }
    members = {"payer": ["m1"], "other": []}
    uses = {"m1": ["A"]}

    result = compute_splits(classified, members, uses, "payer")

    invoice_total = sum(i["total"] for i in classified["items"])
    split_total = sum(s["amount"] for s in result["splits"])
    assert split_total == invoice_total  # 88 == 88


async def test_total_invariant_nothing_matched():
    """When nothing matches, all items go to payer, fees to everyone."""
    classified = {
        "items": [
            {"upc": "A", "description": "Item", "total": 100.0, "category": "item"},
            {"upc": "-", "description": "Fee", "total": 5.0, "category": "fee"},
        ],
    }
    members = {"payer": [], "other": []}
    uses = {}

    result = compute_splits(classified, members, uses, "payer")

    invoice_total = sum(i["total"] for i in classified["items"])
    split_total = sum(s["amount"] for s in result["splits"])
    assert split_total == invoice_total  # 105 == 105
