from __future__ import annotations

import hmac
import json
import uuid
from hashlib import sha256

from fastapi.testclient import TestClient
from sqlalchemy import select

from app.db import SessionLocal
from app.main import app
from app.models.invoice import Invoice
from app.models.payment import Payment
from app.models.plan import Plan
from app.models.subscription import Subscription
from app.settings import get_settings

client = TestClient(app)


def _seed_plan() -> None:
    with SessionLocal() as db:
        if not db.scalar(select(Plan).where(Plan.code == "P30D")):
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


def _auth() -> str:
    email = f"wb+{uuid.uuid4().hex[:6]}@ex.com"
    password = "secret123"
    client.post("/auth/signup", json={"email": email, "password": password})
    return client.post(
        "/auth/login", json={"email": email, "password": password}
    ).json()["access_token"]


def _sign(body: dict) -> str:
    raw = json.dumps(body, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    sec = get_settings().payments_webhook_secret.get_secret_value().encode("utf-8")
    return "sha256=" + hmac.new(sec, raw, sha256).hexdigest(), raw


def test_webhook_succeeded_is_idempotent() -> None:
    _seed_plan()
    access = _auth()
    idem = f"idem-{uuid.uuid4().hex[:8]}"

    # стартуем подписку -> получаем платёж/инвойс
    r = client.post(
        "/subscriptions/start",
        json={"plan_code": "P30D"},
        headers={"Authorization": f"Bearer {access}", "Idempotency-Key": idem},
    )
    assert r.status_code in (200, 201), r.text
    info = r.json()
    payment_id = info["payment_id"]

    # первый вебхук SUCCEEDED
    body = {"payment_id": payment_id, "status": "SUCCEEDED", "provider": "mock"}
    sig, raw = _sign(body)
    r1 = client.post("/payments/webhook", content=raw, headers={"X-Signature": sig})
    assert r1.status_code == 200, r1.text

    # повтор SUCCEEDED — не должен менять состояние и точно не падать
    r2 = client.post("/payments/webhook", content=raw, headers={"X-Signature": sig})
    assert r2.status_code == 200, r2.text

    with SessionLocal() as db:
        pm = db.get(Payment, payment_id)
        inv = db.get(Invoice, pm.invoice_id) if pm else None
        sub = db.get(Subscription, inv.subscription_id) if inv else None

        assert pm and pm.status == "succeeded"
        assert inv and inv.status == "paid"
        assert sub and sub.status == "active"
        assert sub.current_period_start == inv.period_start
        assert sub.current_period_end == inv.period_end


def test_webhook_bad_signature_rejected() -> None:
    payload = {"payment_id": 123456, "status": "SUCCEEDED", "provider": "mock"}
    raw = json.dumps(payload).encode("utf-8")
    r = client.post(
        "/payments/webhook", content=raw, headers={"X-Signature": "sha256=deadbeef"}
    )
    assert r.status_code == 401
