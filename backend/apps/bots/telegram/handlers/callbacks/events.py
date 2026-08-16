from datetime import datetime
from django.utils import timezone
from ..base import send_message, edit_message, delete_message, answer_callback
from ...keyboards import get_events_calendar_keyboard, MONTHS_RU, get_main_reply_keyboard, get_cancel_reply_keyboard
from ...states import update_user_state, get_user_state, clear_user_state
from ...time_utils import to_user_time, format_user_time, now_user, USER_TIMEZONE, create_user_datetime
from apps.clients.models import ScheduledEvent, Client
import logging

logger = logging.getLogger(__name__)

def handle_show_events_calendar(chat_id, message_id, data_callback):
    """Показать календарь с событиями на текущий месяц"""
    today = datetime.now()
    month = today.month
    year = today.year
    
    if message_id:
        keyboard = get_events_calendar_keyboard(month, year)
        text = f"📅 *Календарь событий*\n{MONTHS_RU[month]} {year}\n\n• — есть события"
        edit_message(chat_id, message_id, text, reply_markup=keyboard)
    else:
        keyboard = get_events_calendar_keyboard(month, year)
        text = f"📅 *Календарь событий*\n{MONTHS_RU[month]} {year}\n\n• — есть события"
        send_message(chat_id, text, reply_markup=keyboard)
    return True

def handle_event_month(chat_id, message_id, data_callback):
    """Переключение месяца в календаре событий"""
    parts = data_callback.split('_')
    month = int(parts[2])
    year = int(parts[3])
    
    keyboard = get_events_calendar_keyboard(month, year)
    text = f"📅 *Календарь событий*\n{MONTHS_RU[month]} {year}\n\n• — есть события"
    edit_message(chat_id, message_id, text, reply_markup=keyboard)
    return True

def handle_event_today(chat_id, message_id, data_callback):
    """Перейти к сегодняшнему дню в календаре"""
    today = datetime.now()
    keyboard = get_events_calendar_keyboard(today.month, today.year)
    text = f"📅 *Календарь событий*\n{today.strftime('%B %Y')}\n\n• — есть события"
    edit_message(chat_id, message_id, text, reply_markup=keyboard)
    return True

def handle_event_day(chat_id, message_id, data_callback):
    """Показать события на выбранный день - разбивка по часам (в MSK)"""
    parts = data_callback.split('_')
    day = int(parts[2])
    month = int(parts[3])
    year = int(parts[4])
    
    # Создаем дату в MSK и конвертируем в UTC
    start_msk = datetime(year, month, day, 0, 0, 0)
    start_msk = timezone.make_aware(start_msk, USER_TIMEZONE)
    start_utc = start_msk.astimezone(timezone.utc)
    
    end_msk = datetime(year, month, day, 23, 59, 59)
    end_msk = timezone.make_aware(end_msk, USER_TIMEZONE)
    end_utc = end_msk.astimezone(timezone.utc)
    
    events = ScheduledEvent.objects.filter(
        scheduled_date__gte=start_utc,
        scheduled_date__lte=end_utc
    ).order_by('scheduled_date')
    
    logger.info(f"🔍 ДЕНЬ {day}.{month}.{year}: найдено {events.count()} событий")
    for event in events:
        user_time = to_user_time(event.scheduled_date)
        logger.info(f"   - {user_time.strftime('%H:%M')} {event.title} (completed: {event.is_completed})")
    
    # Группируем по часам (в MSK)
    events_by_hour = {}
    for event in events:
        user_time = to_user_time(event.scheduled_date)
        hour_key = user_time.hour
        if hour_key not in events_by_hour:
            events_by_hour[hour_key] = []
        events_by_hour[hour_key].append(event)
    
    # Формируем клавиатуру с часами (в MSK)
    keyboard = []
    keyboard.append([
        {"text": f"📅 {day} {MONTHS_RU[month]} {year}", "callback_data": "noop"}
    ])
    
    # Показываем все часы с 00:00 до 23:00 в MSK
    for hour in range(0, 24):
        has_events = hour in events_by_hour
        event_count = len(events_by_hour.get(hour, []))
        
        if has_events:
            pending_events = [e for e in events_by_hour[hour] if not e.is_completed]
            if pending_events:
                text = f"🔴 {hour:02d}:00 ({event_count})"
            else:
                text = f"✅ {hour:02d}:00 ({event_count})"
            callback = f"event_hour_{day}_{month}_{year}_{hour}"
        else:
            text = f"⬜ {hour:02d}:00"
            callback = f"event_hour_empty_{day}_{month}_{year}_{hour}"
        
        keyboard.append([
            {"text": text, "callback_data": callback}
        ])
    
    # Легенда
    keyboard.append([
        {"text": "🔴 Есть активные события", "callback_data": "noop"},
        {"text": "✅ Все выполнены", "callback_data": "noop"},
        {"text": "⬜ Нет событий", "callback_data": "noop"}
    ])
    
    # Навигация
    keyboard.append([
        {"text": f"➕ Запланировать", "callback_data": f"event_plan_at_{day}_{month}_{year}"},
    ])
    keyboard.append([
        {"text": "⬅️ Назад к календарю", "callback_data": f"event_back_to_calendar_{month}_{year}"},
        {"text": "🏠 Главное меню", "callback_data": "main_menu"}
    ])
    
    reply_markup = {"inline_keyboard": keyboard}
    text = f"📅 *События на {day} {MONTHS_RU[month]} {year}*\n\nВыберите час:"
    edit_message(chat_id, message_id, text, reply_markup=reply_markup)
    return True

