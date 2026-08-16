from ..base import send_message
from apps.clients.models import Client, ScheduledEvent

def handle(chat_id, text):
    """Обработчик команды /stats"""
    total = Client.objects.count()
    vip = Client.objects.filter(status='vip').count()
    active = Client.objects.filter(status='active').count()
    regular = Client.objects.filter(status='regular').count()
    lead = Client.objects.filter(status='lead').count()
    events = ScheduledEvent.objects.filter(is_completed=False).count()
    
    response = (
        f"📊 *Статистика CRM:*\n\n"
        f"👥 Всего клиентов: *{total}*\n\n"
        "По статусам:\n"
        f"⭐ VIP: {vip}\n"
        f"✅ Активные: {active}\n"
        f"🔄 Постоянные: {regular}\n"
        f"🆕 Лиды: {lead}\n\n"
        f"📅 Запланировано событий: {events}"
    )
    send_message(chat_id, response)
    return True
