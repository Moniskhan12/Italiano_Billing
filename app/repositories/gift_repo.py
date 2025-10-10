from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.models.gift_card import GiftCard


def get_by_code(db: Session, code: str) -> GiftCard | None:
    return db.query(GiftCard).filter(GiftCard.code == code).one_or_none()


def redeem_code(db: Session, code: str, user_id: int) -> None:
    gift = db.query(GiftCard).filter(GiftCard.code == code).one_or_none()
    if not gift:
        return
    gift.is_redeemed = True
    gift.redeemed_by = user_id
    gift.redeemed_at = datetime.now(timezone.utc)
