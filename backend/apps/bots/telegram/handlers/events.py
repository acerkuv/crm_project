"""Mixin: планирование событий, дни рождения, календарь."""
import logging
from datetime import datetime

import requests
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, ConversationHandler
from django.conf import settings
from django.utils import timezone
from asgiref.sync import sync_to_async

from apps.clients.models import Client, ScheduledEvent
from ..keyboards import (
    get_plan_action_keyboard,
    get_months_keyboard,
    get_days_keyboard,
    get_hours_keyboard,
    get_minutes_keyboard,
    get_cancel_reply_keyboard,
    get_events_calendar_keyboard,
    MONTHS_RU,
)
from ..time_utils import create_user_datetime
from .helpers import main_reply_markup

logger = logging.getLogger(__name__)


class EventsMixin:
    """Планирование событий, дни рождения, календарь."""

    # ============ ПЛАНИРОВАНИЕ СОБЫТИЙ ============

    async def start_event_planning(self, update: Update, context: ContextTypes.DEFAULT_TYPE, client_id, action_type):
        from asgiref.sync import sync_to_async

        query = update.callback_query
        await query.answer()

        context.user_data['planning_client_id'] = client_id
        context.user_data['planning_action_type'] = action_type

        client = await sync_to_async(Client.objects.get)(id=client_id)

        action_names = {
            'call': 'звонок',
            'message': 'сообщение',
            'birthday': 'поздравление',
            'meeting': 'встречу',
            'reminder': 'напоминание',
            'note': 'заметку',
        }

        if action_type == 'birthday' and client.birth_date:
            keyboard = [
                [InlineKeyboardButton("🎂 Поздравить автоматически", callback_data="birthday_auto")],
                [InlineKeyboardButton("✍️ Написать самому", callback_data="birthday_manual")],
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await query.edit_message_text(
                f"🎂 *Поздравление для {client.first_name}*\n\n"
                f"📅 День рождения: {client.birth_date.strftime('%d.%m.%Y')}\n\n"
                "Выберите способ поздравления:",
                parse_mode='Markdown',
                reply_markup=reply_markup,
            )
            return ConversationHandler.END

        await query.edit_message_text(
            f"📝 Введите описание {action_names.get(action_type, 'события')} для {client.first_name}:"
        )
        return ConversationHandler.END

    # ============ ДНИ РОЖДЕНИЯ ============

    async def handle_birthday_choice(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        from asgiref.sync import sync_to_async

        query = update.callback_query
        await query.answer()

        client_id = context.user_data.get('planning_client_id')
        client = await sync_to_async(Client.objects.get)(id=client_id)

        if query.data == 'birthday_auto':
            await query.edit_message_text(
                f"🤖 *Генерация поздравления для {client.first_name}...*\n\n"
                "Искусственный интеллект создает персонализированное поздравление...\n"
                "Пожалуйста, подождите ⏳"
            )
            greeting = await self.generate_ai_greeting(client)
            scheduled_date = client.birth_date.replace(year=timezone.now().year)
            if scheduled_date < timezone.now().date():
                scheduled_date = scheduled_date.replace(year=timezone.now().year + 1)

            event = await sync_to_async(ScheduledEvent.objects.create)(
                client=client,
                title=f"Поздравление с ДР: {client.first_name}",
                description=greeting,
                event_type='birthday',
                scheduled_date=datetime.combine(scheduled_date, timezone.now().time()),
                is_ai_generated=True,
                ai_content=greeting,
            )
            keyboard = [
                [InlineKeyboardButton("📤 Отправить сейчас", callback_data=f"send_birthday_{event.id}")],
                [InlineKeyboardButton("📅 Запланировать", callback_data=f"schedule_birthday_{event.id}")],
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await query.edit_message_text(
                f"🎉 *Поздравление для {client.first_name}*\n\n"
                f"{greeting}\n\n"
                f"📅 Дата: {scheduled_date.strftime('%d.%m.%Y')}\n"
                f"🤖 Сгенерировано ИИ\n\n"
                "Выберите действие:",
                parse_mode='Markdown',
                reply_markup=reply_markup,
            )
        elif query.data == 'birthday_manual':
            await query.edit_message_text(
                f"✍️ *Напишите текст поздравления для {client.first_name}*\n\n"
                "Я запомню его и отправлю в день рождения.\n"
                "Можно использовать переменные:\n"
                "{{first_name}} - имя\n"
                "{{last_name}} - фамилия\n"
                "{{company}} - компания"
            )
            context.user_data['awaiting_birthday_text'] = True
        return ConversationHandler.END

    async def save_birthday_text(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        from asgiref.sync import sync_to_async

        text = update.message.text
        client_id = context.user_data.get('planning_client_id')
        client = await sync_to_async(Client.objects.get)(id=client_id)

        scheduled_date = client.birth_date.replace(year=timezone.now().year)
        if scheduled_date < timezone.now().date():
            scheduled_date = scheduled_date.replace(year=timezone.now().year + 1)

        event = await sync_to_async(ScheduledEvent.objects.create)(
            client=client,
            title=f"Поздравление с ДР: {client.first_name}",
            description=text,
            event_type='birthday',
            scheduled_date=datetime.combine(scheduled_date, timezone.now().time()),
            is_ai_generated=False,
            ai_content=text,
        )
        keyboard = [
            [InlineKeyboardButton("📤 Отправить сейчас", callback_data=f"send_birthday_{event.id}")],
            [InlineKeyboardButton("📅 Запланировать", callback_data=f"schedule_birthday_{event.id}")],
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text(
            f"✅ *Поздравление сохранено!*\n\n"
            f"👤 {client.first_name} {client.last_name}\n"
            f"📅 Дата отправки: {scheduled_date.strftime('%d.%m.%Y')}\n\n"
            f"📝 Текст:\n{text}\n\n"
            "Выберите действие:",
            parse_mode='Markdown',
            reply_markup=reply_markup,
        )
        context.user_data['awaiting_birthday_text'] = False

    async def handle_birthday_action(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        from asgiref.sync import sync_to_async

        query = update.callback_query
        await query.answer()

        event_id = int(query.data.split('_')[-1])
        event = await sync_to_async(ScheduledEvent.objects.get)(id=event_id)

        if query.data.startswith('send_birthday'):
            if event.client.telegram_id:
                await send_telegram_message(
                    event.client.telegram_id,
                    f"🎉 *Поздравление!*\n\n{event.description}",
                )
                event.is_completed = True
                event.completed_at = timezone.now()
                await sync_to_async(event.save)()
                await query.edit_message_text("✅ Поздравление отправлено!")
            else:
                await query.edit_message_text(
                    "❌ У клиента нет Telegram ID.\n"
                    "Сохраните событие как напоминание."
                )
        elif query.data.startswith('schedule_birthday'):
            await query.edit_message_text(
                f"✅ Поздравление запланировано на {event.scheduled_date.strftime('%d.%m.%Y')}\n\n"
                f"👤 {event.client.first_name} {event.client.last_name}\n"
                f"📝 {event.description}"
            )

    async def generate_ai_greeting(self, client):
        try:
            if settings.OPENAI_API_KEY:
                from openai import AsyncOpenAI
                openai_client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
                prompt = f"""
                Создай персонализированное поздравление с днем рождения для {client.first_name} {client.last_name}.
                {"Он/она работает в " + client.company if client.company else ""}
                {"Должность: " + client.position if client.position else ""}
                {"Интересы: " + client.comment[:100] if client.comment else ""}

                Поздравление должно быть:
                - Тёплым и искренним
                - Персонализированным
                - Коротким (3-4 предложения)
                """
                response = await openai_client.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=[{"role": "user", "content": prompt}],
                    max_tokens=150,
                    temperature=0.7,
                )
                return response.choices[0].message.content
        except Exception as e:
            logger.error(f"Ошибка генерации ИИ: {e}")
        return f"🎉 Дорогой(ая) {client.first_name}! Поздравляю с днём рождения! Желаю счастья, здоровья и успехов во всех начинаниях! 🎂"

    # ============ ПЛАНИРОВАНИЕ: ТИП СОБЫТИЯ ============

    async def _handle_plan_start(self, update: Update, context: ContextTypes.DEFAULT_TYPE, client_id: int):
        """Показать типы событий для клиента."""
        query = update.callback_query
        await query.answer()

        context.user_data['planning_client_id'] = client_id

        def _get():
            return Client.objects.filter(id=client_id).first()

        client = await sync_to_async(_get)()
        if not client:
            await query.edit_message_text("❌ Клиент не найден")
            return

        keyboard = get_plan_action_keyboard()
        await query.edit_message_text(
            f"👤 *{client.first_name} {client.last_name}*\n"
            f"📞 {client.phone}\n\n"
            f"Выберите тип события:",
            parse_mode='Markdown',
            reply_markup=keyboard,
        )

    async def _handle_plan_action(self, update: Update, context: ContextTypes.DEFAULT_TYPE, action_type: str):
        """Сохранить тип события и запросить описание."""
        query = update.callback_query
        await query.answer()

        context.user_data['planning_action_type'] = action_type

        client_id = context.user_data.get('planning_client_id')

        def _get():
            return Client.objects.filter(id=client_id).first()

        client = await sync_to_async(_get)()
        if not client:
            await query.edit_message_text("❌ Клиент не найден")
            return

        action_names = {
            'call': '📞 звонок',
            'meeting': '📅 встречу',
            'birthday': '🎂 поздравление',
            'reminder': '🔔 напоминание',
            'custom': '📝 событие',
        }

        await query.edit_message_text(
            f"✅ Вы выбрали: {action_names.get(action_type, 'событие')}\n\n"
            f"👤 {client.first_name} {client.last_name}\n\n"
            f"📝 Введите описание события:"
        )
        context.user_data['awaiting_event_description'] = True

    async def _handle_plan_cancel(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        for key in ('awaiting_event_description', 'planning_client_id',
                    'planning_action_type', 'event_description_client_id',
                    'event_description_action', 'event_description_text',
                    'event_scheduled_date'):
            context.user_data.pop(key, None)
        await update.callback_query.answer("Отменено", show_alert=False)

    # ============ КАЛЕНДАРЬ ПЛАНИРОВАНИЯ ============

    async def _handle_month(self, update: Update, context: ContextTypes.DEFAULT_TYPE, month: int, year: int):
        """Выбор месяца."""
        query = update.callback_query
        await query.answer()

        context.user_data['planning_month'] = month
        context.user_data['planning_year'] = year

        keyboard = get_days_keyboard(month, year)
        await query.edit_message_text(
            f"📅 *Выберите день:*\n{MONTHS_RU[month]} {year}",
            parse_mode='Markdown',
            reply_markup=keyboard,
        )

    async def _handle_day(self, update: Update, context: ContextTypes.DEFAULT_TYPE, day: int, month: int, year: int):
        """Выбор дня."""
        query = update.callback_query
        await query.answer()

        context.user_data['planning_day'] = day
        context.user_data['planning_month'] = month
        context.user_data['planning_year'] = year

        keyboard = get_hours_keyboard()
        await query.edit_message_text(
            f"🕐 *Выберите час:*\n📅 {day} {MONTHS_RU[month]} {year}",
            parse_mode='Markdown',
            reply_markup=keyboard,
        )

    async def _handle_hour(self, update: Update, context: ContextTypes.DEFAULT_TYPE, hour: int):
        """Выбор часа."""
        query = update.callback_query
        await query.answer()

        context.user_data['planning_hour'] = hour

        keyboard = get_minutes_keyboard(hour)
        await query.edit_message_text(
            f"🕐 *Выберите минуты:*\n⏰ {hour:02d}:00",
            parse_mode='Markdown',
            reply_markup=keyboard,
        )

    async def _handle_minute(self, update: Update, context: ContextTypes.DEFAULT_TYPE, hour: int, minute: int):
        """Выбор минут + создание ScheduledEvent."""
        query = update.callback_query
        await query.answer()

        day = context.user_data.get('planning_day')
        month = context.user_data.get('planning_month')
        year = context.user_data.get('planning_year')
        action = context.user_data.get('planning_action_type', 'custom')
        client_id = context.user_data.get('planning_client_id')
        description = context.user_data.get('event_description_text', '')

        if not all([day, month, year, client_id]):
            await query.edit_message_text("❌ Ошибка: данные неполные")
            return

        # Создаём aware datetime в UTC
        try:
            scheduled_date = create_user_datetime(year, month, day, hour, minute)
        except Exception as e:
            await query.edit_message_text(f"❌ Ошибка даты: {e}")
            return

        def _get_client():
            return Client.objects.filter(id=client_id).first()

        client = await sync_to_async(_get_client)()
        if not client:
            await query.edit_message_text("❌ Клиент не найден")
            return

        try:
            event = await sync_to_async(ScheduledEvent.objects.create)(
                client=client,
                title=description[:100] if description else 'Событие',
                description=description or 'Событие',
                event_type=action,
                scheduled_date=scheduled_date,
                is_completed=False,
            )

            action_names = {
                'call': '📞 звонок',
                'meeting': '📅 встречу',
                'birthday': '🎂 поздравление',
                'reminder': '🔔 напоминание',
                'custom': '📝 событие',
            }

            await query.edit_message_text(
                f"✅ *Событие запланировано!*\n\n"
                f"👤 {client.first_name} {client.last_name}\n"
                f"📝 {description or 'Событие'}\n"
                f"📅 {scheduled_date.strftime('%d.%m.%Y %H:%M')}\n"
                f"📌 Тип: {action_names.get(action, 'событие')}\n\n"
                f"Я напомню вам об этом!",
                parse_mode='Markdown',
            )
        except Exception as e:
            logger.error(f"Ошибка создания события: {e}", exc_info=True)
            await query.edit_message_text(f"❌ Ошибка создания события: {e}")

        # Очищаем состояние
        for key in ('planning_client_id', 'planning_action_type',
                    'planning_day', 'planning_month', 'planning_year',
                    'planning_hour', 'event_description_text'):
            context.user_data.pop(key, None)

    async def _handle_back_to_months(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        await query.answer()
        keyboard = get_months_keyboard()
        await query.edit_message_text(
            "📅 *Выберите месяц:*",
            parse_mode='Markdown',
            reply_markup=keyboard,
        )

    async def _handle_back_to_days(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        await query.answer()
        month = context.user_data.get('planning_month', datetime.now().month)
        year = context.user_data.get('planning_year', datetime.now().year)
        keyboard = get_days_keyboard(month, year)
        await query.edit_message_text(
            f"📅 *Выберите день:*\n{MONTHS_RU[month]} {year}",
            parse_mode='Markdown',
            reply_markup=keyboard,
        )

    async def _handle_back_to_hours(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        await query.answer()
        keyboard = get_hours_keyboard()
        await query.edit_message_text(
            "🕐 *Выберите час:*",
            parse_mode='Markdown',
            reply_markup=keyboard,
        )

    async def _handle_year(self, update: Update, context: ContextTypes.DEFAULT_TYPE, year: int):
        query = update.callback_query
        await query.answer()
        context.user_data['planning_year'] = year
        keyboard = get_months_keyboard()
        await query.edit_message_text(
            f"📅 *{year}*\nВыберите месяц:",
            parse_mode='Markdown',
            reply_markup=keyboard,
        )

    # ============ ЗАГЛУШКИ (календарь событий — Шаг 4.5) ============

    async def _handle_event_month(self, update, context, month, year):
        await update.callback_query.answer("⚠️ Скоро", show_alert=True)

    async def _handle_event_today(self, update, context):
        await update.callback_query.answer("⚠️ Скоро", show_alert=True)

    async def _handle_event_day(self, update, context, day, month, year):
        await update.callback_query.answer("⚠️ Скоро", show_alert=True)

    async def _handle_event_hour(self, update, context, day, month, year, hour):
        await update.callback_query.answer("⚠️ Скоро", show_alert=True)

    async def _handle_event_hour_empty(self, update, context, day, month, year, hour):
        await update.callback_query.answer("⚠️ Скоро", show_alert=True)

    async def _handle_event_time_slot(self, update, context, day, month, year, hour, minute):
        await update.callback_query.answer("⚠️ Скоро", show_alert=True)

    async def _handle_event_detail(self, update, context, event_id):
        await update.callback_query.answer("⚠️ Скоро", show_alert=True)

    async def _handle_event_complete(self, update, context, event_id):
        await update.callback_query.answer("⚠️ Скоро", show_alert=True)

    async def _handle_event_plan_at(self, update, context, day, month, year, hour=9, minute=0):
        await update.callback_query.answer("⚠️ Скоро", show_alert=True)

    async def _handle_event_back_to_calendar(self, update, context, month, year):
        await update.callback_query.answer("⚠️ Скоро", show_alert=True)

    async def _handle_event_back_to_day(self, update, context, day, month, year):
        await update.callback_query.answer("⚠️ Скоро", show_alert=True)


# ============ МОДУЛЬНЫЕ ФУНКЦИИ ============

async def send_telegram_message(chat_id, text):
    """Отправка сообщения в Telegram (для поздравлений)."""
    token = settings.TELEGRAM_BOT_TOKEN
    if not token:
        return
    url = f'https://api.telegram.org/bot{token}/sendMessage'
    try:
        requests.post(url, json={
            'chat_id': chat_id,
            'text': text,
            'parse_mode': 'Markdown',
        })
    except Exception as e:
        logger.error(f"Ошибка отправки: {e}")