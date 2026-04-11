from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models import Base


class MealPlan(Base):
    __tablename__ = "meal_plans"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), unique=True
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    # Relationships
    user: Mapped[User] = relationship(back_populates="meal_plan")
    items: Mapped[list[MealPlanItem]] = relationship(
        back_populates="meal_plan", cascade="all, delete-orphan"
    )


class MealPlanItem(Base):
    __tablename__ = "meal_plan_items"
    __table_args__ = (UniqueConstraint("meal_plan_id", "menu_item_id"),)

    meal_plan_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("meal_plans.id", ondelete="CASCADE"), primary_key=True
    )
    menu_item_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("menu_items.id"), primary_key=True
    )

    # Relationships
    meal_plan: Mapped[MealPlan] = relationship(back_populates="items")
    menu_item: Mapped[MenuItem] = relationship()