def handle_event_hour(chat_id, message_id, data_callback):
    """Показать события на выбранный час (в MSK)"""
    parts = data_callback.split('_')
    day = int(parts[2])
    month = int(parts[3])
    year = int(parts[4])
    hour_msk = int(parts[5])  # Час в MSK
    
    # Создаем диапазон в MSK и конвертируем в UTC
    start_msk = datetime(year, month, day, hour_msk, 0, 0)
    start_msk = timezone.make_aware(start_msk, USER_TIMEZONE)
    start_utc = start_msk.astimezone(timezone.utc)
    
    end_msk = datetime(year, month, day, hour_msk, 59, 59)
    end_msk = timezone.make_aware(end_msk, USER_TIMEZONE)
    end_utc = end_msk.astimezone(timezone.utc)
    
    events = ScheduledEvent.objects.filter(
        scheduled_date__gte=start_utc,
        scheduled_date__lte=end_utc
    ).order_by('scheduled_date')
    
    logger.info(f"🔍 ЧАС {day}.{month}.{year} {hour_msk:02d}:00 (MSK): найдено {events.count()} событий")
    
    # Группируем по минутам (в MSK)
    events_by_time = {}
    for event in events:
        user_time = to_user_time(event.scheduled_date)
        time_key = user_time.strftime("%H:%M")
        if time_key not in events_by_time:
            events_by_time[time_key] = []
        events_by_time[time_key].append(event)
    
    # Формируем текст со списком событий
    text = f"📅 *События на {day} {MONTHS_RU[month]} {year} в {hour_msk:02d}:00 (MSK)*\n\n"
    
    if events:
        for time_key in sorted(events_by_time.keys()):
            event_list = events_by_time[time_key]
            text += f"⏰ *{time_key}*\n"
            for event in event_list:
                status = "✅" if event.is_completed else "🔴"
                text += f"   {status} *{event.title}*\n"
                text += f"      👤 {event.client.first_name} {event.client.last_name}\n"
                if event.description:
                    text += f"      📝 {event.description[:50]}...\n"
            text += "\n"
    else:
        text += "📭 Нет событий в этом часе\n\n"
    
    # Формируем клавиатуру с кнопками по 15 минут для планирования
    keyboard = []
    
    row = []
    for minute in ["00", "15", "30", "45"]:
        # ИСПРАВЛЕНО: используем hour_msk вместо hour
        time_str = f"{hour_msk:02d}:{minute}"
        has_event = time_str in events_by_time
        if has_event:
            text_btn = f"🔴 {time_str}"
        else:
            text_btn = f"⬜ {time_str}"
        row.append({
            "text": text_btn,
            "callback_data": f"event_time_slot_{day}_{month}_{year}_{hour_msk}_{minute}"
        })
        if len(row) == 4:
            keyboard.append(row)
            row = []
    if row:
        keyboard.append(row)
    
    # Навигация
    keyboard.append([
        {"text": f"⬅️ Назад к {day}.{month}.{year}", "callback_data": f"event_back_to_day_{day}_{month}_{year}"},
        {"text": "📅 Календарь", "callback_data": f"event_back_to_calendar_{month}_{year}"}
    ])
    keyboard.append([
        {"text": "🏠 Главное меню", "callback_data": "main_menu"}
    ])
    
    reply_markup = {"inline_keyboard": keyboard}
    edit_message(chat_id, message_id, text, reply_markup=reply_markup)
    return True

