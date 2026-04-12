"""
Splitwise Integration with Audit Log

Every API call is persisted in the splitwise_audit_log table:
  1. Insert "pending" row + COMMIT (survives crashes)
  2. Make the API call
  3. Update row to "success" or "failed" + COMMIT

Feature toggle: SPLITWISE_ENABLED must be true or all calls are refused.
"""

import hashlib
import json
import uuid
from datetime import UTC, datetime

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models.splitwise_audit import SplitwiseAuditLog


def _base_url() -> str:
    url = settings.get("SPLITWISE_BASE_URL", "")
    if not url:
        raise SplitwiseDisabledError("SPLITWISE_BASE_URL is not configured.")
    return url


class SplitwiseDisabledError(Exception):
    pass


def _check_enabled() -> None:
    if not settings.get("SPLITWISE_ENABLED", False):
        raise SplitwiseDisabledError(
            "Splitwise integration is disabled. Set SPLITWISE_ENABLED=true in settings."
        )


def _headers() -> dict:
    return {"Authorization": f"Bearer {settings.SPLITWISE_API_KEY}"}


def _payload_hash(payload: dict) -> str:
    """Deterministic hash of a payload for idempotency checks."""
    canonical = json.dumps(payload, sort_keys=True)
    return hashlib.sha256(canonical.encode()).hexdigest()[:16]


def _build_expense_payload(
    description: str,
    cost: float,
    payer_sw_id: int,
    member_sw_ids: list[int],
    group_id: int = 0,
    details: str | None = None,
) -> dict:
    """Build the create_expense payload with equal split shares."""
    num_members = len(member_sw_ids)
    per_person = round(cost / num_members, 2)

    shares = [per_person] * num_members
    remainder = round(cost - sum(shares), 2)
    if remainder != 0:
        shares[0] = round(shares[0] + remainder, 2)

    payload = {
        "cost": f"{cost:.2f}",
        "description": description,
        "currency_code": "INR",
        "group_id": group_id,
    }

    if details:
        payload["details"] = details

    for i, sw_id in enumerate(member_sw_ids):
        payload[f"users__{i}__user_id"] = sw_id
        payload[f"users__{i}__paid_share"] = f"{cost:.2f}" if sw_id == payer_sw_id else "0.00"
        payload[f"users__{i}__owed_share"] = f"{shares[i]:.2f}"

    return payload


# --- Read-only operations (no audit needed) ---


def get_current_user() -> dict:
    _check_enabled()
    resp = httpx.get(f"{_base_url()}/get_current_user", headers=_headers())
    resp.raise_for_status()
    return resp.json()["user"]


def get_friends() -> list[dict]:
    _check_enabled()
    resp = httpx.get(f"{_base_url()}/get_friends", headers=_headers())
    resp.raise_for_status()
    return resp.json()["friends"]


def get_groups() -> list[dict]:
    _check_enabled()
    resp = httpx.get(f"{_base_url()}/get_groups", headers=_headers())
    resp.raise_for_status()
    return resp.json()["groups"]


# --- Audited write operations ---


async def create_expense_audited(
    session: AsyncSession,
    description: str,
    cost: float,
    payer_sw_id: int,
    member_sw_ids: list[int],
    order_id: uuid.UUID | None = None,
    group_id: int = 0,
    details: str | None = None,
) -> SplitwiseAuditLog:
    """Create an expense in Splitwise with full audit trail.

    Returns the audit log row (status will be "success" or "failed").
    """
    _check_enabled()

    payload = _build_expense_payload(
        description=description,
        cost=cost,
        payer_sw_id=payer_sw_id,
        member_sw_ids=member_sw_ids,
        group_id=group_id,
        details=details,
    )

    # Idempotency: check if we already succeeded with this exact payload for this order
    if order_id:
        phash = _payload_hash(payload)
        existing = await session.execute(
            select(SplitwiseAuditLog).where(
                SplitwiseAuditLog.order_id == order_id,
                SplitwiseAuditLog.action == "create_expense",
                SplitwiseAuditLog.status == "success",
            )
        )
        for row in existing.scalars():
            if _payload_hash(row.request_payload) == phash:
                return row  # Already created, skip

    # Step 1: Insert pending audit row
    audit = SplitwiseAuditLog(
        order_id=order_id,
        action="create_expense",
        status="pending",
        request_payload=payload,
    )
    session.add(audit)
    await session.commit()
    await session.refresh(audit)

    # Step 2: Call Splitwise API
    try:
        resp = httpx.post(f"{_base_url()}/create_expense", headers=_headers(), json=payload)
        resp.raise_for_status()
        data = resp.json()

        if data.get("errors") and len(data["errors"]) > 0:
            audit.status = "failed"
            audit.error_message = json.dumps(data["errors"])
        else:
            audit.status = "success"
            audit.splitwise_expense_id = data["expenses"][0]["id"]

        audit.response_payload = data

    except Exception as e:
        audit.status = "failed"
        audit.error_message = str(e)

    # Step 3: Update audit row
    audit.completed_at = datetime.now(UTC)
    await session.commit()

    return audit


