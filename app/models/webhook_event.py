from __future__ import annotations

from datetime import datetime
from typing import Any

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.types import DateTime, Integer, String

from .base import Base


class WebhookEvent(Base):
    __tablename__ = "webhook_events"

    event_type: Mapped[str] = mapped_column(String(30))
    signature: Mapped[str] = mapped_column(String(128))
    raw_json: Mapped[dict[str, Any]] = mapped_column(JSONB)
    attempts: Mapped[int] = mapped_column(Integer, default=0)
    processed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    __table_args__ = (sa.Index("webhook_events_signature_idx", "signature"),)
