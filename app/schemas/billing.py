from __future__ import annotations

from datetime import datetime

from pydantic import AliasChoices, BaseModel, Field


class StartSubscriptionIn(BaseModel):
    plan_code: str = Field(
        examples=["P30D"], validation_alias=AliasChoices("plan_code", "code")
    )
    promo_code: str | None = Field(default=None, examples=["WELCOME10"])
    gift_code: str | None = Field(default=None, examples=["GIFT100"])


class StartSubscriptionOut(BaseModel):
    subscription_id: int
    invoice_id: int
    payment_id: int
    promo_code: str | None = None
    gift_code: str | None = None
    discount_cents: int = 0
    amount_cents: int
    currency: str
    period_start: datetime
    period_end: datetime
    payment_status: str
    provider: str = "mock"
