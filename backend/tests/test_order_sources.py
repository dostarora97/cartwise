"""Unit tests for order source endpoints and the new two-phase order creation."""

import uuid

from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.order_source import OrderSource, OrderSourceType


async def test_upload_source(client: AsyncClient, auth_headers: dict, test_user):
    """POST /orders/sources/upload creates an invoice source with storage_path."""
    resp = await client.post(
        "/api/v1/orders/sources/upload",
        headers=auth_headers,
        files={"file": ("test.pdf", b"%PDF-1.4 fake content", "application/pdf")},
    )
    assert resp.status_code == 201
    data = resp.json()
    assert "source_id" in data
    assert "storage_path" in data


async def test_create_source_json(client: AsyncClient, auth_headers: dict, test_user):
    """POST /orders/sources/ creates a source from JSON body."""
    resp = await client.post(
        "/api/v1/orders/sources/",
        headers=auth_headers,
        json={"type": "swiggy_order", "raw_data": {"swiggy_order_id": "12345"}},
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["type"] == "swiggy_order"
    assert data["raw_data"] == {"swiggy_order_id": "12345"}
    assert data["created_by"] == str(test_user.id)


async def test_create_source_invalid_type(client: AsyncClient, auth_headers: dict, test_user):
    """POST /orders/sources/ with invalid type returns 422."""
    resp = await client.post(
        "/api/v1/orders/sources/",
        headers=auth_headers,
        json={"type": "invalid_type", "raw_data": {}},
    )
    assert resp.status_code == 422


async def test_create_order_source_not_found(client: AsyncClient, auth_headers: dict, test_user):
    """POST /orders/ with non-existent source_id returns 404."""
    resp = await client.post(
        "/api/v1/orders/",
        headers=auth_headers,
        json={"source_id": str(uuid.uuid4()), "participant_ids": [str(test_user.id)]},
    )
    assert resp.status_code == 404


async def test_create_order_not_owner(
    client: AsyncClient, auth_headers: dict, test_user, session: AsyncSession
):
    """POST /orders/ with source owned by another user returns 403."""
    from app.models.user import User

    other = User(email="other@x.com", name="Other", oauth_provider="google", oauth_id="other-id")
    session.add(other)
    await session.flush()

    source = OrderSource(type=OrderSourceType.swiggy_order, raw_data={}, created_by=other.id)
    session.add(source)
    await session.commit()
    await session.refresh(source)

    resp = await client.post(
        "/api/v1/orders/",
        headers=auth_headers,
        json={"source_id": str(source.id), "participant_ids": [str(test_user.id)]},
    )
    assert resp.status_code == 403


async def test_upload_source_no_auth(client: AsyncClient):
    """Upload without auth returns 401/403."""
    resp = await client.post(
        "/api/v1/orders/sources/upload",
        files={"file": ("test.pdf", b"fake", "application/pdf")},
    )
    assert resp.status_code in (401, 403)
