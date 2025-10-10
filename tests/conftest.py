from __future__ import annotations

from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config


@pytest.fixture(scope="session", autouse=True)
def apply_migrations() -> None:
    """Накатываем alembic до head один раз на тестовую БД."""
    cfg_path = Path(__file__).resolve().parents[1] / "alembic.ini"
    cfg = Config(str(cfg_path))
    command.upgrade(cfg, "head")
