from __future__ import annotations

import hmac
import json
import uuid
from datetime import datetime, timezone
from hashlib import sha256

from fastapi.testclient import TestClient
from sqlalchemy import select

from app.db import SessionLocal
from app.main import app
from app.models.plan import Plan
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
    email = f"cnl+{uuid.uuid4().hex[:6]}@ex.com"
    password = "secret123"
    client.post("/auth/signup", json={"email": email, "password": password})
    return client.post(
        "/auth/login", json={"email": email, "password": password}
    ).json()["access_token"]


def _start_active_subscription(access: str) -> int:
    idem = f"idem-{uuid.uuid4().hex[:8]}"
    r = client.post(
        "/subscriptions/start",
        json={"plan_code": "P30D"},
        headers={"Authorization": f"Bearer {access}", "Idempotency-Key": idem},
    )
    assert r.status_code in (200, 201), r.text
    sub_id = r.json()["subscription_id"]
    pay_id = r.json()["payment_id"]
    # подтвердим оплату
    body = {"payment_id": pay_id, "status": "SUCCEEDED", "provider": "mock"}
    raw = json.dumps(body, separators=(",", ":")).encode()
    sig = (
        "sha256="
        + hmac.new(
            get_settings().payments_webhook_secret.get_secret_value().encode(),
            raw,
            sha256,
        ).hexdigest()
    )
    rr = client.post("/payments/webhook", content=raw, headers={"X-Signature": sig})
    assert rr.status_code == 200
    return sub_id


def test_cancel_at_period_end_keeps_active_and_sets_flag() -> None:
    _seed_plan()
    access = _auth()
    sub_id = _start_active_subscription(access)

    r = client.post(
        f"/subscriptions/{sub_id}/cancel",
        json={"at_period_end": True},
        headers={"Authorization": f"Bearer {access}"},
    )
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["status"] == "active"
    assert data["cancel_at_period_end"] is True


def test_cancel_immediately_sets_canceled_and_cuts_period() -> None:
    _seed_plan()
    access = _auth()
    sub_id = _start_active_subscription(access)

    r = client.post(
        f"/subscriptions/{sub_id}/cancel",
        json={"at_period_end": False},
        headers={"Authorization": f"Bearer {access}"},
    )
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["status"] == "canceled"
    # период обрезан до «сейчас» с небольшим люфтом
    now = datetime.now(timezone.utc)
    end = (
        datetime.fromisoformat(data["current_period_end"].replace("Z", "+00:00"))
        if "Z" in data["current_period_end"]
        else datetime.fromisoformat(data["current_period_end"])
    )
    assert abs((now - end).total_seconds()) < 5


def test_freeze_and_unfreeze_cycle() -> None:
    _seed_plan()
    access = _auth()
    sub_id = _start_active_subscription(access)

    r1 = client.post(
        f"/subscriptions/{sub_id}/freeze", headers={"Authorization": f"Bearer {access}"}
    )
    assert r1.status_code == 200, r1.text
    assert r1.json()["status"] == "frozen"

    r2 = client.post(
        f"/subscriptions/{sub_id}/unfreeze",
        headers={"Authorization": f"Bearer {access}"},
    )
    assert r2.status_code == 200, r2.text
    assert r2.json()["status"] in ("active", "inactive")  # в зависимости от дат
