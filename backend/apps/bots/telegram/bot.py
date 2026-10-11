import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    CommandHandler, 
    MessageHandler, 
    CallbackQueryHandler, 
    ConversationHandler,
    ContextTypes,
    filters
)
from django.conf import settings
from django.utils import timezone
from apps.clients.models import Client, Interaction, ScheduledEvent
from apps.events.models import Event
from datetime import datetime, timedelta
import requests
import json

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
            "📋 /list - Список клиентов\n"
            "🔍 /find - Найти клиента\n"
            "📅 /events - Ближайшие события\n"
            "🎂 /birthdays - Дни рождения\n"
            "📊 /stats - Статистика\n"
            "❓ /help - Помощь\n\n"
            "💡 *Новое:*\n"
            "При просмотре клиента появится кнопка 'Запланировать'"
        )
    
    async def help(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        await update.message.reply_text(
            "📖 *Доступные команды:*\n\n"
            "/start - Приветствие\n"
            "/help - Справка\n"
            "/add - Добавить клиента\n"
            "/list - Список клиентов\n"
            "/list_new - Новые сначала\n"
            "/list_old - Старые сначала\n"
            "/list_alpha - По алфавиту\n"
            "/find - Найти клиента\n"
            "/events - Ближайшие события\n"
            "/birthdays - Дни рождения\n"
            "/stats - Статистика\n\n"
            "📷 *Для добавления аватарки:*\n"
            "1. /avatar [имя или телефон] - найти клиента\n"
            "2. Отправить фото (аватарка обработается в фоне)\n\n"
            "👤 *При добавлении контакта:*\n"
            "Аватарка из контакта загружается автоматически!\n\n"
            "📅 *Планирование событий:*\n"
            "1. /list или /find - найти клиента\n"
            "2. Нажмите 'Запланировать событие'\n"
            "3. Следуйте инструкциям"
        )
    
    # ============ ПОИСК И СПИСКИ ============
    
    async def list_clients(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        clients = Client.objects.all()[:10]
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
        for i, client in enumerate(clients[:5], 1):
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
    
    async def find(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        await update.message.reply_text("🔍 Введите имя или телефон клиента:")
        context.user_data['finding'] = True
    
    async def handle_text(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        text = update.message.text
        
        if context.user_data.get('finding'):
            context.user_data['finding'] = False
            clients = Client.objects.filter(
                first_name__icontains=text
            ) | Client.objects.filter(
                last_name__icontains=text
            ) | Client.objects.filter(
                phone__icontains=text
            )
            
            if clients.exists():
                await show_client_options(update, context, clients.first())
            else:
                await update.message.reply_text("❌ Клиент не найден.")
    
    # ============ РАБОТА С КЛИЕНТОМ ============
    
    async def show_client_actions(self, update: Update, context: ContextTypes.DEFAULT_TYPE, client_id):
        try:
            client = Client.objects.get(id=client_id)
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
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            message,
            parse_mode='Markdown',
            reply_markup=reply_markup
        )
        
        context.user_data['selected_client_id'] = client_id
    
    # ============ FSM: ПЛАНИРОВАНИЕ СОБЫТИЙ ============
    
    async def start_event_planning(self, update: Update, context: ContextTypes.DEFAULT_TYPE, client_id, action_type):
        query = update.callback_query
        await query.answer()
        
        context.user_data['planning_client_id'] = client_id
        context.user_data['planning_action_type'] = action_type
        
        client = Client.objects.get(id=client_id)
        
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
                reply_markup=reply_markup
            )
            return ConversationHandler.END
        
        await query.edit_message_text(
            f"📝 Введите описание {action_names.get(action_type, 'события')} для {client.first_name}:"
        )
        return ConversationHandler.END
    
    async def handle_birthday_choice(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        await query.answer()
        
        client_id = context.user_data.get('planning_client_id')
        client = Client.objects.get(id=client_id)
        
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
            
            event = ScheduledEvent.objects.create(
                client=client,
                title=f"Поздравление с ДР: {client.first_name}",
                description=greeting,
                event_type='birthday',
                scheduled_date=datetime.combine(scheduled_date, timezone.now().time()),
                is_ai_generated=True,
                ai_content=greeting
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
                reply_markup=reply_markup
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
        client = Client.objects.get(id=client_id)
        
        scheduled_date = client.birth_date.replace(year=timezone.now().year)
        if scheduled_date < timezone.now().date():
            scheduled_date = scheduled_date.replace(year=timezone.now().year + 1)
        
        event = ScheduledEvent.objects.create(
            client=client,
            title=f"Поздравление с ДР: {client.first_name}",
            description=text,
            event_type='birthday',
            scheduled_date=datetime.combine(scheduled_date, timezone.now().time()),
            is_ai_generated=False,
            ai_content=text
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
            reply_markup=reply_markup
        )
        
        context.user_data['awaiting_birthday_text'] = False
    
    async def handle_birthday_action(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        await query.answer()
        
        event_id = int(query.data.split('_')[-1])
        event = ScheduledEvent.objects.get(id=event_id)
        
        if query.data.startswith('send_birthday'):
            if event.client.telegram_id:
                await send_telegram_message(
                    event.client.telegram_id,
                    f"🎉 *Поздравление!*\n\n{event.description}"
                )
                event.is_completed = True
                event.completed_at = timezone.now()
                event.save()
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
                import openai
                openai.api_key = settings.OPENAI_API_KEY
                
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
                
                response = openai.ChatCompletion.create(
                    model="gpt-3.5-turbo",
                    messages=[{"role": "user", "content": prompt}],
                    max_tokens=150,
                    temperature=0.7
                )
                return response.choices[0].message.content
        except Exception as e:
            logger.error(f"Ошибка генерации ИИ: {e}")
        
        return f"🎉 Дорогой(ая) {client.first_name}! Поздравляю с днём рождения! Желаю счастья, здоровья и успехов во всех начинаниях! 🎂"
    
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
            await self.start_event_planning(update, context, client_id, action_type)
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
        now = timezone.now()
        events = ScheduledEvent.objects.filter(
            scheduled_date__gte=now,
            is_completed=False
        ).order_by('scheduled_date')[:10]
        
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
        today = timezone.now().date()
        clients_list = []
        
        for client in Client.objects.filter(birth_date__isnull=False):
            if client.birth_date:
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
            if client.comment:
                message += f"   📝 {client.comment[:50]}...\n"
            if client.avatar:
                message += f"   🖼️ Есть аватарка\n"
            message += f"   📅 {client.birth_date.strftime('%d.%m')} (через {days} дн.)\n"
            message += "\n"
        
        await update.message.reply_text(message, parse_mode='Markdown')
    
    async def stats(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        total = Client.objects.count()
        vip = Client.objects.filter(status='vip').count()
        active = Client.objects.filter(status='active').count()
        regular = Client.objects.filter(status='regular').count()
        lead = Client.objects.filter(status='lead').count()
        events = ScheduledEvent.objects.filter(is_completed=False).count()
        ai_events = ScheduledEvent.objects.filter(is_ai_generated=True).count()
        
        message = (
            "📊 *Статистика CRM:*\n\n"
            f"👥 Всего клиентов: *{total}*\n\n"
            "По статусам:\n"
            f"⭐ VIP: {vip}\n"
            f"✅ Активные: {active}\n"
            f"🔄 Постоянные: {regular}\n"
            f"🆕 Лиды: {lead}\n\n"
            f"📅 Запланировано событий: {events}\n"
            f"🤖 Сгенерировано ИИ: {ai_events}"
        )
        await update.message.reply_text(message, parse_mode='Markdown')
    
    async def add(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        await update.message.reply_text(
            "📇 Отправьте контакт, чтобы добавить клиента\n\n"
            "Нажмите на скрепку → Контакт\n\n"
            "🖼️ Аватарка из контакта загрузится автоматически!"
        )
    
    async def handle_contact(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        contact = update.message.contact
        if contact:
            client, created = Client.objects.get_or_create(
                phone=contact.phone_number,
                defaults={
                    'first_name': contact.first_name,
                    'last_name': contact.last_name or '',
                    'telegram_id': str(update.effective_user.id),
                    'status': 'lead'
                }
            )
            
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
        search_query = ' '.join(context.args) if context.args else ''
        if not search_query:
            await update.message.reply_text("📷 Используйте: /avatar [имя или телефон]")
            return
        
        clients = Client.objects.filter(
            first_name__icontains=search_query
        ) | Client.objects.filter(
            last_name__icontains=search_query
        ) | Client.objects.filter(
            phone__icontains=search_query
        )
        
        if clients.exists():
            context.user_data['avatar_client_id'] = clients[0].id
            await update.message.reply_text(
                f"📷 Найден клиент: {clients[0].first_name} {clients[0].last_name}\n"
                "Отправьте фото для этого клиента"
            )
        else:
            await update.message.reply_text("❌ Клиент не найден")

    # ============ ЗАПУСК БОТА ============

    def run_polling(self):
        from telegram.ext import Application
        import os

        logger.info("🚀 Запуск бота в режиме polling...")

        proxy_url = os.environ.get('TELEGRAM_PROXY_URL', '')
        builder = Application.builder().token(self.token)
        if proxy_url:
            logger.info(f"🔗 Использую прокси: {proxy_url}")
            builder = builder.proxy(proxy_url).get_updates_proxy(proxy_url)

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

        # Контакты
        app.add_handler(MessageHandler(filters.CONTACT, self.handle_contact))

        # Текстовые сообщения
        app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_text))

        logger.info("✅ Бот запущен, начинаю polling...")
        app.run_polling(allowed_updates=Update.ALL_TYPES)


# ============ МОДУЛЬНЫЕ ФУНКЦИИ ============

async def show_client_options(update, context, client):
    """Показывает опции для клиента"""
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
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        message,
        parse_mode='Markdown',
        reply_markup=reply_markup
    )


async def send_telegram_message(chat_id, text):
    """Отправка сообщения в Telegram"""
    token = settings.TELEGRAM_BOT_TOKEN
    if not token:
        return
    
    url = f'https://api.telegram.org/bot{token}/sendMessage'
    try:
        requests.post(url, json={
            'chat_id': chat_id,
            'text': text,
            'parse_mode': 'Markdown'
        })
    except Exception as e:
        logger.error(f"Ошибка отправки: {e}")
