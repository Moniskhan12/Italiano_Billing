from __future__ import annotations

from typing import Optional, Sequence

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.plan import Plan


def list_active_plans(db: Session) -> Sequence[Plan]:
    stmt = select(Plan).where(Plan.is_active.is_(True)).order_by(Plan.price_cents.asc())
    return list(db.scalars(stmt))


def get_active_by_code(db: Session, code: str) -> Optional[Plan]:
    stmt = select(Plan).where(Plan.code == code, Plan.is_active.is_(True))
    return db.scalar(stmt)
