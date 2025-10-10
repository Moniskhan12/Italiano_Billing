from __future__ import annotations

from prometheus_client import Counter, Gauge, Histogram

# HTTP-метрики (с небольшой нормализацией путей, чтобы не плодить label'ы)
HTTP_REQUESTS = Counter(
    "http_requests_total", "Number of HTTP requests", ["method", "path", "status"]
)
HTTP_LATENCY = Histogram(
    "http_request_latency_seconds", "Request latency", ["method", "path"]
)

# Доменные метрики
PAYMENTS_SUCCEEDED = Counter("payments_succeeded_total", "Succeeded payments")
PAYMENTS_FAILED = Counter("payments_failed_total", "Failed payments")
ACTIVE_SUBSCRIPTIONS = Gauge("active_subscriptions", "Currently active subscriptions")


def normalize_path(path: str) -> str:
    # уменьшаем кардинальность меток
    if path.startswith("/subscriptions/") and path.count("/") >= 2:
        return "/subscriptions/{id}"
    return path


def measure_http(method: str, path: str, status: int, elapsed_s: float) -> None:
    npath = normalize_path(path)
    HTTP_LATENCY.labels(method=method, path=npath).observe(elapsed_s)
    HTTP_REQUESTS.labels(method=method, path=npath, status=str(status)).inc()


def record_payment_succeeded() -> None:
    PAYMENTS_SUCCEEDED.inc()


def record_payment_failed() -> None:
    PAYMENTS_FAILED.inc()


def refresh_active_subscriptions(count: int) -> None:
    ACTIVE_SUBSCRIPTIONS.set(count)
