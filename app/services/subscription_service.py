from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.models.subscription import Subscription
from app.repositories.subscription_repo import get_latest_by_owner
from app.schemas.subscription import SubscriptionStatus


def get_status_for_user(db: Session, user_id: int) -> SubscriptionStatus:
    sub: Subscription | None = get_latest_by_owner(db, user_id)
    if not sub:
        return SubscriptionStatus(status="inactive")
    return SubscriptionStatus(
        status=sub.status,
        plan_code=sub.plan.code if sub.plan else None,
        current_period_start=sub.current_period_start,
        current_period_end=sub.current_period_end,
        cancel_at_period_end=sub.cancel_at_period_end or False,
    )


def _ensure_owner(db: Session, sub_id: int, user_id: int) -> Subscription:
    sub = db.get(Subscription, sub_id)
    if not sub or sub.owner_user_id != user_id:
        raise PermissionError("not_found")
    return sub


def cancel_subscription(
    db: Session, user_id: int, sub_id: int, at_period_end: bool
) -> SubscriptionStatus:
    sub = _ensure_owner(db, sub_id, user_id)
    now = datetime.now(timezone.utc)
    if sub.status in ("canceled",):
        # уже отменена — идемпотентно возвращаем статус
        return get_status_for_user(db, user_id)
    if at_period_end:
        sub.cancel_at_period_end = True
        db.commit()
        return get_status_for_user(db, user_id)
    # немедленная отмена
    sub.status = "canceled"
    sub.current_period_end = now
    db.commit()
    return get_status_for_user(db, user_id)


def freeze_subscription(db: Session, user_id: int, sub_id: int) -> SubscriptionStatus:
    sub = _ensure_owner(db, sub_id, user_id)
    if sub.status == "frozen":
        return get_status_for_user(db, user_id)
    if sub.status != "active":
        raise ValueError("freeze_only_from_active")
    sub.status = "frozen"
    db.commit()
    return get_status_for_user(db, user_id)


def unfreeze_subscription(db: Session, user_id: int, sub_id: int) -> SubscriptionStatus:
    sub = _ensure_owner(db, sub_id, user_id)
    if sub.status != "frozen":
        return get_status_for_user(db, user_id)
    now = datetime.now(timezone.utc)
    if sub.current_period_end and now < sub.current_period_end:
        sub.status = "active"
    else:
        sub.status = "inactive"
    db.commit()
    return get_status_for_user(db, user_id)
