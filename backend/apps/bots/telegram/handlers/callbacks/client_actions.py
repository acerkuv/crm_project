from ..base import send_message, delete_message, send_photo, edit_message, answer_callback
from ...states import get_user_state, update_user_state, clear_user_state
from ...keyboards import get_client_full_actions_keyboard, get_plan_action_keyboard, get_cancel_reply_keyboard
from ...utils import get_client_card, NGROK_URL
from apps.clients.models import Client, ScheduledEvent
import logging

logger = logging.getLogger(__name__)

def handle_client_detail(chat_id, message_id, data_callback):
    """Показать подробную карточку клиента"""
    # Извлекаем client_id из data_callback
    if isinstance(data_callback, str) and data_callback.startswith('client_detail_'):
        client_id = int(data_callback.split('_')[2])
    else:
        client_id = int(data_callback)
    
    client = Client.objects.filter(id=client_id).first()
    if not client:
        send_message(chat_id, "❌ Клиент не найден")
        return True
    
    keyboard = get_client_full_actions_keyboard(client.id)
    card_text = get_client_card(client, show_avatar=False)
    card_text += "\n\n_Выберите действие:_"
    
    if client.avatar and client.avatar.name:
        avatar_url = f"{NGROK_URL}{client.avatar.url}"
        delete_message(chat_id, message_id)
        send_photo(chat_id, avatar_url, card_text, reply_markup=keyboard)
    else:
        edit_message(chat_id, message_id, card_text, reply_markup=keyboard)
    return True

def handle_show_avatar(chat_id, message_id, data_callback):
    """Показать аватарку клиента"""
    client_id = int(data_callback.split('_')[2])
    client = Client.objects.filter(id=client_id).first()
    
    if client and client.avatar and client.avatar.name:
        avatar_url = f"{NGROK_URL}{client.avatar.url}"
        caption = f"🖼️ *Аватарка*\n👤 {client.first_name} {client.last_name}"
        send_photo(chat_id, avatar_url, caption)
    else:
        send_message(chat_id, "❌ У клиента нет аватарки")
    return True

def handle_plan(chat_id, message_id, data_callback):
    """Начать планирование для клиента"""
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
    else:
        send_message(chat_id, "❌ Клиент не найден")
    return True

def handle_plan_action(chat_id, message_id, data_callback):
    """Выбор типа события"""
    # Извлекаем тип действия из callback_data
    # Формат: plan_action_reminder, plan_action_call, etc.
    action_type = data_callback.replace('plan_action_', '')
    
    state = get_user_state(chat_id)
    client_id = state.get('client_id')
    scheduled_date = state.get('scheduled_date')
    
    if not client_id:
        send_message(chat_id, "⚠️ Сессия истекла. Начните заново.")
        clear_user_state(chat_id)
        return True
    
    client = Client.objects.filter(id=client_id).first()
    if not client:
        send_message(chat_id, "❌ Клиент не найден")
        clear_user_state(chat_id)
        return True
    
    action_names = {
        'call': '📞 звонок',
        'meeting': '📅 встречу',
        'birthday': '🎂 поздравление',
        'reminder': '🔔 напоминание',
        'custom': '📝 событие'
    }
    
    # Обновляем состояние
    update_user_state(
        chat_id, 
        action=action_type,
        client_id=client_id,
        scheduled_date=scheduled_date,
        state='waiting_for_event_description'
    )
    
    # Удаляем сообщение с кнопками
    delete_message(chat_id, message_id)
    
    response = (
        f"✅ Вы выбрали: {action_names.get(action_type, 'событие')}\n\n"
        f"👤 {client.first_name} {client.last_name}\n"
        f"📅 {scheduled_date.strftime('%d.%m.%Y %H:%M') if scheduled_date else 'Не указано'}\n\n"
        f"📝 Введите описание события (или нажмите '❌ Отмена'):"
    )
    
    # Отправляем сообщение с кнопкой отмены
    keyboard = get_cancel_reply_keyboard()
    send_message(chat_id, response, reply_markup=keyboard)
    
    logger.info(f"📝 Ожидаем описание события для клиента {client.id}, тип: {action_type}")
    return True

def handle_action(chat_id, message_id, data_callback):
    """Быстрые действия с клиентом (позвонить, заметка)"""
    parts = data_callback.split('_')
    client_id = int(parts[1])
    action_type = parts[2]
    
    client = Client.objects.filter(id=client_id).first()
    if not client:
        send_message(chat_id, "❌ Клиент не найден")
        return True
    
    action_names = {
        'call': '📞 звонок',
        'note': '📝 заметку',
        'meeting': '📅 встречу'
    }
    
    update_user_state(chat_id, client_id=client_id, action=action_type, state='waiting_for_event_description')
    delete_message(chat_id, message_id)
    
    response = (
        f"✅ Вы выбрали: {action_names.get(action_type, 'действие')}\n\n"
        f"👤 {client.first_name} {client.last_name}\n\n"
        f"📝 Введите описание:"
    )
    send_message(chat_id, response)
    return True