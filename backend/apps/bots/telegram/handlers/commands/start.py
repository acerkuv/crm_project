from ..base import send_message, send_reply_keyboard
from ...states import clear_user_state
from ...keyboards import get_main_reply_keyboard

def handle(chat_id, text):
    """Обработчик команды /start с Reply Keyboard"""
    clear_user_state(chat_id)
    
    # Получаем Reply Keyboard
    reply_keyboard = get_main_reply_keyboard()
    
    response = (
        "👋 Привет! Я CRM бот для управления клиентами.\n\n"
        "Используйте кнопки ниже или команды:\n"
        "/help - список всех команд"
    )
    
    send_message(chat_id, response, reply_markup=reply_keyboard)
    return True
