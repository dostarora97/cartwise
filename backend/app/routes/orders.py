"""
Order routes — create sources, initiate splits, manage orders, approve to Splitwise.
"""

from __future__ import annotations

import asyncio
import uuid
from collections import defaultdict
from typing import Annotated

import logfire
import structlog
from fastapi import APIRouter, File, HTTPException, Query, UploadFile
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.auth.dependencies import CurrentUser
from app.database import SessionDep
from app.models.meal_plan import MealPlan
from app.models.menu_item import MenuItem
from app.models.order import Order, OrderParticipant
from app.models.order_source import OrderSource
from app.models.split import Split
from app.models.user import User
from app.schemas.order import EditSplitsRequest, OrderCreate, OrderResponse
from app.schemas.order_source import OrderSourceCreate, OrderSourceResponse, UploadResponse
from app.services.correlate import correlate
from app.services.extraction import run_extraction
from app.services.split import compute_splits
from app.services.storage import save_source_upload

router = APIRouter(prefix="/orders", tags=["orders"])
logger = structlog.get_logger()


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
    """Snapshot participants' meal plans and collect all menu items."""
    # Batch query 1: all meal plans at once
    result = await session.execute(
        select(MealPlan)
        .where(MealPlan.user_id.in_(participant_ids))
        .options(selectinload(MealPlan.items))
    )
    plans_by_user = {plan.user_id: plan for plan in result.scalars().all()}

    members: dict[str, list[str]] = {}
    seen_menu_item_ids: set[uuid.UUID] = set()

    for user_id in participant_ids:
        plan = plans_by_user.get(user_id)
        if plan is None:
            members[str(user_id)] = []
            continue
        menu_item_ids = [str(item.menu_item_id) for item in plan.items]
        members[str(user_id)] = menu_item_ids
        for item in plan.items:
            seen_menu_item_ids.add(item.menu_item_id)

    # Batch query 2: all referenced menu items at once
    all_menu_items: list[dict] = []
    if seen_menu_item_ids:
        mi_result = await session.execute(
            select(MenuItem).where(MenuItem.id.in_(seen_menu_item_ids))
        )
        for mi in mi_result.scalars().all():
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


# --- Swiggy order listing ---


@router.get("/swiggy/orders")
async def list_swiggy_orders(
    session: SessionDep,
    current_user: CurrentUser,
    count: int = Query(default=10, le=20),
):
    """Fetch recent Swiggy orders for the order picker UI.

    Calls the Swiggy MCP get_orders tool and returns parsed order summaries.
    Raises 422 (ProblemDetailError) if re-authentication is required.
    """
    import json

    from app.services.swiggy.auth import get_valid_token
    from app.services.swiggy.client import call_tool
    from app.services.swiggy.extract import _extract_text

    token = await get_valid_token(session, str(current_user.id))
    result = await call_tool(token, "get_orders", {"count": count})
    text = _extract_text(result)
    data = json.loads(text)
    orders = data.get("orders", data.get("data", {}).get("orders", []))
    return orders


# --- Source endpoints ---


@router.post("/sources/upload", response_model=UploadResponse, status_code=201)
async def upload_source(
    session: SessionDep,
    current_user: CurrentUser,
    file: Annotated[UploadFile, File()],
):
    """Upload a file (PDF invoice) and create an invoice source."""
    source = OrderSource(
        type="invoice",
        created_by=current_user.id,
    )
    session.add(source)
    await session.flush()

    content = await file.read()
    filename = file.filename or f"source_{source.id}.pdf"
    storage_path = await asyncio.to_thread(save_source_upload, content, source.id, filename)

    source.raw_data = {"storage_path": storage_path, "filename": filename}
    await session.commit()

    return UploadResponse(source_id=source.id, storage_path=storage_path)


@router.post("/sources/", response_model=OrderSourceResponse, status_code=201)
async def create_source(
    body: OrderSourceCreate,
    session: SessionDep,
    current_user: CurrentUser,
):
    """Create an order source (e.g., swiggy_order with order ID)."""
    source = OrderSource(
        type=body.type,
        raw_data=body.raw_data,
        created_by=current_user.id,
    )
    session.add(source)
    await session.commit()
    await session.refresh(source)
    return source


# --- Order endpoints ---


