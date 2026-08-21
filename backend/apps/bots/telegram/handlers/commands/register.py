from ..base import send_message
from apps.users.models import TelegramUser
from apps.clients.models import Client
from django.contrib.auth.models import User
from django.utils import timezone
import logging

logger = logging.getLogger(__name__)

def handle(chat_id, text):
    """Обработчик команды /register - регистрация пользователя"""
    
    # Проверяем, зарегистрирован ли уже в TelegramUser
    existing = TelegramUser.objects.filter(telegram_id=str(chat_id)).first()
    if existing:
        send_message(
            chat_id,
            f"✅ Вы уже зарегистрированы!\n\n"
            f"👤 Имя: {existing.first_name}\n"
            f"🆔 ID: {existing.telegram_id}\n\n"
            f"Используйте /login для входа в веб-версию."
        )
        return
    
    # Проверяем, есть ли пользователь с таким telegram_id в Client
    existing_client = Client.objects.filter(telegram_id=str(chat_id)).first()
    if existing_client and existing_client.user:
        # Если есть клиент, но нет TelegramUser - создаём связь
        try:
            telegram_user = TelegramUser.objects.create(
                user=existing_client.user,
                telegram_id=str(chat_id),
                first_name=existing_client.first_name,
                last_name=existing_client.last_name or "",
                role='owner',
                is_active=True
            )
            send_message(
                chat_id,
                f"✅ *Связь с существующим аккаунтом установлена!*\n\n"
                f"👤 Имя: {telegram_user.first_name}\n"
                f"🆔 ID: {telegram_user.telegram_id}\n\n"
                f"🎉 Добро пожаловать в CRM Уют!\n"
                f"Используйте /login для входа в веб-версию.",
                parse_mode='Markdown'
            )
            return
        except Exception as e:
            logger.error(f"Ошибка создания TelegramUser: {e}")
    
    try:
        # Создаём нового пользователя
        username = f"tg{chat_id}"
        
        # Проверяем, существует ли пользователь с таким username
        if User.objects.filter(username=username).exists():
            username = f"tg{chat_id}_{int(timezone.now().timestamp())}"
        
        user = User.objects.create_user(
            username=username,
            password=None,
            first_name="Пользователь",
            last_name=""
        )
        
        # Создаём профиль Telegram
        telegram_user = TelegramUser.objects.create(
            user=user,
            telegram_id=str(chat_id),
            username=f"user_{chat_id}",
            first_name="Пользователь",
            last_name="",
            role='owner',
            is_active=True
        )
        
        # Создаём клиента (владельца)
        client = Client.objects.create(
            user=user,
            first_name="Пользователь",
            last_name="",
            phone="",
            telegram_id=str(chat_id),
            status='vip'
        )
        
        send_message(
            chat_id,
            f"✅ *Регистрация успешна!*\n\n"
            f"👤 Имя: {telegram_user.first_name}\n"
            f"🆔 ID: {telegram_user.telegram_id}\n"
            f"👔 Роль: Владелец\n\n"
            f"🎉 Добро пожаловать в CRM Уют!\n"
            f"Используйте /login для входа в веб-версию.",
            parse_mode='Markdown'
        )
        
        logger.info(f"✅ Зарегистрирован новый пользователь: {chat_id}")
        
    except Exception as e:
        logger.error(f"❌ Ошибка регистрации: {e}")
        send_message(
            chat_id,
            f"❌ Ошибка регистрации: {str(e)}\n\n"
            f"Обратитесь к администратору."
        )
