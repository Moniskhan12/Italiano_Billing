"""seed content modules

Revision ID: 38b2b78c712b
Revises: 4345b1ba2f08
Create Date: 2025-10-09 16:57:36.664190
"""

from alembic import op
from sqlalchemy import String
from sqlalchemy.sql import column, table

# revision identifiers, used by Alembic.
revision = "38b2b78c712b"
down_revision = "4345b1ba2f08"
branch_labels = None
depends_on = None

content_modules = table(
    "content_modules",
    column("code", String(50)),
    column("title", String(200)),
    column("min_tier", String(20)),
)


def upgrade() -> None:
    op.bulk_insert(
        content_modules,
        [
            {
                "code": "basics-1",
                "title": "Основы итальянского — Модуль 1",
                "min_tier": "basic",
            },
            {
                "code": "basics-2",
                "title": "Основы итальянского — Модуль 2",
                "min_tier": "basic",
            },
        ],
    )


def downgrade() -> None:
    op.execute("DELETE FROM content_modules WHERE code in ('basics-1','basics-2')")
