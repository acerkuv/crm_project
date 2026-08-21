from ..base import send_message
from apps.users.models import TelegramUser
from django.contrib.auth.models import User

def handle(chat_id, text):
    """Обработчик команды /id - показывает Telegram ID пользователя"""
    
    # Проверяем, зарегистрирован ли пользователь
    try:
        telegram_user = TelegramUser.objects.get(telegram_id=str(chat_id))
        user = telegram_user.user
        
        response = (
            f"🤖 *Ваш Telegram ID:* `{chat_id}`\n\n"
            f"👤 *Имя:* {telegram_user.first_name}\n"
            f"📝 *Username:* @{telegram_user.username or 'не указан'}\n"
            f"👔 *Роль:* {telegram_user.get_role_display()}\n"
            f"📅 *Зарегистрирован:* {telegram_user.created_at.strftime('%d.%m.%Y %H:%M')}\n\n"
            f"💡 *Используйте этот ID для входа в веб-версию CRM*"
        )
        
    except TelegramUser.DoesNotExist:
        # Пользователь не зарегистрирован
        response = (
            f"🤖 *Ваш Telegram ID:* `{chat_id}`\n\n"
            f"⚠️ *Вы не зарегистрированы в системе!*\n\n"
            f"📝 Для регистрации отправьте команду:\n"
            f"`/register {chat_id}`\n\n"
            f"Или обратитесь к администратору."
        )
    
    send_message(chat_id, response, parse_mode='Markdown')
