"""
Mock Splitwise Server

A lightweight FastAPI app that mimics the Splitwise API surface.
Uses an in-memory ledger — no external dependencies.

Run: uv run uvicorn mock.splitwise:app --port 8001
URL: http://localhost:8001/api/mock/splitwise/v3.0/...

The ledger is just a dict in memory. It resets when the server restarts.
For persistent verification, check the splitwise_audit_log table in the real DB.
"""

import itertools
from datetime import UTC, datetime

from fastapi import FastAPI, Request

app = FastAPI(title="Mock Splitwise", version="0.1.0")

# --- In-memory ledger ---

_expense_id_counter = itertools.count(start=9000000001)
_expenses: dict[int, dict] = {}  # expense_id → expense data

MOCK_USER = {
    "id": 99999,
    "first_name": "Mock",
    "last_name": "User",
    "email": "mock@cartwise.local",
    "registration_status": "confirmed",
    "picture": {"small": "", "medium": "", "large": ""},
    "custom_picture": False,
    "default_currency": "INR",
    "locale": "en",
}

MOCK_FRIENDS = [
    {
        "id": 99001,
        "first_name": "Friend",
        "last_name": "One",
        "email": "friend1@cartwise.local",
        "registration_status": "confirmed",
        "picture": {"small": "", "medium": "", "large": ""},
        "custom_picture": False,
        "balance": [],
        "groups": [],
        "updated_at": "2026-01-01T00:00:00Z",
    },
    {
        "id": 99002,
        "first_name": "Friend",
        "last_name": "Two",
        "email": "friend2@cartwise.local",
        "registration_status": "confirmed",
        "picture": {"small": "", "medium": "", "large": ""},
        "custom_picture": False,
        "balance": [],
        "groups": [],
        "updated_at": "2026-01-01T00:00:00Z",
    },
    {
        "id": 99003,
        "first_name": "Friend",
        "last_name": "Three",
        "email": "friend3@cartwise.local",
        "registration_status": "confirmed",
        "picture": {"small": "", "medium": "", "large": ""},
        "custom_picture": False,
        "balance": [],
        "groups": [],
        "updated_at": "2026-01-01T00:00:00Z",
    },
]

PREFIX = "/api/mock/splitwise/v3.0"


# --- Endpoints ---


@app.get(f"{PREFIX}/get_current_user")
async def get_current_user():
    return {"user": MOCK_USER}


@app.get(f"{PREFIX}/get_friends")
async def get_friends():
    return {"friends": MOCK_FRIENDS}


@app.get(f"{PREFIX}/get_groups")
async def get_groups():
    return {"groups": []}


@app.post(f"{PREFIX}/create_expense")
async def create_expense(request: Request):
    body = await request.json()

    expense_id = next(_expense_id_counter)
    now = datetime.now(UTC).isoformat()

    # Extract users from flattened payload
    users = []
    i = 0
    while f"users__{i}__user_id" in body:
        users.append(
            {
                "user": {
                    "id": body[f"users__{i}__user_id"],
                    "first_name": "User",
                    "last_name": str(i),
                },
                "user_id": body[f"users__{i}__user_id"],
                "paid_share": body.get(f"users__{i}__paid_share", "0"),
                "owed_share": body.get(f"users__{i}__owed_share", "0"),
                "net_balance": str(
                    float(body.get(f"users__{i}__paid_share", "0"))
                    - float(body.get(f"users__{i}__owed_share", "0"))
                ),
            }
        )
        i += 1

    # Build repayments (who owes whom)
    payer_id = None
    for u in users:
        if float(u["paid_share"]) > 0:
            payer_id = u["user_id"]
            break

    repayments = []
    for u in users:
        if u["user_id"] != payer_id and float(u["owed_share"]) > 0:
            repayments.append(
                {
                    "from": u["user_id"],
                    "to": payer_id,
                    "amount": u["owed_share"],
                }
            )

    expense = {
        "id": expense_id,
        "cost": body.get("cost", "0"),
        "description": body.get("description", ""),
        "details": body.get("details"),
        "currency_code": body.get("currency_code", "INR"),
        "group_id": body.get("group_id", 0),
        "date": now,
        "created_at": now,
        "updated_at": now,
        "deleted_at": None,
        "payment": False,
        "repayments": repayments,
        "users": users,
        "comments": [],
        "category": {"id": 12, "name": "Groceries"},
        "receipt": {"large": None, "original": None},
        "created_by": MOCK_USER,
        "updated_by": MOCK_USER,
        "deleted_by": None,
    }

    _expenses[expense_id] = expense

    return {"expenses": [expense], "errors": {}}


@app.post(f"{PREFIX}/delete_expense/{{expense_id}}")
async def delete_expense(expense_id: int):
    if expense_id in _expenses:
        _expenses[expense_id]["deleted_at"] = datetime.now(UTC).isoformat()
        return {"success": True, "errors": {}}
    return {"success": False, "errors": {"base": ["Expense not found"]}}


# --- Bonus: inspect the ledger (not part of real Splitwise API) ---


@app.get(f"{PREFIX}/get_expenses")
async def get_expenses():
    active = [e for e in _expenses.values() if e["deleted_at"] is None]
    return {"expenses": active}


@app.get(f"{PREFIX}/_ledger")
async def get_ledger():
    """Debug endpoint: see all expenses including deleted ones."""
    return {
        "total": len(_expenses),
        "active": len([e for e in _expenses.values() if e["deleted_at"] is None]),
        "deleted": len([e for e in _expenses.values() if e["deleted_at"] is not None]),
        "expenses": list(_expenses.values()),
    }


@app.post(f"{PREFIX}/_reset")
async def reset_ledger():
    """Debug endpoint: clear all expenses."""
    _expenses.clear()
    return {"success": True, "message": "Ledger cleared"}
