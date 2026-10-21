"""Mixin: команды /start, /help, /list, /find, /stats, /birthdays, /events, /add."""
import logging
import re
from datetime import datetime

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
            "В карточке клиента нажми '✉️ Написать' — бот отправит письмо\n\n"
            "🎤 *Голосовые команды:*\n"
            "«Найди Ивана», «Список клиентов», «Статистика», «События»\n"
            "«Запланируй звонок Евгению на 25 декабря 18:00»",
            reply_markup=main_reply_markup(),
        )

    async def list_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        def _get():
            return Client.objects.all().order_by('-created_at')

        clients = await sync_to_async(_get)()
        if not clients:
            await update.message.reply_text("📭 Клиентов пока нет.", reply_markup=main_reply_markup())
            return

        message_text, keyboard = get_clients_list_message(clients, 1)
        await update.message.reply_text(message_text, parse_mode='Markdown', reply_markup=keyboard)

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

    async def handle_text(self, update: Update, context: ContextTypes.DEFAULT_TYPE, text: str = None):
        from apps.clients.models import Interaction
        from django.db.models import Q

        if text is None:
            text = update.message.text.strip()
        else:
            text = text.strip()

        # ============ 0. REPLY-КЛАВИАТУРА ============
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
                        'event_description_action', 'planning_client_id',
                        'awaiting_plan_time', 'awaiting_plan_client',
                        'pending_plan', 'confirm_plan'):
                context.user_data.pop(key, None)
            await update.message.reply_text("❌ Отменено", reply_markup=main_reply_markup())
            return

        text_lower = text.lower()

        # ============ ПЛАНИРОВАНИЕ (запланируй/напомни) ============
        if any(word in text_lower for word in ('запланируй', 'запланировать', 'напомни', 'напомнить')):
            await self._handle_plan_voice(update, context, text)
            return

        # Ожидание времени для планирования
        if context.user_data.get('awaiting_plan_time'):
            context.user_data.pop('awaiting_plan_time', None)
            pending = context.user_data.get('pending_plan', {})
            if re.match(r'^\d{1,2}:\d{2}$', text):
                pending['time'] = text
                context.user_data['pending_plan'] = pending
                client_name = pending.get('client_name', '')
                client = None
                if client_name:
                    def _search():
                        return list(Client.objects.filter(
                            Q(first_name__icontains=client_name) |
                            Q(last_name__icontains=client_name)
                        )[:1])
                    clients = await sync_to_async(_search)()
                    if clients:
                        client = clients[0]

                if client:
                    await self._show_plan_confirmation(
                        update, context, client,
                        pending['action'], pending['date'],
                        pending['time'], pending['description'],
                    )
                else:
                    await update.message.reply_text("🔍 Введите имя клиента:", reply_markup=main_reply_markup())
                    context.user_data['awaiting_plan_client'] = True
                return
            else:
                await update.message.reply_text("❌ Неверный формат времени. Введите, например: 18:00")
                context.user_data['awaiting_plan_time'] = True
                return

        # Ожидание клиента для планирования
        if context.user_data.get('awaiting_plan_client'):
            context.user_data.pop('awaiting_plan_client', None)
            pending = context.user_data.get('pending_plan', {})

            def _search(t):
                return list(Client.objects.filter(
                    Q(first_name__icontains=t) |
                    Q(last_name__icontains=t) |
                    Q(phone__icontains=t)
                )[:1])

            clients = await sync_to_async(_search)(text)
            if clients:
                await self._show_plan_confirmation(
                    update, context, clients[0],
                    pending['action'], pending['date'],
                    pending.get('time', '09:00'), pending['description'],
                )
            else:
                await update.message.reply_text(
                    f"❌ Клиент «{text}» не найден. Попробуйте снова:",
                    reply_markup=main_reply_markup(),
                )
                context.user_data['awaiting_plan_client'] = True
            return

        # ============ ЕСТЕСТВЕННЫЕ КОМАНДЫ ============
        # Поиск: "найди X", "поиск X"
        for prefix in ('найди ', 'найти ', 'поиск ', 'ищи ', 'найдите '):
            if text_lower.startswith(prefix):
                query_text = text[len(prefix):].strip()
                if query_text:
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

                    clients = await sync_to_async(_search)(query_text)
                    if clients:
                        await show_client_options(update, context, clients[0])
                    else:
                        await update.message.reply_text(
                            f"❌ Клиент «{query_text}» не найден",
                            reply_markup=main_reply_markup(),
                        )
                    return

        if any(word in text_lower for word in ('список', 'клиенты', 'все клиенты')):
            await self.list_command(update, context)
            return

        if 'статистика' in text_lower or text_lower == 'стат':
            await self.stats(update, context)
            return

        if 'события' in text_lower or 'календарь' in text_lower:
            await self._handle_show_events_calendar_from_message(update, context)
            return

        if 'день рождения' in text_lower or 'дни рождения' in text_lower:
            await self.birthdays(update, context)
            return

        if 'помощь' in text_lower or 'помоги' in text_lower:
            await self.help(update, context)
            return

        # ============ 1. ЗАМЕТКА ============
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

        # ============ 2. ОПИСАНИЕ СОБЫТИЯ ============
        if context.user_data.get('awaiting_event_description'):
            context.user_data.pop('awaiting_event_description', None)
            context.user_data['event_description_text'] = text

            scheduled_date = context.user_data.get('event_scheduled_date')
            if scheduled_date:
                client_id = context.user_data.get('planning_client_id')
                action = context.user_data.get('planning_action_type', 'custom')

                def _get_client():
                    return Client.objects.filter(id=client_id).first()

                client = await sync_to_async(_get_client)()
                if not client:
                    await update.message.reply_text("❌ Клиент не найден", reply_markup=main_reply_markup())
                    return

                try:
                    event = await sync_to_async(ScheduledEvent.objects.create)(
                        client=client,
                        title=text[:100],
                        description=text,
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

                    from ..time_utils import format_user_time
                    time_str = format_user_time(scheduled_date)

                    await update.message.reply_text(
                        f"✅ *Событие запланировано!*\n\n"
                        f"👤 {client.first_name} {client.last_name}\n"
                        f"📝 {text}\n"
                        f"📅 {time_str} (MSK)\n"
                        f"📌 Тип: {action_names.get(action, 'событие')}\n\n"
                        f"Я напомню вам об этом!",
                        parse_mode='Markdown',
                        reply_markup=main_reply_markup(),
                    )
                except Exception as e:
                    logger.error(f"Ошибка создания события: {e}", exc_info=True)
                    await update.message.reply_text(f"❌ Ошибка: {e}", reply_markup=main_reply_markup())

                for key in ('planning_client_id', 'planning_action_type',
                            'event_scheduled_date', 'event_description_text'):
                    context.user_data.pop(key, None)
                return

            keyboard = get_months_keyboard()
            await update.message.reply_text(
                f"📝 Описание: {text[:80]}\n\n📅 *Выберите месяц:*",
                parse_mode='Markdown',
                reply_markup=keyboard,
            )
            return

        # ============ 3. EMAIL ============
        if context.user_data.get('awaiting_email', {}).get('stage') == 'subject':
            await self._handle_email_subject(update, context)
            return

        if context.user_data.get('awaiting_email', {}).get('stage') == 'body':
            await self._handle_email_body(update, context)
            return

        # ============ 4. ПОИСК ============
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
                        f"📞 {clients[0].phone}\n\nВыберите тип события:",
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

    # ============ ПЛАНИРОВАНИЕ ГОЛОСОМ / ТЕКСТОМ (GigaChat) ============

    async def _parse_plan_command(self, text: str) -> dict:
        """Парсит текст через GigaChat → {action, date, time, client_name, description}."""
        import httpx
        import json as json_lib
        import uuid

        async with httpx.AsyncClient(verify=False) as http:
            resp = await http.post(
                "https://ngw.devices.sberbank.ru:9443/api/v2/oauth",
                headers={
                    "Content-Type": "application/x-www-form-urlencoded",
                    "Accept": "application/json",
                    "RqUID": str(uuid.uuid4()),
                    "Authorization": f"Basic {settings.GIGACHAT_AUTH_KEY}",
                },
                data="scope=GIGACHAT_API_PERS",
            )
            access_token = resp.json()["access_token"]

        today = datetime.now()
        prompt = f"""Извлеки из текста данные для планирования события.
Текст: "{text}"

Сегодня: {today.strftime('%Y-%m-%d')} ({today.strftime('%A')}, MSK)

Верни ТОЛЬКО JSON без пояснений:
{{
  "action": "call|meeting|reminder|birthday|custom",
  "date": "YYYY-MM-DD",
  "time": "HH:MM",
  "client_name": "имя клиента или пустая строка",
  "description": "краткое описание события"
}}

Правила:
- Если дата относительная ("завтра", "в пятницу") — вычисли от сегодня.
- Если время не указано — верни пустую строку.
- action: "звонок" → call, "встреча" → meeting, "напомни" → reminder, "поздравить" → birthday, иначе custom."""

        async with httpx.AsyncClient(verify=False, timeout=60) as http:
            chat = await http.post(
                "https://gigachat.devices.sberbank.ru/api/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {access_token}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": "GigaChat",
                    "messages": [{"role": "user", "content": prompt}],
                    "temperature": 0.1,
                },
            )
            content = chat.json()["choices"][0]["message"]["content"]

        content = content.strip()
        if content.startswith("```"):
            content = content.strip("`")
            if content.startswith("json"):
                content = content[4:]
            content = content.strip()

        return json_lib.loads(content)

    async def _handle_plan_voice(self, update: Update, context: ContextTypes.DEFAULT_TYPE, text: str):
        """Обработка «запланируй звонок на 25 декабря 18:00»."""
        from django.db.models import Q

        try:
            await update.message.reply_text("🤔 Анализирую команду...")

            parsed = await self._parse_plan_command(text)

            action = parsed.get('action', 'custom')
            date_str = parsed.get('date', '').strip()
            time_str = parsed.get('time', '').strip()
            client_name = parsed.get('client_name', '').strip()
            description = parsed.get('description', '').strip() or text

            if not date_str:
                await update.message.reply_text(
                    "❌ Не удалось определить дату.\n"
                    "Уточните: «Запланируй звонок на 25 декабря 18:00»",
                    reply_markup=main_reply_markup(),
                )
                return

            if not time_str:
                context.user_data['pending_plan'] = {
                    'action': action, 'date': date_str,
                    'client_name': client_name, 'description': description,
                }
                await update.message.reply_text(
                    f"📅 Дата: {date_str}\n\n🕐 Введите время (например, 18:00):",
                    reply_markup=main_reply_markup(),
                )
                context.user_data['awaiting_plan_time'] = True
                return

            client = None
            if client_name:
                def _search():
                    return list(Client.objects.filter(
                        Q(first_name__icontains=client_name) |
                        Q(last_name__icontains=client_name)
                    )[:1])
                clients = await sync_to_async(_search)()
                if clients:
                    client = clients[0]

            if not client:
                context.user_data['pending_plan'] = {
                    'action': action, 'date': date_str, 'time': time_str,
                    'client_name': client_name, 'description': description,
                }
                await update.message.reply_text(
                    f"⚠️ Клиент «{client_name or '—'}» не найден.\n\n🔍 Введите имя клиента:",
                    reply_markup=main_reply_markup(),
                )
                context.user_data['awaiting_plan_client'] = True
                return

            await self._show_plan_confirmation(update, context, client, action, date_str, time_str, description)

        except Exception as e:
            logger.error(f"Ошибка планирования: {e}", exc_info=True)
            await update.message.reply_text(f"❌ Ошибка: {e}", reply_markup=main_reply_markup())

    async def _show_plan_confirmation(self, update, context, client, action, date_str, time_str, description):
        """Показывает подтверждение создания события."""
        from telegram import InlineKeyboardButton, InlineKeyboardMarkup

        action_names = {
            'call': '📞 звонок', 'meeting': '📅 встреча',
            'reminder': '🔔 напоминание', 'birthday': '🎂 поздравление',
            'custom': '📝 событие',
        }

        context.user_data['confirm_plan'] = {
            'client_id': client.id, 'action': action,
            'date': date_str, 'time': time_str, 'description': description,
        }

        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [
                InlineKeyboardButton("✅ Создать", callback_data="plan_confirm_yes"),
                InlineKeyboardButton("❌ Отмена", callback_data="plan_confirm_no"),
            ]
        ])

        await update.message.reply_text(
            f"📋 *Проверьте событие:*\n\n"
            f"👤 {client.first_name} {client.last_name}\n"
            f"📌 Тип: {action_names.get(action, 'событие')}\n"
            f"📅 Дата: {date_str}\n"
            f"🕐 Время: {time_str} (MSK)\n"
            f"📝 {description}\n\n"
            f"Создать?",
            parse_mode='Markdown',
            reply_markup=keyboard,
        )

    async def _create_plan_from_context(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Создаёт событие из context.user_data['confirm_plan']."""
        from ..time_utils import create_user_datetime, format_user_time

        data = context.user_data.pop('confirm_plan', None)
        if not data:
            await update.message.reply_text("❌ Данные потеряны")
            return

        try:
            scheduled_dt = datetime.strptime(f"{data['date']} {data['time']}", "%Y-%m-%d %H:%M")
        except Exception as e:
            await update.message.reply_text(f"❌ Ошибка даты: {e}")
            return

        client = await sync_to_async(Client.objects.get)(id=data['client_id'])

        scheduled_date = create_user_datetime(
            scheduled_dt.year, scheduled_dt.month, scheduled_dt.day,
            scheduled_dt.hour, scheduled_dt.minute,
        )

        event = await sync_to_async(ScheduledEvent.objects.create)(
            client=client,
            title=data['description'][:100],
            description=data['description'],
            event_type=data['action'],
            scheduled_date=scheduled_date,
            is_completed=False,
        )

        time_str_msk = format_user_time(scheduled_date)
        action_names = {
            'call': '📞 звонок', 'meeting': '📅 встречу',
            'reminder': '🔔 напоминание', 'birthday': '🎂 поздравление',
            'custom': '📝 событие',
        }

        await update.message.reply_text(
            f"✅ *Событие запланировано!*\n\n"
            f"👤 {client.first_name} {client.last_name}\n"
            f"📝 {data['description']}\n"
            f"📅 {time_str_msk} (MSK)\n"
            f"📌 Тип: {action_names.get(data['action'], 'событие')}\n\n"
            f"Я напомню вам об этом!",
            parse_mode='Markdown',
            reply_markup=main_reply_markup(),
        )

    # ============ EMAIL ============

    async def handle_email_action(self, update: Update, context: ContextTypes.DEFAULT_TYPE, client_id: int = None):
        query = update.callback_query
        await query.answer()

        if client_id is None:
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

        context.user_data['awaiting_email'] = {'client_id': client_id, 'stage': 'subject'}
        await query.edit_message_text(
            f"✉️ *Отправка письма*\n\n"
            f"👤 Кому: {client.first_name} {client.last_name}\n"
            f"📧 Email: {client.email}\n\n"
            "Введите *тему* письма:",
            parse_mode='Markdown',
        )

    async def _handle_email_subject(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        email_data = context.user_data['awaiting_email']
        email_data['subject'] = update.message.text
        email_data['stage'] = 'body'
        await update.message.reply_text(
            f"📝 Тема: {email_data['subject']}\n\nТеперь введите *текст* письма:",
            parse_mode='Markdown',
        )

    async def _handle_email_body(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
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
                client=client, type='email',
                content=f"Тема: {email_data['subject']}\n\n{email_data['body']}",
                created_at=timezone.now(), completed_at=timezone.now(),
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