"""Валидаторы дат/времени для событий."""
from datetime import datetime
from django.utils import timezone


def is_past(dt: datetime) -> bool:
    if dt is None:
        return True
    if timezone.is_naive(dt):
        dt = timezone.make_aware(dt, timezone.get_current_timezone())
    return dt < timezone.now()


def past_error_message() -> str:
    return "❌ Нельзя планировать событие в прошлом. Выберите будущую дату и время."


async def ensure_future_or_reply(query, dt) -> bool:
    if is_past(dt):
        msg = past_error_message()
        try:
            await query.edit_message_text(msg)
        except Exception:
            try:
                await query.answer(msg, show_alert=True)
            except Exception:
                pass
        return False
    return True