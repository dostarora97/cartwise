"""
Order routes — upload PDF, run pipeline, manage splits, approve to Splitwise.
"""

from __future__ import annotations

import asyncio
import json
import uuid
from typing import Annotated

from fastapi import APIRouter, File, Form, HTTPException, Query, UploadFile
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.auth.dependencies import CurrentUser
from app.database import SessionDep
from app.models.meal_plan import MealPlan
from app.models.menu_item import MenuItem
from app.models.order import Order, OrderParticipant
from app.models.split import Split
from app.models.user import User
from app.schemas.order import EditSplitsRequest, OrderResponse
from app.services.classify import classify
from app.services.correlate import correlate
from app.services.extract import extract
from app.services.split import compute_splits
from app.services.storage import download_to_temp, save_upload

router = APIRouter(prefix="/orders", tags=["orders"])


def _order_load_options():
    """Eager-load options for Order queries."""
    return [selectinload(Order.participants), selectinload(Order.splits)]


async def _get_order_or_404(session, order_id: uuid.UUID) -> Order:
    result = await session.execute(
        select(Order).where(Order.id == order_id).options(*_order_load_options())
    )
    order = result.scalar_one_or_none()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    return order


async def _snapshot_meal_plans(
    session,
    participant_ids: list[uuid.UUID],
) -> tuple[dict[str, list[str]], list[dict]]:
    """Snapshot participants' meal plans and collect all menu items.

    Returns:
        members: {user_id_str: [menu_item_id_str, ...]}
        menu_items: [{id, name, body}, ...]
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
                            "body": mi.body,
                        }
                    )

    return members, all_menu_items


def _create_split_rows(order_id: uuid.UUID, result: dict) -> list[Split]:
    """Create Split ORM objects from compute_splits result."""
    splits = []
    for split_data in result["splits"]:
        splits.append(
            Split(
                order_id=order_id,
                amount=split_data["amount"],
                grocery_items=split_data["groceryItems"],
                member_ids=split_data["splitEquallyAmong"],
            )
        )
    return splits


@router.post("/", response_model=OrderResponse, status_code=201)
async def create_order(
    session: SessionDep,
    current_user: CurrentUser,
    file: Annotated[UploadFile, File()],
    participant_ids: Annotated[str, Form()],
):
    """Upload a PDF invoice and run the full splitting pipeline.

    Creates a draft order with split rows. Use PATCH /{id}/approve to push to Splitwise.
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
    )
    session.add(order)
    await session.flush()

    # Add participants
    for pid in parsed_ids:
        session.add(OrderParticipant(order_id=order.id, user_id=pid))
    await session.flush()

    # Save PDF to storage
    content = await file.read()
    storage_path = await asyncio.to_thread(save_upload, content, order.id)

    # Snapshot meal plans
    members, menu_items = await _snapshot_meal_plans(session, parsed_ids)

    # Pipeline: extract → classify → correlate → split
    local_pdf = await asyncio.to_thread(download_to_temp, storage_path)
    extracted = await asyncio.to_thread(extract, local_pdf)
    classified = await classify(extracted)

    # Get only "item" category grocery items for correlation
    grocery_items = [g for g in classified["items"] if g["category"] == "item"]
    uses = await correlate(menu_items, grocery_items)

    result = compute_splits(classified, members, uses, str(current_user.id))

    # Store snapshot, result, and create split rows
    order.snapshot = {"members": members, "uses": uses, "menu_items": menu_items}
    order.result = result

    for split in _create_split_rows(order.id, result):
        session.add(split)

    await session.commit()

    # Reload with participants + splits
    return await _get_order_or_404(session, order.id)


@router.get("/", response_model=list[OrderResponse])
async def list_orders(
    session: SessionDep,
    current_user: CurrentUser,
    user_id: uuid.UUID | None = Query(default=None),
    status: str | None = Query(default=None),
):
    """List orders.

    - ?user_id=X — list orders where X is the payer (for profile invoices tab)
    - ?status=draft — filter by status
    - Default: list orders where current user is a participant
    """
    if user_id:
        stmt = select(Order).where(Order.paid_by == user_id)
    else:
        stmt = (
            select(Order).join(OrderParticipant).where(OrderParticipant.user_id == current_user.id)
        )

    if status:
        stmt = stmt.where(Order.status == status)

    stmt = stmt.options(*_order_load_options()).order_by(Order.created_at.desc())
    result = await session.execute(stmt)
    return result.scalars().unique().all()


@router.get("/{order_id}", response_model=OrderResponse)
async def get_order(order_id: uuid.UUID, session: SessionDep):
    """Get a specific order. Visible to all authenticated users."""
    return await _get_order_or_404(session, order_id)


@router.patch("/{order_id}/cancel", response_model=OrderResponse)
async def cancel_order(
    order_id: uuid.UUID,
    session: SessionDep,
    current_user: CurrentUser,
):
    """Cancel a draft order. Only the payer can cancel."""
    order = await _get_order_or_404(session, order_id)

    if order.paid_by != current_user.id:
        raise HTTPException(status_code=403, detail="Only the payer can cancel this order")
    if order.status != "draft":
        raise HTTPException(
            status_code=400, detail=f"Cannot cancel order with status '{order.status}'"
        )

    order.status = "cancelled"
    await session.commit()
    return await _get_order_or_404(session, order.id)


