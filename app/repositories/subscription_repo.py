from __future__ import annotations

from typing import Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.subscription import Subscription


def get_latest_by_owner(db: Session, user_id: int) -> Optional[Subscription]:
    stmt = (
        select(Subscription)
        .where(Subscription.owner_user_id == user_id)
        .order_by(Subscription.id.desc())
    )
    return db.scalar(stmt)
