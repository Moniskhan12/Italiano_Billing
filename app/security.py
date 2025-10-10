from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any, Dict, cast

import jwt
from fastapi import HTTPException, status
from passlib.context import CryptContext

from .settings import get_settings

pwd = CryptContext(schemes=["pbkdf2_sha256"], deprecated="auto")
settings = get_settings()


def hash_password(raw: str) -> str:
    return pwd.hash(raw)


def verify_password(raw: str, hashed: str) -> bool:
    return bool(pwd.verify(raw, hashed))



def _make_token(sub: str, ttl: timedelta, token_type: str) -> str:
    now = datetime.now(timezone.utc)
    payload: Dict[str, Any] = {
        "sub": sub,
        "type": token_type,
        "iat": int(now.timestamp()),
        "exp": int((now + ttl).timestamp()),
    }
    token: str = jwt.encode(
        payload,
        settings.jwt_secret.get_secret_value(),
        algorithm=settings.jwt_algorithm,
    )
    return token


def make_access_token(user_id: int) -> str:
    return _make_token(
        str(user_id), timedelta(minutes=settings.access_ttl_minutes), "access"
    )


def make_refresh_token(user_id: int) -> str:
    return _make_token(
        str(user_id), timedelta(days=settings.refresh_ttl_days), "refresh"
    )


def decode_token(token: str) -> Dict[str, Any]:
    try:
        payload = jwt.decode(
            token,
            settings.jwt_secret.get_secret_value(),
            algorithms=[settings.jwt_algorithm],
            options={"require": ["exp", "sub", "type"]},
        )
        return cast(Dict[str, Any], payload)
    except jwt.ExpiredSignatureError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="token_expired"
        ) from e
    except jwt.InvalidTokenError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="invalid_token"
        ) from e
