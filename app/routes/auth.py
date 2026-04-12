"""
Auth routes.

OAuth login is handled by Supabase Auth on the frontend.
The backend only validates Supabase JWTs and returns user info.

In development (DEBUG=true), a dev-login endpoint is available
for testing without a frontend.
"""

import uuid

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from sqlalchemy import select

from app.auth.dependencies import CurrentUser
from app.auth.jwt import create_test_token
from app.config import settings
from app.database import SessionDep
from app.models.user import User
from app.schemas.user import UserResponse

router = APIRouter(prefix="/auth", tags=["auth"])


@router.get("/me", response_model=UserResponse)
async def get_me(current_user: CurrentUser):
    """Get the current authenticated user."""
    return current_user


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
