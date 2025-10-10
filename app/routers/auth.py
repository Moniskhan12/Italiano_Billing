from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Header, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import get_session
from app.models.user import User
from app.schemas.auth import SignUpIn, TokenPair, UserOut
from app.security import (
    decode_token,
    hash_password,
    make_access_token,
    make_refresh_token,
    verify_password,
)

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/signup", response_model=UserOut, status_code=status.HTTP_201_CREATED)
def signup(payload: SignUpIn, db: Session = Depends(get_session)) -> UserOut:
    exists = db.scalar(select(User).where(User.email == payload.email))
    if exists:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email_taken")
    user = User(
        email=payload.email,
        password_hash=hash_password(payload.password),
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return UserOut(id=user.id, email=user.email, role=user.role, locale=user.locale)


@router.post("/login", response_model=TokenPair)
def login(payload: SignUpIn, db: Session = Depends(get_session)) -> TokenPair:
    user = db.scalar(select(User).where(User.email == payload.email))
    if not user or not verify_password(payload.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="bad_credentials"
        )
    return TokenPair(
        access_token=make_access_token(user.id),
        refresh_token=make_refresh_token(user.id),
    )


@router.post("/refresh", response_model=TokenPair)
def refresh(
    authorization: Annotated[str | None, Header(alias="Authorization")] = None,
) -> TokenPair:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="missing_token"
        )
    token = authorization.split(" ", 1)[1]
    payload = decode_token(token)
    if payload.get("type") != "refresh":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="wrong_token_type"
        )
    user_id = int(payload["sub"])
    return TokenPair(
        access_token=make_access_token(user_id),
        refresh_token=make_refresh_token(user_id),
    )


@router.get("/me", response_model=UserOut)
def me(
    authorization: Annotated[str | None, Header(alias="Authorization")] = None,
    db: Session = Depends(get_session),
) -> UserOut:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="missing_token"
        )
    token = authorization.split(" ", 1)[1]
    payload = decode_token(token)
    if payload.get("type") != "access":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="wrong_token_type"
        )
    user = db.get(User, int(payload["sub"]))
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="user_not_found"
        )
    return UserOut(id=user.id, email=user.email, role=user.role, locale=user.locale)
