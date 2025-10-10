from __future__ import annotations

from pydantic import BaseModel


class ContentModuleOut(BaseModel):
    code: str
    title: str
    min_tier: str
