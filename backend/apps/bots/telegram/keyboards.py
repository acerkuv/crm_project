from django.utils import timezone
from .time_utils import USER_TIMEZONE, to_user_time
from datetime import datetime
from calendar import monthrange
import logging

# Русские названия месяцев
MONTHS_RU = {
    1: 'Январь', 2: 'Февраль', 3: 'Март', 4: 'Апрель',
    5: 'Май', 6: 'Июнь', 7: 'Июль', 8: 'Август',
    9: 'Сентябрь', 10: 'Октябрь', 11: 'Ноябрь', 12: 'Декабрь'
}

def get_months_keyboard():
    """Клавиатура с месяцами"""
    current_year = datetime.now().year
    keyboard = []
    row = []
    for month in range(1, 13):
        month_name = MONTHS_RU[month][:3]
        row.append({"text": month_name, "callback_data": f"month_{month}_{current_year}"})
        if len(row) == 4:
            keyboard.append(row)
            row = []
    if row:
        keyboard.append(row)
    
    keyboard.append([
        {"text": "⬅️ 2025", "callback_data": "year_2025"},
        {"text": "📅 2026", "callback_data": "year_2026"},
        {"text": "2027 ➡️", "callback_data": "year_2027"}
    ])
    keyboard.append([{"text": "❌ Отмена", "callback_data": "plan_cancel"}])
    return {"inline_keyboard": keyboard}

def get_events_calendar_keyboard(month, year):
    """Календарь с событиями (точки на днях с событиями)"""
    from apps.clients.models import ScheduledEvent
    from django.utils import timezone
    from .time_utils import USER_TIMEZONE, to_user_time
    
    logger = logging.getLogger(__name__)
    
    days_in_month = monthrange(year, month)[1]
    first_day_of_month = datetime(year, month, 1).weekday()
    
    # Получаем дни с событиями (в UTC)
    start_msk = datetime(year, month, 1, 0, 0, 0)
    start_msk = timezone.make_aware(start_msk, USER_TIMEZONE)
    start_utc = start_msk.astimezone(timezone.utc)
    
    end_msk = datetime(year, month, days_in_month, 23, 59, 59)
    end_msk = timezone.make_aware(end_msk, USER_TIMEZONE)
    end_utc = end_msk.astimezone(timezone.utc)
    
    events_days = set()
    events = ScheduledEvent.objects.filter(
        scheduled_date__gte=start_utc,
        scheduled_date__lte=end_utc
    )
    
    logger.info(f"📅 Календарь {month}.{year}: найдено {events.count()} событий")
    for event in events:
        user_time = to_user_time(event.scheduled_date)
        events_days.add(user_time.day)
        logger.info(f"   - {user_time.day}: {event.title}")
    
    
    keyboard = []
    
    # Заголовок
    keyboard.append([
        {"text": f"📅 {MONTHS_RU[month]} {year}", "callback_data": "noop"}
    ])
    
    # Дни недели
    weekdays = ['Пн', 'Вт', 'Ср', 'Чт', 'Пт', 'Сб', 'Вс']
    header_row = []
    for day in weekdays:
        header_row.append({"text": day, "callback_data": "noop"})
    keyboard.append(header_row)
    
    # Заполняем календарь
    row = []
    for i in range(first_day_of_month):
        row.append({"text": " ", "callback_data": "noop"})
    
    today = datetime.now()
    current_month = today.month
    current_year = today.year
    current_day_num = today.day
    
    for day in range(1, days_in_month + 1):
        # Проверяем, есть ли события в этот день
        has_events = day in events_days
        
        # Формируем текст кнопки
        is_past = False
        if year < current_year or (year == current_year and month < current_month):
            is_past = True
        elif year == current_year and month == current_month and day < current_day_num:
            is_past = True
        
        if is_past:
            text = f"◻️{day}" if not has_events else f"•{day}•"
        else:
            text = f"{day}" if not has_events else f"•{day}•"
        
        row.append({
            "text": text,
            "callback_data": f"event_day_{day}_{month}_{year}"
        })
        
        if len(row) == 7:
            keyboard.append(row)
            row = []
    
    if row:
        while len(row) < 7:
            row.append({"text": " ", "callback_data": "noop"})
        keyboard.append(row)
    
    # Навигация
    prev_month = month - 1 if month > 1 else 12
    prev_year = year if month > 1 else year - 1
    next_month = month + 1 if month < 12 else 1
    next_year = year if month < 12 else year + 1
    
    keyboard.append([
        {"text": f"◀️ {MONTHS_RU[prev_month]}", "callback_data": f"event_month_{prev_month}_{prev_year}"},
        {"text": "📅 Сегодня", "callback_data": "event_today"},
        {"text": f"{MONTHS_RU[next_month]} ▶️", "callback_data": f"event_month_{next_month}_{next_year}"}
    ])
    keyboard.append([
        {"text": "🏠 Главное меню", "callback_data": "main_menu"}
    ])
    
    return {"inline_keyboard": keyboard}

