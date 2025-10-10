from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone

from sqlalchemy.orm import Session

from app.db import SessionLocal
from app.models.invoice import Invoice
from app.models.plan import Plan
from app.models.subscription import Subscription
from app.models.user import User
from app.security import hash_password
from app.services.dunning_service import generate_renewal_invoices


def _seed_active_sub_ending_soon(db: Session, days_left: int = 2) -> Subscription:
    u = User(
        email=f"renew+{uuid.uuid4().hex[:6]}@ex.com", password_hash=hash_password("x")
    )
    p = Plan(
        code=f"P30D-{uuid.uuid4().hex[:4]}",
        name="30d",
        period_iso="P30D",
        price_cents=1000,
        currency="EUR",
        seats=1,
    )
    db.add_all([u, p])
    db.commit()
    db.refresh(u)
    db.refresh(p)

    now = datetime.now(timezone.utc)
    sub = Subscription(
        owner_user_id=u.id,
        plan_id=p.id,
        status="active",
        current_period_start=now - timedelta(days=28),
        current_period_end=now + timedelta(days=days_left),
        cancel_at_period_end=False,
        seats_used=1,
    )
    db.add(sub)
    db.commit()
    db.refresh(sub)
    return sub


def test_generate_renewal_invoices_idempotent() -> None:
    with SessionLocal() as db:
        sub = _seed_active_sub_ending_soon(db, days_left=2)

        # первый запуск — создаст один инвойс
        created1 = generate_renewal_invoices(db, days_before=3)
        assert created1 == 1

        # второй запуск — не создаст дубль
        created2 = generate_renewal_invoices(db, days_before=3)
        assert created2 == 0

        # в БД ровно один инвойс на следующий период
        next_start = sub.current_period_end
        next_end = next_start + timedelta(days=30)
        q = db.query(Invoice).filter(
            Invoice.subscription_id == sub.id,
            Invoice.period_start == next_start,
            Invoice.period_end == next_end,
        )
        assert q.count() == 1
