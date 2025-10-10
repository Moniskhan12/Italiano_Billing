from __future__ import annotations

import uuid

from fastapi.testclient import TestClient
from sqlalchemy import func, select

from app.db import SessionLocal
from app.main import app
from app.models.payment import Payment
from app.models.plan import Plan

client = TestClient(app)


def _auth() -> str:
    email = f"idem+{uuid.uuid4().hex[:6]}@ex.com"
    password = "secret123"
    client.post("/auth/signup", json={"email": email, "password": password})
    tok = client.post("/auth/login", json={"email": email, "password": password}).json()
    return tok["access_token"]


def _seed_plan() -> None:
    with SessionLocal() as db:
        p = db.scalar(select(Plan).where(Plan.code == "P30D"))
        if not p:
            db.add(
                Plan(
                    code="P30D",
                    name="30 days",
                    period_iso="P30D",
                    price_cents=9900,
                    currency="EUR",
                    seats=1,
                    is_active=True,
                )
            )
            db.commit()
        elif not p.is_active:
            p.is_active = True
            db.commit()


def test_idempotent_start_creates_single_payment_and_invoice() -> None:
    _seed_plan()
    access = _auth()
    idem = f"test-{uuid.uuid4().hex[:10]}"

    # первый вызов
    r1 = client.post(
        "/subscriptions/start",
        json={"plan_code": "P30D"},
        headers={"Authorization": f"Bearer {access}", "Idempotency-Key": idem},
    )
    assert r1.status_code == 201, r1.text
    body1 = r1.json()
    pay_id_1 = body1["payment_id"]
    inv_id_1 = body1["invoice_id"]

    # повторный вызов с тем же ключом
    r2 = client.post(
        "/subscriptions/start",
        json={"plan_code": "P30D"},
        headers={"Authorization": f"Bearer {access}", "Idempotency-Key": idem},
    )
    assert r2.status_code in (200, 201)
    body2 = r2.json()

    # тот же платеж и инвойс
    assert body2["payment_id"] == pay_id_1
    assert body2["invoice_id"] == inv_id_1

    # в базе ровно один платеж с этим ключом
    with SessionLocal() as db:
        cnt = db.scalar(
            select(func.count())
            .select_from(Payment)
            .where(Payment.idempotency_key == idem)
        )
        assert cnt == 1