def handle_event_time_slot(chat_id, message_id, data_callback):
    """Обработка нажатия на временной слот (15 минут) - в MSK"""
    parts = data_callback.split('_')
    day = int(parts[3])
    month = int(parts[4])
    year = int(parts[5])
    hour = int(parts[6])
    minute = int(parts[7])
    
    # Создаем время в MSK и конвертируем в UTC
    start_msk = datetime(year, month, day, hour, int(minute), 0)
    start_msk = timezone.make_aware(start_msk, USER_TIMEZONE)
    start_utc = start_msk.astimezone(timezone.utc)
    
    end_msk = datetime(year, month, day, hour, int(minute), 59)
    end_msk = timezone.make_aware(end_msk, USER_TIMEZONE)
    end_utc = end_msk.astimezone(timezone.utc)
    
    events = ScheduledEvent.objects.filter(
        scheduled_date__gte=start_utc,
        scheduled_date__lte=end_utc
    ).order_by('scheduled_date')
    
    if events:
        # Если есть события - показываем их с деталями
        user_time = to_user_time(events[0].scheduled_date)
        time_str = user_time.strftime('%H:%M')
        
        text = f"📅 *События на {day} {MONTHS_RU[month]} {year} в {time_str} (MSK)*\n\n"
        text += f"🔴 *Занято: {len(events)} событий*\n\n"
        
        for event in events:
            status = "✅" if event.is_completed else "🔴"
            text += f"{status} *{event.title}*\n"
            text += f"   👤 {event.client.first_name} {event.client.last_name}\n"
            text += f"   📞 {event.client.phone}\n"
            if event.client.company:
                text += f"   🏢 {event.client.company}\n"
            if event.description:
                text += f"   📝 {event.description}\n"
            text += "\n" + "─" * 20 + "\n"
        
        # Кнопки действий
        keyboard = [
            [{"text": "➕ Запланировать ещё", "callback_data": f"event_plan_at_{day}_{month}_{year}_{hour}_{minute}"}],
            [{"text": "⬅️ Назад к часу", "callback_data": f"event_hour_{day}_{month}_{year}_{hour}"}],
            [{"text": "🏠 Главное меню", "callback_data": "main_menu"}]
        ]
        reply_markup = {"inline_keyboard": keyboard}
        edit_message(chat_id, message_id, text, reply_markup=reply_markup)
    else:
        # Если нет событий - предлагаем запланировать
        user_time = start_msk
        time_str = user_time.strftime('%H:%M')
        
        text = f"📅 *Планирование на {day} {MONTHS_RU[month]} {year} в {time_str} (MSK)*\n\n"
        text += "⬜ *Свободно*\n\n"
        text += "Хотите запланировать событие?"
        
        keyboard = [
            [{"text": "✅ Запланировать", "callback_data": f"event_plan_at_{day}_{month}_{year}_{hour}_{minute}"}],
            [{"text": "⬅️ Назад к часу", "callback_data": f"event_hour_{day}_{month}_{year}_{hour}"}],
            [{"text": "🏠 Главное меню", "callback_data": "main_menu"}]
        ]
        reply_markup = {"inline_keyboard": keyboard}
        edit_message(chat_id, message_id, text, reply_markup=reply_markup)
    
    return True

