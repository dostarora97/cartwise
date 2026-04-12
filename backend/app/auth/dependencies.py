"""
Auth dependencies for FastAPI route protection.

Validates Supabase JWT and looks up the user in our database.
Users must complete onboarding (POST /auth/onboard) before they exist in the DB.
"""

from typing import Annotated

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.jwt import decode_supabase_jwt
from app.database import get_session
from app.models.user import User

security = HTTPBearer()


async def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials, Depends(security)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> User:
    """Validate Supabase JWT and find user in our DB.

    Returns 401 if the token is invalid.
    Returns 404 if the user hasn't completed onboarding yet.
    """
    supabase_user = decode_supabase_jwt(credentials.credentials)
    if supabase_user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
        )

    result = await session.execute(select(User).where(User.oauth_id == supabase_user.auth_id))
    user = result.scalar_one_or_none()

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found — complete onboarding first",
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User account is inactive",
        )

    return user


CurrentUser = Annotated[User, Depends(get_current_user)]
