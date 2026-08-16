import logging
import requests
from django.conf import settings
from django.utils import timezone
from datetime import datetime, timedelta
from apps.clients.models import Client, ScheduledEvent
from .states import user_states, clear_user_state, get_user_state, update_user_state
from .keyboards import *
from .utils import get_client_card, get_clients_list_message, action_names

logger = logging.getLogger(__name__)

def send_message(chat_id, text, reply_markup=None, parse_mode='Markdown'):
    """Утилита для отправки сообщений"""
    token = settings.TELEGRAM_BOT_TOKEN
    url = f'https://api.telegram.org/bot{token}/sendMessage'
    data = {
        'chat_id': chat_id,
        'text': text,
        'parse_mode': parse_mode
    }
    if reply_markup:
        data['reply_markup'] = reply_markup
    return requests.post(url, json=data)

def delete_message(chat_id, message_id):
    """Удаление сообщения"""
    token = settings.TELEGRAM_BOT_TOKEN
    url = f'https://api.telegram.org/bot{token}/deleteMessage'
    try:
        requests.post(url, json={'chat_id': chat_id, 'message_id': message_id})
    except:
        pass

def answer_callback(callback_id, text=None, show_alert=False):
    """Ответ на callback"""
    token = settings.TELEGRAM_BOT_TOKEN
    url = f'https://api.telegram.org/bot{token}/answerCallbackQuery'
    data = {'callback_query_id': callback_id}
    if text:
        data['text'] = text
        data['show_alert'] = show_alert
    return requests.post(url, json=data)

def edit_message(chat_id, message_id, text, reply_markup=None):
    """Редактирование сообщения"""
    token = settings.TELEGRAM_BOT_TOKEN
    url = f'https://api.telegram.org/bot{token}/editMessageText'
    data = {
        'chat_id': chat_id,
        'message_id': message_id,
        'text': text,
        'parse_mode': 'Markdown'
    }
    if reply_markup:
        data['reply_markup'] = reply_markup
    return requests.post(url, json=data)

def send_photo(chat_id, photo_url, caption=None, reply_markup=None):
    """Отправка фото"""
    token = settings.TELEGRAM_BOT_TOKEN
    url = f'https://api.telegram.org/bot{token}/sendPhoto'
    data = {
        'chat_id': chat_id,
        'photo': photo_url,
        'parse_mode': 'Markdown'
    }
    if caption:
        data['caption'] = caption
    if reply_markup:
        data['reply_markup'] = reply_markup
    return requests.post(url, json=data)

# ============ ОБРАБОТЧИКИ КОМАНД ============

def handle_start(chat_id, text):
    """Обработчик команды /start"""
    clear_user_state(chat_id)
    response = "👋 Привет! Я CRM бот для управления клиентами.\n\nИспользуйте /help для списка команд."
    send_message(chat_id, response)

def handle_help(chat_id, text):
    """Обработчик команды /help"""
    response = (
        "📖 *Доступные команды:*\n\n"
        "/start - Приветствие\n"
        "/help - Справка\n"
        "/add - Добавить клиента\n"
        "/list - Список клиентов\n"
        "/find - Найти клиента\n"
        "/stats - Статистика\n"
        "/plan - Запланировать событие\n\n"
        "💡 *Интерактивный режим:*\n"
        "/list - показывает карточки с кнопками"
    )
    send_message(chat_id, response)

def handle_list(chat_id, text):
    """Обработчик команды /list"""
    clients = Client.objects.all().order_by('-created_at')
    message_text, keyboard = get_clients_list_message(clients, 1)
    send_message(chat_id, message_text, reply_markup=keyboard)

def handle_stats(chat_id, text):
    """Обработчик команды /stats"""
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
    send_message(chat_id, response)

def handle_add(chat_id, text):
    """Обработчик команды /add"""
    response = "📇 Отправьте контакт, чтобы добавить клиента\n\nНажмите на скрепку → Контакт"
    send_message(chat_id, response)

def handle_find(chat_id, text):
    """Обработчик команды /find"""
    response = "🔍 Введите имя или телефон для поиска"
    send_message(chat_id, response)

def handle_birthdays(chat_id, text):
    """Обработчик команды /birthdays"""
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
    
    send_message(chat_id, response)

def handle_plan(chat_id, text):
    """Обработчик команды /plan"""
    clear_user_state(chat_id)
    
    search_query = text.replace('/plan', '').strip()
    if not search_query:
        send_message(chat_id, "📝 Используйте: /plan [имя или телефон]")
        return
    
    clients = Client.objects.filter(
        first_name__icontains=search_query
    ) | Client.objects.filter(
        last_name__icontains=search_query
    ) | Client.objects.filter(
        phone__icontains=search_query
    )
    
    if clients.count() == 1:
        client = clients.first()
        update_user_state(chat_id, client_id=client.id, state='selecting_action')
        
        keyboard = get_plan_action_keyboard()
        response = (
            f"👤 *{client.first_name} {client.last_name}*\n"
            f"📞 {client.phone}\n\n"
            f"Выберите тип события:"
        )
        send_message(chat_id, response, reply_markup=keyboard)
        
    elif clients.count() > 1:
        response = "🔍 Найдено несколько клиентов:\n\n"
        for i, client in enumerate(clients[:5], 1):
            response += f"{i}. {client.first_name} {client.last_name} - {client.phone}\n"
        response += "\nУточните запрос: /plan [имя или телефон]"
        send_message(chat_id, response)
    else:
        send_message(chat_id, "❌ Клиент не найден")