def handle_event_hour_detail(chat_id, message_id, data_callback):
    """Показать все события часа с полными деталями (в MSK)"""
    parts = data_callback.split('_')
    day = int(parts[3])
    month = int(parts[4])
    year = int(parts[5])
    hour = int(parts[6])
    
    # Создаем диапазон в MSK и конвертируем в UTC
    start_msk = datetime(year, month, day, hour, 0, 0)
    start_msk = timezone.make_aware(start_msk, USER_TIMEZONE)
    start_utc = start_msk.astimezone(timezone.utc)
    
    end_msk = datetime(year, month, day, hour, 59, 59)
    end_msk = timezone.make_aware(end_msk, USER_TIMEZONE)
    end_utc = end_msk.astimezone(timezone.utc)
    
    events = ScheduledEvent.objects.filter(
        scheduled_date__gte=start_utc,
        scheduled_date__lte=end_utc
    ).order_by('scheduled_date')
    
    text = f"📅 *Все события {day} {MONTHS_RU[month]} {year} в {hour:02d}:00 (MSK)*\n\n"
    
    if events:
        for event in events:
            user_time = to_user_time(event.scheduled_date)
            time_str = user_time.strftime("%H:%M")
            status = "✅" if event.is_completed else "🔴"
            text += f"{status} *{time_str}* - {event.title}\n"
            text += f"   👤 {event.client.first_name} {event.client.last_name}\n"
            text += f"   📞 {event.client.phone}\n"
            if event.description:
                text += f"   📝 {event.description}\n"
            text += "\n"
    else:
        text += "📭 Нет событий"
    
    keyboard = [
        [{"text": "⬅️ Назад к часу", "callback_data": f"event_hour_{day}_{month}_{year}_{hour}"}],
        [{"text": "🏠 Главное меню", "callback_data": "main_menu"}]
    ]
    reply_markup = {"inline_keyboard": keyboard}
    edit_message(chat_id, message_id, text, reply_markup=reply_markup)
    return True

def handle_event_hour_empty(chat_id, message_id, data_callback):
    """Обработка пустого часа - показать кнопки по 15 минут для планирования"""
    parts = data_callback.split('_')
    try:
        day = int(parts[3])
        month = int(parts[4])
        year = int(parts[5])
        hour = int(parts[6])
        
        text = f"📅 *Планирование на {day} {MONTHS_RU[month]} {year} в {hour:02d}:00*\n\n"
        text += "Выберите время для планирования события:"
        
        keyboard = []
        row = []
        for minute in [0, 15, 30, 45]:
            row.append({
                "text": f"⬜ {hour:02d}:{minute:02d}",
                "callback_data": f"event_plan_at_{day}_{month}_{year}_{hour}_{minute}"
            })
            if len(row) == 4:
                keyboard.append(row)
                row = []
        if row:
            keyboard.append(row)
        
        keyboard.append([
            {"text": f"⬅️ Назад к {day}.{month}.{year}", "callback_data": f"event_back_to_day_{day}_{month}_{year}"},
            {"text": "📅 Календарь", "callback_data": f"event_back_to_calendar_{month}_{year}"}
        ])
        keyboard.append([
            {"text": "🏠 Главное меню", "callback_data": "main_menu"}
        ])
        
        reply_markup = {"inline_keyboard": keyboard}
        edit_message(chat_id, message_id, text, reply_markup=reply_markup)
        
    except (IndexError, ValueError) as e:
        logger.error(f"Ошибка парсинга event_hour_empty: {data_callback}, ошибка: {e}")
        send_message(chat_id, "❌ Ошибка при обработке. Попробуйте еще раз.")
    return True

def handle_event_time(chat_id, message_id, data_callback):
    """Обработка выбора времени (устаревший метод)"""
    parts = data_callback.split('_')
    day = int(parts[2])
    month = int(parts[3])
    year = int(parts[4])
    hour = int(parts[5])
    minute = int(parts[6])
    
    handle_event_time_slot(chat_id, message_id, f"event_time_slot_{day}_{month}_{year}_{hour}_{minute}")
    return True

def handle_event_empty(chat_id, message_id, data_callback):
    """Обработка пустого времени (устаревший метод)"""
    parts = data_callback.split('_')
    day = int(parts[2])
    month = int(parts[3])
    year = int(parts[4])
    hour = int(parts[5])
    minute = int(parts[6])
    
    handle_event_plan_at(chat_id, message_id, f"event_plan_at_{day}_{month}_{year}_{hour}_{minute}")
    return True

