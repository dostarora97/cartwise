"""
Auth routes.

OAuth login is handled by Supabase Auth on the frontend.
The backend only validates Supabase JWTs and returns user info.

Splitwise OAuth 2.0 connection is handled here — users connect their
Splitwise account during onboarding so expenses are created from their account.

In development (DEBUG=true), a dev-login endpoint is available
for testing without a frontend.
"""

import secrets
import uuid
from datetime import UTC, datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials
from itsdangerous import BadSignature, URLSafeTimedSerializer
from pydantic import BaseModel
from sqlalchemy import select

from app.auth.dependencies import CurrentUser, security
from app.auth.jwt import create_test_token, decode_supabase_jwt
from app.config import settings
from app.database import SessionDep
from app.models.order import Order
from app.models.user import User
from app.schemas.user import UserResponse
from app.services.storage import delete_order_files
from app.services.vault import delete_secret, store_secret

_signer = URLSafeTimedSerializer(settings.SESSION_SECRET_KEY)
STATE_MAX_AGE = 600  # 10 minutes


def _sign_state(user_id: str, nonce: str) -> str:
    return _signer.dumps({"uid": user_id, "nonce": nonce})


def _verify_state(state: str, max_age: int = STATE_MAX_AGE) -> str | None:
    try:
        data = _signer.loads(state, max_age=max_age)
        return data["uid"]
    except BadSignature, KeyError, TypeError:
        return None


router = APIRouter(prefix="/auth", tags=["auth"])


@router.get("/me", response_model=UserResponse)
async def get_me(current_user: CurrentUser):
    """Get the current authenticated user.

    Returns 404 if the user hasn't completed onboarding yet.
    """
    return current_user


class DeleteAccountRequest(BaseModel):
    action: str


@router.delete("/me")
async def delete_account(
    body: DeleteAccountRequest, current_user: CurrentUser, session: SessionDep
):
    """Permanently delete the current user's account and all associated data."""
    if body.action != "delete":
        raise HTTPException(status_code=400, detail="Must confirm with action: 'delete'")

    # 1. Delete vault secret (Splitwise token)
    await delete_secret(session, f"splitwise_token:{current_user.id}")

    # 2. Delete storage files for user's orders
    import asyncio

    result = await session.execute(select(Order).where(Order.paid_by == current_user.id))
    for order in result.scalars():
        await asyncio.to_thread(delete_order_files, order.id)

    # 3. Delete user — DB CASCADE handles all related rows
    from sqlalchemy import delete

    await session.execute(delete(User).where(User.id == current_user.id))
    await session.commit()

    return {"detail": "Account deleted"}


@router.post("/onboard", response_model=UserResponse, status_code=201)
async def onboard(
    credentials: Annotated[HTTPAuthorizationCredentials, Depends(security)],
    session: SessionDep,
):
    """Complete onboarding — creates the user record in the DB.

    Requires a valid Supabase JWT. The user must NOT already exist.
    All user fields (email, name, avatar, provider) come from JWT claims.
    """
    supabase_user = decode_supabase_jwt(credentials.credentials)
    if supabase_user is None:
        raise HTTPException(status_code=401, detail="Invalid or expired token")

    result = await session.execute(select(User).where(User.oauth_id == supabase_user.auth_id))
    if result.scalar_one_or_none() is not None:
        raise HTTPException(status_code=409, detail="User already onboarded")

    user = User(
        email=supabase_user.email,
        name=supabase_user.name or supabase_user.email.split("@")[0],
        avatar_url=supabase_user.avatar_url,
        oauth_provider=supabase_user.provider,
        oauth_id=supabase_user.auth_id,
    )
    session.add(user)
    await session.commit()
    await session.refresh(user)
    return user


# --- Splitwise OAuth 2.0 ---


class SplitwiseExchangeRequest(BaseModel):
    code: str
    state: str
    redirect_uri: str


class SplitwiseConnectResponse(BaseModel):
    authorize_url: str
    redirect_uri: str


