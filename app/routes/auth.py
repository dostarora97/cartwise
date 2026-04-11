from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.requests import Request
from starlette.responses import RedirectResponse

from app.auth.dependencies import CurrentUser
from app.auth.jwt import create_access_token
from app.auth.oauth import oauth
from app.database import get_session
from app.models.user import User
from app.schemas.user import UserResponse

router = APIRouter(prefix="/auth", tags=["auth"])


async def _get_or_create_user(
    session: AsyncSession,
    email: str,
    name: str,
    avatar_url: str | None,
    oauth_provider: str,
    oauth_id: str,
) -> User:
    result = await session.execute(
        select(User).where(User.oauth_provider == oauth_provider, User.oauth_id == oauth_id)
    )
    user = result.scalar_one_or_none()

    if user is None:
        user = User(
            email=email,
            name=name,
            avatar_url=avatar_url,
            oauth_provider=oauth_provider,
            oauth_id=oauth_id,
        )
        session.add(user)
        await session.commit()
        await session.refresh(user)

    return user


# --- Google OAuth ---


@router.get("/login/google")
async def login_google(request: Request):
    redirect_uri = request.url_for("auth_google_callback")
    return await oauth.google.authorize_redirect(request, redirect_uri)


@router.get("/callback/google", name="auth_google_callback")
async def auth_google_callback(
    request: Request,
    session: Annotated[AsyncSession, Depends(get_session)],
):
    token = await oauth.google.authorize_access_token(request)
    userinfo = token.get("userinfo")
    if userinfo is None:
        raise HTTPException(status_code=400, detail="Failed to get user info from Google")

    user = await _get_or_create_user(
        session=session,
        email=userinfo["email"],
        name=userinfo.get("name", userinfo["email"]),
        avatar_url=userinfo.get("picture"),
        oauth_provider="google",
        oauth_id=userinfo["sub"],
    )

    access_token = create_access_token(user.id)
    return {"access_token": access_token, "token_type": "bearer"}


# --- GitHub OAuth ---


@router.get("/login/github")
async def login_github(request: Request):
    redirect_uri = request.url_for("auth_github_callback")
    return await oauth.github.authorize_redirect(request, redirect_uri)


@router.get("/callback/github", name="auth_github_callback")
async def auth_github_callback(
    request: Request,
    session: Annotated[AsyncSession, Depends(get_session)],
):
    token = await oauth.github.authorize_access_token(request)

    resp = await oauth.github.get("user", token=token)
    github_user = resp.json()

    email = github_user.get("email")
    if not email:
        # GitHub user may not have a public email — fetch from /user/emails
        emails_resp = await oauth.github.get("user/emails", token=token)
        emails = emails_resp.json()
        primary = next((e for e in emails if e.get("primary")), None)
        email = primary["email"] if primary else f"{github_user['id']}@github.noemail"

    user = await _get_or_create_user(
        session=session,
        email=email,
        name=github_user.get("name") or github_user["login"],
        avatar_url=github_user.get("avatar_url"),
        oauth_provider="github",
        oauth_id=str(github_user["id"]),
    )

    access_token = create_access_token(user.id)
    return {"access_token": access_token, "token_type": "bearer"}


# --- Current User ---


@router.get("/me", response_model=UserResponse)
async def get_me(current_user: CurrentUser):
    return current_user
