from django.db.models import Q
from ..base import send_message
from ...states import clear_user_state, update_user_state
from ...keyboards import get_plan_action_keyboard
from apps.clients.models import Client

def handle(chat_id, text):
    """Обработчик команды /plan"""
    clear_user_state(chat_id)
    
    search_query = text.replace('/plan', '').strip()
    if not search_query:
        send_message(chat_id, "📝 Используйте: /plan [имя или телефон]")
        return True
    
    clients = Client.objects.filter(
        Q(first_name__icontains=search_query) |
        Q(last_name__icontains=search_query) |
        Q(phone__icontains=search_query)
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
    
    return True
