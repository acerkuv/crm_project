from ..base import send_message
from ...keyboards import get_main_reply_keyboard

def handle(chat_id, text):
    """Обработчик команды /help с Reply Keyboard"""
    reply_keyboard = get_main_reply_keyboard()
    
    response = (
        "📖 *Доступные команды:*\n\n"
        "/start - Приветствие\n"
        "/help - Справка\n"
        "/add - Добавить клиента\n"
        "/list - Список клиентов\n"
        "/find [текст] - Поиск клиента\n"
        "/stats - Статистика\n"
        "/plan [имя] - Запланировать событие\n"
        "/birthdays - Дни рождения\n\n"
        "💡 *Примеры:*\n"
        "/list - все клиенты\n"
        "/list А - клиенты на букву 'А'\n"
        "/find 567 - поиск по номеру\n"
        "/find Анна - поиск по имени\n"
        "/plan Анна - план события для Анны\n\n"
        "📱 *Используйте кнопки ниже для быстрого доступа!*"
    )
    
    send_message(chat_id, response, reply_markup=reply_keyboard)
    return True
