# Italiano Billing — сервис подписок, инвойсов и вебхуков (FastAPI)

[![CI](https://img.shields.io/github/actions/workflow/status/DeBugHowardDuck/Italiano_Billing/ci.yml?branch=main&label=CI)](https://github.com/DeBugHowardDuck/Italiano_Billing/actions)
[![Release](https://img.shields.io/github/v/tag/DeBugHowardDuck/Italiano_Billing?label=release)](https://github.com/DeBugHowardDuck/Italiano_Billing/tags)
[![GHCR](https://img.shields.io/badge/GHCR-italiano--billing-blue)](https://ghcr.io/debughowardduck/italiano_billing/italiano-billing)
![Python](https://img.shields.io/badge/python-3.12-blue)
![mypy](https://img.shields.io/badge/type--check-mypy--strict-green)
![ruff](https://img.shields.io/badge/lint-ruff-green)
![license](https://img.shields.io/badge/license-MIT-green)


## Что это за проект
Учебный, но «производственный» backend для продажи подписок на обучение итальянскому. Код демонстрирует практики, которые ожидают в реальных командах: идемпотентность, миграции, транзакции, вебхуки с подписью, фоновые задачи, метрики Prometheus, строгие линтеры и типизация.

## Возможности
- Тарифные планы: 30 дней, 6 месяцев, 1 год.
- Регистрация и вход (JWT), роль по умолчанию — студент.
- Старт подписки с идемпотентностью: заголовок `Idempotency-Key` предотвращает дубли.
- Инвойсы и платежи. Подтверждение оплаты через вебхук `/payments/webhook` с HMAC-подписью.
- Промокоды и подарочные сертификаты (gift cards), валидации и скидки.
- Продления и dunning-ретраи (APScheduler): генерируются новые инвойсы до конца периода.
- Отмена/заморозка подписки.
- Доступ к контенту: `GET /content/modules` доступен при активной подписке.
- Обсервабилити: `/metrics` в формате Prometheus, структурные JSON-логи, `trace_id` и заголовок `X-Request-ID`.

## Технологии
- Python 3.12, FastAPI, SQLAlchemy 2.0, Alembic, PostgreSQL
- Pydantic v2
- pytest, coverage, ruff, mypy --strict
- APScheduler
- structlog, prometheus-client

## Архитектура каталога
```
app/
 ├─ routers/          # HTTP-слой (auth, subscriptions, payments, content)
 ├─ services/         # бизнес-логика (billing, dunning, promo)
 ├─ repositories/     # работа с БД (user_repo, invoice_repo, payment_repo ...)
 ├─ models/           # SQLAlchemy модели
 ├─ schemas/          # Pydantic схемы
 ├─ utils/            # метрики, утилиты
 └─ workers/          # планировщик продлений
migrations/           # Alembic
docker/               # конфиги для мониторинга (опционально)
```

## Быстрый запуск через Docker Compose
1. Создайте `.env` (можно на основе `.env.example`).
2. Запустите:
   ```bash
   docker compose up --build
   ```
3. Откройте:
   - Документация API: `http://127.0.0.1:8000/docs`
   - Метрики: `http://127.0.0.1:8000/metrics`

При старте контейнера автоматически применяются миграции (`alembic upgrade head`).

## Запуск без Docker (локально)
```bash
pip install fastapi uvicorn pydantic sqlalchemy alembic psycopg[binary]             structlog apscheduler prometheus-client python-dotenv
alembic upgrade head
uvicorn app.main:app --reload
```

## Переменные окружения
См. `.env.example`. Минимум:
- `DATABASE_URL` — строка подключения (в Docker: `postgresql+psycopg://postgres:postgres@db:5432/ibilling`).
- `JWT_SECRET`, `JWT_ALG`.
- `PAYMENTS_WEBHOOK_SECRET` — строка для HMAC подписи вебхука.

## Типовой сценарий проверки
1. `POST /auth/signup` → регистрация.
2. `POST /auth/login` → `access_token`.
3. `POST /subscriptions/start` с заголовком:
   ```
   Idempotency-Key: any-unique-key
   ```
   В теле запроса укажите тариф (`plan_code`) и, при необходимости, `promo_code` или `gift_code`.
4. Отправьте вебхук об успешном платеже:
   ```bash
   body='{"payment_id":1,"status":"SUCCEEDED","provider":"mock"}'
   sig='sha256='$(echo -n $body | openssl dgst -sha256 -hmac "$PAYMENTS_WEBHOOK_SECRET" | sed 's/^.* //')
   curl -X POST http://127.0.0.1:8000/payments/webhook         -H "X-Signature: $sig" -H "Content-Type: application/json" -d "$body"
   ```
5. `GET /content/modules` с заголовком `Authorization: Bearer <access_token>` → доступен список модулей при активной подписке.
6. `/metrics` — убедитесь, что растут метрики `payments_succeeded_total`, `http_requests_total`, корректен `active_subscriptions`.

## Метрики и логи
- Приложение экспортирует метрики по адресу `/metrics` в формате Prometheus: 
  - `http_requests_total`, `http_request_latency_seconds`
  - `payments_succeeded_total`, `payments_failed_total`
  - `active_subscriptions`
- Логи — в JSON через structlog. К каждому запросу добавляется `trace_id`, а в ответ — заголовок `X-Request-ID`.

## CI/CD
Файл `.github/workflows/ci.yml`:
- При каждом push/PR в `main`: линтеры (ruff), типы (mypy), тесты (pytest) с выгрузкой `coverage.xml` как артефакта.
- При пуше тега `v*`: сборка Docker-образа и публикация в GHCR под тем же тегом.
- Для публикации нужен секрет `GHCR_TOKEN` со scope `write:packages`.

## Безопасность и инварианты
- Денежные суммы — в центах (целые числа).
- UTC-время. `current_period_end > current_period_start`.
- Уникальный индекс на `payments.idempotency_key`.
- Вебхук `/payments/webhook` проверяет HMAC подпись заголовка `X-Signature` (`sha256=<hex>`).

## Дорожная карта
- CSV-экспорт оплаченных инвойсов.
- OpenTelemetry traces (Jaeger/Tempo).
- Семейные слоты (owner + до 4 участников).
- Proration при смене тарифа в середине периода.

## Лицензия
MIT
