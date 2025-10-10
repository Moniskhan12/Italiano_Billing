from __future__ import annotations

from pydantic import BaseModel


class PlanOut(BaseModel):
    id: int
    code: str
    name: str
    period_iso: str
    price_cents: int
    currency: str
    seats: int
