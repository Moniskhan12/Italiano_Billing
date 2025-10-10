from __future__ import annotations

from typing import Any, Optional, Sequence

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.payment import Payment
from app.models.plan import Plan


def create_payment(
    db: Session,
    invoice_id: int,
    idempotency_key: str,
    provider: str = "mock",
    status: str = "created",
    raw_payload: dict[str, Any] | None = None,
) -> Payment:
    pm = Payment(
        invoice_id=invoice_id,
        provider=provider,
        status=status,
        idempotency_key=idempotency_key,
        raw_payload=raw_payload,
    )
    db.add(pm)
    db.commit()
    db.refresh(pm)
    return pm


def get_by_idempotency_key(db: Session, idem: str) -> Optional[Payment]:
    return db.scalar(select(Payment).where(Payment.idempotency_key == idem))


def list_active_plans(db: Session) -> Sequence[Plan]:
    stmt = select(Plan).where(Plan.is_active.is_(True)).order_by(Plan.price_cents.asc())
    return list(db.scalars(stmt))


def get_active_by_code(db: Session, code: str) -> Optional[Plan]:
    stmt = select(Plan).where(Plan.code == code, Plan.is_active.is_(True))
    return db.scalar(stmt)
