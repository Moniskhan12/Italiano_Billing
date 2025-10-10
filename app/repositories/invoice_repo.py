from __future__ import annotations

from datetime import datetime

from sqlalchemy.orm import Session

from app.models.invoice import Invoice


def create_invoice(
    db: Session,
    subscription_id: int,
    amount_cents: int,
    currency: str,
    period_start: datetime,
    period_end: datetime,
    *,
    discount_cents: int = 0,
    promocode_code: str | None = None,
    giftcard_code: str | None = None,
) -> Invoice:
    inv = Invoice(
        subscription_id=subscription_id,
        amount_cents=amount_cents,
        currency=currency,
        period_start=period_start,
        period_end=period_end,
        status="pending",
        attempts=0,
        discount_cents=discount_cents,
        promocode_code=promocode_code,
        giftcard_code=giftcard_code,
    )
    db.add(inv)
    db.commit()
    db.refresh(inv)
    return inv