def get_event_day_keyboard(day, month, year):
    """Клавиатура с разбивкой дня на часы и четверти"""
    from apps.clients.models import ScheduledEvent
    from django.utils import timezone
    import datetime as dt
    
    date = datetime(year, month, day)
    start_date = datetime(year, month, day, 0, 0, 0)
    end_date = datetime(year, month, day, 23, 59, 59)
    
    events = ScheduledEvent.objects.filter(
        scheduled_date__gte=start_date,
        scheduled_date__lte=end_date,
        is_completed=False
    ).order_by('scheduled_date')
    
    # Создаем словарь событий по времени
    events_by_time = {}
    for event in events:
        time_key = event.scheduled_date.strftime("%H:%M")
        if time_key not in events_by_time:
            events_by_time[time_key] = []
        events_by_time[time_key].append(event)
    
    keyboard = []
    
    # Заголовок
    keyboard.append([
        {"text": f"📅 {day} {MONTHS_RU[month]} {year}", "callback_data": "noop"}
    ])
    
    # Часы с 8:00 до 22:00
    for hour in range(8, 23):
        row = []
        for minute in [0, 15, 30, 45]:
            time_str = f"{hour:02d}:{minute:02d}"
            has_event = time_str in events_by_time
            
            if has_event:
                # Если есть событие - показываем с точкой и делаем кнопкой
                event_count = len(events_by_time[time_str])
                text = f"🔴{time_str}" if event_count == 1 else f"🔴{time_str}({event_count})"
                row.append({
                    "text": text,
                    "callback_data": f"event_time_{day}_{month}_{year}_{hour}_{minute}"
                })
            else:
                # Если нет события - просто время
                row.append({
                    "text": f"⬜{time_str}",
                    "callback_data": f"event_empty_{day}_{month}_{year}_{hour}_{minute}"
                })
        
        keyboard.append(row)
    
    # Легенда
    keyboard.append([
        {"text": "🔴 Есть событие", "callback_data": "noop"},
        {"text": "⬜ Нет события", "callback_data": "noop"}
    ])
    
    keyboard.append([
        {"text": "⬅️ Назад к календарю", "callback_data": f"event_back_to_calendar_{month}_{year}"},
        {"text": "🏠 Главное меню", "callback_data": "main_menu"}
    ])
    
    return {"inline_keyboard": keyboard}

def get_main_menu_keyboard():
    """Главное меню со статичными кнопками"""
    return {
        "inline_keyboard": [
            [
                {"text": "📋 Список клиентов", "callback_data": "back_to_list"},
                {"text": "📊 Статистика", "callback_data": "show_stats"}
            ],
            [
                {"text": "🎂 Дни рождения", "callback_data": "show_birthdays"},
                {"text": "📅 События", "callback_data": "show_events_calendar"}
            ],
            [
                {"text": "🔍 Поиск", "callback_data": "find_client"},
                {"text": "➕ Добавить", "callback_data": "add_client"}
            ],
            [
                {"text": "❓ Помощь", "callback_data": "show_help"}
            ]
        ]
    }

def get_plan_action_keyboard():
    """Клавиатура выбора типа события"""
    return {
        "inline_keyboard": [
            [
                {"text": "📞 Позвонить", "callback_data": "plan_action_call"},
                {"text": "📅 Встреча", "callback_data": "plan_action_meeting"}
            ],
            [
                {"text": "🎂 Поздравить", "callback_data": "plan_action_birthday"},
                {"text": "🔔 Напомнить", "callback_data": "plan_action_reminder"}
            ],
            [
                {"text": "📝 Своё событие", "callback_data": "plan_action_custom"}
            ],
            [
                {"text": "❌ Отмена", "callback_data": "plan_cancel"}
            ]
        ]
    }

