from __future__ import annotations

import uuid
from datetime import datetime
from enum import StrEnum

from sqlalchemy import DateTime, Enum, ForeignKey, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models import Base


class OrderSourceType(StrEnum):
    invoice = "invoice"
    swiggy_order = "swiggy_order"


class OrderSource(Base):
    __tablename__ = "order_sources"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    type: Mapped[OrderSourceType] = mapped_column(
        Enum(OrderSourceType, name="order_source_type", native_enum=True)
    )
    raw_data: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    items: Mapped[list | None] = mapped_column(JSONB, nullable=True)
    created_by: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    creator: Mapped[User] = relationship(foreign_keys=[created_by])
    order: Mapped[Order | None] = relationship(back_populates="source")
