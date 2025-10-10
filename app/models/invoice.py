from __future__ import annotations

from datetime import datetime

import sqlalchemy as sa
from sqlalchemy import CheckConstraint, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import DateTime, Integer, String

from .base import Base


class Invoice(Base):
    __tablename__ = "invoices"

    subscription_id: Mapped[int] = mapped_column(
        ForeignKey("subscriptions.id", ondelete="CASCADE"), index=True
    )
    amount_cents: Mapped[int] = mapped_column(Integer)
    currency: Mapped[str] = mapped_column(String(3), default="EUR")

    period_start: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    period_end: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )

    status: Mapped[str] = mapped_column(String(20), default="pending")
    attempts: Mapped[int] = mapped_column(Integer, default=0)
    discount_cents: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    promocode_code: Mapped[str | None] = mapped_column(String(50), nullable=True)
    giftcard_code: Mapped[str | None] = mapped_column(String(50), nullable=True)
    next_retry_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=sa.text("now()"), nullable=False
    )

    subscription = relationship("Subscription", lazy="joined")
    payments = relationship("Payment", back_populates="invoice", lazy="selectin")

    __table_args__ = (
        CheckConstraint("amount_cents >= 0", name="invoice_amount_non_negative"),
        CheckConstraint("period_end > period_start", name="invoice_period_valid"),
    )
