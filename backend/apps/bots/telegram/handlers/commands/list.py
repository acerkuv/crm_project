from django.db.models import Q
from ..base import send_message
from ...utils import get_client_card
from ...keyboards import get_client_compact_keyboard
from apps.clients.models import Client
import logging

logger = logging.getLogger(__name__)

# Количество клиентов на одной странице
CLIENTS_PER_PAGE = 5

def handle(chat_id, text):
    """Обработчик команды /list - с пагинацией"""
    
    # Разбираем аргументы
    parts = text.split(' ', 1)
    filter_text = None
    page = 1
    
    # Проверяем аргументы
    if len(parts) > 1:
        arg = parts[1].strip()
        if arg.isdigit():
            # Если аргумент - число, это номер страницы
            page = int(arg)
        else:
            filter_text = arg
    
    # Формируем запрос
    if filter_text:
        if len(filter_text) == 1 and filter_text.isalpha():
            letter = filter_text.upper()
            clients = Client.objects.filter(
                Q(first_name__istartswith=letter) |
                Q(last_name__istartswith=letter)
            ).order_by('first_name')
            
            if not clients.exists():
                send_message(chat_id, f"📭 Нет клиентов на букву '{letter}'")
                return True
            
            # Отправляем с пагинацией
            send_clients_with_pagination(chat_id, clients, page, f"на букву '{letter}'")
            
        else:
            clients = Client.objects.filter(
                Q(first_name__icontains=filter_text) |
                Q(last_name__icontains=filter_text)
            ).order_by('first_name')
            
            if not clients.exists():
                send_message(chat_id, f"📭 Нет клиентов с именем или фамилией '{filter_text}'")
                return True
            
            send_clients_with_pagination(chat_id, clients, page, f"по запросу '{filter_text}'")
    else:
        # Все клиенты
        clients = Client.objects.all().order_by('-created_at')
        
        if not clients.exists():
            send_message(chat_id, "📭 Клиентов пока нет")
            return True
        
        send_clients_with_pagination(chat_id, clients, page, "все")
    
    return True

def send_clients_with_pagination(chat_id, clients, page, filter_name):
    """Отправляет клиентов с пагинацией"""
    total = clients.count()
    total_pages = (total + CLIENTS_PER_PAGE - 1) // CLIENTS_PER_PAGE
    
    # Проверяем, что страница существует
    if page > total_pages:
        send_message(chat_id, f"❌ Страница {page} не существует. Всего страниц: {total_pages}")
        return
    
    # Вычисляем смещение
    start = (page - 1) * CLIENTS_PER_PAGE
    end = start + CLIENTS_PER_PAGE
    page_clients = clients[start:end]
    
    # Отправляем заголовок
    header = f"📋 *Клиенты {filter_name}* (стр. {page}/{total_pages}, всего {total})"
    send_message(chat_id, header)
    
    # Отправляем каждого клиента отдельным сообщением
    for client in page_clients:
        card = get_client_card(client, show_avatar=False, compact=True)
        keyboard = get_client_compact_keyboard(client.id)
        send_message(chat_id, card, reply_markup=keyboard)
    
    # Отправляем навигацию
    nav_message = "─" * 30 + "\n\n"
    nav_message += "📌 *Навигация:*\n"
    
    if page > 1:
        nav_message += f"◀️ /list {page - 1} - Предыдущая\n"
    nav_message += f"📄 Страница {page}/{total_pages}\n"
    if page < total_pages:
        nav_message += f"▶️ /list {page + 1} - Следующая\n"
    
    nav_message += "\n💡 *Советы:*\n"
    nav_message += "/list А - клиенты на букву 'А'\n"
    nav_message += "/list 2 - вторая страница\n"
    nav_message += "/list Анна - поиск по имени\n"
    nav_message += "/find Анна - детальный поиск"
    
    send_message(chat_id, nav_message)
