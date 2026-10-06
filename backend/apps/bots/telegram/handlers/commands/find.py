from ..base import send_message
from ...states import update_user_state, clear_user_state, get_user_state
from ...utils import get_client_card
from ...keyboards import get_client_compact_keyboard
from apps.clients.models import Client
from django.db.models import Q

def handle(chat_id, text):
    """Обработчик команды /find с выдачей карточек с кнопками"""
    
    # Проверяем, есть ли активная сессия планирования
    state = get_user_state(chat_id)
    scheduled_date = state.get('scheduled_date')

    # Если есть дата - сохраняем её
    if scheduled_date:
        update_user_state(chat_id, finding=True, scheduled_date=scheduled_date)
    else:
        update_user_state(chat_id, finding=True)
    
    # Проверяем, есть ли аргументы в команде
    parts = text.split(' ', 1)
    
    if len(parts) > 1:
        # Если есть аргумент - ищем сразу
        search_query = parts[1].strip()
        clients = Client.objects.filter(
            Q(first_name__icontains=search_query) |
            Q(last_name__icontains=search_query) |
            Q(phone__icontains=search_query) |
            Q(company__icontains=search_query) |
            Q(email__icontains=search_query) |
            Q(comment__icontains=search_query)
        )
        
        if clients.exists():
            # Если есть дата и найден 1 клиент - сразу переходим к выбору действия
            if scheduled_date and clients.count() == 1:
                client = clients.first()
                from ...keyboards import get_plan_action_keyboard
                
                update_user_state(chat_id,
                    client_id=client.id,
                    scheduled_date=scheduled_date,
                    state='selecting_action'
                )
                
                keyboard = get_plan_action_keyboard()
                response = (
                    f"👤 *{client.first_name} {client.last_name}*\n"
                    f"📞 {client.phone}\n"
                    f"📅 {scheduled_date.strftime('%d.%m.%Y %H:%M')}\n\n"
                    f"Выберите тип события:"
                )
                send_message(chat_id, response, reply_markup=keyboard)
                return True
            
            # Иначе показываем список клиентов
            total = clients.count()
            header = f"🔍 *Результаты поиска по запросу '{search_query}'* (найдено {total})"
            send_message(chat_id, header)
            
            # Отправляем каждого клиента отдельным сообщением с кнопками
            for client in clients[:10]:
                card = get_client_card(client, show_avatar=False, compact=True)
                keyboard = get_client_compact_keyboard(client.id)
                send_message(chat_id, card, reply_markup=keyboard)
            
            if total > 10:
                send_message(chat_id, f"_и еще {total - 10} клиентов..._\n\nУточните запрос для более точного поиска")
            
            clear_user_state(chat_id)
        else:
            response = "❌ Клиент не найден.\n\nПопробуйте другой запрос или используйте /find без аргументов для поиска по шагам."
            send_message(chat_id, response)
        
        return True
    
    # Если аргументов нет - переходим в режим поиска
    # Сохраняем scheduled_date если есть
    if scheduled_date:
        update_user_state(chat_id, finding=True, scheduled_date=scheduled_date)
    else:
        update_user_state(chat_id, finding=True)
    
    response = "🔍 Введите имя, телефон, компанию или email для поиска"
    send_message(chat_id, response)
    return True