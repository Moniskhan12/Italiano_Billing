from __future__ import annotations

import uuid

from fastapi.testclient import TestClient
from sqlalchemy import select

from app.db import SessionLocal
from app.main import app
from app.models.plan import Plan
from app.models.promocode import Promocode

client = TestClient(app)


def _seed_plan() -> None:
    # делаем план P30D детерминированным: либо обновляем, либо создаём
    with SessionLocal() as db:
        p = db.scalar(select(Plan).where(Plan.code == "P30D"))
        if p:
            p.name = "30 days"
            p.period_iso = "P30D"
            p.price_cents = 10_000  # фиксируем 10 000, чтобы расчёт был стабильный
            p.currency = "EUR"
            p.seats = 1
            p.is_active = True
        else:
            db.add(
                Plan(
                    code="P30D",
                    name="30 days",
                    period_iso="P30D",
                    price_cents=10_000,
                    currency="EUR",
                    seats=1,
                    is_active=True,
                )
            )
        db.commit()


def _auth() -> str:
    email = f"pc+{uuid.uuid4().hex[:6]}@ex.com"
    password = "secret123"
    client.post("/auth/signup", json={"email": email, "password": password})
    return client.post(
        "/auth/login", json={"email": email, "password": password}
    ).json()["access_token"]


def _create_promocode(code: str | None = None) -> str:
    code = code or f"WELCOME10-{uuid.uuid4().hex[:6]}"
    with SessionLocal() as db:
        db.add(
            Promocode(
                code=code,
                discount_type="percent",
                amount=10,  # 10%
                max_redemptions=1,  # можно применить один раз
                applicable_plans="P30D",
                is_active=True,
            )
        )
        db.commit()
    return code


def test_promocode_applies_and_blocks_second_use() -> None:
    _seed_plan()
    code = _create_promocode()  # используем реальный код

    # первый пользователь — успех
    a1 = _auth()
    idem1 = f"idem-{uuid.uuid4().hex[:8]}"
    r1 = client.post(
        "/subscriptions/start",
        json={"plan_code": "P30D", "promo_code": code},
        headers={"Authorization": f"Bearer {a1}", "Idempotency-Key": idem1},
    )
    assert r1.status_code in (200, 201), r1.text
    body = r1.json()

    # проверяем размер скидки от фактической цены (10% от 10_000 = 1000)
    with SessionLocal() as db:
        price = db.scalar(select(Plan.price_cents).where(Plan.code == "P30D"))
    expected_discount = price * 10 // 100

    assert body["promo_code"] == code
    assert body["discount_cents"] == expected_discount

    # второй пользователь — тот же код -> 409 (промокод исчерпан)
    a2 = _auth()
    idem2 = f"idem-{uuid.uuid4().hex[:8]}"
    r2 = client.post(
        "/subscriptions/start",
        json={"plan_code": "P30D", "promo_code": code},
        headers={"Authorization": f"Bearer {a2}", "Idempotency-Key": idem2},
    )
    assert r2.status_code == 409, r2.text
    assert r2.json()["detail"] in ("promocode_exhausted",)
