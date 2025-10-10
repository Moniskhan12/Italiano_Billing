from __future__ import annotations

import os

from dotenv import load_dotenv
from sqlalchemy import create_engine, inspect


def test_core_tables_exist() -> None:
    load_dotenv()
    url = os.getenv(
        "DATABASE_URL", "postgresql+psycopg://postgres:postgres@localhost:5432/italiano"
    )
    engine = create_engine(url, future=True)
    inspector = inspect(engine)
    tables = set(inspector.get_table_names(schema="public"))
    assert {"users", "plans", "subscriptions"}.issubset(tables)
