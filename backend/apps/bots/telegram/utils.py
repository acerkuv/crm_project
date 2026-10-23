from datetime import datetime
from apps.clients.models import Client, ScheduledEvent

NGROK_URL = "https://553e-194-58-37-17.ngrok-free.app"

def get_client_card(client, show_avatar=True, compact=False):
    """Генерирует карточку клиента"""
    status_emoji = {'vip': '⭐', 'active': '✅', 'regular': '🔄', 'lead': '🆕', 'inactive': '⏸️'}.get(client.status, '📌')
    
    if compact:
        # Компактная версия для списка
        card = f"{status_emoji} *{client.first_name} {client.last_name}*\n"
        card += f"📞 {client.phone}\n"
        if client.company:
            card += f"🏢 {client.company}\n"
        if client.birth_date:
            days_until = (client.birth_date.replace(year=datetime.now().year) - datetime.now().date()).days
            if days_until < 0:
                days_until = (client.birth_date.replace(year=datetime.now().year + 1) - datetime.now().date()).days
            card += f"🎂 {client.birth_date.strftime('%d.%m')} (через {days_until} дн.)\n"
        card += f"📅 В базе: {(datetime.now().date() - client.created_at.date()).days} дн."
        
    else:
        # Полная версия для детального просмотра
        card = f"{status_emoji} *{client.first_name} {client.last_name}*\n"
        
        if show_avatar and client.avatar and client.avatar.name:
            try:
                avatar_url = f"{NGROK_URL}{client.avatar.url}"
                card += f"🖼️ [Аватарка]({avatar_url})\n"
            except:
                pass
        
        card += f"📞 {client.phone}\n"
        if client.email:
            card += f"✉️ {client.email}\n"
        if client.company:
            card += f"🏢 {client.company}\n"
        if client.position:
            card += f"💼 {client.position}\n"
        if client.birth_date:
            days_until = (client.birth_date.replace(year=datetime.now().year) - datetime.now().date()).days
            if days_until < 0:
                days_until = (client.birth_date.replace(year=datetime.now().year + 1) - datetime.now().date()).days
            card += f"🎂 {client.birth_date.strftime('%d.%m.%Y')} (через {days_until} дн.)\n"
        if getattr(client, 'address', ''):
            card += f"📍 {client.address}\n"
        if client.hobby:
            card += f"🎯 {client.hobby[:100]}\n"
        if client.comment:
            card += f"📝 {client.comment[:100]}...\n" if len(client.comment) > 100 else f"📝 {client.comment}\n"
        card += f"📅 В базе: {(datetime.now().date() - client.created_at.date()).days} дн."
        
        # Кастомные поля
        try:
            cfs = list(client.custom_fields.all()[:10])
            if cfs:
                card += "\n\n➕ *Доп. поля:*\n"
                for cf in cfs:
                    card += f"• {cf.name}: {cf.value[:60]}\n"
        except Exception:
            pass
        
        # Последние 3 заметки (Interaction type='note')
        try:
            notes = client.interactions.filter(
                type='note', is_deleted=False
            ).order_by('-created_at')[:3]
            if notes:
                card += "\n\n📝 *Последние заметки:*\n"
                for note in notes:
                    date_str = note.created_at.strftime('%d.%m')
                    content = note.content[:60].replace('\n', ' ')
                    if len(note.content) > 60:
                        content += '...'
                    card += f"• {date_str}: {content}\n"
        except Exception:
            pass

        # Запланированные события
        try:
            from django.utils import timezone as tz
            now = tz.now()
            upcoming = list(client.scheduled_events.filter(
                is_completed=False,
                scheduled_date__gte=now,
            ).order_by('scheduled_date')[:10])

            if upcoming:
                card += "\n\n📅 *Запланированные события:*\n"
                from apps.bots.telegram.time_utils import to_user_time
                for ev in upcoming:
                    ut = to_user_time(ev.scheduled_date)
                    date_str = ut.strftime('%d.%m %H:%M')
                    card += f"🔴 {date_str} — {ev.title[:50]}\n"
        except Exception:
            pass
    
    return card

def get_clients_list_message(clients, page=1, per_page=5):
    """Формирует сообщение со списком клиентов - кнопки под каждой карточкой"""
    from .keyboards import get_client_compact_keyboard
    
    total = clients.count()
    total_pages = (total + per_page - 1) // per_page if total > 0 else 1
    
    start = (page - 1) * per_page
    end = start + per_page
    page_clients = clients[start:end]
    
    if not page_clients:
        return "📭 Клиентов пока нет.", None
    
    message = f"📋 *Клиенты* (стр. {page}/{total_pages}, всего {total})\n\n"
    message += "═" * 30 + "\n\n"
    
    # Создаем клавиатуру с кнопками для каждого клиента
    keyboard = []
    
    for client in page_clients:
        # Карточка клиента (компактная)
        message += get_client_card(client, show_avatar=False, compact=True)
        message += "\n"
        
        if client.avatar and client.avatar.name:
            message += "🖼️ *Есть аватарка*\n"
        
        # Добавляем кнопки ПОД карточкой (2 кнопки в ряд)
        keyboard.append([
            {"text": f"👤 {client.first_name}", "callback_data": f"client_detail_{client.id}"},
            {"text": "📅 План", "callback_data": f"plan_{client.id}"}
        ])
        
        message += "─" * 30 + "\n\n"
    
    # Навигация
    nav_row = []
    if page > 1:
        nav_row.append({"text": "◀️ Назад", "callback_data": f"list_page_{page-1}"})
    nav_row.append({"text": f"📄 {page}/{total_pages}", "callback_data": "noop"})
    if page < total_pages:
        nav_row.append({"text": "Вперед ▶️", "callback_data": f"list_page_{page+1}"})
    keyboard.append(nav_row)
    
    # Общие кнопки
    keyboard.append([
        {"text": "🔍 Поиск", "callback_data": "find_client"},
        {"text": "📊 Статистика", "callback_data": "show_stats"}
    ])
    keyboard.append([
        {"text": "🎂 Дни рождения", "callback_data": "show_birthdays"},
        {"text": "📅 События", "callback_data": "show_events"}
    ])
    
    return message, {"inline_keyboard": keyboard}

def action_names():
    return {
        'call': '📞 звонок',
        'meeting': '📅 встречу',
        'birthday': '🎂 поздравление',
        'reminder': '🔔 напоминание',
        'custom': '📝 событие',
        'note': '📝 заметку'
    }