from __future__ import annotations

from itertools import count
from uuid import UUID

from app.config import settings

from .static_json import StaticJsonSupplier

SUPPLIER_TYPES = {
    "static_json": StaticJsonSupplier,
}


def get_supplier(
    supplier_id: str,
    user_id: UUID,
    meal_plan_id: UUID | None,
    rank_counter: count,
) -> StaticJsonSupplier:
    configs = settings.IMPORT_SUPPLIERS
    config = next((c for c in configs if c["id"] == supplier_id), None)
    if not config:
        raise KeyError(supplier_id)
    cls = SUPPLIER_TYPES[config["type"]]
    return cls(
        supplier_id=config["id"],
        url=config["url"],
        user_id=user_id,
        meal_plan_id=meal_plan_id,
        rank_counter=rank_counter,
    )
