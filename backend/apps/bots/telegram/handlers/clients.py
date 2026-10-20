"""Mixin: работа с клиентами (карточки, список, действия, аватарки)."""
import logging
from io import BytesIO

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from django.utils import timezone
from django.db.models import Q
from asgiref.sync import sync_to_async

from apps.clients.models import Client
from ..keyboards import (
    get_client_full_actions_keyboard,
    get_events_calendar_keyboard,
    MONTHS_RU,
)
from ..utils import get_clients_list_message, get_client_card
from .helpers import main_reply_markup

logger = logging.getLogger(__name__)


class ClientsMixin:
    """Методы для работы с клиентами и главного меню."""

    # ============ СПИСОК ============

    async def list_clients(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Старая карточка-список (reply-кнопка может использовать list_command)."""
        clients = await self._get_clients_list()
        if not clients:
            await update.message.reply_text("📭 Клиентов пока нет.", reply_markup=main_reply_markup())
            return

        message = "📋 *Список клиентов:*\n\n"
        for i, client in enumerate(clients, 1):
            status_emoji = {'vip': '⭐', 'active': '✅', 'regular': '🔄', 'lead': '🆕', 'inactive': '⏸️'}.get(client.status, '📌')
            message += f"{i}. {status_emoji} {client.first_name} {client.last_name}\n"
            message += f"   📞 {client.phone}\n"
            if client.company:
                message += f"   🏢 {client.company}\n"
            message += "\n"

        keyboard = []
        for client in clients[:5]:
            keyboard.append([
                InlineKeyboardButton(
                    f"📌 {client.first_name} {client.last_name}",
                    callback_data=f"client_{client.id}"
                )
            ])
        keyboard.append([InlineKeyboardButton("📋 Все клиенты", callback_data="back_to_list")])

        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text(
            message,
            parse_mode='Markdown',
            reply_markup=reply_markup,
        )

    async def _get_clients_list(self):
        return await sync_to_async(lambda: list(Client.objects.all()[:10]))()

    # ============ КАРТОЧКА КЛИЕНТА (callback client_*) ============

    async def show_client_actions(self, update: Update, context: ContextTypes.DEFAULT_TYPE, client_id):
        try:
            client = await sync_to_async(Client.objects.get)(id=client_id)
        except Client.DoesNotExist:
            await update.callback_query.message.edit_text("❌ Клиент не найден")
            return

        query = update.callback_query
        await query.answer()

        status_emoji = {'vip': '⭐', 'active': '✅', 'regular': '🔄', 'lead': '🆕', 'inactive': '⏸️'}.get(client.status, '📌')
        message = f"{status_emoji} *{client.first_name} {client.last_name}*\n\n"
        message += f"📞 {client.phone}\n"
        if client.email:
            message += f"✉️ {client.email}\n"
        if client.company:
            message += f"🏢 {client.company}\n"
        if client.comment:
            message += f"📝 {client.comment[:100]}...\n"
        message += f"📅 В базе: {(timezone.now() - client.created_at).days} дн."

        keyboard = [
            [
                InlineKeyboardButton("📞 Позвонить", callback_data=f"action_{client.id}_call"),
                InlineKeyboardButton("✉️ Написать", callback_data=f"action_{client.id}_message"),
            ],
            [
                InlineKeyboardButton("🎂 Поздравить", callback_data=f"action_{client.id}_birthday"),
                InlineKeyboardButton("📅 Встреча", callback_data=f"action_{client.id}_meeting"),
            ],
            [
                InlineKeyboardButton("🔔 Напомнить", callback_data=f"action_{client.id}_reminder"),
                InlineKeyboardButton("📝 Комментарий", callback_data=f"action_{client.id}_note"),
            ],
            [
                InlineKeyboardButton("🤖 ИИ помощь", callback_data=f"action_{client.id}_ai"),
                InlineKeyboardButton("⬅️ Назад", callback_data="back_to_list"),
            ],
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        await query.edit_message_text(
            message,
            parse_mode='Markdown',
            reply_markup=reply_markup,
        )

        context.user_data['selected_client_id'] = client_id

    # ============ ГЛАВНОЕ МЕНЮ И СПИСКИ ============

    async def _handle_main_menu(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        await query.answer()
        await query.edit_message_text(
            "🏠 *Главное меню*\n\nВыберите действие:",
            parse_mode='Markdown',
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton("📋 Список клиентов", callback_data="back_to_list"),
                 InlineKeyboardButton("📊 Статистика", callback_data="show_stats")],
                [InlineKeyboardButton("🎂 Дни рождения", callback_data="show_birthdays"),
                 InlineKeyboardButton("📅 События", callback_data="show_events_calendar")],
                [InlineKeyboardButton("🔍 Поиск", callback_data="find_client"),
                 InlineKeyboardButton("➕ Добавить", callback_data="add_client")],
                [InlineKeyboardButton("❓ Помощь", callback_data="show_help")],
            ])
        )

    async def _handle_back_to_list(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        await query.answer()

        def _get():
            return Client.objects.all().order_by('-created_at')

        clients = await sync_to_async(_get)()
        message_text, keyboard = get_clients_list_message(clients, 1)
        try:
            await query.edit_message_text(message_text, parse_mode='Markdown', reply_markup=keyboard)
        except Exception as e:
            logger.error(f"Ошибка редактирования списка: {e}")
            await query.message.reply_text(message_text, parse_mode='Markdown', reply_markup=keyboard)

    async def _handle_list_page(self, update: Update, context: ContextTypes.DEFAULT_TYPE, page: int):
        query = update.callback_query
        await query.answer()

        def _get():
            return Client.objects.all().order_by('-created_at')

        clients = await sync_to_async(_get)()
        message_text, keyboard = get_clients_list_message(clients, page)
        await query.edit_message_text(message_text, parse_mode='Markdown', reply_markup=keyboard)

    async def _handle_list_letter(self, update: Update, context: ContextTypes.DEFAULT_TYPE, letter: str):
        query = update.callback_query
        await query.answer()

        def _get():
            return Client.objects.filter(
                Q(first_name__istartswith=letter) | Q(last_name__istartswith=letter)
            ).order_by('first_name')

        clients = await sync_to_async(_get)()
        if not clients:
            await query.edit_message_text(f"📭 Нет клиентов на букву '{letter}'")
            return

        message_text, keyboard = get_clients_list_message(clients, 1)
        header = f"📋 *Клиенты на букву '{letter}'* (всего {len(clients)})\n\n"
        if '\n\n' in message_text:
            message_text = header + message_text.split('\n\n', 1)[1]
        else:
            message_text = header + message_text
        await query.edit_message_text(message_text, parse_mode='Markdown', reply_markup=keyboard)

    async def _handle_client_detail(self, update: Update, context: ContextTypes.DEFAULT_TYPE, client_id: int):
        """Полная карточка клиента с аватаркой (callback client_detail_*)."""
        query = update.callback_query
        await query.answer()

        def _get():
            return Client.objects.filter(id=client_id).first()

        client = await sync_to_async(_get)()
        if not client:
            await query.edit_message_text("❌ Клиент не найден")
            return

        card_text = get_client_card(client, show_avatar=False) + "\n\n_Выберите действие:_"
        keyboard = get_client_full_actions_keyboard(client.id)

        has_avatar = bool(client.avatar and client.avatar.name)
        logger.info(f"🖼️ _handle_client_detail: client_id={client_id}, has_avatar={has_avatar}")

        if has_avatar:
            try:
                def _read_avatar():
                    client.avatar.open('rb')
                    try:
                        return client.avatar.read()
                    finally:
                        client.avatar.close()

                photo_data = await sync_to_async(_read_avatar)()
                buf = BytesIO(photo_data)
                buf.name = f'avatar_{client_id}.jpg'

                await query.message.chat.send_photo(
                    photo=buf,
                    caption=card_text,
                    parse_mode='Markdown',
                    reply_markup=keyboard,
                )
                try:
                    await query.message.delete()
                except Exception:
                    pass
                logger.info(f"🖼️ _handle_client_detail: фото отправлено для client_id={client_id}")
            except Exception as e:
                logger.error(f"❌ Ошибка отправки аватарки client_id={client_id}: {e}", exc_info=True)
                try:
                    await query.edit_message_text(card_text, parse_mode='Markdown', reply_markup=keyboard)
                except Exception:
                    pass
        else:
            await query.edit_message_text(card_text, parse_mode='Markdown', reply_markup=keyboard)

    async def _handle_show_avatar(self, update: Update, context: ContextTypes.DEFAULT_TYPE, client_id: int):
        query = update.callback_query
        await query.answer()

        def _get():
            return Client.objects.filter(id=client_id).first()

        client = await sync_to_async(_get)()
        if not (client and client.avatar and client.avatar.name):
            await query.message.reply_text("❌ У клиента нет аватарки")
            return

        caption = f"🖼️ *Аватарка*\n👤 {client.first_name} {client.last_name}"
        try:
            def _read_avatar():
                client.avatar.open('rb')
                try:
                    return client.avatar.read()
                finally:
                    client.avatar.close()

            photo_data = await sync_to_async(_read_avatar)()
            buf = BytesIO(photo_data)
            buf.name = f'avatar_{client_id}.jpg'

            await query.message.chat.send_photo(
                photo=buf,
                caption=caption,
                parse_mode='Markdown',
            )
            logger.info(f"🖼️ _handle_show_avatar: фото отправлено для client_id={client_id}")
        except Exception as e:
            logger.error(f"❌ Ошибка отправки аватарки client_id={client_id}: {e}", exc_info=True)
            await query.message.reply_text("❌ Не удалось отправить аватарку")

    # ============ СТАТИСТИКА / ДНИ РОЖДЕНИЯ / СОБЫТИЯ (inline) ============

    async def _handle_show_stats(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Статистика (inline callback show_stats)."""
        from apps.clients.models import ScheduledEvent

        query = update.callback_query
        await query.answer()

        def _get_stats():
            return {
                'total': Client.objects.count(),
                'vip': Client.objects.filter(status='vip').count(),
                'active': Client.objects.filter(status='active').count(),
                'regular': Client.objects.filter(status='regular').count(),
                'lead': Client.objects.filter(status='lead').count(),
                'events': ScheduledEvent.objects.filter(is_completed=False).count(),
            }

        s = await sync_to_async(_get_stats)()
        response = (
            f"📊 *Статистика CRM:*\n\n"
            f"👥 Всего клиентов: *{s['total']}*\n\n"
            "По статусам:\n"
            f"⭐ VIP: {s['vip']}\n"
            f"✅ Активные: {s['active']}\n"
            f"🔄 Постоянные: {s['regular']}\n"
            f"🆕 Лиды: {s['lead']}\n\n"
            f"📅 Запланировано событий: {s['events']}"
        )
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton("⬅️ Назад к списку", callback_data="back_to_list")]
        ])
        await query.edit_message_text(response, parse_mode='Markdown', reply_markup=keyboard)

    async def _handle_show_birthdays(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Дни рождения (inline callback show_birthdays)."""
        query = update.callback_query
        await query.answer()

        def _get():
            return list(Client.objects.filter(birth_date__isnull=False))

        all_clients = await sync_to_async(_get)()
        today = timezone.now().date()
        clients_list = []
        for client in all_clients:
            next_birthday = client.birth_date.replace(year=today.year)
            if next_birthday < today:
                next_birthday = next_birthday.replace(year=today.year + 1)
            days_until = (next_birthday - today).days
            if 0 <= days_until <= 7:
                clients_list.append((client, days_until))

        if clients_list:
            response = "🎂 *Дни рождения в ближайшую неделю:*\n\n"
            for client, days in sorted(clients_list, key=lambda x: x[1]):
                status_emoji = {'vip': '⭐', 'active': '✅', 'regular': '🔄', 'lead': '🆕', 'inactive': '⏸️'}.get(client.status, '📌')
                response += f"{status_emoji} *{client.first_name} {client.last_name}*\n"
                response += f"   📞 {client.phone}\n"
                if client.company:
                    response += f"   🏢 {client.company}\n"
                response += f"   📅 {client.birth_date.strftime('%d.%m')} (через {days} дн.)\n\n"
        else:
            response = "🎂 В ближайшую неделю нет дней рождения."

        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton("⬅️ Назад к списку", callback_data="back_to_list")]
        ])
        await query.edit_message_text(response, parse_mode='Markdown', reply_markup=keyboard)

    async def _handle_show_events_calendar(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Календарь событий (inline callback show_events_calendar)."""
        from datetime import datetime

        query = update.callback_query
        await query.answer()
        today = datetime.now()
        month, year = today.month, today.year
        keyboard = get_events_calendar_keyboard(month, year)
        text = f"📅 *Календарь событий*\n{MONTHS_RU[month]} {year}\n\n• — есть события"
        try:
            await query.edit_message_text(text, parse_mode='Markdown', reply_markup=keyboard)
        except Exception as e:
            logger.error(f"Ошибка показа календаря: {e}")
            await query.message.reply_text(text, parse_mode='Markdown', reply_markup=keyboard)

    async def _handle_show_events_calendar_from_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Календарь событий (reply-кнопка 📅 События)."""
        from datetime import datetime

        today = datetime.now()
        month, year = today.month, today.year
        keyboard = get_events_calendar_keyboard(month, year)
        text = f"📅 *Календарь событий*\n{MONTHS_RU[month]} {year}\n\n• — есть события"
        await update.message.reply_text(text, parse_mode='Markdown', reply_markup=keyboard)

    # ============ ДЕЙСТВИЯ С КЛИЕНТОМ ============

    async def _handle_action(self, update: Update, context: ContextTypes.DEFAULT_TYPE, client_id: int, action_type: str):
        """Роутер быстрых действий с клиентом.

        Вызывается из _button_handler_impl для callback'ов action_<id>_<type>.
        client_id — из callback, action_type — тип действия.
        """
        query = update.callback_query
        await query.answer()

        # Позвонить — сразу отправляем контакт + логируем Interaction(call)
        if action_type == 'call':
            await self._handle_call_with_log(update, context, client_id)
            return

        # Заметка — FSM: запрашиваем текст, сохраняем как Interaction(note)
        if action_type == 'note':
            context.user_data['note_client_id'] = client_id
            context.user_data['awaiting_note'] = True

            def _get():
                return Client.objects.filter(id=client_id).first()

            client = await sync_to_async(_get)()
            if not client:
                await query.edit_message_text("❌ Клиент не найден")
                return

            try:
                await query.message.delete()
            except Exception:
                pass

            await query.message.chat.send_message(
                f"📝 *Заметка для {client.first_name} {client.last_name}*\n\n"
                f"Введите текст заметки (или отправьте «❌ Отмена»):",
                parse_mode='Markdown',
            )
            return

        # Email — начало отправки письма
        if action_type == 'message':
            await self.handle_email_action(update, context, client_id)
            return

        # meeting, reminder, birthday, ai — в планирование (заглушка до Шага 4)
        await self._handle_plan_start(update, context, client_id)

    async def _handle_call_with_log(self, update: Update, context: ContextTypes.DEFAULT_TYPE, client_id: int):
        """Позвонить + записать Interaction(type='call')."""
        from apps.clients.models import Interaction

        query = update.callback_query

        def _get():
            return Client.objects.filter(id=client_id).first()

        client = await sync_to_async(_get)()
        if not client or not client.phone:
            await query.message.reply_text("❌ У клиента нет телефона.")
            return

        # Логируем Interaction(call)
        try:
            await sync_to_async(Interaction.objects.create)(
                client=client,
                type='call',
                content=f"Звонок клиенту {client.first_name} {client.last_name}",
                created_at=timezone.now(),
            )
        except Exception as e:
            logger.error(f"Ошибка создания Interaction(call): {e}")

        # Текст с номером (для копирования)
        await query.message.reply_text(
            f"📞 *Позвонить: {client.first_name} {client.last_name}*\n\n"
            f"`{client.phone}`\n\n"
            f"_Нажмите на контакт ниже, чтобы сохранить и позвонить_",
            parse_mode='Markdown',
        )

        await query.message.reply_contact(
            phone_number=client.phone,
            first_name=client.first_name,
            last_name=client.last_name or '',
        )

    async def handle_call_action(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Кнопка 📞 Позвонить из старой карточки (callback action_*_call)."""
        query = update.callback_query
        await query.answer()

        client_id = context.user_data.get('selected_client_id')
        if not client_id:
            await query.edit_message_text("❌ Выберите клиента сначала.")
            return

        client = await sync_to_async(Client.objects.get)(id=client_id)
        if not client.phone:
            await query.edit_message_text("❌ У клиента нет телефона.")
            return

        await query.message.reply_text(
            f"📞 *Позвонить: {client.first_name} {client.last_name}*\n\n"
            f"`{client.phone}`\n\n"
            f"_Нажмите на контакт ниже, чтобы сохранить и позвонить_",
            parse_mode='Markdown',
        )

        await query.message.reply_contact(
            phone_number=client.phone,
            first_name=client.first_name,
            last_name=client.last_name or '',
        )       
        


# ============ МОДУЛЬНЫЕ ФУНКЦИИ ============

async def show_client_options(update, context, client):
    """Показывает карточку клиента с кнопками (для поиска)."""
    status_emoji = {'vip': '⭐', 'active': '✅', 'regular': '🔄', 'lead': '🆕', 'inactive': '⏸️'}.get(client.status, '📌')
    message = f"{status_emoji} *{client.first_name} {client.last_name}*\n\n"
    message += f"📞 {client.phone}\n"
    if client.email:
        message += f"✉️ {client.email}\n"
    if client.company:
        message += f"🏢 {client.company}\n"
    message += f"📅 В базе: {(timezone.now() - client.created_at).days} дн."

    keyboard = [
        [
            InlineKeyboardButton("📞 Позвонить", callback_data=f"action_{client.id}_call"),
            InlineKeyboardButton("✉️ Написать", callback_data=f"action_{client.id}_message"),
        ],
        [
            InlineKeyboardButton("🎂 Поздравить", callback_data=f"action_{client.id}_birthday"),
            InlineKeyboardButton("📅 Встреча", callback_data=f"action_{client.id}_meeting"),
        ],
        [
            InlineKeyboardButton("🔔 Напомнить", callback_data=f"action_{client.id}_reminder"),
            InlineKeyboardButton("📝 Комментарий", callback_data=f"action_{client.id}_note"),
        ],
        [
            InlineKeyboardButton("🤖 ИИ помощь", callback_data=f"action_{client.id}_ai"),
        ],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(message, parse_mode='Markdown', reply_markup=reply_markup)