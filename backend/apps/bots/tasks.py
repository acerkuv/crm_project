import logging
from celery import shared_task
from django.core.files.base import ContentFile
from django.utils import timezone
from io import BytesIO
from PIL import Image
import requests
from django.conf import settings
import os

logger = logging.getLogger(__name__)

# Мини-размер для аватарок (70x70)
AVATAR_SIZE = (70, 70)
AVATAR_QUALITY = 85

@shared_task
def process_avatar(client_id, file_id, token):
    """
    Фоновая обработка аватарки клиента с уменьшением до 70x70
    """
    try:
        from apps.clients.models import Client
        
        logger.info(f"📷 Начата обработка аватарки для клиента {client_id}")
        
        client = Client.objects.get(id=client_id)
        
        # Скачиваем фото из Telegram
        file_info_url = f'https://api.telegram.org/bot{token}/getFile?file_id={file_id}'
        file_info = requests.get(file_info_url).json()
        
        if not file_info.get('ok'):
            logger.error(f"❌ Не удалось получить информацию о файле")
            return {"status": "error", "message": "Не удалось получить файл"}
        
        file_path = file_info['result']['file_path']
        file_url = f'https://api.telegram.org/file/bot{token}/{file_path}'
        
        response = requests.get(file_url)
        if response.status_code != 200:
            logger.error(f"❌ Не удалось скачать фото: {response.status_code}")
            return {"status": "error", "message": "Не удалось скачать фото"}
        
        # Обрабатываем изображение
        img = Image.open(BytesIO(response.content))
        
        if img.mode in ('RGBA', 'LA', 'P'):
            img = img.convert('RGB')
        
        # Уменьшаем до мини-размера 70x70
        img.thumbnail(AVATAR_SIZE, Image.Resampling.LANCZOS)
        logger.info(f"📐 Размер аватарки: {img.size}")
        
        output = BytesIO()
        img.save(output, format='JPEG', quality=AVATAR_QUALITY, optimize=True)
        output.seek(0)
        
        # Сохраняем в модель
        filename = f"avatar_{client.id}_{timezone.now().strftime('%Y%m%d_%H%M%S')}.jpg"
        
        media_dir = os.path.join(settings.MEDIA_ROOT, 'avatars')
        if not os.path.exists(media_dir):
            os.makedirs(media_dir, exist_ok=True)
        
        client.avatar.save(filename, ContentFile(output.read()), save=True)
        
        logger.info(f"✅ Мини-аватарка (70x70) сохранена для {client.first_name} {client.last_name}")
        return {"status": "success", "message": f"Аватарка добавлена для {client.first_name}"}
        
    except Exception as e:
        logger.error(f"❌ Ошибка обработки аватарки: {e}")
        return {"status": "error", "message": str(e)}


@shared_task
def check_birthdays():
    """
    Проверка дней рождения и отправка уведомлений
    """
    try:
        from apps.clients.models import Client
        from django.utils import timezone
        
        today = timezone.now().date()
        logger.info(f"🎂 Проверка дней рождения на {today}")
        
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
            for client, days in clients_list:
                logger.info(f"🎂 {client.first_name} {client.last_name} - через {days} дней")
        
        return f"Обработано {len(clients_list)} клиентов с днями рождения"
        
    except Exception as e:
        logger.error(f"❌ Ошибка проверки дней рождения: {e}")
        return f"Ошибка: {str(e)}"




@shared_task
def send_due_reminders():
    """
    Отправляет напоминания о ScheduledEvent, у которых наступило время.
    Работает каждую минуту (или раз в N минут — настраивается в PeriodicTask).
    """
    try:
        from apps.clients.models import ScheduledEvent

        now = timezone.now()
        # События, у которых наступило время, но ещё не выполнены
        events = ScheduledEvent.objects.filter(
            scheduled_date__lte=now,
            is_completed=False,
        ).order_by('scheduled_date')[:50]

        if not events.exists():
            logger.debug("📭 Нет событий для напоминания")
            return "Нет событий"

        owner_chat_id = getattr(settings, 'OWNER_CHAT_ID', None)
        if not owner_chat_id:
            logger.warning("⚠️ OWNER_CHAT_ID не задан — напоминания не отправляются")
            return "OWNER_CHAT_ID не задан"

        token = settings.TELEGRAM_BOT_TOKEN
        sent_count = 0
        errors = 0

        for event in events:
            text = (
                f"🔔 *Напоминание*\n\n"
                f"📌 {event.title}\n"
                f"👤 {event.client.first_name} {event.client.last_name}\n"
                f"📞 {event.client.phone}\n"
                f"📅 {event.scheduled_date.strftime('%d.%m.%Y %H:%M')}\n"
            )
            if event.description:
                text += f"📝 {event.description[:200]}\n"

            try:
                response = requests.post(
                    f'https://api.telegram.org/bot{token}/sendMessage',
                    json={
                        'chat_id': owner_chat_id,
                        'text': text,
                        'parse_mode': 'Markdown',
                    },
                    timeout=10,
                )
                if response.status_code == 200:
                    event.is_completed = True
                    event.completed_at = now
                    event.save(update_fields=['is_completed', 'completed_at'])
                    sent_count += 1
                    logger.info(f"✅ Напоминание отправлено: {event.title} (client_id={event.client_id})")
                else:
                    errors += 1
                    logger.error(f"❌ Telegram API {response.status_code}: {response.text[:200]}")
            except Exception as e:
                errors += 1
                logger.error(f"❌ Ошибка отправки напоминания {event.id}: {e}")

        return f"Отправлено: {sent_count}, ошибок: {errors}"

    except Exception as e:
        logger.error(f"❌ Ошибка в send_due_reminders: {e}", exc_info=True)
        return f"Ошибка: {e}"