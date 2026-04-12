"""
Auth dependencies for FastAPI route protection.

Validates Supabase JWT, finds or creates the user in our database.
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
    """Validate Supabase JWT and find-or-create user in our DB."""
    supabase_user = decode_supabase_jwt(credentials.credentials)
    if supabase_user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
        )

    # Find user by oauth_id (Supabase Auth UUID)
    result = await session.execute(select(User).where(User.oauth_id == supabase_user.auth_id))
    user = result.scalar_one_or_none()

    if user is None:
        # First login — create user from Supabase JWT claims
        user = User(
            email=supabase_user.email,
            name=supabase_user.name,
            avatar_url=supabase_user.avatar_url,
            oauth_provider=supabase_user.provider,
            oauth_id=supabase_user.auth_id,
        )
        session.add(user)
        await session.commit()
        await session.refresh(user)

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User account is inactive",
        )

    return user


CurrentUser = Annotated[User, Depends(get_current_user)]
