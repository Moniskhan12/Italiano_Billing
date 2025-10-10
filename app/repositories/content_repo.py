from __future__ import annotations

from sqlalchemy.orm import Session

from app.models.content_module import ContentModule


def list_all(db: Session) -> list[ContentModule]:
    return db.query(ContentModule).order_by(ContentModule.code.asc()).all()
