import logging
import os
import base64
import json
import tempfile
from io import BytesIO
from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    ReplyKeyboardMarkup,
    KeyboardButton,
)
from telegram.ext import (
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ConversationHandler,
    ContextTypes,
    filters,
)
from django.conf import settings
from django.utils import timezone
from django.core.mail import send_mail
from apps.clients.models import Client, Interaction, ScheduledEvent
from apps.events.models import Event
from datetime import datetime, timedelta
import requests
import json as json_lib
import uuid

from .handlers.photos import PhotosMixin
from .handlers.commands import CommandsMixin
from .handlers.clients import ClientsMixin
from .handlers.events import EventsMixin
from .handlers.callbacks import CallbacksMixin
from .handlers.helpers import main_reply_markup

from apps.bots.telegram.keyboards import (
    get_main_menu_keyboard,
    get_main_reply_keyboard,
    get_cancel_reply_keyboard,
    get_letters_keyboard,
    get_plan_action_keyboard,
    get_client_full_actions_keyboard,
    get_client_compact_keyboard,
    get_months_keyboard,
    get_days_keyboard,
    get_hours_keyboard,
    get_minutes_keyboard,
    get_events_calendar_keyboard,
    get_event_day_keyboard,
    get_event_list_keyboard,
    get_event_time_list_keyboard,
    MONTHS_RU,
)
from apps.bots.telegram.time_utils import (
    USER_TIMEZONE,
    to_user_time,
    format_user_time,
    create_user_datetime,
)
from apps.bots.telegram.utils import get_client_card, get_clients_list_message, NGROK_URL
from django.db.models import Q

logger = logging.getLogger(__name__)

(
    SELECTING_CLIENT,
    SELECTING_ACTION,
    ENTERING_EVENT_DESCRIPTION,
    ENTERING_EVENT_DATETIME,
    SELECTING_REMINDER_TYPE,
    CONFIRMING_EVENT,
    ENTERING_BIRTHDAY_MESSAGE,
) = range(7)

(
    EMAIL_SUBJECT,
    EMAIL_BODY,
) = range(7, 9)



class TelegramBot(PhotosMixin, CommandsMixin, ClientsMixin, EventsMixin, CallbacksMixin):
    def __init__(self):
        self.token = settings.TELEGRAM_BOT_TOKEN
        logger.info("🤖 Бот инициализирован")

    # ============ КОМАНДЫ ============

    def run_polling(self):
        from telegram.ext import Application

        logger.info("🚀 Запуск бота в режиме polling...")

        proxy_url = os.environ.get('TELEGRAM_PROXY_URL', '')
        builder = Application.builder().token(self.token)
        if proxy_url:
            logger.info(f"🔗 Использую прокси: {proxy_url}")
            builder = builder.proxy(proxy_url).get_updates_proxy(proxy_url)

        app = builder.build()

        app.add_handler(CommandHandler("start", self.start))
        app.add_handler(CommandHandler("help", self.help))
        app.add_handler(CommandHandler("list", self.list_command))
        app.add_handler(CommandHandler("find", self.find))
        app.add_handler(CommandHandler("events", self.events))
        app.add_handler(CommandHandler("birthdays", self.birthdays))
        app.add_handler(CommandHandler("stats", self.stats))
        app.add_handler(CommandHandler("add", self.add))
        app.add_handler(CommandHandler("avatar", self.avatar))

        app.add_handler(CallbackQueryHandler(self.button_handler))
        app.add_handler(MessageHandler(filters.CONTACT, self.handle_contact))
        app.add_handler(MessageHandler(filters.PHOTO, self.handle_photo))
        app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_text))

        logger.info("✅ Бот запущен, начинаю polling...")
        app.run_polling(allowed_updates=Update.ALL_TYPES)

