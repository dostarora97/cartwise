"""
Grocery Cost Splitter

Given a classified invoice, member→menu-item mappings, and menu-item→grocery-item
usage relationships, produces the minimum set of split invocations needed.

Each invocation is a unique group of members who equally share the cost of
one or more grocery items. The grouping is derived from the bipartite graph
between GroceryItems and Members — items with identical member neighbor sets
collapse into a single invocation.
"""

from collections import defaultdict

import logfire
import structlog

logger = structlog.get_logger()

# Type aliases
MemberId = str
MenuItemId = str
GroceryItemUpc = str

# Input shapes
Members = dict[MemberId, list[MenuItemId]]  # member → [menu_item_id, ...]
Uses = dict[MenuItemId, list[GroceryItemUpc]]  # menu_item_id → [upc, ...]


def build_grocery_to_members(members: Members, uses: Uses) -> dict[GroceryItemUpc, set[MemberId]]:
    """Build the bipartite adjacency: grocery item UPC → set of members who consume it.

    Traverses: Member → MenuItem → GroceryItem, accumulating the transitive
    Member↔GroceryItem relationship.
    """
    grocery_to_members: dict[GroceryItemUpc, set[MemberId]] = defaultdict(set)
    for member, menu_items in members.items():
        for menu_item in menu_items:
            for upc in uses.get(menu_item, []):
                grocery_to_members[upc].add(member)
    return grocery_to_members


@logfire.instrument("compute_splits")
def compute_splits(
    classified: dict,
    members: Members,
    uses: Uses,
    paid_by: MemberId,
) -> dict:
    """Group grocery items by their member neighbor set and produce split invocations.

    Args:
        classified: Output of classify(), with "items" key.
        members: Member → list of menu item IDs.
        uses: Menu item ID → list of grocery item UPCs.
        paid_by: The member who paid for the order.

    Returns:
        Dict with "paidBy", "splits", and "noSplit" keys.

    Fees are split among members who have at least one non-fee item.
    Items with no member mapping are assigned to the payer only.
    noSplit is True when only the payer has items (no money moves).
    """
    grocery_items_count = sum(1 for i in classified["items"] if i["category"] == "item")
    fees_count = sum(1 for i in classified["items"] if i["category"] == "fee")
    logger.info(
        "split_start",
        members_count=len(members),
        grocery_items_count=grocery_items_count,
        fees_count=fees_count,
    )

    grocery_to_members = build_grocery_to_members(members, uses)

    # Phase 1: process non-fee items, track which members have items
    members_with_items: set[MemberId] = set()
    groups: dict[frozenset[MemberId], list[dict]] = defaultdict(list)

    for grocery_item in classified["items"]:
        if grocery_item["category"] == "fee":
            continue
        matched = grocery_to_members.get(grocery_item["upc"])
        neighbor_set = frozenset(matched) if matched else frozenset({paid_by})
        groups[neighbor_set].append(grocery_item)
        members_with_items.update(neighbor_set)

    # Phase 2: assign fees to members who have at least one item
    fee_members = frozenset(members_with_items) if members_with_items else frozenset({paid_by})
    for grocery_item in classified["items"]:
        if grocery_item["category"] == "fee":
            groups[fee_members].append(grocery_item)

    # Each unique neighbor set = one split invocation
    splits = []
    for member_set, grocery_items in groups.items():
        amount = round(sum(g["total"] for g in grocery_items), 2)
        splits.append(
            {
                "amount": amount,
                "groceryItems": [
                    {
                        "upc": g["upc"],
                        "description": g["description"],
                        "total": g["total"],
                        "category": g["category"],
                    }
                    for g in grocery_items
                ],
                "splitEquallyAmong": sorted(member_set),
            }
        )

    no_split = members_with_items <= {paid_by}

    logger.info("split_complete", split_groups_count=len(splits), no_split=no_split)

    return {"paidBy": paid_by, "splits": splits, "noSplit": no_split}
