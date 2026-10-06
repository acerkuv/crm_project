from datetime import datetime
from django.utils import timezone
import pytz

# Часовой пояс пользователя (Москва)
USER_TIMEZONE = pytz.timezone('Europe/Moscow')
UTC_TIMEZONE = pytz.UTC

def get_user_timezone():
    """Получить часовой пояс пользователя (Москва)"""
    return USER_TIMEZONE

def now_user():
    """Текущее время в часовом поясе пользователя"""
    return datetime.now(USER_TIMEZONE)

def now_utc():
    """Текущее время в UTC"""
    return datetime.now(UTC_TIMEZONE)

def to_user_time(dt):
    """
    Преобразовать datetime из UTC в время пользователя (Москва)
    """
    if dt is None:
        return None
    
    # Если datetime наивный (без timezone) - делаем его UTC
    if dt.tzinfo is None:
        dt = timezone.make_aware(dt, UTC_TIMEZONE)
    
    # Конвертируем в часовой пояс пользователя
    return dt.astimezone(USER_TIMEZONE)

def to_utc_time(dt):
    """
    Преобразовать datetime из времени пользователя в UTC
    """
    if dt is None:
        return None
    
    # Если datetime наивный (без timezone) - делаем его в часовом поясе пользователя
    if dt.tzinfo is None:
        dt = timezone.make_aware(dt, USER_TIMEZONE)
    
    # Конвертируем в UTC
    return dt.astimezone(UTC_TIMEZONE)

def format_user_time(dt, format_str="%d.%m.%Y %H:%M"):
    """
    Отформатировать время для показа пользователю (в его часовом поясе)
    """
    if dt is None:
        return "Не указано"
    
    user_dt = to_user_time(dt)
    return user_dt.strftime(format_str)

def format_user_date(dt, format_str="%d.%m.%Y"):
    """
    Отформатировать дату для показа пользователю
    """
    if dt is None:
        return "Не указано"
    
    user_dt = to_user_time(dt)
    return user_dt.strftime(format_str)

def parse_user_datetime(date_str, time_str=None):
    """
    Разобрать дату и время от пользователя в UTC
    """
    try:
        if time_str:
            dt_str = f"{date_str} {time_str}"
            dt = datetime.strptime(dt_str, "%d.%m.%Y %H:%M")
        else:
            dt = datetime.strptime(date_str, "%d.%m.%Y")
        
        # Делаем время в часовом поясе пользователя
        dt = timezone.make_aware(dt, USER_TIMEZONE)
        # Конвертируем в UTC
        return dt.astimezone(UTC_TIMEZONE)
    except Exception as e:
        return None

def create_user_datetime(year, month, day, hour=0, minute=0):
    """
    Создать datetime в часовом поясе пользователя и конвертировать в UTC
    """
    dt = datetime(year, month, day, hour, minute)
    dt = timezone.make_aware(dt, USER_TIMEZONE)
    return dt.astimezone(UTC_TIMEZONE)