@router.post("/splitwise/connect", response_model=SplitwiseConnectResponse)
async def splitwise_connect(current_user: CurrentUser):
    """Start the Splitwise OAuth flow.

    Returns an authorize_url the frontend navigates to, plus the redirect_uri
    that the frontend callback route must echo back during token exchange.
    """
    from authlib.integrations.httpx_client import AsyncOAuth2Client

    state = _sign_state(str(current_user.id), secrets.token_urlsafe(16))
    redirect_uri = f"{settings.FRONTEND_URL}/auth/connect/splitwise"

    async with AsyncOAuth2Client(
        client_id=settings.SPLITWISE_CONSUMER_KEY,
        client_secret=settings.SPLITWISE_CONSUMER_SECRET,
    ) as client:
        uri, _ = client.create_authorization_url(
            f"{settings.SPLITWISE_OAUTH_BASE_URL}/oauth/authorize",
            redirect_uri=redirect_uri,
            state=state,
        )

    return {"authorize_url": uri, "redirect_uri": redirect_uri}


@router.post("/splitwise/exchange")
async def splitwise_exchange(body: SplitwiseExchangeRequest, session: SessionDep):
    """Exchange a Splitwise authorization code for an access token.

    Called by the frontend callback route after Splitwise redirects back.
    The frontend forwards code + state + redirect_uri; backend handles
    token exchange, stores the token in Vault, and returns success/failure.
    """
    from authlib.integrations.httpx_client import AsyncOAuth2Client

    user_id = _verify_state(body.state)
    if not user_id:
        raise HTTPException(status_code=400, detail="Invalid state")

    try:
        async with AsyncOAuth2Client(
            client_id=settings.SPLITWISE_CONSUMER_KEY,
            client_secret=settings.SPLITWISE_CONSUMER_SECRET,
            token_endpoint_auth_method="client_secret_post",
        ) as client:
            token = await client.fetch_token(
                f"{settings.SPLITWISE_OAUTH_BASE_URL}/oauth/token",
                code=body.code,
                redirect_uri=body.redirect_uri,
            )

            access_token = token.get("access_token")
            if not access_token:
                raise HTTPException(status_code=502, detail="No access token received")

            resp = await client.get(
                f"{settings.SPLITWISE_BASE_URL}/get_current_user",
                headers={"Authorization": f"Bearer {access_token}"},
            )
            if resp.status_code != 200:
                raise HTTPException(status_code=502, detail="Failed to fetch Splitwise user")

            sw_user = resp.json()["user"]

    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=502, detail="Splitwise OAuth exchange failed") from exc

    await store_secret(
        session,
        f"splitwise_token:{user_id}",
        access_token,
        f"Splitwise token for user {user_id}",
    )

    user = await session.get(User, uuid.UUID(user_id))
    user.splitwise_user_id = sw_user["id"]
    user.splitwise_connected_at = datetime.now(UTC)
    await session.commit()

    return {"success": True}


# --- Swiggy OAuth 2.1 + PKCE ---


class SwiggyConnectResponse(BaseModel):
    authorize_url: str
    redirect_uri: str
    code_verifier: str


class SwiggyExchangeRequest(BaseModel):
    code: str
    state: str
    code_verifier: str
    redirect_uri: str


@router.post("/swiggy/connect", response_model=SwiggyConnectResponse)
async def swiggy_connect(current_user: CurrentUser):
    """Start the Swiggy OAuth 2.1 + PKCE flow.

    Returns authorize_url, redirect_uri, and code_verifier.
    The frontend stores code_verifier and sends it back during exchange.
    """
    import base64
    import hashlib

    code_verifier = secrets.token_urlsafe(64)
    digest = hashlib.sha256(code_verifier.encode()).digest()
    code_challenge = base64.urlsafe_b64encode(digest).rstrip(b"=").decode()

    state = _sign_state(str(current_user.id), secrets.token_urlsafe(16))
    redirect_uri = f"{settings.FRONTEND_URL}/auth/connect/swiggy"

    authorize_url = (
        f"{settings.SWIGGY_MCP_SERVER_URL}/auth/authorize?"
        f"response_type=code&"
        f"client_id={settings.SWIGGY_MCP_CLIENT_ID}&"
        f"code_challenge={code_challenge}&"
        f"code_challenge_method=S256&"
        f"redirect_uri={redirect_uri}&"
        f"state={state}&"
        f"scope=mcp:tools+mcp:resources+mcp:prompts"
    )

    return {
        "authorize_url": authorize_url,
        "redirect_uri": redirect_uri,
        "code_verifier": code_verifier,
    }