def handle_event_plan_at(chat_id, message_id, data_callback):
    """Запланировать событие (сохраняем в UTC, показываем в MSK)"""
    parts = data_callback.split('_')
    day = int(parts[3])
    month = int(parts[4])
    year = int(parts[5])
    
    if len(parts) >= 7:
        hour = int(parts[6])
        if len(parts) >= 8:
            minute = int(parts[7])
        else:
            minute = 0
    else:
        hour = 9
        minute = 0
    
    # Создаем дату в MSK и конвертируем в UTC
    dt_msk = datetime(year, month, day, hour, minute)
    dt_msk = timezone.make_aware(dt_msk, USER_TIMEZONE)
    scheduled_date = dt_msk.astimezone(timezone.utc)
    
    now_utc = datetime.now(timezone.utc)
    if scheduled_date < now_utc:
        answer_callback(parts[0], '❌ Нельзя запланировать на прошедшее время!', show_alert=True)
        return True
    
    update_user_state(chat_id, 
        scheduled_date=scheduled_date,
        state='selecting_client_for_event'
    )
    
    # Показываем пользователю время в MSK
    user_time_str = format_user_time(scheduled_date)
    
    keyboard = {
        "inline_keyboard": [
            [{"text": "❌ Отмена", "callback_data": "plan_cancel"}]
        ]
    }
    
    if message_id:
        edit_message(chat_id, message_id, 
            f"📅 *Планирование события*\n\n"
            f"📅 {user_time_str} (MSK)\n\n"
            f"🔍 Введите имя, телефон или компанию клиента:",
            reply_markup=keyboard
        )
    else:
        send_message(chat_id, 
            f"📅 *Планирование события*\n\n"
            f"📅 {user_time_str} (MSK)\n\n"
            f"🔍 Введите имя, телефон или компанию клиента:",
            reply_markup=keyboard
        )
    return True

def show_hour_selection(chat_id, message_id, day, month, year):
    """Показать выбор часа для планирования"""
    text = f"📅 *Планирование на {day} {MONTHS_RU[month]} {year}*\n\n"
    text += "Выберите час для планирования:"
    
    keyboard = []
    row = []
    # Все часы с 00:00 до 23:00
    for hour in range(0, 24):
        row.append({
            "text": f"{hour:02d}:00",
            "callback_data": f"event_plan_hour_{day}_{month}_{year}_{hour}"
        })
        if len(row) == 4:
            keyboard.append(row)
            row = []
    if row:
        keyboard.append(row)
    
    keyboard.append([
        {"text": "⬅️ Назад к дням", "callback_data": f"event_back_to_day_{day}_{month}_{year}"},
        {"text": "📅 Календарь", "callback_data": f"event_back_to_calendar_{month}_{year}"}
    ])
    keyboard.append([
        {"text": "❌ Отмена", "callback_data": "plan_cancel"}
    ])
    
    reply_markup = {"inline_keyboard": keyboard}
    
    if message_id:
        edit_message(chat_id, message_id, text, reply_markup=reply_markup)
    else:
        send_message(chat_id, text, reply_markup=reply_markup)

def show_quarter_selection(chat_id, message_id, day, month, year, hour):
    """Показать выбор четверти часа для планирования"""
    text = f"📅 *Планирование на {day} {MONTHS_RU[month]} {year} в {hour:02d}:00*\n\n"
    text += "Выберите четверть часа для планирования:"
    
    keyboard = []
    row = []
    for minute in [0, 15, 30, 45]:
        row.append({
            "text": f"{hour:02d}:{minute:02d}",
            "callback_data": f"event_plan_at_{day}_{month}_{year}_{hour}_{minute}"
        })
        if len(row) == 4:
            keyboard.append(row)
            row = []
    if row:
        keyboard.append(row)
    
    keyboard.append([
        {"text": "⬅️ Назад к часам", "callback_data": f"event_plan_hour_{day}_{month}_{year}_{hour}"},
        {"text": "📅 Календарь", "callback_data": f"event_back_to_calendar_{month}_{year}"}
    ])
    keyboard.append([
        {"text": "❌ Отмена", "callback_data": "plan_cancel"}
    ])
    
    reply_markup = {"inline_keyboard": keyboard}
    
    if message_id:
        edit_message(chat_id, message_id, text, reply_markup=reply_markup)
    else:
        send_message(chat_id, text, reply_markup=reply_markup)

