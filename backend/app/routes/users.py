import uuid

from fastapi import APIRouter, HTTPException
from sqlalchemy import select

from app.auth.dependencies import CurrentUser
from app.database import SessionDep
from app.models.user import User
from app.schemas.user import UserResponse, UserUpdate

router = APIRouter(prefix="/users", tags=["users"])


@router.get("/", response_model=list[UserResponse])
async def list_users(session: SessionDep):
    result = await session.execute(select(User).where(User.is_active.is_(True)))
    return result.scalars().all()


@router.get("/{user_id}", response_model=UserResponse)
async def get_user(user_id: uuid.UUID, session: SessionDep):
    user = await session.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user


@router.patch("/{user_id}", response_model=UserResponse)
async def update_user(
    user_id: uuid.UUID,
    data: UserUpdate,
    session: SessionDep,
    current_user: CurrentUser,
):
    if current_user.id != user_id:
        raise HTTPException(status_code=403, detail="Can only update your own profile")

    user = await session.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    update_data = data.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(user, key, value)

    await session.commit()
    await session.refresh(user)
    return user
