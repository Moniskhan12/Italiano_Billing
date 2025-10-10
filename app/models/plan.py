from __future__ import annotations

from sqlalchemy import CheckConstraint
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.types import Boolean, Integer, String

from .base import Base


class Plan(Base):
    __tablename__ = "plans"

    code: Mapped[str] = mapped_column(
        String(50), unique=True, index=True
    )  # e.g. P30D / P6M / P1Y
    name: Mapped[str] = mapped_column(String(100))
    period_iso: Mapped[str] = mapped_column(String(20))  # ISO 8601: P30D, P6M, P1Y
    price_cents: Mapped[int] = mapped_column(Integer)
    currency: Mapped[str] = mapped_column(String(3), default="EUR")
    seats: Mapped[int] = mapped_column(Integer, default=1)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    __table_args__ = (
        CheckConstraint("price_cents >= 0", name="plans_price_non_negative"),
        CheckConstraint("seats >= 1", name="plans_seats_positive"),
    )
