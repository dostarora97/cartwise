"""
MenuItem ↔ GroceryItem Correlator

For each MenuItem, sends its name + body (recipe and ingredient details)
alongside the full list of GroceryItems to the LLM, which returns the
matched UPCs. This builds the bipartite adjacency used by the split service.
"""

from app.ai.client import generate

SYSTEM_PROMPT = (
    "You match a menu item to grocery items from an invoice. "
    "Given a menu item (name + body containing recipe and ingredient details) "
    "and a list of grocery items (description + UPC), "
    "return the UPCs of grocery items that would be used to prepare this menu item. "
    "Only match items that are clearly needed for the dish. "
    "If no grocery items match, return an empty list."
)

CORRELATE_SCHEMA = {
    "type": "object",
    "properties": {
        "matched_upcs": {
            "type": "array",
            "items": {"type": "string"},
        }
    },
    "required": ["matched_upcs"],
}


def _build_grocery_list_text(grocery_items: list[dict]) -> str:
    """Format grocery items into a readable list for the prompt."""
    return "\n".join(f"- UPC: {g['upc']}, Description: {g['description']}" for g in grocery_items)


async def _correlate_menu_item(
    menu_item_name: str,
    menu_item_body: str,
    grocery_list_text: str,
) -> list[str]:
    """Ask LLM to match one MenuItem to GroceryItem UPCs."""
    prompt = (
        f"Menu Item: {menu_item_name}\n"
        f"Menu Item Details:\n{menu_item_body}\n\n"
        f"Available Grocery Items:\n{grocery_list_text}\n\n"
        f"Which grocery items (by UPC) are used to prepare this menu item?"
    )

    result = await generate(
        system=SYSTEM_PROMPT,
        prompt=prompt,
        schema=CORRELATE_SCHEMA,
    )
    return result.get("matched_upcs", [])


async def correlate(
    menu_items: list[dict],
    grocery_items: list[dict],
) -> dict[str, list[str]]:
    """Build uses mapping: menu_item_id → [upc, ...].

    Args:
        menu_items: List of dicts with "id", "name", "body" keys.
        grocery_items: List of dicts with "upc", "description" keys
                       (items only, not fees).

    Returns:
        Dict mapping menu_item_id (str) → list of matched UPC strings.
    """
    grocery_list_text = _build_grocery_list_text(grocery_items)
    valid_upcs = {g["upc"] for g in grocery_items}
    uses: dict[str, list[str]] = {}

    for item in menu_items:
        matched = await _correlate_menu_item(
            menu_item_name=item["name"],
            menu_item_body=item["body"],
            grocery_list_text=grocery_list_text,
        )
        uses[str(item["id"])] = [upc for upc in matched if upc in valid_upcs]

    return uses
