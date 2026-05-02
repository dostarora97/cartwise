"""MCP dynamic client registration (RFC 7591) for Swiggy."""

from __future__ import annotations

import httpx
import structlog

from app.config import settings

logger = structlog.get_logger()

_registered_clients: dict[str, str] = {}


async def ensure_client_registered(redirect_uri: str) -> str:
    """Register our redirect_uri with Swiggy MCP and return the client_id.

    Uses RFC 7591 dynamic client registration via the registration_endpoint
    advertised in Swiggy's OAuth well-known metadata.

    Results are cached in-memory — registration only happens once per
    redirect_uri per process lifetime.
    """
    if redirect_uri in _registered_clients:
        logger.info(
            "swiggy_registration_cache_hit",
            redirect_uri=redirect_uri,
            cached_client_id=_registered_clients[redirect_uri],
        )
        return _registered_clients[redirect_uri]

    registration_url = f"{settings.SWIGGY_MCP_SERVER_URL}/auth/register"

    payload = {
        "client_name": "CartWise",
        "redirect_uris": [redirect_uri],
        "grant_types": ["authorization_code"],
        "response_types": ["code"],
        "token_endpoint_auth_method": "none",
        "scope": "mcp:tools mcp:resources mcp:prompts",
    }

    logger.info(
        "swiggy_registration_request",
        url=registration_url,
        payload=payload,
    )

    async with httpx.AsyncClient() as client:
        resp = await client.post(
            registration_url,
            json=payload,
            timeout=10.0,
        )

    logger.info(
        "swiggy_registration_response",
        status_code=resp.status_code,
        headers=dict(resp.headers),
        body=resp.text,
    )

    if resp.status_code not in (200, 201):
        logger.error(
            "swiggy_registration_failed",
            status=resp.status_code,
            body=resp.text,
        )
        raise httpx.HTTPStatusError(
            f"Swiggy client registration failed: {resp.status_code}",
            request=resp.request,
            response=resp,
        )

    data = resp.json()
    client_id = data["client_id"]
    _registered_clients[redirect_uri] = client_id

    logger.info(
        "swiggy_client_registered",
        client_id=client_id,
        redirect_uri=redirect_uri,
        full_response_data=data,
    )

    return client_id
