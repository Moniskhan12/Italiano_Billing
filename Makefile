SHELL := /usr/bin/env bash

.PHONY: dev lint type test cov fmt run migrate revision

dev:
	docker compose up -d db

lint:
	ruff check .

fmt:
	ruff format .

type:
	mypy app

test:
	pytest

cov:
	pytest --cov=app --cov-report=term-missing

run:
	uvicorn app.main:app --reload --port 8000

migrate:
	alembic upgrade head

revision:
	alembic revision --autogenerate -m "$(msg)"

down:
	docker compose down -v

logs:
	docker compose logs -f db