"""Mixin: команды /start, /help, /list, /find, /stats, /birthdays, /events, /add."""
import logging

from telegram import Update
from telegram.ext import ContextTypes
from django.utils import timezone
from asgiref.sync import sync_to_async

from apps.clients.models import Client, ScheduledEvent
from ..keyboards import get_months_keyboard, get_plan_action_keyboard
from ..utils import get_clients_list_message
from .helpers import main_reply_markup
from .clients import show_client_options

logger = logging.getLogger(__name__)


class CommandsMixin:
    """Команды и обработка текста для reply-клавиатуры."""

    # ============ КОМАНДЫ ============

    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user = update.effective_user
        await update.message.reply_text(
            f"👋 Привет, {user.first_name}!\n\n"
            "Я CRM бот для управления клиентами.\n"
            "Используйте меню ниже или команды:\n\n"
            "📋 /list — список клиентов\n"
            "🔍 /find — поиск\n"
            "📊 /stats — статистика\n"
            "❓ /help — помощь",
            reply_markup=main_reply_markup(),
        )

    async def help(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        await update.message.reply_text(
            "📖 *Доступные команды:*\n\n"
            "/start - Приветствие\n"
            "/help - Справка\n"
            "/add - Добавить клиента (контакт)\n"
            "/list - Список клиентов\n"
            "/find - Найти клиента\n"
            "/events - Ближайшие события\n"
            "/birthdays - Дни рождения\n"
            "/stats - Статистика\n"
            "/avatar [имя] - Найти клиента для фото\n\n"
            "📸 *Распознавание визиток:*\n"
            "Отправь фото визитки — бот распознает ФИО, телефон, email\n\n"
            "📞 *Звонки:*\n"
            "В карточке клиента нажми '📞 Позвонить' — телефон станет кликабельным\n\n"
            "✉️ *Email:*\n"
            "В карточке клиента нажми '✉️ Написать' — бот отправит письмо",
            reply_markup=main_reply_markup(),
        )

    async def list_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """/list — список клиентов с пагинацией."""
        def _get():
            return Client.objects.all().order_by('-created_at')

        clients = await sync_to_async(_get)()

        if not clients:
            await update.message.reply_text(
                "📭 Клиентов пока нет.",
                reply_markup=main_reply_markup(),
            )
            return

        message_text, keyboard = get_clients_list_message(clients, 1)
        await update.message.reply_text(
            message_text,
            parse_mode='Markdown',
            reply_markup=keyboard,
        )

    async def find(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        await update.message.reply_text("🔍 Введите имя или телефон клиента:")
        context.user_data['finding'] = True

    async def events(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        now = timezone.now()

        def _get_events():
            return list(ScheduledEvent.objects.filter(
                scheduled_date__gte=now, is_completed=False,
            ).order_by('scheduled_date')[:10])

        events = await sync_to_async(_get_events)()
        if not events:
            await update.message.reply_text("📅 Нет запланированных событий.", reply_markup=main_reply_markup())
            return

        message = "📅 *Запланированные события:*\n\n"
        for event in events:
            date_str = event.scheduled_date.strftime("%d.%m %H:%M")
            status = "✅" if event.is_completed else "⏳"
            message += f"{status} *{event.title}*\n"
            message += f"   👤 {event.client.first_name} {event.client.last_name}\n"
            message += f"   🕐 {date_str}\n"
            if event.is_ai_generated:
                message += f"   🤖 Сгенерировано ИИ\n"
            message += "\n"
        await update.message.reply_text(message, parse_mode='Markdown', reply_markup=main_reply_markup())

    async def birthdays(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        today = timezone.now().date()

        def _get_clients():
            return list(Client.objects.filter(birth_date__isnull=False))

        all_clients = await sync_to_async(_get_clients)()
        clients_list = []
        for client in all_clients:
            next_birthday = client.birth_date.replace(year=today.year)
            if next_birthday < today:
                next_birthday = next_birthday.replace(year=today.year + 1)
            days_until = (next_birthday - today).days
            if 0 <= days_until <= 7:
                clients_list.append((client, days_until))

        if not clients_list:
            await update.message.reply_text("🎂 В ближайшую неделю нет дней рождения.", reply_markup=main_reply_markup())
            return

        message = "🎂 *Дни рождения в ближайшую неделю:*\n\n"
        for client, days in sorted(clients_list, key=lambda x: x[1]):
            status_emoji = {'vip': '⭐', 'active': '✅', 'regular': '🔄', 'lead': '🆕', 'inactive': '⏸️'}.get(client.status, '📌')
            message += f"{status_emoji} *{client.first_name} {client.last_name}*\n"
            message += f"   📞 {client.phone}\n"
            if client.company:
                message += f"   🏢 {client.company}\n"
            message += f"   📅 {client.birth_date.strftime('%d.%m')} (через {days} дн.)\n\n"
        await update.message.reply_text(message, parse_mode='Markdown', reply_markup=main_reply_markup())

    async def stats(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        def _get_stats():
            return {
                'total': Client.objects.count(),
                'vip': Client.objects.filter(status='vip').count(),
                'active': Client.objects.filter(status='active').count(),
                'regular': Client.objects.filter(status='regular').count(),
                'lead': Client.objects.filter(status='lead').count(),
                'events': ScheduledEvent.objects.filter(is_completed=False).count(),
                'ai_events': ScheduledEvent.objects.filter(is_ai_generated=True).count(),
            }

        s = await sync_to_async(_get_stats)()
        message = (
            "📊 *Статистика CRM:*\n\n"
            f"👥 Всего клиентов: *{s['total']}*\n\n"
            "По статусам:\n"
            f"⭐ VIP: {s['vip']}\n"
            f"✅ Активные: {s['active']}\n"
            f"🔄 Постоянные: {s['regular']}\n"
            f"🆕 Лиды: {s['lead']}\n\n"
            f"📅 Запланировано событий: {s['events']}\n"
            f"🤖 Сгенерировано ИИ: {s['ai_events']}"
        )
        await update.message.reply_text(message, parse_mode='Markdown', reply_markup=main_reply_markup())

    async def add(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        await update.message.reply_text(
            "📇 *Добавить клиента:*\n\n"
            "1. *Отправьте контакт* — нажмите 📎 → Контакт\n\n"
            "2. *Отправьте фото визитки* — бот распознает ФИО, телефон, email, компанию\n\n"
            "💡 Аватарку можно загрузить отдельно: /avatar Имя",
            parse_mode='Markdown',
            reply_markup=main_reply_markup(),
        )

    async def handle_contact(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработка контакта из Telegram.

        В PTB 21.x у объекта Contact НЕТ поля .photo — аватарку из контакта получить нельзя.
        """
        contact = update.message.contact

        def _get_or_create():
            return Client.objects.get_or_create(
                phone=contact.phone_number,
                defaults={
                    'first_name': contact.first_name,
                    'last_name': contact.last_name or '',
                    'telegram_id': str(update.effective_user.id),
                    'status': 'lead',
                },
            )

        client, created = await sync_to_async(_get_or_create)()

        if created:
            await update.message.reply_text(
                f"✅ Клиент добавлен!\n\n"
                f"👤 {client.first_name} {client.last_name}\n"
                f"📞 {client.phone}\n\n"
                f"💡 Чтобы загрузить аватарку — используйте /avatar {client.first_name}",
                reply_markup=main_reply_markup(),
            )
        else:
            await update.message.reply_text(
                f"ℹ️ Клиент уже существует:\n\n"
                f"👤 {client.first_name} {client.last_name}\n"
                f"📞 {client.phone}",
                reply_markup=main_reply_markup(),
            )

    # ============ ОБРАБОТКА ТЕКСТА ============

    async def handle_text(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        from apps.clients.models import Interaction
        
        from django.db.models import Q

        text = update.message.text.strip()

        # Reply-кнопки
        if text in ('📋 Список', '📋 Список клиентов'):
            await self.list_command(update, context)
            return
        if text == '📊 Статистика':
            await self.stats(update, context)
            return
        if text in ('📅 События', '📅 Календарь'):
            await self._handle_show_events_calendar_from_message(update, context)
            return
        if text == '🎂 Дни рождения':
            await self.birthdays(update, context)
            return
        if text == '🔍 Поиск':
            await self.find(update, context)
            return
        if text == '➕ Добавить':
            await self.add(update, context)
            return
        if text == '❓ Помощь':
            await self.help(update, context)
            return
        if text == '❌ Отмена':
            for key in ('awaiting_note', 'awaiting_email', 'finding',
                        'note_client_id', 'event_description_client_id',
                        'event_description_action', 'planning_client_id'):
                context.user_data.pop(key, None)
            await update.message.reply_text("❌ Отменено", reply_markup=main_reply_markup())
            return

        # FSM: заметка
        if context.user_data.get('awaiting_note'):
            client_id = context.user_data.get('note_client_id')
            context.user_data.pop('awaiting_note', None)
            context.user_data.pop('note_client_id', None)

            def _get():
                return Client.objects.filter(id=client_id).first()

            client = await sync_to_async(_get)()
            if not client:
                await update.message.reply_text("❌ Клиент не найден", reply_markup=main_reply_markup())
                return

            try:
                await sync_to_async(Interaction.objects.create)(
                    client=client,
                    type='note',
                    content=text,
                    created_at=timezone.now(),
                )
                await update.message.reply_text(
                    f"✅ *Заметка сохранена*\n\n"
                    f"👤 {client.first_name} {client.last_name}\n"
                    f"📝 {text[:200]}",
                    parse_mode='Markdown',
                    reply_markup=main_reply_markup(),
                )
            except Exception as e:
                logger.error(f"Ошибка сохранения заметки: {e}")
                await update.message.reply_text(f"❌ Ошибка: {e}", reply_markup=main_reply_markup())
            return

        # FSM: описание события
        if context.user_data.get('awaiting_event_description'):
            client_id = context.user_data.get('event_description_client_id')
            action = context.user_data.get('event_description_action')

            context.user_data.pop('awaiting_event_description', None)
            context.user_data['event_description_text'] = text
            context.user_data['planning_client_id'] = client_id
            context.user_data['planning_action_type'] = action

            keyboard = get_months_keyboard()
            await update.message.reply_text(
                f"📝 Описание: {text[:80]}\n\n"
                f"📅 *Выберите месяц:*",
                parse_mode='Markdown',
                reply_markup=keyboard,
            )
            return

        # FSM: email
        if context.user_data.get('awaiting_email', {}).get('stage') == 'subject':
            await self._handle_email_subject(update, context)
            return

        if context.user_data.get('awaiting_email', {}).get('stage') == 'body':
            await self._handle_email_body(update, context)
            return

        # FSM: поиск
        if context.user_data.get('finding'):
            context.user_data['finding'] = False

            def _search(t):
                return list(
                    Client.objects.filter(
                        Q(first_name__icontains=t) |
                        Q(last_name__icontains=t) |
                        Q(phone__icontains=t) |
                        Q(company__icontains=t) |
                        Q(email__icontains=t)
                    )
                )

            clients = await sync_to_async(_search)(text)
            if clients:
                scheduled_date = context.user_data.get('event_scheduled_date')
                if scheduled_date:
                    context.user_data['planning_client_id'] = clients[0].id
                    context.user_data['event_scheduled_date'] = scheduled_date
                    await update.message.reply_text(
                        f"👤 *{clients[0].first_name} {clients[0].last_name}*\n"
                        f"📞 {clients[0].phone}\n\n"
                        f"Выберите тип события:",
                        parse_mode='Markdown',
                        reply_markup=get_plan_action_keyboard(),
                    )
                else:
                    await show_client_options(update, context, clients[0])
            else:
                await update.message.reply_text(
                    "❌ Клиент не найден. Попробуйте ещё раз или отправьте «❌ Отмена».",
                    reply_markup=main_reply_markup(),
                )
            return

        await update.message.reply_text(
            "🤔 Не понял команду. Используйте меню ниже или /help",
            reply_markup=main_reply_markup(),
        )

        # ============ EMAIL ============

    async def handle_email_action(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Начало отправки email клиенту (callback action_ID_message)."""
        query = update.callback_query
        await query.answer()

        client_id = context.user_data.get('selected_client_id')
        if not client_id:
            await query.edit_message_text("❌ Выберите клиента сначала.")
            return

        client = await sync_to_async(Client.objects.get)(id=client_id)

        if not client.email:
            await query.edit_message_text(
                f"❌ У клиента {client.first_name} {client.last_name} нет email.\n"
                "Добавьте email через админку или отредактируйте клиента."
            )
            return

        context.user_data['awaiting_email'] = {
            'client_id': client_id,
            'stage': 'subject',
        }
        await query.edit_message_text(
            f"✉️ *Отправка письма*\n\n"
            f"👤 Кому: {client.first_name} {client.last_name}\n"
            f"📧 Email: {client.email}\n\n"
            "Введите *тему* письма:",
            parse_mode='Markdown',
        )

    async def _handle_email_subject(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработка ввода темы письма."""
        email_data = context.user_data['awaiting_email']
        email_data['subject'] = update.message.text
        email_data['stage'] = 'body'
        await update.message.reply_text(
            f"📝 Тема: {email_data['subject']}\n\n"
            "Теперь введите *текст* письма:",
            parse_mode='Markdown',
        )

    async def _handle_email_body(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработка ввода тела письма и отправка."""
        from django.conf import settings
        from django.core.mail import send_mail
        from apps.clients.models import Interaction

        email_data = context.user_data['awaiting_email']
        email_data['body'] = update.message.text
        client = await sync_to_async(Client.objects.get)(id=email_data['client_id'])

        try:
            await sync_to_async(send_mail)(
                subject=email_data['subject'],
                message=email_data['body'],
                from_email=settings.DEFAULT_FROM_EMAIL or settings.EMAIL_HOST_USER,
                recipient_list=[client.email],
                fail_silently=False,
            )
            await sync_to_async(Interaction.objects.create)(
                client=client,
                type='email',
                content=f"Тема: {email_data['subject']}\n\n{email_data['body']}",
                created_at=timezone.now(),
                completed_at=timezone.now(),
            )
            await update.message.reply_text(
                f"✅ Письмо отправлено!\n\n"
                f"📧 Кому: {client.email}\n"
                f"📝 Тема: {email_data['subject']}",
                reply_markup=main_reply_markup(),
            )
        except Exception as e:
            logger.error(f"Ошибка отправки email: {e}")
            await update.message.reply_text(f"❌ Ошибка отправки: {e}", reply_markup=main_reply_markup())

        context.user_data.pop('awaiting_email', None)