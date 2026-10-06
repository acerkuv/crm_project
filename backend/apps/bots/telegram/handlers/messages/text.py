# apps/bots/telegram/handlers/messages/text.py
from ..base import send_message, delete_message
from ...states import get_user_state, update_user_state, clear_user_state
from ...keyboards import get_main_reply_keyboard, get_cancel_reply_keyboard
from ..callbacks.events import handle_event_description_force
from apps.clients.models import Client, ScheduledEvent
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

def handle(chat_id, text_message):
    """Основной обработчик текстовых сообщений"""
    state = get_user_state(chat_id)
    
    if state.get('finding'):
        handle_find_text(chat_id, text_message)
        return
    
    if state.get('state') == 'waiting_for_event_description':
        handle_event_description(chat_id, text_message)
        return

    if state.get('state') == 'waiting_for_event_description_force':
        handle_event_description_force(chat_id, text_message)
        return
    
    handle_general_text(chat_id, text_message)

def handle_find_text(chat_id, text_message):
    """Обработка текста в режиме поиска"""
    from apps.clients.models import Client
    from django.db.models import Q
    
    # Получаем состояние
    state = get_user_state(chat_id)
    scheduled_date = state.get('scheduled_date')
    
    # Проверяем, не отмена ли это
    if text_message == "❌ Отмена":
        clear_user_state(chat_id)
        keyboard = get_main_reply_keyboard()
        send_message(chat_id, "🔍 Поиск отменен", reply_markup=keyboard)
        return
    
    clients = Client.objects.filter(
        Q(first_name__icontains=text_message) |
        Q(last_name__icontains=text_message) |
        Q(phone__icontains=text_message) |
        Q(company__icontains=text_message) |
        Q(email__icontains=text_message)
    )
    
    if clients.count() == 1:
        client = clients.first()
        
        # Если есть дата события - переходим к выбору типа
        if scheduled_date:
            from ...keyboards import get_plan_action_keyboard
            
            update_user_state(chat_id,
                client_id=client.id,
                scheduled_date=scheduled_date,
                state='selecting_action',
                finding=False
            )
            
            keyboard = get_plan_action_keyboard()
            response = (
                f"👤 *{client.first_name} {client.last_name}*\n"
                f"📞 {client.phone}\n"
                f"📅 {scheduled_date.strftime('%d.%m.%Y %H:%M')}\n\n"
                f"Выберите тип события:"
            )
            send_message(chat_id, response, reply_markup=keyboard)
        else:
            # Просто показываем карточку клиента
            from ...utils import get_client_card
            from ...keyboards import get_client_full_actions_keyboard
            
            card = get_client_card(client, show_avatar=False)
            keyboard = get_client_full_actions_keyboard(client.id)
            send_message(chat_id, card, reply_markup=keyboard)
            clear_user_state(chat_id)
            
    elif clients.count() > 1:
        response = "🔍 Найдено несколько клиентов:\n\n"
        for i, client in enumerate(clients[:5], 1):
            response += f"{i}. {client.first_name} {client.last_name} - {client.phone}\n"
        if clients.count() > 5:
            response += f"\n_и еще {clients.count() - 5} клиентов..._"
        response += "\n\nУточните запрос (введите номер телефона или полное имя)"
        send_message(chat_id, response)
    else:
        send_message(chat_id, "❌ Клиент не найден. Попробуйте еще раз или введите '❌ Отмена'")
        # Не очищаем состояние, чтобы можно было попробовать снова

def handle_event_description(chat_id, text_message):
    """Обработка описания события"""
    state = get_user_state(chat_id)
    
    # Проверяем, не отмена ли это
    if text_message == "❌ Отмена":
        clear_user_state(chat_id)
        keyboard = get_main_reply_keyboard()
        send_message(chat_id, "❌ Создание события отменено", reply_markup=keyboard)
        return
    
    client_id = state.get('client_id')
    action = state.get('action')
    scheduled_date = state.get('scheduled_date')
    
    if not client_id:
        send_message(chat_id, "⚠️ Ошибка: клиент не выбран. Попробуйте заново.")
        clear_user_state(chat_id)
        return
    
    if not action:
        send_message(chat_id, "⚠️ Ошибка: тип события не выбран. Попробуйте заново.")
        clear_user_state(chat_id)
        return
    
    if not scheduled_date:
        send_message(chat_id, "⚠️ Ошибка: дата события не указана. Попробуйте заново.")
        clear_user_state(chat_id)
        return
    
    client = Client.objects.filter(id=client_id).first()
    if not client:
        send_message(chat_id, "❌ Клиент не найден")
        clear_user_state(chat_id)
        return
    
    # ПРОВЕРКА: есть ли уже событие в это время
    existing_events = ScheduledEvent.objects.filter(
        scheduled_date=scheduled_date
    )
    
    if existing_events.exists():
        # Показываем, какие события уже есть в этом слоте
        text = f"⚠️ *Этот слот уже занят!*\n\n"
        text += f"📅 {scheduled_date.strftime('%d.%m.%Y %H:%M')}\n\n"
        text += "Уже запланированы события:\n"
        for event in existing_events:
            status = "✅" if event.is_completed else "🔴"
            text += f"{status} {event.client.first_name} {event.client.last_name} - {event.title}\n"
        
        text += f"\nХотите запланировать ещё одно событие на это же время?"
        
        keyboard = {
            "inline_keyboard": [
                [{"text": "✅ Да, запланировать", "callback_data": f"event_force_plan_{client_id}_{action}_{scheduled_date.timestamp()}"}],
                [{"text": "❌ Отмена", "callback_data": "plan_cancel"}]
            ]
        }
        send_message(chat_id, text, reply_markup=keyboard)
        return True
    
    # Создаем событие
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
            f"✅ Событие создано!\n\n"
            f"👤 {client.first_name} {client.last_name}\n"
            f"📝 {text_message}\n"
            f"📅 {scheduled_date.strftime('%d.%m.%Y %H:%M')}\n"
            f"📌 Тип: {action_names.get(action, 'событие')}\n\n"
            f"Я напомню вам об этом!"
        )
        
        clear_user_state(chat_id)
        keyboard = get_main_reply_keyboard()
        send_message(chat_id, response, reply_markup=keyboard)
        
        logger.info(f"✅ Создано событие #{event.id} для клиента {client.id} на {scheduled_date}")
        
    except Exception as e:
        logger.error(f"❌ Ошибка создания события: {e}")
        send_message(chat_id, f"❌ Ошибка при создании события: {str(e)}")

def handle_general_text(chat_id, text_message):
    """Обработка обычных текстовых сообщений"""
    # Проверяем, может это команда
    if text_message.startswith('/'):
        send_message(chat_id, f"Неизвестная команда: {text_message}\nИспользуйте /help для списка команд")
    else:
        # Отправляем в общий обработчик views.py
        from ...views import handle_text_message
        handle_text_message(chat_id, text_message)