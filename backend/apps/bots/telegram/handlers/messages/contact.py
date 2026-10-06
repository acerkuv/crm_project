from ..base import send_message
from apps.clients.models import Client

def handle(chat_id, contact):
    """Обработка контакта"""
    phone = contact.get('phone_number', '')
    first_name = contact.get('first_name', '')
    last_name = contact.get('last_name', '')
    telegram_id = str(chat_id)
    
    client, created = Client.objects.get_or_create(
        phone=phone,
        defaults={
            'first_name': first_name,
            'last_name': last_name or '',
            'telegram_id': telegram_id,
            'status': 'lead'
        }
    )
    
    if created:
        response = f"✅ Клиент добавлен!\n\n👤 {client.first_name} {client.last_name}\n📞 {client.phone}"
    else:
        response = f"ℹ️ Клиент уже существует:\n\n👤 {client.first_name} {client.last_name}\n📞 {client.phone}"
    
    send_message(chat_id, response)
    return True
