from __future__ import annotations

from typing import Annotated, List

from fastapi import APIRouter, Depends, Header, HTTPException, status
from sqlalchemy.orm import Session

from app.db import get_session
from app.deps import get_current_user
from app.models import User
from app.repositories.plan_repo import list_active_plans
from app.schemas.billing import StartSubscriptionIn, StartSubscriptionOut
from app.schemas.plan import PlanOut
from app.schemas.subscription import CancelIn, SubscriptionStatus
from app.services.billing_service import start_subscription
from app.services.subscription_service import (
    cancel_subscription,
    freeze_subscription,
    get_status_for_user,
    unfreeze_subscription,
)

router = APIRouter(tags=["subscriptions"])


@router.get("/plans", response_model=List[PlanOut])
def get_plans(db: Session = Depends(get_session)) -> List[PlanOut]:
    plans = list_active_plans(db)
    return [
        PlanOut(
            id=p.id,
            code=p.code,
            name=p.name,
            period_iso=p.period_iso,
            price_cents=p.price_cents,
            currency=p.currency,
            seats=p.seats,
        )
        for p in plans
    ]


@router.get("/me/subscription", response_model=SubscriptionStatus)
def my_subscription_status(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_session),
) -> SubscriptionStatus:
    return get_status_for_user(db, user.id)


@router.post("/subscriptions/{sub_id}/cancel", response_model=SubscriptionStatus)
def cancel_endpoint(
    sub_id: int,
    payload: CancelIn,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_session),
) -> SubscriptionStatus:
    try:
        return cancel_subscription(
            db, user.id, sub_id=sub_id, at_period_end=payload.at_period_end
        )
    except PermissionError:
        raise HTTPException(status_code=404, detail="subscription_not_found")


@router.post("/subscriptions/{sub_id}/freeze", response_model=SubscriptionStatus)
def freeze_endpoint(
    sub_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_session),
) -> SubscriptionStatus:
    try:
        return freeze_subscription(db, user.id, sub_id=sub_id)
    except PermissionError:
        raise HTTPException(status_code=404, detail="subscription_not_found")
    except ValueError as e:
        if str(e) == "freeze_only_from_active":
            raise HTTPException(status_code=409, detail="freeze_only_from_active")
        raise


@router.post("/subscriptions/{sub_id}/unfreeze", response_model=SubscriptionStatus)
def unfreeze_endpoint(
    sub_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_session),
) -> SubscriptionStatus:
    try:
        return unfreeze_subscription(db, user.id, sub_id=sub_id)
    except PermissionError:
        raise HTTPException(status_code=404, detail="subscription_not_found")


@router.post(
    "/subscriptions/start",
    response_model=StartSubscriptionOut,
    status_code=status.HTTP_201_CREATED,
)
def start_subscription_endpoint(
    payload: StartSubscriptionIn,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_session)],
    idempotency_key: Annotated[str | None, Header(alias="Idempotency-Key")] = None,
) -> StartSubscriptionOut:
    if not idempotency_key:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="missing_idempotency_key.",
        )
    try:
        return start_subscription(
            db,
            user_id=user.id,
            plan_code=payload.plan_code,
            idempotency_key=idempotency_key,
            promo_code=payload.promo_code,
        )
    except Exception as e:
        if str(e) == "plan_not_found":
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="plan_not_found.",
            ) from e
        raise
