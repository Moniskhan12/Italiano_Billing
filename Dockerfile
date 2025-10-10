FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_NO_CACHE_DIR=1 \
    PYTHONPATH=/app

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential curl ca-certificates libpq-dev && \
    rm -rf /var/lib/apt/lists/*


RUN python -m pip install --upgrade pip wheel && \
    pip install \
      fastapi uvicorn pydantic sqlalchemy alembic psycopg[binary] \
      structlog apscheduler prometheus-client python-dotenv \
      pytest pytest-cov ruff mypy httpx

COPY . .

EXPOSE 8000

CMD ["/bin/sh","-c","alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port 8000"]
