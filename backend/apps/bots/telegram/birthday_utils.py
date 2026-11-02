"""Утилиты для дней рождения (корректная обработка 29.02)."""
from datetime import date
from typing import Optional


def _safe_replace_year(d: date, year: int) -> date:
    """replace(year=...) с фолбэком 29.02 → 28.02 в невисокосный год."""
    try:
        return d.replace(year=year)
    except ValueError:
        # 29 февраля в невисокосный год → 28 февраля
        return d.replace(year=year, day=28)


def next_birthday(birth_date: Optional[date], today: Optional[date] = None) -> Optional[date]:
    """Ближайший день рождения (сегодня или в будущем). None если birth_date пуст."""
    if not birth_date:
        return None
    today = today or date.today()
    nb = _safe_replace_year(birth_date, today.year)
    if nb < today:
        nb = _safe_replace_year(birth_date, today.year + 1)
    return nb


def days_until_birthday(birth_date: Optional[date], today: Optional[date] = None) -> Optional[int]:
    """Сколько дней до ближайшего ДР. None если birth_date пуст."""
    nb = next_birthday(birth_date, today)
    if nb is None:
        return None
    today = today or date.today()
    return (nb - today).days