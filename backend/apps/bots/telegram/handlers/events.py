"""Mixin: планирование событий, дни рождения, календарь."""
import logging
from datetime import datetime
from ..time_utils import to_user_time

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
            from apps.bots.telegram.birthday_utils import next_birthday as _nb
            scheduled_date = _nb(client.birth_date, timezone.now().date())

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
        text = update.message.text
        client_id = context.user_data.get('planning_client_id')
        client = await sync_to_async(Client.objects.get)(id=client_id)

        from apps.bots.telegram.birthday_utils import next_birthday as _nb
        scheduled_date = _nb(client.birth_date, timezone.now().date())

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
        query = update.callback_query
        await query.answer()

        event_id = int(query.data.split('_')[-1])
        event = await sync_to_async(ScheduledEvent.objects.get)(id=event_id)

        if query.data.startswith('send_birthday'):
            if event.client.telegram_id:
                ok = await sync_to_async(_tg_send_message_sync)(
                    event.client.telegram_id,
                    f"🎉 *Поздравление!*\n\n{event.description}",
                )
                if not ok:
                    await query.edit_message_text("❌ Не удалось отправить (см. логи)")
                    return
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
                f"✅ Поздравление запланировано на {to_user_time(event.scheduled_date).strftime('%d.%m.%Y')}\n\n"
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
                    'event_scheduled_date', 'event_editing'):
            context.user_data.pop(key, None)
        await update.callback_query.answer("Отменено", show_alert=False)

    # ============ КАЛЕНДАРЬ ПЛАНИРОВАНИЯ ============

    async def _handle_month(self, update: Update, context: ContextTypes.DEFAULT_TYPE, month: int, year: int):
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

        try:
            scheduled_date = create_user_datetime(year, month, day, hour, minute)
        except Exception as e:
            await query.edit_message_text(f"❌ Ошибка даты: {e}")
            return
        from ..validators import ensure_future_or_reply
        if not await ensure_future_or_reply(query, scheduled_date):
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
                f"📅 {to_user_time(scheduled_date).strftime('%d.%m.%Y %H:%M')}\n"
                f"📌 Тип: {action_names.get(action, 'событие')}\n\n"
                f"Я напомню вам об этом!",
                parse_mode='Markdown',
            )
        except Exception as e:
            logger.error(f"Ошибка создания события: {e}", exc_info=True)
            await query.edit_message_text(f"❌ Ошибка создания события: {e}")

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

    # ============ КАЛЕНДАРЬ СОБЫТИЙ ============

    async def _handle_event_month(self, update, context, month, year):
        query = update.callback_query
        await query.answer()
        keyboard = get_events_calendar_keyboard(month, year)
        text = f"📅 *Календарь событий*\n{MONTHS_RU[month]} {year}\n\n• — есть события"
        try:
            await query.edit_message_text(text, parse_mode='Markdown', reply_markup=keyboard)
        except Exception as e:
            logger.error(f"Ошибка показа календаря: {e}")

    async def _handle_event_today(self, update, context):
        query = update.callback_query
        await query.answer()
        today = datetime.now()
        keyboard = get_events_calendar_keyboard(today.month, today.year)
        text = f"📅 *Календарь событий*\n{MONTHS_RU[today.month]} {today.year}\n\n• — есть события"
        try:
            await query.edit_message_text(text, parse_mode='Markdown', reply_markup=keyboard)
        except Exception as e:
            logger.error(f"Ошибка показа календаря: {e}")

    async def _handle_event_day(self, update, context, day, month, year):
        from ..keyboards import get_event_day_keyboard
        query = update.callback_query
        await query.answer()
        keyboard = get_event_day_keyboard(day, month, year)
        text = f"📅 *{day} {MONTHS_RU[month]} {year}*\n\nВыберите время:"
        try:
            await query.edit_message_text(text, parse_mode='Markdown', reply_markup=keyboard)
        except Exception as e:
            logger.error(f"Ошибка показа дня: {e}")

    async def _handle_event_hour(self, update, context, day, month, year, hour):
        from ..keyboards import get_event_time_list_keyboard
        from ..time_utils import to_user_time
        query = update.callback_query
        await query.answer()

        def _get_events():
            from datetime import timedelta
            start = create_user_datetime(year, month, day, hour, 0)
            end = start + timedelta(hours=1)
            return list(ScheduledEvent.objects.filter(
                scheduled_date__gte=start, scheduled_date__lt=end,
            ).order_by('scheduled_date'))

        events = await sync_to_async(_get_events)()
        events_by_time = {}
        for e in events:
            ut = to_user_time(e.scheduled_date)
            key = ut.strftime('%H:%M')
            events_by_time.setdefault(key, []).append(e)

        if not events:
            keyboard = get_event_day_keyboard(day, month, year)
            text = f"📅 *{day} {MONTHS_RU[month]} {year}*\n\nНет событий в {hour:02d}:00"
            try:
                await query.edit_message_text(text, parse_mode='Markdown', reply_markup=keyboard)
            except Exception as e:
                logger.error(f"Ошибка: {e}")
            return

        time_str = f"{hour:02d}:00"
        keyboard = get_event_time_list_keyboard(events_by_time, time_str, day, month, year)
        text = f"📅 *События {day} {MONTHS_RU[month]} {year} в {hour:02d}:00*\n\n"
        for time_key in sorted(events_by_time.keys()):
            for e in events_by_time[time_key]:
                status = "✅" if e.is_completed else "🔴"
                text += f"{status} {time_key} — {e.title}\n"
        try:
            await query.edit_message_text(text, parse_mode='Markdown', reply_markup=keyboard)
        except Exception as e:
            logger.error(f"Ошибка: {e}")

    async def _handle_event_hour_empty(self, update, context, day, month, year, hour):
        from ..keyboards import get_event_day_keyboard
        query = update.callback_query
        await query.answer()
        keyboard = get_event_day_keyboard(day, month, year)
        text = f"📅 *{day} {MONTHS_RU[month]} {year}*\n\nВыберите время:"
        try:
            await query.edit_message_text(text, parse_mode='Markdown', reply_markup=keyboard)
        except Exception as e:
            logger.error(f"Ошибка: {e}")

    async def _handle_event_time_slot(self, update, context, day, month, year, hour, minute):
        query = update.callback_query
        await query.answer()

        def _get_events():
            from datetime import timedelta
            start = create_user_datetime(year, month, day, hour, minute)
            end = start + timedelta(minutes=15)
            return list(ScheduledEvent.objects.filter(
                scheduled_date__gte=start, scheduled_date__lt=end,
            ).order_by('scheduled_date'))

        events = await sync_to_async(_get_events)()
        time_str = f"{hour:02d}:{minute:02d}"

        keyboard = []
        if events:
            text = f"📅 *{day} {MONTHS_RU[month]} {year} в {time_str}*\n\n"
            text += f"🔴 Занято: {len(events)} событий\n\n"
            for e in events:
                status = "✅" if e.is_completed else "🔴"
                text += f"{status} *{e.title}*\n"
                text += f"   👤 {e.client.first_name} {e.client.last_name}\n"
                if e.description:
                    text += f"   📝 {e.description[:80]}\n"
                text += "\n"
                keyboard.append([InlineKeyboardButton(
                    f"🔍 {e.title[:30]}", callback_data=f"event_detail_{e.id}"
                )])
            keyboard.append([InlineKeyboardButton(
                "➕ Запланировать ещё",
                callback_data=f"event_plan_at_{day}_{month}_{year}_{hour}_{minute}"
            )])
        else:
            text = f"📅 *{day} {MONTHS_RU[month]} {year} в {time_str}*\n\n⬜ Свободно"
            keyboard.append([InlineKeyboardButton(
                "➕ Запланировать",
                callback_data=f"event_plan_at_{day}_{month}_{year}_{hour}_{minute}"
            )])

        keyboard.append([
            InlineKeyboardButton("⬅️ К дню", callback_data=f"event_back_to_day_{day}_{month}_{year}"),
            InlineKeyboardButton("📅 Календарь", callback_data=f"event_back_to_calendar_{month}_{year}"),
        ])
        keyboard.append([InlineKeyboardButton("🏠 Главное меню", callback_data="main_menu")])

        reply_markup = InlineKeyboardMarkup(inline_keyboard=keyboard)
        try:
            await query.edit_message_text(text, parse_mode='Markdown', reply_markup=reply_markup)
        except Exception as e:
            logger.error(f"Ошибка слота: {e}")

    async def _handle_event_detail(self, update, context, event_id):
        query = update.callback_query
        await query.answer()

        def _get():
            return ScheduledEvent.objects.filter(id=event_id).first()

        event = await sync_to_async(_get)()
        if not event:
            await query.edit_message_text("❌ Событие не найдено")
            return

        from ..time_utils import to_user_time
        ut = to_user_time(event.scheduled_date)
        time_str = ut.strftime('%d.%m.%Y %H:%M')
        if event.is_completed:
            status = "✅ Отправлено" if event.event_type == 'birthday' else "✅ Выполнено"
        else:
            status = "⏳ Ожидает отправки" if event.event_type == 'birthday' else "⏳ Ожидает"

        text = (
            f"📌 *{event.title}*\n\n"
            f"👤 {event.client.first_name} {event.client.last_name}\n"
            f"📞 {event.client.phone}\n"
            f"📅 {time_str}\n"
            f"📊 {status}\n"
        )
        if event.description:
            text += f"\n📝 {event.description}\n"

        keyboard = []
        if event.event_type == 'birthday' and event.client and event.client.telegram_id and not event.is_completed:
            keyboard.append([InlineKeyboardButton(
                "📤 Отправить поздравление сейчас",
                callback_data=f"event_send_birthday_{event.id}"
            )])
        if not event.is_completed:
            keyboard.append([InlineKeyboardButton(
                "✅ Отметить выполненным", callback_data=f"event_complete_{event.id}"
            )])
        keyboard.append([InlineKeyboardButton(
            "✏️ Изменить", callback_data=f"event_edit_menu_{event.id}"
        )])
        keyboard.append([InlineKeyboardButton(
            "🗑 Удалить", callback_data=f"event_delete_confirm_{event.id}"
        )])
        keyboard.append([
            InlineKeyboardButton("⬅️ К дню", callback_data=f"event_back_to_day_{ut.day}_{ut.month}_{ut.year}"),
            InlineKeyboardButton("📅 Календарь", callback_data=f"event_back_to_calendar_{ut.month}_{ut.year}"),
        ])
        keyboard.append([InlineKeyboardButton("🏠 Главное меню", callback_data="main_menu")])

        reply_markup = InlineKeyboardMarkup(inline_keyboard=keyboard)
        try:
            await query.edit_message_text(text, parse_mode='Markdown', reply_markup=reply_markup)
        except Exception as e:
            logger.error(f"Ошибка деталей: {e}")

    async def _handle_event_complete(self, update, context, event_id):
        query = update.callback_query
        await query.answer("✅ Событие выполнено")

        def _complete():
            event = ScheduledEvent.objects.filter(id=event_id).first()
            if event:
                event.is_completed = True
                event.completed_at = timezone.now()
                event.save()
            return event

        event = await sync_to_async(_complete)()
        if not event:
            await query.edit_message_text("❌ Событие не найдено")
            return

        from ..time_utils import to_user_time
        ut = to_user_time(event.scheduled_date)
        text = (
            f"✅ *Выполнено*\n\n"
            f"📌 {event.title}\n"
            f"👤 {event.client.first_name} {event.client.last_name}\n"
            f"📅 {ut.strftime('%d.%m.%Y %H:%M')}"
        )
        keyboard = [
            [InlineKeyboardButton("⬅️ К дню", callback_data=f"event_back_to_day_{ut.day}_{ut.month}_{ut.year}")],
            [InlineKeyboardButton("🏠 Главное меню", callback_data="main_menu")],
        ]
        reply_markup = InlineKeyboardMarkup(inline_keyboard=keyboard)
        try:
            await query.edit_message_text(text, parse_mode='Markdown', reply_markup=reply_markup)
        except Exception as e:
            logger.error(f"Ошибка: {e}")

    async def _handle_event_send_birthday(self, update, context, event_id):
        query = update.callback_query
        await query.answer()

        def _get():
            return ScheduledEvent.objects.filter(id=event_id).select_related('client').first()

        event = await sync_to_async(_get)()
        if not event:
            await query.edit_message_text("❌ Событие не найдено")
            return
        if not (event.client and event.client.telegram_id):
            await query.edit_message_text("❌ У клиента нет Telegram ID — отправьте вручную.")
            return
        if event.is_completed:
            await query.edit_message_text("ℹ️ Поздравление уже отправлено.")
            return

        greet_text = event.description or event.title
        resp_ok = await sync_to_async(_tg_send_message_sync)(
            event.client.telegram_id, greet_text
        )
        if not resp_ok:
            await query.edit_message_text("❌ Не удалось отправить (см. логи).")
            return

        def _complete():
            event.is_completed = True
            event.completed_at = timezone.now()
            event.reminder_sent_at = timezone.now()
            event.save(update_fields=['is_completed', 'completed_at', 'reminder_sent_at'])

        await sync_to_async(_complete)()
        await query.edit_message_text(
            f"✅ Поздравление отправлено клиенту {event.client.first_name} {event.client.last_name}"
        )

    # ============ C2: УДАЛЕНИЕ ============

    async def _handle_event_delete_confirm(self, update, context, event_id):
        query = update.callback_query
        await query.answer()

        def _get():
            return ScheduledEvent.objects.filter(id=event_id).select_related('client').first()

        event = await sync_to_async(_get)()
        if not event:
            await query.edit_message_text("❌ Событие не найдено")
            return

        from ..time_utils import to_user_time
        ut = to_user_time(event.scheduled_date)
        text = (
            f"🗑 *Удалить событие?*\n\n"
            f"📌 {event.title}\n"
            f"👤 {event.client.first_name} {event.client.last_name}\n"
            f"📅 {ut.strftime('%d.%m.%Y %H:%M')}\n\n"
            f"_Действие необратимо._"
        )
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton("✅ Да, удалить", callback_data=f"event_delete_{event_id}")],
            [InlineKeyboardButton("❌ Отмена", callback_data=f"event_detail_{event_id}")],
        ])
        try:
            await query.edit_message_text(text, parse_mode='Markdown', reply_markup=keyboard)
        except Exception as e:
            logger.error(f"delete_confirm: {e}")

    async def _handle_event_delete(self, update, context, event_id):
        query = update.callback_query
        await query.answer("🗑 Удаляю...")

        def _delete():
            event = ScheduledEvent.objects.filter(id=event_id).first()
            if not event:
                return None
            ut = to_user_time(event.scheduled_date)
            event.delete()
            return ut

        from ..time_utils import to_user_time
        ut = await sync_to_async(_delete)()
        if ut is None:
            await query.edit_message_text("❌ Событие уже удалено")
            return

        text = "✅ *Событие удалено*"
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton("⬅️ К дню", callback_data=f"event_back_to_day_{ut.day}_{ut.month}_{ut.year}")],
            [InlineKeyboardButton("📅 Календарь", callback_data=f"event_back_to_calendar_{ut.month}_{ut.year}")],
            [InlineKeyboardButton("🏠 Главное меню", callback_data="main_menu")],
        ])
        try:
            await query.edit_message_text(text, parse_mode='Markdown', reply_markup=keyboard)
        except Exception as e:
            logger.error(f"delete: {e}")

    # ============ C3.1: РЕДАКТИРОВАНИЕ ============

    async def _handle_event_edit_menu(self, update, context, event_id):
        """Подменю «Что изменить?»."""
        query = update.callback_query
        await query.answer()

        def _get():
            return ScheduledEvent.objects.filter(id=event_id).select_related('client').first()

        event = await sync_to_async(_get)()
        if not event:
            await query.edit_message_text("❌ Событие не найдено")
            return

        from ..time_utils import to_user_time
        ut = to_user_time(event.scheduled_date)
        text = (
            f"✏️ *Что изменить?*\n\n"
            f"📌 {event.title}\n"
            f"👤 {event.client.first_name} {event.client.last_name}\n"
            f"📅 {ut.strftime('%d.%m.%Y %H:%M')}\n\n"
            f"📝 Описание: {event.description or '—'}\n"
            f"📌 Тип: {event.event_type}"
        )
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton("📝 Описание", callback_data=f"event_edit_desc_{event.id}")],
            [InlineKeyboardButton("📌 Тип", callback_data=f"event_edit_type_{event.id}")],
            [InlineKeyboardButton("⬅️ Назад", callback_data=f"event_detail_{event.id}")],
        ])
        try:
            await query.edit_message_text(text, parse_mode='Markdown', reply_markup=keyboard)
        except Exception as e:
            logger.error(f"edit_menu: {e}")

    async def _handle_event_edit_desc_start(self, update, context, event_id):
        """Запрос нового описания."""
        query = update.callback_query
        await query.answer()

        def _get():
            return ScheduledEvent.objects.filter(id=event_id).first()

        event = await sync_to_async(_get)()
        if not event:
            await query.edit_message_text("❌ Событие не найдено")
            return

        context.user_data['event_editing'] = {'event_id': event_id, 'field': 'description'}

        await query.edit_message_text(
            f"📝 *Редактирование описания*\n\n"
            f"Текущее: {event.description or '—'}\n\n"
            f"Введите новое описание (или «—», чтобы очистить):"
        )

    async def _apply_event_edit(self, update, context, text):
        """Применить редактирование (описание). Возвращает True, если обработано."""
        data = context.user_data.pop('event_editing', None)
        if not data:
            return False

        event_id = data.get('event_id')
        field = data.get('field')
        value = '' if text.strip() in ('—', '-') else text.strip()

        def _save():
            event = ScheduledEvent.objects.filter(id=event_id).first()
            if not event:
                return None
            setattr(event, field, value)
            event.save(update_fields=[field])
            return event

        event = await sync_to_async(_save)()
        if not event:
            await update.message.reply_text("❌ Событие не найдено")
            return True

        await update.message.reply_text(
            f"✅ *Обновлено*\n\n"
            f"📌 {event.title}\n"
            f"📝 {value or '—'}",
            parse_mode='Markdown',
        )

        # Показываем детали
        from ..time_utils import to_user_time
        ut = to_user_time(event.scheduled_date)
        if event.is_completed:
            status = "✅ Отправлено" if event.event_type == 'birthday' else "✅ Выполнено"
        else:
            status = "⏳ Ожидает отправки" if event.event_type == 'birthday' else "⏳ Ожидает"

        card_text = (
            f"📌 *{event.title}*\n\n"
            f"👤 {event.client.first_name} {event.client.last_name}\n"
            f"📞 {event.client.phone}\n"
            f"📅 {ut.strftime('%d.%m.%Y %H:%M')}\n"
            f"📊 {status}\n"
        )
        if event.description:
            card_text += f"\n📝 {event.description}\n"

        keyboard = []
        if event.event_type == 'birthday' and event.client and event.client.telegram_id and not event.is_completed:
            keyboard.append([InlineKeyboardButton(
                "📤 Отправить поздравление сейчас",
                callback_data=f"event_send_birthday_{event.id}"
            )])
        if not event.is_completed:
            keyboard.append([InlineKeyboardButton(
                "✅ Отметить выполненным", callback_data=f"event_complete_{event.id}"
            )])
        keyboard.append([InlineKeyboardButton(
            "✏️ Изменить", callback_data=f"event_edit_menu_{event.id}"
        )])
        keyboard.append([InlineKeyboardButton(
            "🗑 Удалить", callback_data=f"event_delete_confirm_{event.id}"
        )])
        keyboard.append([
            InlineKeyboardButton("⬅️ К дню", callback_data=f"event_back_to_day_{ut.day}_{ut.month}_{ut.year}"),
            InlineKeyboardButton("📅 Календарь", callback_data=f"event_back_to_calendar_{ut.month}_{ut.year}"),
        ])
        keyboard.append([InlineKeyboardButton("🏠 Главное меню", callback_data="main_menu")])

        await update.message.reply_text(
            card_text, parse_mode='Markdown',
            reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard),
        )
        return True

    async def _handle_event_edit_type_menu(self, update, context, event_id):
        """Показать клавиатуру типов."""
        query = update.callback_query
        await query.answer()

        def _get():
            return ScheduledEvent.objects.filter(id=event_id).first()

        event = await sync_to_async(_get)()
        if not event:
            await query.edit_message_text("❌ Событие не найдено")
            return

        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton("📞 Звонок", callback_data=f"event_edit_type_{event_id}_call")],
            [InlineKeyboardButton("📅 Встреча", callback_data=f"event_edit_type_{event_id}_meeting")],
            [InlineKeyboardButton("🎂 Поздравление", callback_data=f"event_edit_type_{event_id}_birthday")],
            [InlineKeyboardButton("🔔 Напоминание", callback_data=f"event_edit_type_{event_id}_reminder")],
            [InlineKeyboardButton("📝 Своё событие", callback_data=f"event_edit_type_{event_id}_custom")],
            [InlineKeyboardButton("⬅️ Назад", callback_data=f"event_detail_{event_id}")],
        ])
        await query.edit_message_text(
            f"📌 *Выберите новый тип:*\n\n"
            f"Текущий: {event.event_type}",
            parse_mode='Markdown',
            reply_markup=keyboard,
        )

    async def _handle_event_edit_type_apply(self, update, context, event_id, new_type):
        """Применить новый тип."""
        query = update.callback_query
        await query.answer("✅ Сохраняю...")

        def _save():
            event = ScheduledEvent.objects.filter(id=event_id).first()
            if not event:
                return None
            event.event_type = new_type
            event.save(update_fields=['event_type'])
            return event

        event = await sync_to_async(_save)()
        if not event:
            await query.edit_message_text("❌ Событие не найдено")
            return

        await query.edit_message_text(
            f"✅ *Тип обновлён:* {new_type}\n\n"
            f"📌 {event.title}",
            parse_mode='Markdown',
        )
        await self._handle_event_detail(update, context, event_id)

    # ============ ПЛАНИРОВАНИЕ: СЛОТ ============

    async def _handle_event_plan_at(self, update, context, day, month, year, hour=9, minute=0):
        query = update.callback_query
        await query.answer()

        from ..validators import ensure_future_or_reply
        dt = create_user_datetime(year, month, day, hour, minute)
        if not await ensure_future_or_reply(query, dt):
            return
        context.user_data['event_scheduled_date'] = dt
        context.user_data['finding'] = True

        from ..time_utils import format_user_time
        time_str = format_user_time(dt)

        text = (
            f"📅 *Планирование события*\n\n"
            f"📅 {time_str} (MSK)\n\n"
            f"🔍 Введите имя, телефон или компанию клиента:"
        )
        keyboard = [[InlineKeyboardButton("❌ Отмена", callback_data="plan_cancel")]]
        reply_markup = InlineKeyboardMarkup(inline_keyboard=keyboard)
        try:
            await query.edit_message_text(text, parse_mode='Markdown', reply_markup=reply_markup)
        except Exception as e:
            logger.error(f"Ошибка планирования: {e}")

    async def _handle_event_back_to_calendar(self, update, context, month, year):
        query = update.callback_query
        await query.answer()
        keyboard = get_events_calendar_keyboard(month, year)
        text = f"📅 *Календарь событий*\n{MONTHS_RU[month]} {year}\n\n• — есть события"
        try:
            await query.edit_message_text(text, parse_mode='Markdown', reply_markup=keyboard)
        except Exception as e:
            logger.error(f"Ошибка: {e}")

    async def _handle_event_back_to_day(self, update, context, day, month, year):
        query = update.callback_query
        await query.answer()
        from ..keyboards import get_event_day_keyboard
        keyboard = get_event_day_keyboard(day, month, year)
        text = f"📅 *{day} {MONTHS_RU[month]} {year}*\n\nВыберите время:"
        try:
            await query.edit_message_text(text, parse_mode='Markdown', reply_markup=keyboard)
        except Exception as e:
            logger.error(f"Ошибка: {e}")


# ============ МОДУЛЬНЫЕ ФУНКЦИИ ============

def _tg_send_message_sync(chat_id, text):
    """Синхронная отправка через requests; вызывать из sync_to_async. True при успехе."""
    import requests
    token = settings.TELEGRAM_BOT_TOKEN
    proxy = getattr(settings, 'TELEGRAM_PROXY_URL', '') or None
    proxies = {'https': proxy, 'http': proxy} if proxy else None
    try:
        r = requests.post(
            f'https://api.telegram.org/bot{token}/sendMessage',
            json={'chat_id': chat_id, 'text': text, 'parse_mode': 'Markdown'},
            proxies=proxies, timeout=10,
        )
        if r.status_code == 200:
            return True
        logger.error(f"_tg_send_message_sync: {r.status_code}: {r.text[:200]}")
        return False
    except Exception as e:
        logger.error(f"_tg_send_message_sync: {e}")
        return False