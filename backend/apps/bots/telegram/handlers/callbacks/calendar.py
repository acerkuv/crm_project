from datetime import datetime
from ..base import send_message, delete_message, edit_message, answer_callback
from ...states import get_user_state, update_user_state, clear_user_state
from ...keyboards import get_days_keyboard, get_hours_keyboard, get_minutes_keyboard, get_months_keyboard, MONTHS_RU
from apps.clients.models import Client, ScheduledEvent

def handle_month(chat_id, message_id, data_callback):
    """Выбор месяца в календаре"""
    parts = data_callback.split('_')
    month = int(parts[1])
    year = int(parts[2])
    
    update_user_state(chat_id, selected_month=month, selected_year=year)
    keyboard = get_days_keyboard(month, year)
    edit_message(chat_id, message_id, f"📅 *Выберите день:*\n{MONTHS_RU[month]} {year}", reply_markup=keyboard)
    return True

def handle_day(chat_id, message_id, data_callback):
    """Выбор дня в календаре"""
    parts = data_callback.split('_')
    day = int(parts[1])
    month = int(parts[2])
    year = int(parts[3])
    is_past = len(parts) > 4 and parts[4] == 'past'
    
    if is_past:
        answer_callback(parts[0], '❌ Нельзя выбрать прошедшую дату!', show_alert=True)
        return True
    
    update_user_state(chat_id, selected_day=day, selected_month=month, selected_year=year, state='selecting_hour')
    keyboard = get_hours_keyboard()
    edit_message(chat_id, message_id, f"🕐 *Выберите час:*\n📅 {day} {MONTHS_RU[month]} {year}", reply_markup=keyboard)
    return True

def handle_hour(chat_id, message_id, data_callback):
    """Выбор часа"""
    hour = int(data_callback.split('_')[1])
    
    update_user_state(chat_id, selected_hour=hour, state='selecting_minute')
    keyboard = get_minutes_keyboard(hour)
    edit_message(chat_id, message_id, f"🕐 *Выберите минуты:*\n⏰ {hour:02d}:00", reply_markup=keyboard)
    return True

def handle_minute(chat_id, message_id, data_callback):
    """Выбор минут (финальный шаг)"""
    parts = data_callback.split('_')
    hour = int(parts[1])
    minute = int(parts[2])
    
    state = get_user_state(chat_id)
    
    if not ('selected_day' in state and 'selected_month' in state and 'selected_year' in state):
        send_message(chat_id, "❌ Ошибка: данные неполные")
        return True
    
    day = state['selected_day']
    month = state['selected_month']
    year = state['selected_year']
    
    scheduled_date = datetime(year, month, day, hour, minute)
    
    if scheduled_date < datetime.now():
        answer_callback(parts[0], '❌ Нельзя выбрать прошедшее время!', show_alert=True)
        return True
    
    client_id = state.get('client_id')
    client = Client.objects.filter(id=client_id).first()
    
    if not client:
        send_message(chat_id, "❌ Клиент не найден")
        return True
    
    action_names = {
        'call': '📞 звонок',
        'meeting': '📅 встречу',
        'birthday': '🎂 поздравление',
        'reminder': '🔔 напоминание',
        'custom': '📝 событие',
        'note': '📝 заметку'
    }
    action = state.get('action', 'custom')
    
    # Сохраняем событие
    ScheduledEvent.objects.create(
        client=client,
        title=state.get('description', 'Событие'),
        description=state.get('description', 'Событие'),
        event_type=action,
        scheduled_date=scheduled_date,
        is_completed=False
    )
    
    response = (
        f"✅ Событие запланировано!\n\n"
        f"👤 {client.first_name} {client.last_name}\n"
        f"📝 {state.get('description', 'Событие')}\n"
        f"📅 {scheduled_date.strftime('%d.%m.%Y %H:%M')}\n"
        f"📌 Тип: {action_names.get(action, 'событие')}\n\n"
        f"Я напомню вам об этом!"
    )
    
    delete_message(chat_id, message_id)
    send_message(chat_id, response)
    clear_user_state(chat_id)
    return True

def handle_back_to_months(chat_id, message_id, data_callback):
    """Возврат к выбору месяца"""
    keyboard = get_months_keyboard()
    edit_message(chat_id, message_id, "📅 *Выберите месяц:*", reply_markup=keyboard)
    return True

def handle_back_to_days(chat_id, message_id, data_callback):
    """Возврат к выбору дня"""
    state = get_user_state(chat_id)
    month = state.get('selected_month', datetime.now().month)
    year = state.get('selected_year', datetime.now().year)
    
    keyboard = get_days_keyboard(month, year)
    edit_message(chat_id, message_id, f"📅 *Выберите день:*\n{MONTHS_RU[month]} {year}", reply_markup=keyboard)
    return True

def handle_back_to_hours(chat_id, message_id, data_callback):
    """Возврат к выбору часа"""
    keyboard = get_hours_keyboard()
    edit_message(chat_id, message_id, "🕐 *Выберите час:*", reply_markup=keyboard)
    return True
