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
from app.models.user import User
from app.schemas.user import UserResponse
from app.services.vault import store_secret

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


@router.post("/splitwise/connect")
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
