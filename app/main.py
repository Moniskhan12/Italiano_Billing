from __future__ import annotations

from contextlib import asynccontextmanager
from time import perf_counter
from typing import AsyncIterator, Awaitable, Callable, Dict

from fastapi import Depends, FastAPI, Request, Response
from prometheus_client import CONTENT_TYPE_LATEST, generate_latest
from sqlalchemy.orm import Session

from app.db import get_session
from app.models.subscription import Subscription
from app.utils.metrics import measure_http, refresh_active_subscriptions
from app.workers.scheduler import start_scheduler

from .logging import configurate_logging, get_logger
from .routers.auth import router as auth_router
from .routers.content import router as content_router
from .routers.payments import router as payments_router
from .routers.subscriptions import router as subs_router
from .settings import get_settings


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Старт/остановка приложения. Инициализация логов."""
    configurate_logging()
    log = get_logger("startup")
    settings = get_settings()
    log.info("app_starting", app_name=settings.app_name, env=settings.env)
    try:
        # Старт фонового планировщика.
        start_scheduler()
        yield
    finally:
        get_logger("shutdown").info("app_stopping")


app = FastAPI(title="Italiano Billing", version="0.0.1", lifespan=lifespan)
log = get_logger("api")
app.include_router(auth_router)
app.include_router(subs_router)
app.include_router(payments_router)
app.include_router(content_router)


@app.middleware("http")
async def logging_middleware(
    request: Request,
    call_next: Callable[[Request], Awaitable[Response]],
) -> Response:  # noqa: ANN001
    start = perf_counter()
    response = await call_next(request)
    elapsed_ms = round((perf_counter() - start) * 1000, 2)
    log.info(
        "request",
        method=request.method,
        path=request.url.path,
        status_code=response.status_code,
        elapsed_ms=elapsed_ms,
    )
    return response


@app.middleware("http")
async def metrics_middleware(
    request: Request,
    call_next: Callable[[Request], Awaitable[Response]],
) -> Response:  # noqa ANN001
    start = perf_counter()
    response = await call_next(request)
    elapsed = perf_counter() - start
    try:
        measure_http(request.method, request.url.path, response.status_code, elapsed)
    finally:
        return response


@app.get("/metrics")
def metrics(db: Session = Depends(get_session)) -> Response:
    cnt = db.query(Subscription).filter(Subscription.status == "active").count()
    refresh_active_subscriptions(cnt)
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)


@app.get("/healthz", tags=["tech"])
async def healthz() -> Dict[str, str]:
    return {"status": "ok"}


@app.get("/readyz", tags=["tech"])
async def readyz() -> Dict[str, str]:
    return {"ready": "true"}