@router.put("/{order_id}/splits", response_model=OrderResponse)
async def edit_splits(
    order_id: uuid.UUID,
    data: EditSplitsRequest,
    session: SessionDep,
    current_user: CurrentUser,
):
    """Edit split assignments for a draft order. Backend recomputes amounts.

    The client sends who-gets-what (member assignments per grocery item UPC).
    The backend groups by identical member sets and recalculates amounts from
    the original invoice prices stored in order.result.
    """
    order = await _get_order_or_404(session, order_id)

    if order.paid_by != current_user.id:
        raise HTTPException(status_code=403, detail="Only the payer can edit splits")
    if order.status != "draft":
        raise HTTPException(
            status_code=400, detail=f"Cannot edit splits for order with status '{order.status}'"
        )

    if not order.result:
        raise HTTPException(status_code=400, detail="Order has no result data")

    # Build a UPC→price lookup from the original classified items
    all_items = order.result.get("splits", [])
    upc_to_item: dict[str, dict] = {}
    for split_group in all_items:
        for item in split_group.get("groceryItems", []):
            upc_to_item[item["upc"]] = item

    # Group assignments by identical member set → recompute splits
    from collections import defaultdict

    groups: dict[frozenset, list[dict]] = defaultdict(list)
    for assignment in data.assignments:
        if assignment.upc not in upc_to_item:
            raise HTTPException(status_code=400, detail=f"Unknown UPC: {assignment.upc}")
        member_key = (
            frozenset(assignment.member_ids)
            if assignment.member_ids
            else frozenset([str(order.paid_by)])
        )
        groups[member_key].append(upc_to_item[assignment.upc])

    # Delete old splits, create new ones
    for old_split in order.splits:
        await session.delete(old_split)
    await session.flush()

    for member_set, items in groups.items():
        amount = round(sum(item["total"] for item in items), 2)
        session.add(
            Split(
                order_id=order.id,
                amount=amount,
                grocery_items=items,
                member_ids=sorted(member_set),
            )
        )

    await session.commit()
    return await _get_order_or_404(session, order.id)


@router.post("/{order_id}/approve", response_model=OrderResponse)
async def approve_order(
    order_id: uuid.UUID,
    session: SessionDep,
    current_user: CurrentUser,
):
    """Approve a draft order — push splits to Splitwise.

    Looks up each participant's splitwise_user_id and calls push_splits_audited().
    """
    order = await _get_order_or_404(session, order_id)

    if order.paid_by != current_user.id:
        raise HTTPException(status_code=403, detail="Only the payer can approve this order")
    if order.status != "draft":
        raise HTTPException(
            status_code=400, detail=f"Cannot approve order with status '{order.status}'"
        )

    # Build member_id_to_sw_id mapping from DB
    participant_user_ids = [p.user_id for p in order.participants]
    member_id_to_sw_id: dict[str, int] = {}
    payer_sw_id: int | None = None

    for uid in participant_user_ids:
        user = await session.get(User, uid)
        if not user or user.splitwise_user_id is None:
            raise HTTPException(
                status_code=400,
                detail=f"User {uid} has no Splitwise user ID configured",
            )
        member_id_to_sw_id[str(uid)] = user.splitwise_user_id
        if uid == order.paid_by:
            payer_sw_id = user.splitwise_user_id

    if payer_sw_id is None:
        raise HTTPException(status_code=400, detail="Payer not found in participants")

    # Build split_result from the Split rows for push_splits_audited
    split_result = {
        "paidBy": str(order.paid_by),
        "splits": [
            {
                "amount": float(s.amount),
                "groceryItems": s.grocery_items,
                "splitEquallyAmong": s.member_ids,
            }
            for s in order.splits
        ],
    }

    from app.services.splitwise import push_splits_audited

    audits = await push_splits_audited(
        session=session,
        order_id=order.id,
        split_result=split_result,
        member_id_to_sw_id=member_id_to_sw_id,
        payer_sw_id=payer_sw_id,
    )

    # Update split statuses from audit results
    audit_by_desc = {a.request_payload.get("description", ""): a for a in audits}
    all_success = True
    for split in order.splits:
        item_names = [g["description"] for g in split.grocery_items]
        desc = (
            ", ".join(item_names)
            if len(item_names) <= 3
            else f"{item_names[0]}, {item_names[1]} +{len(item_names) - 2} more"
        )
        audit = audit_by_desc.get(desc)
        if audit:
            split.status = audit.status
            split.splitwise_expense_id = audit.splitwise_expense_id
            if audit.status != "success":
                all_success = False
        else:
            all_success = False

    if all_success:
        order.status = "completed"

    await session.commit()
    return await _get_order_or_404(session, order.id)