def handle_contact(chat_id, contact):
    """Обработка контакта"""
    phone = contact.get('phone_number', '')
    first_name = contact.get('first_name', '')
    last_name = contact.get('last_name', '')
    telegram_id = str(chat_id)
    
    client, created = Client.objects.get_or_create(
        phone=phone,
        defaults={
            'first_name': first_name,
            'last_name': last_name or '',
            'telegram_id': telegram_id,
            'status': 'lead'
        }
    )
    
    if created:
        response = f"✅ Клиент добавлен!\n\n👤 {client.first_name} {client.last_name}\n📞 {client.phone}"
    else:
        response = f"ℹ️ Клиент уже существует:\n\n👤 {client.first_name} {client.last_name}\n📞 {client.phone}"
    
    send_message(chat_id, response)

def handle_text_input(chat_id, text):
    """Обработка текстового ввода (для FSM)"""
    state = get_user_state(chat_id)
    
    if state.get('state') == 'waiting_for_event_description':
        # Сохраняем описание события
        update_user_state(chat_id, description=text, state='selecting_month')
        
        keyboard = get_months_keyboard()
        response = "📅 *Выберите месяц:*"
        send_message(chat_id, response, reply_markup=keyboard)
        return True
    
    return False

# ============ ОБРАБОТЧИКИ CALLBACK ============