def get_client_compact_keyboard(client_id):
    """Компактная клавиатура для клиента"""
    return {
        "inline_keyboard": [
            [
                {"text": "👤 Подробнее", "callback_data": f"client_detail_{client_id}"},
                {"text": "📅 План", "callback_data": f"plan_{client_id}"}
            ]
        ]
    }

def get_client_full_actions_keyboard(client_id):
    """Полная клавиатура с действиями"""
    return {
        "inline_keyboard": [
            [
                {"text": "📞 Позвонить", "callback_data": f"action_{client_id}_call"},
                {"text": "📝 Заметка", "callback_data": f"action_{client_id}_note"}
            ],
            [
                {"text": "📅 План", "callback_data": f"plan_{client_id}"},
                {"text": "🖼️ Аватарка", "callback_data": f"show_avatar_{client_id}"}
            ],
            [
                {"text": "⬅️ Назад к списку", "callback_data": "back_to_list"}
            ]
        ]
    }

def get_letters_keyboard():
    """Клавиатура с буквами алфавита"""
    alphabet = 'АБВГДЕЁЖЗИЙКЛМНОПРСТУФХЦЧШЩЪЫЬЭЮЯ'
    keyboard = []
    row = []
    
    for letter in alphabet:
        row.append({"text": letter, "callback_data": f"list_letter_{letter}"})
        if len(row) == 7:
            keyboard.append(row)
            row = []
    if row:
        keyboard.append(row)
    
    keyboard.append([
        {"text": "📋 Все клиенты", "callback_data": "back_to_list"},
        {"text": "❌ Закрыть", "callback_data": "close"}
    ])
    
    return {"inline_keyboard": keyboard}

def get_days_keyboard(month, year):
    """Клавиатура с днями месяца"""
    days_in_month = monthrange(year, month)[1]
    first_day_of_month = datetime(year, month, 1).weekday()
    
    keyboard = []
    weekdays = ['Пн', 'Вт', 'Ср', 'Чт', 'Пт', 'Сб', 'Вс']
    header_row = []
    for day in weekdays:
        header_row.append({"text": day, "callback_data": "noop"})
    keyboard.append(header_row)
    
    row = []
    for i in range(first_day_of_month):
        row.append({"text": " ", "callback_data": "noop"})
    
    today = datetime.now()
    current_month = today.month
    current_year = today.year
    current_day_num = today.day
    
    for day in range(1, days_in_month + 1):
        is_past = False
        if year < current_year or (year == current_year and month < current_month):
            is_past = True
        elif year == current_year and month == current_month and day < current_day_num:
            is_past = True
        
        if is_past:
            row.append({"text": f"◻️{day}", "callback_data": f"day_{day}_{month}_{year}_past"})
        else:
            row.append({"text": f"{day}", "callback_data": f"day_{day}_{month}_{year}"})
        
        if len(row) == 7:
            keyboard.append(row)
            row = []
    
    if row:
        while len(row) < 7:
            row.append({"text": " ", "callback_data": "noop"})
        keyboard.append(row)
    
    prev_month = month - 1 if month > 1 else 12
    prev_year = year if month > 1 else year - 1
    next_month = month + 1 if month < 12 else 1
    next_year = year if month < 12 else year + 1
    
    keyboard.append([
        {"text": f"◀️ {MONTHS_RU[prev_month]}", "callback_data": f"month_{prev_month}_{prev_year}"},
        {"text": f"{MONTHS_RU[month]} {year}", "callback_data": "noop"},
        {"text": f"{MONTHS_RU[next_month]} ▶️", "callback_data": f"month_{next_month}_{next_year}"}
    ])
    keyboard.append([
        {"text": "⬅️ Назад к месяцам", "callback_data": "back_to_months"},
        {"text": "❌ Отмена", "callback_data": "plan_cancel"}
    ])
    
    return {"inline_keyboard": keyboard}

