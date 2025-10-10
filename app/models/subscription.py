from __future__ import annotations

from datetime import datetime

from sqlalchemy import CheckConstraint, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import Boolean, DateTime, Integer, String

from .base import Base


class Subscription(Base):
    __tablename__ = "subscriptions"

    owner_user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE")
    )
    plan_id: Mapped[int] = mapped_column(ForeignKey("plans.id"))
    status: Mapped[str] = mapped_column(String(20), default="inactive")
    current_period_start: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    current_period_end: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    cancel_at_period_end: Mapped[bool] = mapped_column(Boolean, default=False)
    trial_end: Mapped[Mapped[datetime | None]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    seats_used: Mapped[int] = mapped_column(Integer, default=1)

    owner = relationship("User", lazy="joined")
    plan = relationship("Plan", lazy="joined")

    __table_args__ = (
        CheckConstraint(
            "(current_period_end IS NULL) OR (current_period_start IS NOT NULL AND current_period_end > current_period_start)",
            name="sub_period_valid",
        ),
        CheckConstraint("seats_used >= 0", name="sub_seats_used_non_negative"),
    )