@router.post("/swiggy/exchange")
async def swiggy_exchange(body: SwiggyExchangeRequest, session: SessionDep):
    """Exchange a Swiggy authorization code for tokens.

    The frontend sends code, state, code_verifier, and redirect_uri.
    Backend exchanges for tokens, stores them in Vault, and updates the user.
    """
    import json

    import httpx

    user_id = _verify_state(body.state)
    if not user_id:
        raise HTTPException(status_code=400, detail="Invalid state")

    async with httpx.AsyncClient() as client:
        resp = await client.post(
            f"{settings.SWIGGY_MCP_SERVER_URL}/auth/token",
            data={
                "grant_type": "authorization_code",
                "client_id": settings.SWIGGY_MCP_CLIENT_ID,
                "code": body.code,
                "code_verifier": body.code_verifier,
                "redirect_uri": body.redirect_uri,
            },
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            timeout=10.0,
        )

    if resp.status_code != 200:
        raise HTTPException(status_code=502, detail="Swiggy token exchange failed")

    token_data = resp.json()
    access_token = token_data.get("access_token")
    refresh_token = token_data.get("refresh_token")
    if not access_token:
        raise HTTPException(status_code=502, detail="No access token received from Swiggy")

    # Decode JWT to get sub (Swiggy user ID) and exp
    from app.services.swiggy.auth import _extract_exp

    swiggy_user_id = _extract_sub(access_token)
    expires_at = _extract_exp(access_token)

    # Store tokens in vault
    vault_data = json.dumps(
        {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "expires_at": expires_at,
        }
    )
    await store_secret(
        session,
        f"swiggy_token:{user_id}",
        vault_data,
        f"Swiggy MCP tokens for user {user_id}",
    )

    # Update user record
    user = await session.get(User, uuid.UUID(user_id))
    if user:
        user.swiggy_user_id = swiggy_user_id
        user.swiggy_connected_at = datetime.now(UTC)
    await session.commit()

    return {"success": True}


def _extract_sub(token: str) -> str | None:
    """Extract sub claim from JWT without verification."""
    import base64
    import json

    parts = token.split(".")
    if len(parts) != 3:
        return None
    payload = parts[1] + "=" * (4 - len(parts[1]) % 4)
    claims = json.loads(base64.urlsafe_b64decode(payload))
    return claims.get("sub")


# --- Dev-only endpoints (DEBUG=true) ---


class DevLoginRequest(BaseModel):
    email: str
    name: str


class DevLoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserResponse


@router.post("/dev-login", response_model=DevLoginResponse)
async def dev_login(data: DevLoginRequest, session: SessionDep):
    """Development-only login. Creates a user and returns a JWT.

    NOT available in production (DEBUG must be true).
    Use this to test authenticated endpoints from Swagger UI.
    """
    if not settings.get("DEBUG", False):
        raise HTTPException(status_code=404, detail="Not found")

    # Find or create user
    result = await session.execute(select(User).where(User.email == data.email))
    user = result.scalar_one_or_none()

    if user is None:
        user = User(
            email=data.email,
            name=data.name,
            oauth_provider="dev",
            oauth_id=f"dev-{uuid.uuid4()}",
        )
        session.add(user)
        await session.commit()
        await session.refresh(user)

    token = create_test_token(user.oauth_id, user.email)

    return DevLoginResponse(
        access_token=token,
        user=UserResponse.model_validate(user),
    )