async def delete_expense_audited(
    session: AsyncSession,
    splitwise_expense_id: int,
    order_id: uuid.UUID | None = None,
) -> SplitwiseAuditLog:
    """Delete an expense from Splitwise with audit trail."""
    _check_enabled()

    payload = {"expense_id": splitwise_expense_id}

    audit = SplitwiseAuditLog(
        order_id=order_id,
        action="delete_expense",
        status="pending",
        request_payload=payload,
        splitwise_expense_id=splitwise_expense_id,
    )
    session.add(audit)
    await session.commit()
    await session.refresh(audit)

    try:
        resp = httpx.post(
            f"{_base_url()}/delete_expense/{splitwise_expense_id}", headers=_headers()
        )
        resp.raise_for_status()
        data = resp.json()

        if data.get("success"):
            audit.status = "success"
        else:
            audit.status = "failed"
            audit.error_message = json.dumps(data.get("errors", {}))

        audit.response_payload = data

    except Exception as e:
        audit.status = "failed"
        audit.error_message = str(e)

    audit.completed_at = datetime.now(UTC)
    await session.commit()

    return audit


# --- High-level orchestrators ---


async def push_splits_audited(
    session: AsyncSession,
    order_id: uuid.UUID,
    split_result: dict,
    member_id_to_sw_id: dict[str, int],
    payer_sw_id: int,
    group_id: int = 0,
) -> list[SplitwiseAuditLog]:
    """Push all split groups to Splitwise with per-expense auditing.

    Args:
        session: DB session.
        order_id: Our order UUID (for audit trail).
        split_result: Output of compute_splits().
        member_id_to_sw_id: Map of our member ID → Splitwise user ID.
        payer_sw_id: Splitwise user ID of the payer.
        group_id: Splitwise group ID (0 for non-group).

    Returns:
        List of audit log rows (one per split).
    """
    _check_enabled()
    audits = []

    for split in split_result["splits"]:
        sw_ids = []
        for member_id in split["splitEquallyAmong"]:
            sw_id = member_id_to_sw_id.get(member_id)
            if sw_id is None:
                raise ValueError(f"No Splitwise user ID for member: {member_id}")
            sw_ids.append(sw_id)

        item_names = [g["description"] for g in split["groceryItems"]]
        desc = (
            ", ".join(item_names)
            if len(item_names) <= 3
            else f"{item_names[0]}, {item_names[1]} +{len(item_names) - 2} more"
        )

        details_lines = [f"- {g['description']}: ₹{g['total']:.2f}" for g in split["groceryItems"]]
        details = "\n".join(details_lines)

        audit = await create_expense_audited(
            session=session,
            description=desc,
            cost=split["amount"],
            payer_sw_id=payer_sw_id,
            member_sw_ids=sw_ids,
            order_id=order_id,
            group_id=group_id,
            details=details,
        )
        audits.append(audit)

        status_icon = "✓" if audit.status == "success" else "✗"
        print(f"  {status_icon} ₹{split['amount']:.2f} — {desc} [{audit.status}]")

    return audits


async def rollback_order_expenses(
    session: AsyncSession,
    order_id: uuid.UUID,
) -> list[SplitwiseAuditLog]:
    """Delete all successfully created Splitwise expenses for an order.

    Returns audit rows for the delete operations.
    """
    _check_enabled()

    result = await session.execute(
        select(SplitwiseAuditLog).where(
            SplitwiseAuditLog.order_id == order_id,
            SplitwiseAuditLog.action == "create_expense",
            SplitwiseAuditLog.status == "success",
            SplitwiseAuditLog.splitwise_expense_id.isnot(None),
        )
    )
    successful = result.scalars().all()

    delete_audits = []
    for audit_row in successful:
        delete_audit = await delete_expense_audited(
            session=session,
            splitwise_expense_id=audit_row.splitwise_expense_id,
            order_id=order_id,
        )
        delete_audits.append(delete_audit)

    return delete_audits


async def get_audit_log(
    session: AsyncSession,
    order_id: uuid.UUID,
) -> list[SplitwiseAuditLog]:
    """Get all audit log entries for an order."""
    result = await session.execute(
        select(SplitwiseAuditLog)
        .where(SplitwiseAuditLog.order_id == order_id)
        .order_by(SplitwiseAuditLog.created_at)
    )
    return list(result.scalars().all())
