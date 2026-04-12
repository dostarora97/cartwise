"""
Auth routes.

OAuth login is handled by Supabase Auth on the frontend.
The backend only validates Supabase JWTs and returns user info.
"""

from fastapi import APIRouter

from app.auth.dependencies import CurrentUser
from app.schemas.user import UserResponse

router = APIRouter(prefix="/auth", tags=["auth"])


@router.get("/me", response_model=UserResponse)
async def get_me(current_user: CurrentUser):
    """Get the current authenticated user.

    The frontend obtains a JWT from Supabase Auth (via Google/GitHub OAuth),
    then sends it in the Authorization header. This endpoint validates it
    and returns the user profile.
    """
    return current_user