def handle_callback(chat_id, message_id, data_callback):
    """Главный обработчик callback'ов"""
    
    # Отвечаем на callback
    answer_callback(data_callback.split('_')[0] if '_' in data_callback else data_callback)
    
    # NOOP
    if data_callback == 'noop':
        return True
    
    # Отмена
    if data_callback == 'plan_cancel':
        clear_user_state(chat_id)
        send_message(chat_id, "❌ Планирование отменено")
        delete_message(chat_id, message_id)
        return True
    
    # Показать аватарку
    if data_callback.startswith('show_avatar_'):
        client_id = int(data_callback.split('_')[2])
        client = Client.objects.filter(id=client_id).first()
        
        if client and client.avatar and client.avatar.name:
            from .utils import NGROK_URL
            avatar_url = f"{NGROK_URL}{client.avatar.url}"
            caption = f"🖼️ *Аватарка*\n👤 {client.first_name} {client.last_name}"
            send_photo(chat_id, avatar_url, caption)
        else:
            send_message(chat_id, "❌ У клиента нет аватарки")
        return True
    
    # Обновить список
    if data_callback == 'refresh_list':
        clients = Client.objects.all().order_by('-created_at')
        message_text, keyboard = get_clients_list_message(clients, 1)
        edit_message(chat_id, message_id, message_text, reply_markup=keyboard)
        return True
    
    # Главное меню
    if data_callback == 'main_menu':
        keyboard = get_main_menu_keyboard()
        edit_message(chat_id, message_id, "🏠 *Главное меню*\n\nВыберите действие:", reply_markup=keyboard)
        return True
    
    # Пагинация
    if data_callback.startswith('list_page_'):
        page = int(data_callback.split('_')[2])
        clients = Client.objects.all().order_by('-created_at')
        message_text, keyboard = get_clients_list_message(clients, page)
        edit_message(chat_id, message_id, message_text, reply_markup=keyboard)
        return True
    
    # Назад к списку
    if data_callback == 'back_to_list':
        clients = Client.objects.all().order_by('-created_at')
        message_text, keyboard = get_clients_list_message(clients, 1)
        edit_message(chat_id, message_id, message_text, reply_markup=keyboard)
        return True
    
    # Подробнее о клиенте
    if data_callback.startswith('client_detail_'):
        client_id = int(data_callback.split('_')[2])
        client = Client.objects.filter(id=client_id).first()
        
        if client:
            keyboard = get_client_full_actions_keyboard(client_id)
            card_text = get_client_card(client, show_avatar=False)
            card_text += "\n\n_Выберите действие:_"
            
            if client.avatar and client.avatar.name:
                from .utils import NGROK_URL
                avatar_url = f"{NGROK_URL}{client.avatar.url}"
                delete_message(chat_id, message_id)
                send_photo(chat_id, avatar_url, card_text, reply_markup=keyboard)
            else:
                edit_message(chat_id, message_id, card_text, reply_markup=keyboard)
        return True
    
    # Планирование
    if data_callback.startswith('plan_'):
        client_id = int(data_callback.split('_')[1])
        client = Client.objects.filter(id=client_id).first()
        
        if client:
            update_user_state(chat_id, client_id=client_id, state='selecting_action')
            delete_message(chat_id, message_id)
            
            keyboard = get_plan_action_keyboard()
            response = (
                f"👤 *{client.first_name} {client.last_name}*\n"
                f"📞 {client.phone}\n\n"
                f"Выберите тип события:"
            )
            send_message(chat_id, response, reply_markup=keyboard)
        return True
    
    # Выбор типа события
    if data_callback.startswith('plan_action_'):
        action_type = data_callback.replace('plan_action_', '')
        state = get_user_state(chat_id)
        client_id = state.get('client_id')
        
        if client_id:
            client = Client.objects.filter(id=client_id).first()
            if client:
                update_user_state(chat_id, action=action_type, state='waiting_for_event_description')
                delete_message(chat_id, message_id)
                
                action_names_dict = action_names()
                response = (
                    f"✅ Вы выбрали: {action_names_dict.get(action_type, 'событие')}\n\n"
                    f"👤 {client.first_name} {client.last_name}\n\n"
                    f"📝 Введите описание события:"
                )
                send_message(chat_id, response)
        return True
    
    # Действия с клиентом
    if data_callback.startswith('action_'):
        parts = data_callback.split('_')
        client_id = int(parts[1])
        action_type = parts[2]
        
        client = Client.objects.filter(id=client_id).first()
        if client:
            update_user_state(chat_id, client_id=client_id, action=action_type, state='waiting_for_event_description')
            delete_message(chat_id, message_id)
            
            action_names_dict = action_names()
            response = (
                f"✅ Вы выбрали: {action_names_dict.get(action_type, 'действие')}\n\n"
                f"👤 {client.first_name} {client.last_name}\n\n"
                f"📝 Введите описание:"
            )
            send_message(chat_id, response)
        return True
    
    # Календарь: выбор месяца
    if data_callback.startswith('month_'):
        parts = data_callback.split('_')
        month = int(parts[1])
        year = int(parts[2])
        
        update_user_state(chat_id, selected_month=month, selected_year=year)
        keyboard = get_days_keyboard(month, year)
        edit_message(chat_id, message_id, f"📅 *Выберите день:*\n{MONTHS_RU[month]} {year}", reply_markup=keyboard)
        return True
    
    # Календарь: выбор дня
    if data_callback.startswith('day_'):
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
    
    # Календарь: выбор часа
    if data_callback.startswith('hour_'):
        hour = int(data_callback.split('_')[1])
        
        update_user_state(chat_id, selected_hour=hour, state='selecting_minute')
        keyboard = get_minutes_keyboard(hour)
        edit_message(chat_id, message_id, f"🕐 *Выберите минуты:*\n⏰ {hour:02d}:00", reply_markup=keyboard)
        return True
    
    # Календарь: выбор минут (финальный шаг)
    if data_callback.startswith('minute_'):
        parts = data_callback.split('_')
        hour = int(parts[1])
        minute = int(parts[2])
        
        state = get_user_state(chat_id)
        
        if 'selected_day' in state and 'selected_month' in state and 'selected_year' in state:
            day = state['selected_day']
            month = state['selected_month']
            year = state['selected_year']
            
            scheduled_date = datetime(year, month, day, hour, minute)
            
            if scheduled_date < datetime.now():
                answer_callback(parts[0], '❌ Нельзя выбрать прошедшее время!', show_alert=True)
                return True
            
            client_id = state.get('client_id')
            client = Client.objects.filter(id=client_id).first()
            
            if client:
                action = state.get('action', 'custom')
                action_names_dict = action_names()
                
                event = ScheduledEvent.objects.create(
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
                    f"📌 Тип: {action_names_dict.get(action, 'событие')}\n\n"
                    f"Я напомню вам об этом!"
                )
                
                delete_message(chat_id, message_id)
                send_message(chat_id, response)
                clear_user_state(chat_id)
            else:
                send_message(chat_id, "❌ Клиент не найден")
        else:
            send_message(chat_id, "❌ Ошибка: данные неполные")
        
        return True
    
    # Возврат к месяцам
    if data_callback == 'back_to_months':
        keyboard = get_months_keyboard()
        edit_message(chat_id, message_id, "📅 *Выберите месяц:*", reply_markup=keyboard)
        return True
    
    # Возврат к дням
    if data_callback == 'back_to_days':
        state = get_user_state(chat_id)
        month = state.get('selected_month', datetime.now().month)
        year = state.get('selected_year', datetime.now().year)
        
        keyboard = get_days_keyboard(month, year)
        edit_message(chat_id, message_id, f"📅 *Выберите день:*\n{MONTHS_RU[month]} {year}", reply_markup=keyboard)
        return True
    
    # Возврат к часам
    if data_callback == 'back_to_hours':
        keyboard = get_hours_keyboard()
        edit_message(chat_id, message_id, "🕐 *Выберите час:*", reply_markup=keyboard)
        return True
    
    return False
