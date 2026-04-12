"""
Auth routes.

OAuth login is handled by Supabase Auth on the frontend.
The backend only validates Supabase JWTs and returns user info.

In development (DEBUG=true), a dev-login endpoint is available
for testing without a frontend.
"""

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials
from pydantic import BaseModel
from sqlalchemy import select

from app.auth.dependencies import CurrentUser, security
from app.auth.jwt import create_test_token, decode_supabase_jwt
from app.config import settings
from app.database import SessionDep
from app.models.user import User
from app.schemas.user import OnboardRequest, UserResponse

router = APIRouter(prefix="/auth", tags=["auth"])


@router.get("/me", response_model=UserResponse)
async def get_me(current_user: CurrentUser):
    """Get the current authenticated user.

    Returns 404 if the user hasn't completed onboarding yet.
    """
    return current_user


@router.post("/onboard", response_model=UserResponse, status_code=201)
async def onboard(
    data: OnboardRequest,
    credentials: Annotated[HTTPAuthorizationCredentials, Depends(security)],
    session: SessionDep,
):
    """Complete onboarding — creates the user record in the DB.

    Requires a valid Supabase JWT. The user must NOT already exist.
    OAuth claims (email, avatar, provider) come from the JWT.
    Name, phone, and splitwise_user_id come from the request body.
    """
    supabase_user = decode_supabase_jwt(credentials.credentials)
    if supabase_user is None:
        raise HTTPException(status_code=401, detail="Invalid or expired token")

    # Check user doesn't already exist
    result = await session.execute(select(User).where(User.oauth_id == supabase_user.auth_id))
    if result.scalar_one_or_none() is not None:
        raise HTTPException(status_code=409, detail="User already onboarded")

    user = User(
        email=supabase_user.email,
        name=data.name,
        phone=data.phone,
        avatar_url=supabase_user.avatar_url,
        oauth_provider=supabase_user.provider,
        oauth_id=supabase_user.auth_id,
        splitwise_user_id=data.splitwise_user_id,
    )
    session.add(user)
    await session.commit()
    await session.refresh(user)
    return user


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
