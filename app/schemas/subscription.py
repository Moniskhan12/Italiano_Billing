from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel


class SubscriptionStatus(BaseModel):
    status: str
    plan_code: str | None = None
    current_period_start: datetime | None = None
    current_period_end: datetime | None = None
    cancel_at_period_end: bool = False


class CancelIn(BaseModel):
    at_period_end: bool = True
