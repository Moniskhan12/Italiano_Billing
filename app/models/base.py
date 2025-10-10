from __future__ import annotations

import sqlalchemy as sa
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    """Базовый класс для всех моделей."""

    id: Mapped[int] = mapped_column(
        sa.BigInteger, sa.Identity(always=False), primary_key=True
    )
