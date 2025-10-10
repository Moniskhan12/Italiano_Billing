from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app.models.promocode import Promocode


def get_active_by_code(db: Session, code: str) -> Optional[Promocode]:
    now = datetime.now(timezone.utc)
    stmt = select(Promocode).where(
        Promocode.code == code,
        Promocode.is_active.is_(True),
        (Promocode.valid_from.is_(None) | (Promocode.valid_from <= now)),
        (Promocode.valid_from.is_(None) | (Promocode.valid_to >= now)),
    )
    return db.scalar(stmt)


def increment_redeemed(db: Session, code: str) -> None:
    db.execute(
        update(Promocode)
        .where(Promocode.code == code)
        .values(redeemed_count=(Promocode.redeemed_count + 1))
    )
    db.commit()
