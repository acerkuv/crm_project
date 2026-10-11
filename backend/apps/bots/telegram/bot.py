import logging
import os
import base64
import json
import tempfile
from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
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

logger = logging.getLogger(__name__)

# Состояния FSM
(
    SELECTING_CLIENT,
    SELECTING_ACTION,
    ENTERING_EVENT_DESCRIPTION,
    ENTERING_EVENT_DATETIME,
    SELECTING_REMINDER_TYPE,
    CONFIRMING_EVENT,
    ENTERING_BIRTHDAY_MESSAGE,
) = range(7)

# Дополнительные состояния для email
(
    EMAIL_SUBJECT,
    EMAIL_BODY,
) = range(7, 9)


class TelegramBot:
    def __init__(self):
        self.token = settings.TELEGRAM_BOT_TOKEN
        logger.info(f"🤖 Бот инициализирован")

    # ============ ХЭНДЛЕРЫ КОМАНД ============

    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user = update.effective_user
        await update.message.reply_text(
            f"👋 Привет, {user.first_name}!\n\n"
            "Я CRM бот для управления клиентами.\n"
            "Вот что я умею:\n\n"
            "📝 /add - Добавить нового клиента\n"
            "📸 Отправь фото визитки — распознаю данные\n"
            "📋 /list - Список клиентов\n"
            "🔍 /find - Найти клиента\n"
            "📅 /events - Ближайшие события\n"
            "🎂 /birthdays - Дни рождения\n"
            "📊 /stats - Статистика\n"
            "❓ /help - Помощь\n\n"
            "💡 *Новое:*\n"
            "• Распознавание визиток по фото\n"
            "• Отправка email клиентам\n"
            "• Кликабельные телефоны"
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
            "В карточке клиента нажми '✉️ Написать' — бот отправит письмо"
        )

    # ============ ПОИСК И СПИСКИ ============

    async def list_clients(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        clients = await self._get_clients_list()
        if not clients:
            await update.message.reply_text("📭 Клиентов пока нет.")
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
        keyboard.append([InlineKeyboardButton("📋 Все клиенты", callback_data="list_all")])

        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text(
            message,
            parse_mode='Markdown',
            reply_markup=reply_markup
        )

    async def _get_clients_list(self):
        """Получить список клиентов (sync-to-async wrapper)."""
        from asgiref.sync import sync_to_async
        return await sync_to_async(lambda: list(Client.objects.all()[:10]))()

    async def find(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        await update.message.reply_text("🔍 Введите имя или телефон клиента:")
        context.user_data['finding'] = True

    async def handle_text(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        text = update.message.text

        # --- Email: ввод темы ---
        if context.user_data.get('awaiting_email', {}).get('stage') == 'subject':
            await self._handle_email_subject(update, context)
            return

        # --- Email: ввод тела ---
        if context.user_data.get('awaiting_email', {}).get('stage') == 'body':
            await self._handle_email_body(update, context)
            return

        # --- Поиск ---
        if context.user_data.get('finding'):
            context.user_data['finding'] = False
            from asgiref.sync import sync_to_async

            def _search(t):
                return list(
                    Client.objects.filter(first_name__icontains=t)
                    | Client.objects.filter(last_name__icontains=t)
                    | Client.objects.filter(phone__icontains=t)
                )

            clients = await sync_to_async(_search)(text)

            if clients:
                await show_client_options(update, context, clients[0])
            else:
                await update.message.reply_text("❌ Клиент не найден.")
            return

    # ============ РАБОТА С КЛИЕНТОМ ============

    async def show_client_actions(self, update: Update, context: ContextTypes.DEFAULT_TYPE, client_id):
        from asgiref.sync import sync_to_async

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

    # ============ FSM: ПЛАНИРОВАНИЕ СОБЫТИЙ ============

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

    # ============ РАСПОЗНАВАНИЕ ВИЗИТОК ============

    async def handle_photo(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработка фото — распознавание визитки или аватарки."""
        from asgiref.sync import sync_to_async

        # Если ожидаем аватарку для клиента
        if context.user_data.get('avatar_client_id'):
            await self._save_avatar(update, context)
            return

        # Иначе — визитка
        photo = update.message.photo[-1]
        file = await photo.get_file()

        with tempfile.NamedTemporaryFile(delete=False, suffix='.jpg') as tmp:
            await file.download_to_drive(tmp.name)
            tmp_path = tmp.name

        try:
            await update.message.reply_text("🔍 Распознаю данные с визитки...")

            data = await self._recognize_business_card(tmp_path)

            if not data or not (data.get('phone') or data.get('email')):
                await update.message.reply_text(
                    "❌ Не удалось распознать данные.\n\n"
                    "Попробуйте:\n"
                    "• Сфотографировать визитку крупнее\n"
                    "• Обеспечить лучшее освещение\n"
                    "• Держать камеру параллельно визитке"
                )
                return

            # Сохраняем во временное хранилище
            context.user_data['pending_contact'] = data

            keyboard = [
                [InlineKeyboardButton("✅ Сохранить", callback_data="save_contact")],
                [InlineKeyboardButton("❌ Отмена", callback_data="cancel_contact")],
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)

            text = "📇 *Распознано:*\n\n"
            text += f"👤 {data.get('first_name', '')} {data.get('last_name', '')}\n"
            if data.get('phone'):
                text += f"📞 {data['phone']}\n"
            if data.get('email'):
                text += f"✉️ {data['email']}\n"
            if data.get('company'):
                text += f"🏢 {data['company']}\n"
            if data.get('position'):
                text += f"💼 {data['position']}\n"
            text += "\nСохранить в CRM?"

            await update.message.reply_text(
                text,
                parse_mode='Markdown',
                reply_markup=reply_markup,
            )

        except Exception as e:
            logger.error(f"Ошибка обработки фото: {e}")
            await update.message.reply_text(f"❌ Ошибка: {e}")
        finally:
            try:
                os.unlink(tmp_path)
            except Exception:
                pass

    async def _recognize_business_card(self, image_path: str) -> dict:
        """Распознать визитку через GigaChat."""
        from openai import AsyncOpenAI
        import httpx

        # 1. Получаем токен доступа из ключа авторизации
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

        # 2. Вызываем GigaChat через OpenAI SDK
        client = AsyncOpenAI(
            api_key=access_token,
            base_url="https://api.giga.chat/v1",
            http_client=httpx.AsyncClient(verify=False),  # отключаем проверку SSL
        )

        with open(image_path, 'rb') as f:
            image_data = base64.b64encode(f.read()).decode('utf-8')

        response = await client.chat.completions.create(
            model="GigaChat-2-Max",  # или GigaChat-Max
            messages=[{
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": (
                            "Распознай данные с визитки. Верни ТОЛЬКО JSON:\n"
                            '{"first_name": "", "last_name": "", "phone": "", '
                            '"email": "", "company": "", "position": ""}'
                        ),
                    },
                    {
                        "type": "image_url",
                        "image_url": {"url": f"data:image/jpeg;base64,{image_data}"},
                    },
                ],
            }],
            max_tokens=500,
        )

        return json.loads(response.choices[0].message.content)

    async def handle_save_contact(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Сохранение распознанного контакта."""
        from asgiref.sync import sync_to_async

        query = update.callback_query
        await query.answer()

        data = context.user_data.get('pending_contact')
        if not data:
            await query.edit_message_text("❌ Данные потеряны, попробуйте снова.")
            return

        # Ищем по телефону или email
        phone = data.get('phone', '').strip()
        email = data.get('email', '').strip()

        def _find_existing():
            if phone:
                c = Client.objects.filter(phone=phone).first()
                if c:
                    return c
            if email:
                c = Client.objects.filter(email=email).first()
                if c:
                    return c
            return None

        existing = await sync_to_async(_find_existing)()

        if existing:
            # Обновляем
            for field in ['first_name', 'last_name', 'email', 'company', 'position']:
                if data.get(field):
                    setattr(existing, field, data[field])
            await sync_to_async(existing.save)()
            await query.edit_message_text(
                f"✅ Клиент обновлён:\n"
                f"👤 {existing.first_name} {existing.last_name}\n"
                f"📞 {existing.phone}"
            )
        else:
            # Создаём нового
            client = await sync_to_async(Client.objects.create)(
                first_name=data.get('first_name', '') or 'Без имени',
                last_name=data.get('last_name', ''),
                phone=phone or f"unknown_{timezone.now().timestamp()}",
                email=email,
                company=data.get('company', ''),
                position=data.get('position', ''),
                telegram_id=str(update.effective_user.id),
                status='lead',
            )
            await query.edit_message_text(
                f"✅ Клиент добавлен:\n"
                f"👤 {client.first_name} {client.last_name}\n"
                f"📞 {client.phone}\n"
                f"✉️ {client.email or '—'}"
            )

        context.user_data.pop('pending_contact', None)

    async def handle_cancel_contact(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Отмена сохранения контакта."""
        query = update.callback_query
        await query.answer()
        context.user_data.pop('pending_contact', None)
        await query.edit_message_text("❌ Отменено.")

    # ============ EMAIL ============

    async def handle_email_action(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Начало отправки email клиенту."""
        from asgiref.sync import sync_to_async

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
        from asgiref.sync import sync_to_async

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

            # Сохраняем Interaction
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
                f"📝 Тема: {email_data['subject']}"
            )
        except Exception as e:
            logger.error(f"Ошибка отправки email: {e}")
            await update.message.reply_text(f"❌ Ошибка отправки: {e}")

        context.user_data.pop('awaiting_email', None)

    # ============ ЗВОНКИ ============

    async def handle_call_action(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Отправка контакта для кликабельного звонка."""
        from asgiref.sync import sync_to_async

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
            f"Нажмите на номер ниже — телефон предложит позвонить:",
            parse_mode='Markdown',
        )

        await query.message.reply_contact(
            phone_number=client.phone,
            first_name=client.first_name,
            last_name=client.last_name or '',
        )

    # ============ ОБРАБОТЧИКИ КНОПОК ============

    async def button_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        data = query.data

        if data.startswith('client_'):
            client_id = int(data.split('_')[1])
            await self.show_client_actions(update, context, client_id)
            return

        if data.startswith('action_'):
            parts = data.split('_')
            client_id = int(parts[1])
            action_type = parts[2]

            # Сохраняем выбранного клиента
            context.user_data['selected_client_id'] = client_id

            if action_type == 'call':
                await self.handle_call_action(update, context)
                return

            if action_type == 'message':
                await self.handle_email_action(update, context)
                return

            await self.start_event_planning(update, context, client_id, action_type)
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

        if data == 'back_to_list':
            await self.list_clients(update, context)
            return

        if data == 'list_all':
            await self.list_clients(update, context)
            return

    # ============ ДРУГИЕ КОМАНДЫ ============

    async def events(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        from asgiref.sync import sync_to_async

        now = timezone.now()

        def _get_events():
            return list(
                ScheduledEvent.objects.filter(
                    scheduled_date__gte=now,
                    is_completed=False,
                ).order_by('scheduled_date')[:10]
            )

        events = await sync_to_async(_get_events)()

        if not events:
            await update.message.reply_text("📅 Нет запланированных событий.")
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

        await update.message.reply_text(message, parse_mode='Markdown')

    async def birthdays(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        from asgiref.sync import sync_to_async

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
            await update.message.reply_text("🎂 В ближайшую неделю нет дней рождения.")
            return

        message = "🎂 *Дни рождения в ближайшую неделю:*\n\n"
        for client, days in sorted(clients_list, key=lambda x: x[1]):
            status_emoji = {'vip': '⭐', 'active': '✅', 'regular': '🔄', 'lead': '🆕', 'inactive': '⏸️'}.get(client.status, '📌')
            message += f"{status_emoji} *{client.first_name} {client.last_name}*\n"
            message += f"   📞 {client.phone}\n"
            if client.company:
                message += f"   🏢 {client.company}\n"
            message += f"   📅 {client.birth_date.strftime('%d.%m')} (через {days} дн.)\n\n"

        await update.message.reply_text(message, parse_mode='Markdown')

    async def stats(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        from asgiref.sync import sync_to_async

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
        await update.message.reply_text(message, parse_mode='Markdown')

    async def add(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        await update.message.reply_text(
            "📇 *Добавить клиента:*\n\n"
            "1. *Отправьте контакт* — нажмите 📎 → Контакт\n\n"
            "2. *Отправьте фото визитки* — бот распознает ФИО, телефон, email, компанию\n\n"
            "🖼️ Аватарка из контакта загрузится автоматически!",
            parse_mode='Markdown',
        )

    async def handle_contact(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        from asgiref.sync import sync_to_async

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
                f"📞 {client.phone}"
            )
        else:
            await update.message.reply_text(
                f"ℹ️ Клиент уже существует:\n\n"
                f"👤 {client.first_name} {client.last_name}\n"
                f"📞 {client.phone}"
            )

    # ============ АВАТАРКИ ============

    async def avatar(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        from asgiref.sync import sync_to_async

        search_query = ' '.join(context.args) if context.args else ''
        if not search_query:
            await update.message.reply_text("📷 Используйте: /avatar [имя или телефон]")
            return

        def _find():
            return list(
                Client.objects.filter(first_name__icontains=search_query)
                | Client.objects.filter(last_name__icontains=search_query)
                | Client.objects.filter(phone__icontains=search_query)
            )

        clients = await sync_to_async(_find)()

        if clients:
            context.user_data['avatar_client_id'] = clients[0].id
            await update.message.reply_text(
                f"📷 Найден клиент: {clients[0].first_name} {clients[0].last_name}\n"
                "Отправьте фото для этого клиента"
            )
        else:
            await update.message.reply_text("❌ Клиент не найден")

    async def _save_avatar(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Сохранение аватарки клиента."""
        from asgiref.sync import sync_to_async

        client_id = context.user_data.pop('avatar_client_id', None)
        if not client_id:
            return

        photo = update.message.photo[-1]
        file = await photo.get_file()

        with tempfile.NamedTemporaryFile(delete=False, suffix='.jpg') as tmp:
            await file.download_to_drive(tmp.name)

            client = await sync_to_async(Client.objects.get)(id=client_id)
            from django.core.files import File
            with open(tmp.name, 'rb') as f:
                client.avatar.save(f'avatar_{client_id}.jpg', File(f), save=True)

            os.unlink(tmp.name)

        await update.message.reply_text(
            f"✅ Аватарка сохранена для {client.first_name} {client.last_name}"
        )

    # ============ ЗАПУСК БОТА ============

    def run_polling(self):
        from telegram.ext import Application
        import os

        logger.info("🚀 Запуск бота в режиме polling...")

        proxy_url = os.environ.get('TELEGRAM_PROXY_URL', '')
        builder = Application.builder().token(self.token)
        if proxy_url:
            logger.info(f"🔗 Использую прокси: {proxy_url}")
            builder = builder.proxy_url(proxy_url).get_updates_proxy_url(proxy_url)

        app = builder.build()

        # Команды
        app.add_handler(CommandHandler("start", self.start))
        app.add_handler(CommandHandler("help", self.help))
        app.add_handler(CommandHandler("list", self.list_clients))
        app.add_handler(CommandHandler("find", self.find))
        app.add_handler(CommandHandler("events", self.events))
        app.add_handler(CommandHandler("birthdays", self.birthdays))
        app.add_handler(CommandHandler("stats", self.stats))
        app.add_handler(CommandHandler("add", self.add))
        app.add_handler(CommandHandler("avatar", self.avatar))

        # Callback-кнопки
        app.add_handler(CallbackQueryHandler(self.button_handler))

        # Контакты (из Telegram)
        app.add_handler(MessageHandler(filters.CONTACT, self.handle_contact))

        # Фото (визитки + аватарки)
        app.add_handler(MessageHandler(filters.PHOTO, self.handle_photo))

        # Текстовые сообщения (поиск, email, FSM)
        app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_text))

        logger.info("✅ Бот запущен, начинаю polling...")
        app.run_polling(allowed_updates=Update.ALL_TYPES)


# ============ МОДУЛЬНЫЕ ФУНКЦИИ ============

async def show_client_options(update, context, client):
    """Показывает опции для клиента."""
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

    await update.message.reply_text(
        message,
        parse_mode='Markdown',
        reply_markup=reply_markup,
    )


async def send_telegram_message(chat_id, text):
    """Отправка сообщения в Telegram."""
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