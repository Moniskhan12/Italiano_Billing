from __future__ import annotations

import os
import sys
from logging.config import fileConfig

from alembic import context
from dotenv import load_dotenv
from sqlalchemy import engine_from_config, pool

CURRENT_DIR = os.path.dirname(__file__)  # .../migrations
PROJECT_ROOT = os.path.abspath(os.path.join(CURRENT_DIR, os.pardir))
if PROJECT_ROOT not in sys.path:
    sys.path.append(PROJECT_ROOT)

# .env в корне проекта (если есть)
load_dotenv(os.path.join(PROJECT_ROOT, ".env"))

config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# URL БД: .env -> переменная окружения -> дефолт
db_url = (
    os.getenv("DATABASE_URL")
    or "postgresql+psycopg://postgres:postgres@localhost:5432/italiano"
)
config.set_main_option("sqlalchemy.url", db_url)

# импорт теперь ПОСЛЕ sys.path и .env
from app.models import Base  # noqa: E402

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        compare_type=True,
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    connectable = engine_from_config(
        config.get_section(config.config_ini_section),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
        future=True,
    )
    with connectable.connect() as connection:
        context.configure(
            connection=connection, target_metadata=target_metadata, compare_type=True
        )
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
