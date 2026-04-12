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
        Dict with "paidBy" and "splits" keys.

    Items with category "fee" are always split among all members.
    Items with no member mapping (miscellaneous) are ignored.
    """
    all_members = sorted(members.keys())
    grocery_to_members = build_grocery_to_members(members, uses)

    # Group grocery items by identical splitEquallyAmong sets
    groups: dict[frozenset[MemberId], list[dict]] = defaultdict(list)

    for grocery_item in classified["items"]:
        if grocery_item["category"] == "fee":
            neighbor_set = frozenset(all_members)
        else:
            matched = grocery_to_members.get(grocery_item["upc"])
            if not matched:
                continue
            neighbor_set = frozenset(matched)

        groups[neighbor_set].append(grocery_item)

    # Each unique neighbor set = one split invocation
    splits = []
    for member_set, grocery_items in groups.items():
        amount = round(sum(g["total"] for g in grocery_items), 2)
        splits.append(
            {
                "amount": amount,
                "groceryItems": [
                    {"upc": g["upc"], "description": g["description"], "total": g["total"]}
                    for g in grocery_items
                ],
                "splitEquallyAmong": sorted(member_set),
            }
        )

    return {"paidBy": paid_by, "splits": splits}
