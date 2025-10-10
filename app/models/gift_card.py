from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class GiftCard(Base):
    __tablename__ = "gift_card"

    code: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    amount_cents: Mapped[int] = mapped_column(Integer, nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False)
    is_redeemed: Mapped[bool] = mapped_column(Boolean, default=False)
    redeemed_by: Mapped[int | None] = mapped_column(
        ForeignKey("users.id"), nullable=True
    )
    redeemed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
