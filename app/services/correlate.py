"""
MenuItem ↔ GroceryItem Correlator

For each MenuItem, sends its name + ingredients alongside the full list of
GroceryItems to the LLM, which returns the matched UPCs. This builds the
bipartite adjacency used by the split service.
"""

import json

import httpx

from app.config import settings

MODEL = "qwen2.5:3b"

SYSTEM_PROMPT = (
    "You match a menu item's ingredients to grocery items from a Blinkit invoice. "
    "Given a menu item (name + ingredients) and a list of grocery items (description + UPC), "
    "return the UPCs of grocery items that would be used to prepare this menu item. "
    "Only match items that are clearly ingredients for the dish. "
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
    lines = []
    for g in grocery_items:
        lines.append(f"- UPC: {g['upc']}, Description: {g['description']}")
    return "\n".join(lines)


async def _correlate_menu_item(
    client: httpx.AsyncClient,
    menu_item_name: str,
    menu_item_ingredients: str,
    grocery_list_text: str,
) -> list[str]:
    """Ask LLM to match one MenuItem's ingredients to GroceryItem UPCs."""
    prompt = (
        f"Menu Item: {menu_item_name}\n"
        f"Ingredients: {menu_item_ingredients}\n\n"
        f"Available Grocery Items:\n{grocery_list_text}\n\n"
        f"Which grocery items (by UPC) are used to prepare this menu item?"
    )

    response = await client.post(
        f"{settings.AI_BASE_URL}/api/generate",
        json={
            "model": MODEL,
            "system": SYSTEM_PROMPT,
            "prompt": prompt,
            "format": CORRELATE_SCHEMA,
            "stream": False,
        },
        timeout=60.0,
    )
    response.raise_for_status()
    result = json.loads(response.json()["response"])
    return result.get("matched_upcs", [])


async def correlate(
    menu_items: list[dict],
    grocery_items: list[dict],
) -> dict[str, list[str]]:
    """Build uses mapping: menu_item_id → [upc, ...].

    Args:
        menu_items: List of dicts with "id", "name", "ingredients" keys.
        grocery_items: List of dicts with "upc", "description" keys
                       (items only, not fees).

    Returns:
        Dict mapping menu_item_id (str) → list of matched UPC strings.
    """
    grocery_list_text = _build_grocery_list_text(grocery_items)
    uses: dict[str, list[str]] = {}

    async with httpx.AsyncClient() as client:
        for item in menu_items:
            matched = await _correlate_menu_item(
                client,
                menu_item_name=item["name"],
                menu_item_ingredients=item["ingredients"],
                grocery_list_text=grocery_list_text,
            )
            # Only keep UPCs that actually exist in our grocery items
            valid_upcs = {g["upc"] for g in grocery_items}
            uses[str(item["id"])] = [upc for upc in matched if upc in valid_upcs]

    return uses
