from __future__ import annotations

from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.db import get_session
from app.deps import get_current_user
from app.models.subscription import Subscription
from app.models.user import User
from app.repositories.content_repo import list_all
from app.schemas.content import ContentModuleOut

router = APIRouter(prefix="/content", tags=["content"])


@router.get("/modules", response_model=List[ContentModuleOut])
def get_modules(
    db: Session = Depends(get_session),
    user: User = Depends(get_current_user),
) -> list[ContentModuleOut]:
    sub = (
        db.query(Subscription)
        .filter(Subscription.owner_user_id == user.id)
        .order_by(Subscription.id.desc())
        .first()
    )
    if not sub or sub.status != "active":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="subscription_inactive"
        )
    items = list_all(db)
    return [
        ContentModuleOut(code=i.code, title=i.title, min_tier=i.min_tier) for i in items
    ]
