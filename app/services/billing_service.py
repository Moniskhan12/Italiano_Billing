from __future__ import annotations

from datetime import datetime, timezone

from fastapi import HTTPException
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.payment import Payment
from app.models.subscription import Subscription
from app.repositories.gift_repo import get_by_code as get_gift_by_code
from app.repositories.invoice_repo import create_invoice
from app.repositories.payment_repo import create_payment, get_by_idempotency_key
from app.repositories.plan_repo import get_active_by_code as get_plan_by_code
from app.repositories.promo_repo import get_active_by_code as get_promo_by_code
from app.repositories.promo_repo import increment_redeemed
from app.schemas.billing import StartSubscriptionOut
from app.utils.metrics import record_payment_succeeded
from app.utils.periods import add_iso_period


def start_subscription(  # noqa: C901
    db: Session,
    user_id: int,
    plan_code: str,
    idempotency_key: str,
    promo_code: str | None = None,
    gift_code: str | None = None,
) -> StartSubscriptionOut:
    # Идемпотентность: если платеж уже есть — вернём его и связанный инвойс
    existing = get_by_idempotency_key(db, idempotency_key)
    if existing:
        inv = existing.invoice
        return StartSubscriptionOut(
            subscription_id=inv.subscription_id,
            invoice_id=inv.id,
            payment_id=existing.id,
            amount_cents=inv.amount_cents,
            currency=inv.currency,
            period_start=inv.period_start,
            period_end=inv.period_end,
            payment_status=existing.status,
            provider=existing.provider,
            promo_code=inv.promocode_code,
            gift_code=getattr(inv, "gift_code", None),
            discount_cents=inv.discount_cents or 0,
        )

    # Тариф
    plan = get_plan_by_code(db, plan_code)
    if not plan:
        raise ValueError("plan_not_found_or_inactive")

    # Подписка пользователя (для MVP — одна на пользователя; создадим, если нет)
    sub = (
        db.query(Subscription)
        .filter(Subscription.owner_user_id == user_id)
        .order_by(Subscription.id.desc())
        .first()
    )
    if not sub:
        sub = Subscription(
            owner_user_id=user_id, plan_id=plan.id, status="inactive", seats_used=1
        )
        db.add(sub)
        db.commit()
        db.refresh(sub)
    else:
        sub.plan_id = plan.id
        db.commit()

    # Инвойс на текущий период.
    now = datetime.now(timezone.utc)
    period_start = now
    period_end = add_iso_period(period_start, plan.period_iso)

    # Скидка.
    discount_cents = 0
    applied_code: str | None = None
    applied_gift: str | None = None
    if promo_code:
        pc = get_promo_by_code(db, promo_code)
        if not pc:
            raise HTTPException(status_code=404, detail="promocode_not_found")
        if pc.max_redemptions is not None and pc.redeemed_count >= pc.max_redemptions:
            raise HTTPException(status_code=409, detail="promocode_exhausted")
        if pc.applicable_plans:
            allowed = {c.strip() for c in pc.applicable_plans.split(",") if c.strip()}
            if plan.code not in allowed:
                raise HTTPException(status_code=409, detail="promocode_not_applicable")
            if pc.discount_type == "percent":
                discount_cents = (plan.price_cents * pc.amount) // 100
            else:
                if pc.currency != plan.currency:
                    raise HTTPException(
                        status_code=409, detail="promocode_currency_mismatch"
                    )
                discount_cents = min(pc.amount, plan.price_cents)
            applied_code = pc.code
        if gift_code:
            if applied_code:
                raise HTTPException(status_code=422, detail="cannot_combine_codes")
            gc = get_gift_by_code(db, gift_code)
            if not gc:
                raise HTTPException(status_code=404, detail="giftcard_not_found")
            if gc.is_redeemed:
                raise HTTPException(status_code=409, detail="giftcard_already_redeemed")
            if gc.currency != plan.currency:
                raise HTTPException(
                    status_code=409, detail="giftcard_currency_mismatch"
                )
            if gc.amount_cents < plan.price_cents:
                raise HTTPException(status_code=409, detail="giftcard_insufficient")
            discount_cents = plan.price_cents
            applied_gift = gc.code

            gc.is_redeemed = True
            gc.redeemed_by = user_id
            gc.redeemed_at = now

    inv = create_invoice(
        db,
        subscription_id=sub.id,
        amount_cents=plan.price_cents - discount_cents,
        currency=plan.currency,
        period_start=period_start,
        period_end=period_end,
        discount_cents=discount_cents,
        promocode_code=applied_code,
        giftcard_code=applied_gift,
    )
    if applied_code:
        increment_redeemed(db, applied_code)

    # Платёж с идемпотентным ключом_____________________________________________________________________________________
    try:
        pm: Payment = create_payment(
            db,
            invoice_id=inv.id,
            idempotency_key=idempotency_key,
            provider="gift" if applied_gift else "mock",
            status="succeeded" if applied_gift else "created",
        )
    except IntegrityError:
        db.rollback()
        pm_opt = get_by_idempotency_key(db, idempotency_key)
        if pm_opt is None:
            raise RuntimeError("idempotency_race_lost_but_record_missing")
        pm = pm_opt

    else:
        if applied_gift:
            inv.status = "paid"
            sub.status = "active"
            sub.current_period_start = period_start
            sub.current_period_end = period_end
            record_payment_succeeded()
            db.commit()

    return StartSubscriptionOut(
        subscription_id=sub.id,
        invoice_id=inv.id,
        payment_id=pm.id,
        promo_code=applied_code,
        gift_code=applied_gift,
        discount_cents=discount_cents,
        amount_cents=inv.amount_cents,
        currency=inv.currency,
        period_start=inv.period_start,
        period_end=inv.period_end,
        payment_status=pm.status,
        provider=pm.provider,
    )
