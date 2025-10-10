from __future__ import annotations

from datetime import datetime, timedelta, timezone

from sqlalchemy import and_, func, select
from sqlalchemy.orm import Session, joinedload

from app.models.invoice import Invoice
from app.models.plan import Plan
from app.models.subscription import Subscription
from app.repositories.invoice_repo import create_invoice
from app.utils.periods import add_iso_period


def generate_renewal_invoices(db: Session, days_before: int = 3) -> int:
    """
    Находит активные подписки, у которых скоро заканчивается период,
    и создаёт по одному инвойсу на следующий период, если такого ещё нет.
    Возвращает количество созданных инвойсов.
    """
    now = datetime.now(timezone.utc)
    window_end = now + timedelta(days=days_before)

    # Активные, не отменённые на конец периода, с указанной датой окончания
    stmt = (
        select(Subscription)
        .options(joinedload(Subscription.plan))
        .where(
            Subscription.status == "active",
            Subscription.cancel_at_period_end.is_(False),
            Subscription.current_period_end.is_not(None),
            Subscription.current_period_end <= window_end,
        )
    )

    created = 0
    for sub in db.scalars(stmt):
        assert isinstance(sub.plan, Plan)
        next_start = sub.current_period_end
        if next_start is None:
            continue
        next_end = add_iso_period(next_start, sub.plan.period_iso)

        exists_stmt = (
            select(func.count())
            .select_from(Invoice)
            .where(
                and_(
                    Invoice.subscription_id == sub.id,
                    Invoice.period_start == next_start,
                    Invoice.period_end == next_end,
                )
            )
        )
        exists = db.scalar(exists_stmt)
        if exists:
            continue

        create_invoice(
            db,
            subscription_id=sub.id,
            amount_cents=sub.plan.price_cents,
            currency=sub.plan.currency,
            period_start=next_start,
            period_end=next_end,
        )
        created += 1

    return created
