from ..base import send_message
from apps.users.models import TelegramUser, LoginCode
from django.utils import timezone
import random
import logging

logger = logging.getLogger(__name__)

def handle(chat_id, text):
    """Обработчик команды /login - получить код для входа в веб-версию"""
    
    try:
        telegram_user = TelegramUser.objects.get(telegram_id=str(chat_id))
        code = ''.join(random.choices('0123456789', k=6))
        
        LoginCode.objects.filter(
            telegram_user=telegram_user,
            is_used=False,
            expires_at__lt=timezone.now()
        ).delete()
        
        LoginCode.objects.create(
            telegram_user=telegram_user,
            code=code,
            expires_at=timezone.now() + timezone.timedelta(minutes=5)
        )
        
        response = (
            "🔑 *Ваш код для входа в CRM:*\n\n"
            f"`{code}`\n\n"
            "⏰ Код действителен 5 минут\n"
            "Введите этот код на странице входа в веб-версии CRM.\n\n"
            "Если вы не запрашивали код, проигнорируйте это сообщение."
        )
        
        send_message(chat_id, response, parse_mode='Markdown')
        logger.info(f"Код входа для {chat_id}: {code}")
        
    except TelegramUser.DoesNotExist:
        response = (
            "❌ *Вы не зарегистрированы в системе!*\n\n"
            "Для регистрации отправьте команду:\n"
            "`/register`\n\n"
            "Или обратитесь к администратору."
        )
        send_message(chat_id, response, parse_mode='Markdown')
