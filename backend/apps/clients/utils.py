"""Утилиты для нормализации полей клиента."""
import re
from datetime import datetime, date
from typing import Optional


def normalize_phone(raw: str) -> str:
    """Приводит телефон к +7XXXXXXXXXX.
    +7 (999) 123-45-67 / 8 999 123 45 67 / 9991234567 → +79991234567
    Если не удалось — возвращает исходную строку (strip).
    """
    if not raw:
        return ''
    digits = re.sub(r'\D', '', raw)
    if not digits:
        return raw.strip()
    if len(digits) == 10:
        return f'+7{digits}'
    if len(digits) == 11 and digits[0] in ('7', '8'):
        return f'+7{digits[1:]}'
    return f'+{digits}' if len(digits) > 10 else raw.strip()


def parse_birth_date(raw: str) -> Optional[date]:
    """Парсит дату рождения: 25.12.1990 / 25/12/1990 / 25-12-1990 / 1990-12-25.
    Пустое значение или «—» → None.
    Бросает ValueError с понятным сообщением, если формат не распознан.
    """
    if not raw or raw.strip() in ('—', '-', ''):
        return None
    raw = raw.strip()
    for fmt in ('%d.%m.%Y', '%d/%m/%Y', '%d-%m-%Y', '%Y-%m-%d'):
        try:
            return datetime.strptime(raw, fmt).date()
        except ValueError:
            continue
    raise ValueError(
        f"Неверный формат даты: {raw}. Используйте ДД.ММ.ГГГГ (например, 25.12.1990)"
    )