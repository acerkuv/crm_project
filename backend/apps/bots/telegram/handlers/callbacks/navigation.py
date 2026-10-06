from ..base import send_message, edit_message, delete_message, answer_callback
from ...states import clear_user_state
from ...keyboards import get_main_menu_keyboard, get_letters_keyboard
from ...utils import get_clients_list_message
from apps.clients.models import Client
from django.db.models import Q

def handle_back_to_list(chat_id, message_id, data_callback):
    """Возврат к списку клиентов"""
    clients = Client.objects.all().order_by('-created_at')
    message_text, keyboard = get_clients_list_message(clients, 1)
    edit_message(chat_id, message_id, message_text, reply_markup=keyboard)
    return True

def handle_refresh_list(chat_id, message_id, data_callback):
    """Обновить список клиентов"""
    clients = Client.objects.all().order_by('-created_at')
    message_text, keyboard = get_clients_list_message(clients, 1)
    edit_message(chat_id, message_id, message_text, reply_markup=keyboard)
    return True

def handle_main_menu(chat_id, message_id, data_callback):
    """Показать главное меню"""
    keyboard = get_main_menu_keyboard()
    edit_message(chat_id, message_id, "🏠 *Главное меню*\n\nВыберите действие:", reply_markup=keyboard)
    return True

def handle_list_page(chat_id, message_id, data_callback):
    """Пагинация списка клиентов"""
    page = int(data_callback.split('_')[2])
    clients = Client.objects.all().order_by('-created_at')
    message_text, keyboard = get_clients_list_message(clients, page)
    edit_message(chat_id, message_id, message_text, reply_markup=keyboard)
    return True

def handle_list_letter(chat_id, message_id, data_callback):
    """Обработка выбора буквы для фильтрации списка"""
    letter = data_callback.split('_')[2]
    
    clients = Client.objects.filter(
        Q(first_name__istartswith=letter) |
        Q(last_name__istartswith=letter)
    ).order_by('first_name')
    
    if not clients.exists():
        send_message(chat_id, f"📭 Нет клиентов на букву '{letter}'")
        return True
    
    message_text, keyboard = get_clients_list_message(clients, 1)
    header = f"📋 *Клиенты на букву '{letter}'* (всего {clients.count()})\n\n"
    if '\n\n' in message_text:
        message_text = header + message_text.split('\n\n', 1)[1]
    else:
        message_text = header + message_text
    
    edit_message(chat_id, message_id, message_text, reply_markup=keyboard)
    return True

def handle_plan_cancel(chat_id, message_id, data_callback):
    """Отмена планирования"""
    clear_user_state(chat_id)
    delete_message(chat_id, message_id)
    send_message(chat_id, "❌ Планирование отменено")
    return True

def handle_show_stats(chat_id, message_id, data_callback):
    """Показать статистику"""
    from apps.clients.models import Client, ScheduledEvent
    
    total = Client.objects.count()
    vip = Client.objects.filter(status='vip').count()
    active = Client.objects.filter(status='active').count()
    regular = Client.objects.filter(status='regular').count()
    lead = Client.objects.filter(status='lead').count()
    events = ScheduledEvent.objects.filter(is_completed=False).count()
    
    response = (
        f"📊 *Статистика CRM:*\n\n"
        f"👥 Всего клиентов: *{total}*\n\n"
        "По статусам:\n"
        f"⭐ VIP: {vip}\n"
        f"✅ Активные: {active}\n"
        f"🔄 Постоянные: {regular}\n"
        f"🆕 Лиды: {lead}\n\n"
        f"📅 Запланировано событий: {events}"
    )
    
    # Показываем статистику с кнопкой "Назад"
    keyboard = {
        "inline_keyboard": [
            [{"text": "⬅️ Назад к списку", "callback_data": "back_to_list"}]
        ]
    }
    
    edit_message(chat_id, message_id, response, reply_markup=keyboard)
    return True

def handle_show_birthdays(chat_id, message_id, data_callback):
    """Показать дни рождения"""
    from django.utils import timezone
    from apps.clients.models import Client
    from datetime import datetime
    
    today = timezone.now().date()
    clients_list = []
    
    for client in Client.objects.filter(birth_date__isnull=False):
        if client.birth_date:
            next_birthday = client.birth_date.replace(year=today.year)
            if next_birthday < today:
                next_birthday = next_birthday.replace(year=today.year + 1)
            days_until = (next_birthday - today).days
            if 0 <= days_until <= 7:
                clients_list.append((client, days_until))
    
    if clients_list:
        response = "🎂 *Дни рождения в ближайшую неделю:*\n\n"
        for client, days in sorted(clients_list, key=lambda x: x[1]):
            status_emoji = {'vip': '⭐', 'active': '✅', 'regular': '🔄', 'lead': '🆕', 'inactive': '⏸️'}.get(client.status, '📌')
            response += f"{status_emoji} *{client.first_name} {client.last_name}*\n"
            response += f"   📞 {client.phone}\n"
            if client.company:
                response += f"   🏢 {client.company}\n"
            if client.comment:
                response += f"   📝 {client.comment[:50]}...\n"
            response += f"   📅 {client.birth_date.strftime('%d.%m')} (через {days} дн.)\n"
            response += "\n"
    else:
        response = "🎂 В ближайшую неделю нет дней рождения."
    
    keyboard = {
        "inline_keyboard": [
            [{"text": "⬅️ Назад к списку", "callback_data": "back_to_list"}]
        ]
    }
    
    edit_message(chat_id, message_id, response, reply_markup=keyboard)
    return True

def handle_show_events(chat_id, message_id, data_callback):
    """Показать события"""
    from apps.clients.models import ScheduledEvent
    from django.utils import timezone
    
    events = ScheduledEvent.objects.filter(
        scheduled_date__gte=timezone.now(),
        is_completed=False
    ).order_by('scheduled_date')[:10]
    
    if events:
        response = "📅 *Запланированные события:*\n\n"
        for event in events:
            date_str = event.scheduled_date.strftime('%d.%m.%Y %H:%M')
            response += f"📌 *{event.title}*\n"
            response += f"   👤 {event.client.first_name} {event.client.last_name}\n"
            response += f"   🕐 {date_str}\n"
            if event.description:
                response += f"   📝 {event.description[:50]}...\n"
            response += "\n"
    else:
        response = "📅 Нет запланированных событий."
    
    keyboard = {
        "inline_keyboard": [
            [{"text": "⬅️ Назад к списку", "callback_data": "back_to_list"}]
        ]
    }
    
    edit_message(chat_id, message_id, response, reply_markup=keyboard)
    return True