def get_hours_keyboard():
    """Клавиатура с часами"""
    keyboard = []
    row = []
    for hour in range(8, 23):
        row.append({"text": f"{hour:02d}:00", "callback_data": f"hour_{hour}"})
        if len(row) == 4:
            keyboard.append(row)
            row = []
    if row:
        keyboard.append(row)
    
    keyboard.append([
        {"text": "⬅️ Назад к дням", "callback_data": "back_to_days"},
        {"text": "❌ Отмена", "callback_data": "plan_cancel"}
    ])
    return {"inline_keyboard": keyboard}

def get_minutes_keyboard(hour):
    """Клавиатура с минутами"""
    keyboard = []
    row = []
    for minute in [0, 15, 30, 45]:
        row.append({"text": f"{hour:02d}:{minute:02d}", "callback_data": f"minute_{hour}_{minute}"})
    keyboard.append(row)
    
    keyboard.append([
        {"text": "⬅️ Назад к часам", "callback_data": "back_to_hours"},
        {"text": "❌ Отмена", "callback_data": "plan_cancel"}
    ])
    return {"inline_keyboard": keyboard}

# ==================== REPLY KEYBOARD (Виртуальная клавиатура) ====================

def get_main_reply_keyboard():
    """Reply Keyboard - всегда доступные кнопки"""
    return {
        "keyboard": [
            [
                {"text": "📋 Список"},
                {"text": "🔍 Поиск"},
                {"text": "📅 События"}
            ],
            [
                {"text": "➕ Добавить"},
                {"text": "📊 Статистика"},
                {"text": "🎂 Дни рождения"}
            ],
            [
                {"text": "❓ Помощь"}
            ]
        ],
        "resize_keyboard": True,
        "one_time_keyboard": False,
        "input_field_placeholder": "Выберите действие или введите команду..."
    }

def get_cancel_reply_keyboard():
    """Reply Keyboard с кнопкой Отмена"""
    return {
        "keyboard": [
            [
                {"text": "❌ Отмена"}
            ]
        ],
        "resize_keyboard": True,
        "one_time_keyboard": True
    }

def get_event_list_keyboard(events, day, month, year):
    """Клавиатура со списком событий на выбранное время"""
    keyboard = []
    
    if events:
        for event in events:
            time_str = event.scheduled_date.strftime("%H:%M")
            keyboard.append([
                {
                    "text": f"🔴 {time_str} - {event.title[:30]}",
                    "callback_data": f"event_detail_{event.id}"
                }
            ])
        
        # Кнопка "Запланировать новое событие"
        keyboard.append([
            {"text": "➕ Запланировать", "callback_data": f"event_plan_at_{day}_{month}_{year}"}
        ])
    else:
        keyboard.append([
            {"text": "📭 Нет событий", "callback_data": "noop"}
        ])
        keyboard.append([
            {"text": "➕ Запланировать", "callback_data": f"event_plan_at_{day}_{month}_{year}"}
        ])
    
    # Навигация
    keyboard.append([
        {"text": "⬅️ Назад к календарю", "callback_data": f"event_back_to_calendar_{month}_{year}"},
        {"text": "🏠 Главное меню", "callback_data": "main_menu"}
    ])
    
    return {"inline_keyboard": keyboard}

def get_event_time_list_keyboard(events_by_time, time_str, day, month, year):
    """Клавиатура со списком событий на конкретное время"""
    keyboard = []
    
    events = events_by_time.get(time_str, [])
    
    if events:
        for event in events:
            status = "✅" if event.is_completed else "🔴"
            keyboard.append([
                {
                    "text": f"{status} {event.title[:40]}",
                    "callback_data": f"event_detail_{event.id}"
                }
            ])
        
        # Кнопка "Запланировать на это время"
        hour, minute = map(int, time_str.split(':'))
        keyboard.append([
            {"text": "➕ Запланировать", "callback_data": f"event_plan_at_{day}_{month}_{year}_{hour}_{minute}"}
        ])
    else:
        keyboard.append([
            {"text": "📭 Нет событий", "callback_data": "noop"}
        ])
    
    # Навигация
    keyboard.append([
        {"text": f"⬅️ Назад к {day}.{month}.{year}", "callback_data": f"event_back_to_day_{day}_{month}_{year}"},
        {"text": "📅 Календарь", "callback_data": f"event_back_to_calendar_{month}_{year}"}
    ])
    keyboard.append([
        {"text": "🏠 Главное меню", "callback_data": "main_menu"}
    ])
    
    return {"inline_keyboard": keyboard}