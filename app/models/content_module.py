from __future__ import annotations

from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.types import String

from app.models.base import Base


class ContentModule(Base):
    __tablename__ = "content_modules"

    code: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    min_tier: Mapped[str] = mapped_column(String(20), nullable=False, default="basic")
