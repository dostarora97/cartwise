from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, Integer, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(255))
    avatar_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    oauth_provider: Mapped[str] = mapped_column(String(50))
    oauth_id: Mapped[str] = mapped_column(String(255))
    splitwise_user_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    splitwise_connected_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    swiggy_user_id: Mapped[str | None] = mapped_column(String(50), nullable=True)
    swiggy_connected_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    is_active: Mapped[bool] = mapped_column(default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    # Relationships (string references — no circular imports needed)
    created_menu_items: Mapped[list[MenuItem]] = relationship(
        back_populates="creator", foreign_keys="MenuItem.created_by"
    )
    meal_plan: Mapped[MealPlan | None] = relationship(back_populates="user")

    @property
    def splitwise_connected(self) -> bool:
        return self.splitwise_connected_at is not None

    @property
    def swiggy_connected(self) -> bool:
        return self.swiggy_connected_at is not None