@router.post("/", response_model=OrderResponse, status_code=201)
async def create_order(
    body: OrderCreate,
    session: SessionDep,
    current_user: CurrentUser,
):
    """Initiate the splitting pipeline from a source.

    Two-phase flow: source was created earlier (fast write),
    this endpoint runs the full pipeline (extract → correlate → split).
    Idempotent: if an order already exists for this source, returns it.
    """
    with logfire.span("pipeline", source_id=str(body.source_id), user_id=str(current_user.id)):
        structlog.contextvars.bind_contextvars(source_id=str(body.source_id))
        logger.info("pipeline_start", user_id=str(current_user.id))

        # Load source
        source = await session.get(OrderSource, body.source_id)
        if not source:
            raise HTTPException(status_code=404, detail="Source not found")
        if source.created_by != current_user.id:
            raise HTTPException(status_code=403, detail="Not your source")

        # Idempotent: check if order already exists for this source
        existing = await session.execute(
            select(Order).where(Order.source_id == body.source_id).options(*_order_load_options())
        )
        existing_order = existing.scalar_one_or_none()
        if existing_order:
            return existing_order

        # Ensure current user is included in participants
        parsed_ids = list(body.participant_ids)
        if current_user.id not in parsed_ids:
            parsed_ids.append(current_user.id)

        with logfire.span("extraction"):
            items = await run_extraction(session, source)

        # Build classified dict for compute_splits
        item_total = sum(i["total"] for i in items if i["category"] == "item")
        fee_total = sum(i["total"] for i in items if i["category"] == "fee")
        classified = {
            "summary": {
                "item_total": item_total,
                "fee_total": fee_total,
                "grand_total": item_total + fee_total,
            },
            "items": items,
        }

        with logfire.span("snapshot_meal_plans"):
            members, menu_items = await _snapshot_meal_plans(session, parsed_ids)

        with logfire.span("correlate"):
            grocery_items = [i for i in items if i["category"] == "item"]
            uses = await correlate(menu_items, grocery_items)

        with logfire.span("split"):
            result = compute_splits(classified, members, uses, str(current_user.id))

        with logfire.span("persist"):
            is_no_split = result.get("noSplit", False)
            order = Order(
                paid_by=current_user.id,
                source_id=source.id,
                status="no_split" if is_no_split else "draft",
                snapshot={"members": members, "uses": uses, "menu_items": menu_items},
                result=result,
            )
            session.add(order)
            await session.flush()

            structlog.contextvars.bind_contextvars(order_id=str(order.id))

            for pid in parsed_ids:
                session.add(OrderParticipant(order_id=order.id, user_id=pid))

            if not is_no_split:
                for split in _create_split_rows(order.id, result):
                    session.add(split)

            await session.commit()

        logger.info("pipeline_complete")

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
    """Cancel a draft or no_split order. Only the payer can cancel."""
    order = await _get_order_or_404(session, order_id)

    if order.paid_by != current_user.id:
        raise HTTPException(status_code=403, detail="Only the payer can cancel this order")
    if order.status not in ("draft", "no_split"):
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
    """Edit split assignments for a draft or no_split order. Backend recomputes amounts."""
    order = await _get_order_or_404(session, order_id)

    if order.paid_by != current_user.id:
        raise HTTPException(status_code=403, detail="Only the payer can edit splits")
    if order.status not in ("draft", "no_split"):
        raise HTTPException(
            status_code=400, detail=f"Cannot edit splits for order with status '{order.status}'"
        )

    if not order.result:
        raise HTTPException(status_code=400, detail="Order has no result data")

    # Flatten all items from stored result, separate by category
    all_items_flat: list[dict] = []
    for split_group in order.result.get("splits", []):
        for item in split_group.get("groceryItems", []):
            all_items_flat.append(item)

    fee_items = [i for i in all_items_flat if i.get("category") == "fee"]
    non_fee_items = {i["upc"]: i for i in all_items_flat if i.get("category") != "fee"}
    fee_upcs = {i["upc"] for i in fee_items}

    # Reject fee UPCs in request
    for assignment in data.assignments:
        if assignment.upc in fee_upcs:
            raise HTTPException(status_code=400, detail=f"Cannot assign fee item: {assignment.upc}")

    # Validate all non-fee UPCs are present
    request_upcs = {a.upc for a in data.assignments}
    missing = set(non_fee_items.keys()) - request_upcs
    if missing:
        raise HTTPException(
            status_code=400, detail=f"Missing assignments for UPCs: {sorted(missing)}"
        )
    unknown = request_upcs - set(non_fee_items.keys())
    if unknown:
        raise HTTPException(status_code=400, detail=f"Unknown UPC: {sorted(unknown)[0]}")

    # Group non-fee items by member set, track members_with_items
    members_with_items: set[str] = set()
    groups: dict[frozenset, list[dict]] = defaultdict(list)
    for assignment in data.assignments:
        member_key = (
            frozenset(assignment.member_ids)
            if assignment.member_ids
            else frozenset([str(order.paid_by)])
        )
        groups[member_key].append(non_fee_items[assignment.upc])
        members_with_items.update(member_key)

    # Auto-assign fees to members who have items
    fee_member_key = (
        frozenset(members_with_items) if members_with_items else frozenset([str(order.paid_by)])
    )
    for fee_item in fee_items:
        groups[fee_member_key].append(fee_item)

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

    # Auto-transition status based on post-condition
    order.status = "no_split" if members_with_items <= {str(order.paid_by)} else "draft"

    await session.commit()
    session.expunge_all()
    return await _get_order_or_404(session, order.id)


@router.post("/{order_id}/approve", response_model=OrderResponse)
async def approve_order(
    order_id: uuid.UUID,
    session: SessionDep,
    current_user: CurrentUser,
):
    """Approve a draft order — push splits to Splitwise."""
    order = await _get_order_or_404(session, order_id)

    if order.paid_by != current_user.id:
        raise HTTPException(status_code=403, detail="Only the payer can approve this order")
    if order.status != "draft":
        raise HTTPException(
            status_code=400, detail=f"Cannot approve order with status '{order.status}'"
        )

    # Build member_id_to_sw_id mapping from DB (single bulk query)
    participant_user_ids = [p.user_id for p in order.participants]
    member_id_to_sw_id: dict[str, int] = {}
    payer_sw_id: int | None = None

    users_result = await session.execute(select(User).where(User.id.in_(participant_user_ids)))
    users_by_id = {u.id: u for u in users_result.scalars().all()}

    for uid in participant_user_ids:
        user = users_by_id.get(uid)
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
    from app.services.vault import get_secret

    payer_token = await get_secret(session, f"splitwise_token:{order.paid_by}")

    audits = await push_splits_audited(
        session=session,
        order_id=order.id,
        split_result=split_result,
        member_id_to_sw_id=member_id_to_sw_id,
        payer_sw_id=payer_sw_id,
        token=payer_token,
    )

    # Update split statuses from audit results
    audit_by_desc = {a.request_payload.get("description", ""): a for a in audits}
    payer_id = str(order.paid_by)
    all_success = True
    for split in order.splits:
        if split.member_ids == [payer_id]:
            split.status = "success"
            continue

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
