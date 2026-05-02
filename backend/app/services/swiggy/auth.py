"""Swiggy MCP token management with auto-refresh."""

from __future__ import annotations

import json
from datetime import UTC, datetime

import httpx
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.errors import ProblemDetailError
from app.services.vault import get_secret, store_secret


async def get_valid_token(session: AsyncSession, user_id: str) -> str:
    """Get a valid Swiggy access token, refreshing if expired.

    Raises ProblemDetailError if re-authentication is required.
    """
    raw = await get_secret(session, f"swiggy_token:{user_id}")
    if not raw:
        _raise_reauth_required()

    token_data = json.loads(raw)
    access_token = token_data.get("access_token")
    refresh_token = token_data.get("refresh_token")
    expires_at = token_data.get("expires_at")

    if not access_token or not refresh_token:
        _raise_reauth_required()

    if expires_at and datetime.fromtimestamp(expires_at, tz=UTC) > datetime.now(tz=UTC):
        return access_token

    # Token expired — attempt refresh
    # TODO(#130): Migrate to FastMCP's built-in OAuth token refresh
    new_token_data = await _refresh_token(refresh_token)
    if not new_token_data:
        _raise_reauth_required()

    await store_secret(
        session,
        f"swiggy_token:{user_id}",
        json.dumps(new_token_data),
        "Swiggy MCP OAuth tokens",
    )
    return new_token_data["access_token"]


async def _refresh_token(refresh_token: str) -> dict | None:
    """Attempt to refresh the Swiggy access token."""
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            f"{settings.SWIGGY_MCP_SERVER_URL}/auth/token",
            data={
                "grant_type": "refresh_token",
                "client_id": settings.SWIGGY_MCP_CLIENT_ID,
                "refresh_token": refresh_token,
            },
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            timeout=10.0,
        )

    if resp.status_code != 200:
        return None

    data = resp.json()
    return {
        "access_token": data["access_token"],
        "refresh_token": data.get("refresh_token", refresh_token),
        "expires_at": data.get("expires_at") or _extract_exp(data["access_token"]),
    }


def _extract_exp(access_token: str) -> int | None:
    """Extract expiry from JWT without verification (we trust the issuer)."""
    import base64

    parts = access_token.split(".")
    if len(parts) != 3:
        return None
    payload = parts[1] + "=" * (4 - len(parts[1]) % 4)
    claims = json.loads(base64.urlsafe_b64decode(payload))
    return claims.get("exp")


def _raise_reauth_required() -> None:
    raise ProblemDetailError(
        type="tag:cartwise.app,2026:problem/provider-auth-required",
        title="External provider authentication required",
        status=422,
        detail="Your Swiggy connection has expired. Please reconnect.",
        provider="swiggy",
        connect_url="/api/v1/auth/swiggy/connect",
    )
