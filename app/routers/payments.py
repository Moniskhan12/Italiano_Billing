from __future__ import annotations

import hmac
import json
from datetime import datetime, timezone
from hashlib import sha256
from typing import Annotated

from fastapi import APIRouter, Depends, Header, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.db import get_session
from app.models.invoice import Invoice
from app.models.payment import Payment
from app.models.subscription import Subscription
from app.models.webhook_event import WebhookEvent
from app.settings import get_settings
from app.utils.metrics import record_payment_failed, record_payment_succeeded

router = APIRouter(tags=["payments"])


def _verify_signature(secret: str, body: bytes, header_value: str | None) -> None:
    if not header_value or not header_value.startswith("sha256="):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="signature_missing"
        )
    expected = "sha256=" + hmac.new(secret.encode("utf-8"), body, sha256).hexdigest()
    if not hmac.compare_digest(expected, header_value):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="signature_invalid"
        )


@router.post("/payments/webhook")
async def payments_webhook(
    request: Request,
    db: Session = Depends(get_session),
    x_signature: Annotated[str | None, Header(alias="X-Signature")] = None,
) -> dict[str, bool]:
    body = await request.body()
    settings = get_settings()
    _verify_signature(
        settings.payments_webhook_secret.get_secret_value(), body, x_signature
    )

    try:
        payload = json.loads(body.decode("utf-8"))
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="invalid_json"
        )

    # ожидаем { "payment_id": int, "status": "SUCCEEDED"|"FAILED", "provider": "mock" }
    if (
        not isinstance(payload, dict)
        or "payment_id" not in payload
        or "status" not in payload
    ):
        raise HTTPException(status_code=400, detail="invalid_payload")

    event = WebhookEvent(
        event_type=payload["status"],
        signature=x_signature or "",
        raw_json=payload,  # либо json.dumps(payload)
        attempts=1,
    )
    db.add(event)
    db.commit()  # фиксируем факт приёма

    pm = db.get(Payment, int(payload["payment_id"]))
    if not pm:
        # платёж не наш — игнор, но 200 (как делают провайдеры)
        return {"ok": True, "ignored": True}

    # идемпотентная обработка: повтор SUCCEEDED не должен ничего ломать
    if payload["status"] == "SUCCEEDED":
        if pm.status != "succeeded":
            pm.status = "succeeded"
            inv = db.get(Invoice, pm.invoice_id)
            if inv and inv.status != "paid":
                inv.status = "paid"
                # активируем подписку по периоду инвойса
                sub = db.get(Subscription, inv.subscription_id)
                if sub:
                    sub.status = "active"
                    sub.current_period_start = inv.period_start
                    sub.current_period_end = inv.period_end
            record_payment_succeeded()
        # если уже succeeded — просто ничего не меняем
    elif payload["status"] == "FAILED":
        if pm.status not in ("succeeded", "failed"):
            pm.status = "failed"
            inv = db.get(Invoice, pm.invoice_id)
            if inv and inv.status != "paid":
                inv.status = "failed"
            record_payment_failed()
    else:
        raise HTTPException(status_code=400, detail="unsupported_status")

    event.processed_at = datetime.now(timezone.utc)
    db.commit()
    return {"ok": True}
