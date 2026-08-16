import json
import logging
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from django.conf import settings

from .handlers.base import send_message

# Импортируем обработчики команд из __init__.py
from .handlers.commands import (
    start as cmd_start,
    help as cmd_help,
    list_clients as cmd_list,
    stats as cmd_stats,
    add as cmd_add,
    find as cmd_find,
    birthdays as cmd_birthdays,
    plan as cmd_plan,
)

# Импортируем обработчики callback'ов
from .handlers.callbacks import *
from .handlers.messages import contact
from .handlers.messages.text import handle as text_handler
from .states import get_user_state, update_user_state, clear_user_state
from .keyboards import get_main_reply_keyboard

logger = logging.getLogger(__name__)

# Регистрация обработчиков callback'ов
CALLBACK_HANDLERS = {
    # Навигация
    'back_to_list': handle_back_to_list,
    'refresh_list': handle_refresh_list,
    'main_menu': handle_main_menu,
    'list_page_': handle_list_page,
    'list_letter_': handle_list_letter,
    'plan_cancel': handle_plan_cancel,
    
    # Статистика и дни рождения
    'show_stats': handle_show_stats,
    'show_birthdays': handle_show_birthdays,
    
    # События (календарь)
    'show_events_calendar': handle_show_events_calendar,
    'event_month_': handle_event_month,
    'event_today': handle_event_today,
    'event_day_': handle_event_day,
    'event_hour_': handle_event_hour,
    'event_hour_empty_': handle_event_hour_empty,
    'event_time_': handle_event_time,
    'event_empty_': handle_event_empty,
    'event_plan_at_': handle_event_plan_at,
    'event_back_to_day_': handle_event_back_to_day,
    'event_back_to_calendar_': handle_event_back_to_calendar,
    'event_complete_': handle_event_complete,
    'event_detail_': handle_event_detail,
    'event_hour_detail_': handle_event_hour_detail,
    'event_time_slot_': handle_event_time_slot,
    'event_plan_hour_': handle_event_plan_hour,
    'event_force_plan_': handle_event_force_plan,

    
    # Клиенты
    'client_detail_': handle_client_detail,
    'show_avatar_': handle_show_avatar,
    'plan_': handle_plan,
    'plan_action_': handle_plan_action,
    'action_': handle_action,
    
    # Календарь (планирование)
    'month_': handle_month,
    'day_': handle_day,
    'hour_': handle_hour,
    'minute_': handle_minute,
    'back_to_months': handle_back_to_months,
    'back_to_days': handle_back_to_days,
    'back_to_hours': handle_back_to_hours,

    'noop': lambda chat_id, message_id, data_callback: None,

}

def find_handler(callback_data):
    # Сортируем префиксы по длине (от длинных к коротким)
    # Это гарантирует, что 'plan_action_' будет проверяться перед 'action_'
    sorted_prefixes = sorted(CALLBACK_HANDLERS.items(), key=lambda x: len(x[0]), reverse=True)
    for prefix, handler in sorted_prefixes:
        if callback_data.startswith(prefix):
            logger.info(f"🔍 Найден обработчик для '{callback_data}': prefix='{prefix}', handler={handler.__name__}")
            return handler
    logger.warning(f"⚠️ Не найден обработчик для: {callback_data}")
    return None

