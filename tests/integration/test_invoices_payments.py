from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.db import SessionLocal
from app.models.plan import Plan
from app.models.subscription import Subscription
from app.models.user import User
from app.repositories.invoice_repo import create_invoice
from app.repositories.payment_repo import create_payment
from app.security import hash_password


def _seed_user_plan_and_subscription(db: Session) -> tuple[User, Plan, Subscription]:
    # юзер и план
    u = User(
        email=f"u+{uuid.uuid4().hex[:6]}@ex.com",
        password_hash=hash_password("secret123"),
    )
    p = Plan(
        code=f"P30D-{uuid.uuid4().hex[:4]}",
        name="30 days",
        period_iso="P30D",
        price_cents=9900,
        currency="EUR",
        seats=1,
    )
    db.add_all([u, p])
    db.commit()
    db.refresh(u)
    db.refresh(p)

    sub = Subscription(
        owner_user_id=u.id,
        plan_id=p.id,
        status="inactive",
        current_period_start=None,
        current_period_end=None,
        cancel_at_period_end=False,
        seats_used=1,
    )
    db.add(sub)
    db.commit()
    db.refresh(sub)
    return u, p, sub


def test_create_invoice_and_payment_with_unique_idempotency() -> None:
    # Проверяем, что второй платеж с тем же idempotency_key бьется об UNIQUE
    with SessionLocal() as db:
        _, _, sub = _seed_user_plan_and_subscription(db)

        now = datetime.now(timezone.utc)
        inv = create_invoice(
            db,
            subscription_id=sub.id,
            amount_cents=9900,
            currency="EUR",
            period_start=now,
            period_end=now + timedelta(days=30),
        )
        db.flush()
        assert inv.id is not None
        assert inv.status in {"pending", "created", "open"}

        idem = f"idem-{uuid.uuid4().hex[:16]}"

        pm = create_payment(
            db,
            invoice_id=inv.id,
            idempotency_key=idem,
            status="created",
        )
        db.flush()
        assert pm.id is not None

        with pytest.raises(IntegrityError):
            create_payment(
                db,
                invoice_id=inv.id,
                idempotency_key=idem,
                status="created",
            )
            db.flush()


def test_invoice_amount_cannot_be_negative() -> None:
    with SessionLocal() as db:
        _, _, sub = _seed_user_plan_and_subscription(db)
        now = datetime.now(timezone.utc)

        with pytest.raises(IntegrityError):
            create_invoice(
                db,
                subscription_id=sub.id,
                amount_cents=-1,
                currency="EUR",
                period_start=now,
                period_end=now + timedelta(days=30),
            )
            db.flush()
