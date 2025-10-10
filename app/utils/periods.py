from __future__ import annotations

from datetime import datetime

from dateutil.relativedelta import relativedelta


def add_iso_period(start: datetime, iso: str) -> datetime:
    """
    Минимальный парсер
    P30D -> +30 дней, P6M -> +6 месяцев, P1Y -> +1 год.
    """
    if not iso.startswith("P"):
        raise ValueError("period nust start with 'P'")
    val = int(iso[1:-1])
    unit = iso[-1].upper()
    if unit == "D":
        return start + relativedelta(days=val)
    if unit == "M":
        return start + relativedelta(months=val)
    if unit == "Y":
        return start + relativedelta(years=val)
    raise ValueError(f"unsupported ISO period: {iso}")