def handle_event_back_to_day(chat_id, message_id, data_callback):
    """Возврат к просмотру дня (разбивка по часам)"""
    # Формат: event_back_to_day_30_8_2026
    parts = data_callback.split('_')
    # parts = ['event', 'back', 'to', 'day', '30', '8', '2026']
    
    try:
        if len(parts) >= 5 and parts[3] == 'day':
            day = int(parts[4])
            month = int(parts[5])
            year = int(parts[6])
        else:
            day = int(parts[3])
            month = int(parts[4])
            year = int(parts[5])
    except (IndexError, ValueError) as e:
        logger.error(f"Ошибка парсинга event_back_to_day: {data_callback}")
        send_message(chat_id, "❌ Ошибка при возврате к дню")
        return True
    
    return handle_event_day(chat_id, message_id, f"event_day_{day}_{month}_{year}")

def handle_event_back_to_calendar(chat_id, message_id, data_callback):
    """Возврат к календарю"""
    parts = data_callback.split('_')
    
    try:
        # event_back_to_calendar_8_2026
        # parts = ['event', 'back', 'to', 'calendar', '8', '2026']
        if len(parts) >= 5 and parts[3] == 'calendar':
            month = int(parts[4])
            year = int(parts[5])
        else:
            month = int(parts[3])
            year = int(parts[4])
    except (IndexError, ValueError) as e:
        logger.error(f"Ошибка парсинга event_back_to_calendar: {data_callback}, ошибка: {e}")
        send_message(chat_id, "❌ Ошибка при возврате к календарю")
        return True
    
    keyboard = get_events_calendar_keyboard(month, year)
    text = f"📅 *Календарь событий*\n{MONTHS_RU[month]} {year}\n\n• — есть события"
    edit_message(chat_id, message_id, text, reply_markup=keyboard)
    return True

def handle_event_complete(chat_id, message_id, data_callback):
    """Отметить событие как выполненное"""
    event_id = int(data_callback.split('_')[2])
    
    try:
        event = ScheduledEvent.objects.get(id=event_id)
        event.is_completed = True
        event.save()
        
        # Показываем время в MSK
        user_time = to_user_time(event.scheduled_date)
        time_str = user_time.strftime('%d.%m.%Y %H:%M')
        
        text = f"✅ Событие выполнено!\n\n"
        text += f"📌 {event.title}\n"
        text += f"👤 {event.client.first_name} {event.client.last_name}\n"
        text += f"📅 {time_str} (MSK)"
        
        # Возвращаемся к часу в MSK
        hour_msk = user_time.hour
        keyboard = {
            "inline_keyboard": [
                [{"text": "⬅️ Назад", "callback_data": f"event_hour_{user_time.day}_{user_time.month}_{user_time.year}_{hour_msk}"}]
            ]
        }
        
        edit_message(chat_id, message_id, text, reply_markup=keyboard)
        answer_callback(parts[0], '✅ Событие отмечено как выполненное!')
        
    except ScheduledEvent.DoesNotExist:
        answer_callback(parts[0], '❌ Событие не найдено', show_alert=True)
    
    return True

def handle_event_detail(chat_id, message_id, data_callback):
    """Показать детали события"""
    event_id = int(data_callback.split('_')[2])
    
    try:
        event = ScheduledEvent.objects.get(id=event_id)
        
        # Показываем время в MSK
        user_time = to_user_time(event.scheduled_date)
        time_str = user_time.strftime('%d.%m.%Y %H:%M')
        hour_msk = user_time.hour
        day = user_time.day
        month = user_time.month
        year = user_time.year
        
        status = "✅ Выполнено" if event.is_completed else "⏳ Ожидает выполнения"
        status_emoji = "✅" if event.is_completed else "⏳"
        
        text = f"{status_emoji} *{event.title}*\n\n"
        text += f"👤 Клиент: {event.client.first_name} {event.client.last_name}\n"
        text += f"📞 Телефон: {event.client.phone}\n"
        text += f"📅 Дата: {time_str} (MSK)\n"
        text += f"📌 Тип: {event.event_type}\n"
        text += f"📊 Статус: {status}\n"
        if event.description:
            text += f"\n📝 Описание:\n{event.description}"
        
        keyboard = []
        
        if not event.is_completed:
            keyboard.append([
                {"text": "✅ Отметить выполненным", "callback_data": f"event_complete_{event.id}"}
            ])
        
        keyboard.append([
            {"text": f"⬅️ Назад к часу", "callback_data": f"event_hour_{day}_{month}_{year}_{hour_msk}"}
        ])
        keyboard.append([
            {"text": "📅 Календарь", "callback_data": f"event_back_to_calendar_{month}_{year}"},
            {"text": "🏠 Главное меню", "callback_data": "main_menu"}
        ])
        
        reply_markup = {"inline_keyboard": keyboard}
        
        if message_id:
            edit_message(chat_id, message_id, text, reply_markup=reply_markup)
        else:
            send_message(chat_id, text, reply_markup=reply_markup)
        
        answer_callback(parts[0])
        
    except ScheduledEvent.DoesNotExist:
        send_message(chat_id, "❌ Событие не найдено")
    
    return True

