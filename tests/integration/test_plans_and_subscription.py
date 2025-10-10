from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.db import SessionLocal
from app.main import app
from app.models.plan import Plan
from app.models.subscription import Subscription
from app.security import decode_token

client = TestClient(app)


def _seed_plan(db: Session) -> Plan:
    p = Plan(
        code=f"P30D-{uuid.uuid4().hex[:4]}",
        name="30 days",
        period_iso="P30D",
        price_cents=9900,
        currency="EUR",
        seats=1,
        is_active=True,
    )
    db.add(p)
    db.commit()
    db.refresh(p)
    return p


def test_get_plans_and_my_subscription_status() -> None:
    # 1) есть хотя бы один план
    with SessionLocal() as db:
        plan = _seed_plan(db)

    # 2) планы видны
    r = client.get("/plans")
    assert r.status_code == 200
    items = r.json()
    assert any(it["code"] == plan.code for it in items)

    # 3) заводим юзера и получаем access
    email = f"u+{uuid.uuid4().hex[:6]}@example.com"
    password = "secret123"
    client.post("/auth/signup", json={"email": email, "password": password})
    tokens = client.post(
        "/auth/login", json={"email": email, "password": password}
    ).json()
    access = tokens["access_token"]

    # 4) без подписки статус inactive
    r = client.get("/me/subscription", headers={"Authorization": f"Bearer {access}"})
    assert r.status_code == 200
    assert r.json()["status"] == "inactive"

    # 5) создаём активную подписку руками
    now = datetime.now(timezone.utc)
    user_id = int(decode_token(access)["sub"])
    with SessionLocal() as db:
        sub = Subscription(
            owner_user_id=user_id,
            plan_id=plan.id,
            status="active",
            current_period_start=now,
            current_period_end=now + timedelta(days=30),
            cancel_at_period_end=False,
            seats_used=1,
        )
        db.add(sub)
        db.commit()

    # 6) теперь статус active и виден код плана
    r = client.get("/me/subscription", headers={"Authorization": f"Bearer {access}"})
    assert r.status_code == 200
    data = r.json()
    assert data["status"] == "active"
    assert data["plan_code"] == plan.code
