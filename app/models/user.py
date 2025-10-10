from __future__ import annotations

import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.types import DateTime, String, Text

from .base import Base


class User(Base):
    __tablename__ = "users"

    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(Text)
    role: Mapped[str] = mapped_column(
        String(30), default="student"
    )  # student|admin|family_owner
    locale: Mapped[str] = mapped_column(String(10), default="ru")
    created_at: Mapped["sa.sql.sqltypes.DateTime"] = mapped_column(
        DateTime(timezone=True), server_default=sa.text("now()"), nullable=False
    )
