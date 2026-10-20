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



class TelegramBot(PhotosMixin, CommandsMixin, ClientsMixin, EventsMixin):
    def __init__(self):
        self.token = settings.TELEGRAM_BOT_TOKEN
        logger.info("🤖 Бот инициализирован")

    # ============ КОМАНДЫ ============

    async def button_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        data = query.data
        logger.info(f"🔘 callback: {data}")

        try:
            await self._button_handler_impl(update, context)
        except Exception as e:
            logger.error(f"❌ Ошибка в button_handler для '{data}': {e}", exc_info=True)
            try:
                await query.answer(f"❌ {type(e).__name__}: {str(e)[:150]}", show_alert=True)
            except Exception:
                pass
            
    async def _button_handler_impl(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        data = query.data

        if data == 'noop':
            await query.answer()
            return

        if data == 'main_menu':
            await self._handle_main_menu(update, context)
            return

        if data == 'back_to_list' or data == 'refresh_list':
            await self._handle_back_to_list(update, context)
            return

        if data.startswith('list_page_'):
            page = int(data.split('_')[2])
            await self._handle_list_page(update, context, page)
            return

        if data.startswith('list_letter_'):
            letter = data.split('_')[2]
            await self._handle_list_letter(update, context, letter)
            return

        if data.startswith('client_detail_'):
            client_id = int(data.split('_')[2])
            await self._handle_client_detail(update, context, client_id)
            return

        if data.startswith('client_'):
            client_id = int(data.split('_')[1])
            await self.show_client_actions(update, context, client_id)
            return

        if data.startswith('action_'):
            parts = data.split('_')
            client_id = int(parts[1])
            action_type = parts[2]
            await self._handle_action(update, context, client_id, action_type)
            return

        if data.startswith('show_avatar_'):
            client_id = int(data.split('_')[2])
            await self._handle_show_avatar(update, context, client_id)
            return

        if data.startswith('plan_action_'):
            action_type = data.replace('plan_action_', '')
            await self._handle_plan_action(update, context, action_type)
            return

        if data.startswith('plan_'):
            client_id = int(data.split('_')[1])
            await self._handle_plan_start(update, context, client_id)
            return

        if data == 'plan_cancel':
            await self._handle_plan_cancel(update, context)
            return

        if data.startswith('month_'):
            parts = data.split('_')
            await self._handle_month(update, context, int(parts[1]), int(parts[2]))
            return

        if data.startswith('day_'):
            parts = data.split('_')
            if len(parts) > 4 and parts[4] == 'past':
                await query.answer('❌ Нельзя выбрать прошедшую дату!', show_alert=True)
                return
            await self._handle_day(update, context, int(parts[1]), int(parts[2]), int(parts[3]))
            return

        if data.startswith('hour_'):
            hour = int(data.split('_')[1])
            await self._handle_hour(update, context, hour)
            return

        if data.startswith('minute_'):
            parts = data.split('_')
            await self._handle_minute(update, context, int(parts[1]), int(parts[2]))
            return

        if data == 'back_to_months':
            await self._handle_back_to_months(update, context)
            return

        if data == 'back_to_days':
            await self._handle_back_to_days(update, context)
            return

        if data == 'back_to_hours':
            await self._handle_back_to_hours(update, context)
            return

        if data == 'show_stats':
            await self._handle_show_stats(update, context)
            return

        if data == 'show_birthdays':
            await self._handle_show_birthdays(update, context)
            return

        if data == 'show_events' or data == 'show_events_calendar':
            await self._handle_show_events_calendar(update, context)
            return

        if data.startswith('event_month_'):
            parts = data.split('_')
            await self._handle_event_month(update, context, int(parts[2]), int(parts[3]))
            return

        if data == 'event_today':
            await self._handle_event_today(update, context)
            return

        if data.startswith('event_day_'):
            parts = data.split('_')
            await self._handle_event_day(update, context, int(parts[2]), int(parts[3]), int(parts[4]))
            return

        if data.startswith('event_hour_empty_'):
            parts = data.split('_')
            await self._handle_event_hour_empty(update, context, int(parts[3]), int(parts[4]), int(parts[5]), int(parts[6]))
            return

        if data.startswith('event_hour_'):
            parts = data.split('_')
            await self._handle_event_hour(update, context, int(parts[2]), int(parts[3]), int(parts[4]), int(parts[5]))
            return

        if data.startswith('event_time_slot_'):
            parts = data.split('_')
            await self._handle_event_time_slot(update, context, int(parts[3]), int(parts[4]), int(parts[5]), int(parts[6]), int(parts[7]))
            return

        if data.startswith('event_detail_'):
            event_id = int(data.split('_')[2])
            await self._handle_event_detail(update, context, event_id)
            return

        if data.startswith('event_complete_'):
            event_id = int(data.split('_')[2])
            await self._handle_event_complete(update, context, event_id)
            return

        if data.startswith('event_plan_at_'):
            parts = data.split('_')
            day = int(parts[3]); month = int(parts[4]); year = int(parts[5])
            hour = int(parts[6]) if len(parts) > 6 else 9
            minute = int(parts[7]) if len(parts) > 7 else 0
            await self._handle_event_plan_at(update, context, day, month, year, hour, minute)
            return

        if data.startswith('event_back_to_calendar_'):
            parts = data.split('_')
            await self._handle_event_back_to_calendar(update, context, int(parts[4]), int(parts[5]))
            return

        if data.startswith('event_back_to_day_'):
            parts = data.split('_')
            await self._handle_event_back_to_day(update, context, int(parts[4]), int(parts[5]), int(parts[6]))
            return

        if data.startswith('year_'):
            year = int(data.split('_')[1])
            await self._handle_year(update, context, year)
            return

        if data == 'find_client':
            await self.find(update, context)
            return

        if data == 'add_client':
            await self.add(update, context)
            return

        if data == 'show_help':
            await self.help(update, context)
            return

        if data == 'save_contact':
            await self.handle_save_contact(update, context)
            return

        if data == 'cancel_contact':
            await self.handle_cancel_contact(update, context)
            return

        if data in ['birthday_auto', 'birthday_manual']:
            await self.handle_birthday_choice(update, context)
            return

        if data.startswith('send_birthday_') or data.startswith('schedule_birthday_'):
            await self.handle_birthday_action(update, context)
            return

        logger.warning(f"⚠️ Необработанный callback: {data}")
        await query.answer("⚠️ Действие не поддерживается", show_alert=False)

    # ============ ЗАГЛУШКИ (до Части 3-4) ============

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


# ============ МОДУЛЬНЫЕ ФУНКЦИИ ============

    except Exception as e:
        logger.error(f"Ошибка отправки: {e}")