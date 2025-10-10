from __future__ import annotations

from datetime import datetime
from typing import Any

import sqlalchemy as sa
from sqlalchemy import ForeignKey, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import DateTime, String

from .base import Base


class Payment(Base):
    __tablename__ = "payments"

    invoice_id: Mapped[int] = mapped_column(
        ForeignKey("invoices.id", ondelete="CASCADE"), index=True
    )

    provider: Mapped[str] = mapped_column(String(30), default="mock")
    external_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="created")

    idempotency_key: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    raw_payload: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=sa.text("now()"), nullable=False
    )

    invoice = relationship("Invoice", back_populates="payments", lazy="joined")

    __table_args__ = (
        UniqueConstraint("idempotency_key", name="payments_idem_key_unique"),
    )
