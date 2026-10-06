from ..base import send_message

def handle(chat_id, text):
    """Обработчик команды /add"""
    response = "📇 Отправьте контакт, чтобы добавить клиента\n\nНажмите на скрепку → Контакт"
    send_message(chat_id, response)
    return True
