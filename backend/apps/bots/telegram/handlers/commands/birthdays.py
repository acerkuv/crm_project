from django.utils import timezone
from ..base import send_message
from apps.clients.models import Client

def handle(chat_id, text):
    """Обработчик команды /birthdays"""
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
    
    if clients_list:
        response = "🎂 *Дни рождения в ближайшую неделю:*\n\n"
        for client, days in sorted(clients_list, key=lambda x: x[1]):
            status_emoji = {'vip': '⭐', 'active': '✅', 'regular': '🔄', 'lead': '🆕', 'inactive': '⏸️'}.get(client.status, '📌')
            response += f"{status_emoji} *{client.first_name} {client.last_name}*\n"
            response += f"   📞 {client.phone}\n"
            if client.company:
                response += f"   🏢 {client.company}\n"
            if client.comment:
                response += f"   📝 {client.comment[:50]}...\n"
            response += f"   📅 {client.birth_date.strftime('%d.%m')} (через {days} дн.)\n"
            response += "\n"
    else:
        response = "🎂 В ближайшую неделю нет дней рождения."
    
    send_message(chat_id, response)
    return True