def handle_event_plan_hour(chat_id, message_id, data_callback):
    """Обработка выбора часа для планирования"""
    parts = data_callback.split('_')
    day = int(parts[3])
    month = int(parts[4])
    year = int(parts[5])
    hour = int(parts[6])
    
    show_quarter_selection(chat_id, message_id, day, month, year, hour)
    return True

# В events.py добавьте новую функцию
def handle_event_force_plan(chat_id, message_id, data_callback):
    """Принудительное планирование события (даже если слот занят)"""
    parts = data_callback.split('_')
    client_id = int(parts[3])
    action = parts[4]
    timestamp = float(parts[5])
    scheduled_date = datetime.fromtimestamp(timestamp)
    
    # Сохраняем в состоянии
    update_user_state(chat_id,
        client_id=client_id,
        action=action,
        scheduled_date=scheduled_date,
        state='waiting_for_event_description_force'
    )
    
    # Спрашиваем описание
    client = Client.objects.filter(id=client_id).first()
    if client:
        response = (
            f"⚠️ *Принудительное планирование*\n\n"
            f"👤 {client.first_name} {client.last_name}\n"
            f"📅 {scheduled_date.strftime('%d.%m.%Y %H:%M')}\n"
            f"📌 Тип: {action}\n\n"
            f"📝 Введите описание события:"
        )
        keyboard = get_cancel_reply_keyboard()
        send_message(chat_id, response, reply_markup=keyboard)
    else:
        send_message(chat_id, "❌ Клиент не найден")
    
    return True

def handle_event_description_force(chat_id, text_message):
    """Принудительное создание события (без проверки занятости)"""
    state = get_user_state(chat_id)
    
    if text_message == "❌ Отмена":
        clear_user_state(chat_id)
        keyboard = get_main_reply_keyboard()
        send_message(chat_id, "❌ Создание события отменено", reply_markup=keyboard)
        return
    
    client_id = state.get('client_id')
    action = state.get('action')
    scheduled_date = state.get('scheduled_date')
    
    if not client_id or not action or not scheduled_date:
        send_message(chat_id, "⚠️ Ошибка: данные неполные")
        clear_user_state(chat_id)
        return
    
    client = Client.objects.filter(id=client_id).first()
    if not client:
        send_message(chat_id, "❌ Клиент не найден")
        clear_user_state(chat_id)
        return
    
    try:
        event = ScheduledEvent.objects.create(
            client=client,
            title=text_message[:100],
            description=text_message,
            event_type=action,
            scheduled_date=scheduled_date,
            is_completed=False
        )
        
        action_names = {
            'call': '📞 звонок',
            'meeting': '📅 встречу',
            'birthday': '🎂 поздравление',
            'reminder': '🔔 напоминание',
            'custom': '📝 событие'
        }
        
        response = (
            f"✅ Событие создано (принудительно)!\n\n"
            f"👤 {client.first_name} {client.last_name}\n"
            f"📝 {text_message}\n"
            f"📅 {scheduled_date.strftime('%d.%m.%Y %H:%M')}\n"
            f"📌 Тип: {action_names.get(action, 'событие')}\n"
            f"⚠️ Внимание: в этом слоте уже были события!"
        )
        
        clear_user_state(chat_id)
        keyboard = get_main_reply_keyboard()
        send_message(chat_id, response, reply_markup=keyboard)
        
    except Exception as e:
        logger.error(f"❌ Ошибка создания события: {e}")
        send_message(chat_id, f"❌ Ошибка: {str(e)}")