"""
Order routes — upload PDF, run pipeline, get results.
"""

from __future__ import annotations

import asyncio
import json
import uuid
from typing import Annotated

from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.auth.dependencies import CurrentUser
from app.database import SessionDep
from app.models.meal_plan import MealPlan
from app.models.menu_item import MenuItem
from app.models.order import Order, OrderParticipant
from app.schemas.order import OrderResponse
from app.services.classify import classify
from app.services.correlate import correlate
from app.services.extract import extract
from app.services.split import compute_splits
from app.services.storage import save_upload

router = APIRouter(prefix="/orders", tags=["orders"])


async def _snapshot_meal_plans(
    session,
    participant_ids: list[uuid.UUID],
) -> tuple[dict[str, list[str]], list[dict]]:
    """Snapshot participants' meal plans and collect all menu items.

    Returns:
        members: {user_id_str: [menu_item_id_str, ...]}
        menu_items: [{id, name, ingredients}, ...]
    """
    members: dict[str, list[str]] = {}
    seen_menu_item_ids: set[uuid.UUID] = set()
    all_menu_items: list[dict] = []

    for user_id in participant_ids:
        result = await session.execute(
            select(MealPlan)
            .where(MealPlan.user_id == user_id)
            .options(selectinload(MealPlan.items))
        )
        plan = result.scalar_one_or_none()

        if plan is None:
            members[str(user_id)] = []
            continue

        menu_item_ids = [str(item.menu_item_id) for item in plan.items]
        members[str(user_id)] = menu_item_ids

        for item in plan.items:
            if item.menu_item_id not in seen_menu_item_ids:
                seen_menu_item_ids.add(item.menu_item_id)
                mi = await session.get(MenuItem, item.menu_item_id)
                if mi:
                    all_menu_items.append(
                        {
                            "id": str(mi.id),
                            "name": mi.name,
                            "ingredients": mi.ingredients,
                        }
                    )

    return members, all_menu_items


@router.post("/", response_model=OrderResponse, status_code=201)
async def create_order(
    session: SessionDep,
    current_user: CurrentUser,
    file: Annotated[UploadFile, File()],
    participant_ids: Annotated[str, Form()],
):
    """Upload a PDF invoice and run the full splitting pipeline.

    participant_ids should be a JSON array of user UUID strings, e.g.:
    ["uuid-1", "uuid-2", "uuid-3"]

    The current user is automatically included as a participant and is the payer.
    """
    # Parse participant IDs
    try:
        parsed_ids = [uuid.UUID(pid) for pid in json.loads(participant_ids)]
    except (json.JSONDecodeError, ValueError) as e:
        raise HTTPException(status_code=400, detail=f"Invalid participant_ids: {e}") from None

    # Ensure current user is included
    if current_user.id not in parsed_ids:
        parsed_ids.append(current_user.id)

    # Create order record
    order = Order(
        paid_by=current_user.id,
        invoice_filename=file.filename or "invoice.pdf",
        status="processing",
    )
    session.add(order)
    await session.flush()

    # Add participants
    for pid in parsed_ids:
        session.add(OrderParticipant(order_id=order.id, user_id=pid))
    await session.flush()

    # Save PDF
    content = await file.read()
    pdf_path = await asyncio.to_thread(save_upload, content, order.id)

    # Snapshot meal plans
    members, menu_items = await _snapshot_meal_plans(session, parsed_ids)

    # Pipeline: extract → classify → correlate → split
    extracted = await asyncio.to_thread(extract, pdf_path)
    classified = await classify(extracted)

    # Get only "item" category grocery items for correlation
    grocery_items = [g for g in classified["items"] if g["category"] == "item"]
    uses = await correlate(menu_items, grocery_items)

    result = compute_splits(classified, members, uses, str(current_user.id))

    # Store snapshot and result
    order.snapshot = {"members": members, "uses": uses, "menu_items": menu_items}
    order.result = result
    order.status = "completed"

    await session.commit()

    # Reload with participants
    stmt = select(Order).where(Order.id == order.id).options(selectinload(Order.participants))
    loaded = await session.execute(stmt)
    return loaded.scalar_one()


@router.get("/", response_model=list[OrderResponse])
async def list_orders(session: SessionDep, current_user: CurrentUser):
    """List orders where current user is a participant."""
    result = await session.execute(
        select(Order)
        .join(OrderParticipant)
        .where(OrderParticipant.user_id == current_user.id)
        .options(selectinload(Order.participants))
        .order_by(Order.created_at.desc())
    )
    return result.scalars().unique().all()


@router.get("/{order_id}", response_model=OrderResponse)
async def get_order(order_id: uuid.UUID, session: SessionDep, current_user: CurrentUser):
    """Get a specific order. Must be a participant."""
    result = await session.execute(
        select(Order).where(Order.id == order_id).options(selectinload(Order.participants))
    )
    order = result.scalar_one_or_none()

    if not order:
        raise HTTPException(status_code=404, detail="Order not found")

    participant_ids = {p.user_id for p in order.participants}
    if current_user.id not in participant_ids:
        raise HTTPException(status_code=403, detail="Not a participant of this order")

    return order