@csrf_exempt
@require_POST
def webhook(request):
    try:
        data = json.loads(request.body.decode('utf-8'))
        logger.info(f"📨 Получен вебхук")
        
        token = settings.TELEGRAM_BOT_TOKEN
        if not token:
            return JsonResponse({'error': 'No token'}, status=400)
        
        # Обработка callback запросов
        if 'callback_query' in data:
            callback = data['callback_query']
            chat_id = callback['message']['chat']['id']
            message_id = callback['message']['message_id']
            data_callback = callback['data']
            
            logger.info(f"🔘 Нажата кнопка: {data_callback}")
            
            handler = find_handler(data_callback)
            if handler:
                handler(chat_id, message_id, data_callback)
            else:
                logger.warning(f"⚠️ Нет обработчика для: {data_callback}")
                send_message(chat_id, "⚠️ Ошибка: неизвестное действие")
            
            return JsonResponse({'status': 'ok'})
        
        # Обработка обычных сообщений
        if 'message' in data:
            message = data['message']
            chat_id = message['chat']['id']
            
            # Обработка контакта
            if 'contact' in message:
                contact(chat_id, message['contact'])
                return JsonResponse({'status': 'ok'})
            
            # Обработка текста
            if 'text' in message:
                text_message = message['text'].strip()
                logger.info(f"💬 Текст: {text_message}")
                
                # Проверяем FSM состояние
                state = get_user_state(chat_id)
                
                # Если в режиме поиска или ожидания описания - отправляем в text handler
                if state.get('finding') or state.get('state') == 'waiting_for_event_description':
                    text_handler(chat_id, text_message)
                    return JsonResponse({'status': 'ok'})
                
                # Если в режиме выбора клиента для события
                if state.get('state') == 'selecting_client_for_event':
                    from apps.clients.models import Client
                    from django.db.models import Q
                    
                    clients = Client.objects.filter(
                        Q(first_name__icontains=text_message) |
                        Q(last_name__icontains=text_message) |
                        Q(phone__icontains=text_message)
                    )
                    
                    if clients.count() == 1:
                        client = clients.first()
                        scheduled_date = state.get('scheduled_date')
                        
                        update_user_state(chat_id, 
                            client_id=client.id,
                            scheduled_date=scheduled_date,
                            state='selecting_action'
                        )
                        
                        from .keyboards import get_plan_action_keyboard
                        keyboard = get_plan_action_keyboard()
                        response = (
                            f"👤 *{client.first_name} {client.last_name}*\n"
                            f"📞 {client.phone}\n"
                            f"📅 {scheduled_date.strftime('%d.%m.%Y %H:%M')}\n\n"
                            f"Выберите тип события:"
                        )
                        send_message(chat_id, response, reply_markup=keyboard)
                        return JsonResponse({'status': 'ok'})
                    elif clients.count() > 1:
                        response = "🔍 Найдено несколько клиентов:\n\n"
                        for i, client in enumerate(clients[:5], 1):
                            response += f"{i}. {client.first_name} {client.last_name} - {client.phone}\n"
                        response += "\nУточните запрос"
                        send_message(chat_id, response)
                        return JsonResponse({'status': 'ok'})
                    else:
                        send_message(chat_id, "❌ Клиент не найден. Попробуйте еще раз")
                        return JsonResponse({'status': 'ok'})
                
                # Обработка нажатий на Reply Keyboard кнопки
                if text_message == "📋 Список":
                    cmd_list(chat_id, "/list")
                    return JsonResponse({'status': 'ok'})
                elif text_message == "🔍 Поиск":
                    # Проверяем, есть ли активная сессия планирования
                    state = get_user_state(chat_id)
                    scheduled_date = state.get('scheduled_date')
                    
                    # Если есть дата - сохраняем её в состоянии поиска
                    if scheduled_date:
                        update_user_state(chat_id, finding=True, scheduled_date=scheduled_date)
                    else:
                        update_user_state(chat_id, finding=True)
                    
                    send_message(chat_id, "🔍 Введите имя, телефон, компанию или email для поиска")
                    return JsonResponse({'status': 'ok'})
                
                elif text_message == "📅 События":
                    # Открываем календарь событий (просмотр)
                    from .handlers.callbacks.events import handle_show_events_calendar
                    handle_show_events_calendar(chat_id, None, None)
                    return JsonResponse({'status': 'ok'})

                    return JsonResponse({'status': 'ok'})
                elif text_message == "➕ Добавить":
                    cmd_add(chat_id, "/add")
                    return JsonResponse({'status': 'ok'})
                elif text_message == "📊 Статистика":
                    cmd_stats(chat_id, "/stats")
                    return JsonResponse({'status': 'ok'})
                elif text_message == "🎂 Дни рождения":
                    cmd_birthdays(chat_id, "/birthdays")
                    return JsonResponse({'status': 'ok'})
                elif text_message == "❓ Помощь":
                    cmd_help(chat_id, "/help")
                    return JsonResponse({'status': 'ok'})
                elif text_message == "❌ Отмена":
                    clear_user_state(chat_id)
                    keyboard = get_main_reply_keyboard()
                    send_message(chat_id, "❌ Действие отменено", reply_markup=keyboard)
                    return JsonResponse({'status': 'ok'})
                
                # Разбиваем команду и аргументы
                parts = text_message.split(' ', 1)
                command = parts[0] if parts else text_message
                
                # Обработка команд через словарь
                command_handlers = {
                    '/start': cmd_start,
                    '/help': cmd_help,
                    '/list': cmd_list,
                    '/stats': cmd_stats,
                    '/add': cmd_add,
                    '/find': cmd_find,
                    '/birthdays': cmd_birthdays,
                    '/plan': cmd_plan,
                }
                
                if command in command_handlers:
                    command_handlers[command](chat_id, text_message)
                else:
                    if text_message.startswith('/'):
                        send_message(chat_id, f"Неизвестная команда: {text_message}\nИспользуйте /help для списка команд")
                    else:
                        send_message(chat_id, f"Получено: {text_message}")
                
                return JsonResponse({'status': 'ok'})
        
        return JsonResponse({'status': 'ok'})
        
    except Exception as e:
        logger.error(f"❌ Ошибка: {e}")
        return JsonResponse({'error': str(e)}, status=400)