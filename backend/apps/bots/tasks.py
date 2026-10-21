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
    Проверка ДР сегодня + GigaChat поздравление + отправка владельцу.
    Запускается каждый день в 09:00 MSK.
    """
    import httpx
    import json as json_lib
    import uuid
    from datetime import date

    try:
        from apps.clients.models import Client

        today = date.today()
        logger.info(f"🎂 check_birthdays: {today}")

        # Клиенты с ДР сегодня
        clients = Client.objects.filter(
            birth_date__month=today.month,
            birth_date__day=today.day,
        )

        if not clients.exists():
            logger.info("🎂 Сегодня ДР нет")
            return "Нет ДР"

        owner_chat_id = getattr(settings, 'OWNER_CHAT_ID', None)
        if not owner_chat_id:
            logger.warning("⚠️ OWNER_CHAT_ID не задан")
            return "OWNER_CHAT_ID не задан"

        # GigaChat OAuth
        async def _get_token():
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
                return resp.json()["access_token"]

        # GigaChat поздравление
        async def _generate_greeting(client):
            token = await _get_token()

            hobby = client.hobby or ''
            comment = client.comment or ''
            company = client.company or ''
            position = client.position or ''

            prompt = f"""Создай персонализированное поздравление с днём рождения для {client.first_name} {client.last_name}.
{('Хобби: ' + hobby) if hobby else ''}
{('Компания: ' + company) if company else ''}
{('Должность: ' + position) if position else ''}
{('Заметки: ' + comment[:200]) if comment else ''}

Поздравление должно быть:
- Тёплым и искренним
- Персонализированным (упомяни хобби, если есть)
- Коротким (3-5 предложений)

Верни ТОЛЬКО текст поздравления, без пояснений."""

            async with httpx.AsyncClient(verify=False, timeout=60) as http:
                chat = await http.post(
                    "https://gigachat.devices.sberbank.ru/api/v1/chat/completions",
                    headers={
                        "Authorization": f"Bearer {token}",
                        "Content-Type": "application/json",
                    },
                    json={
                        "model": "GigaChat",
                        "messages": [{"role": "user", "content": prompt}],
                        "temperature": 0.7,
                    },
                )
                content = chat.json()["choices"][0]["message"]["content"]

            return content.strip()

        # Отправка в Telegram
        def _send_to_owner(text):
            import requests as req
            token = settings.TELEGRAM_BOT_TOKEN
            proxy_url = os.environ.get('TELEGRAM_PROXY_URL', '')
            proxies = {'http': proxy_url, 'https': proxy_url} if proxy_url else None

            req.post(
                f'https://api.telegram.org/bot{token}/sendMessage',
                json={
                    'chat_id': owner_chat_id,
                    'text': text,
                    'parse_mode': 'Markdown',
                },
                timeout=10,
                proxies=proxies,
            )

        # Обрабатываем каждого клиента
        import asyncio
        sent_count = 0

        for client in clients:
            try:
                greeting = asyncio.run(_generate_greeting(client))

                hobby_str = f"\n🎯 Хобби: {client.hobby}" if client.hobby else ""

                text = (
                    f"🎂 *Сегодня ДР у {client.first_name} {client.last_name}!*\n"
                    f"{hobby_str}\n\n"
                    f"🤖 *Поздравление:*\n{greeting}\n\n"
                    f"_Отправьте клиенту вручную или скопируйте текст._"
                )

                _send_to_owner(text)
                sent_count += 1
                logger.info(f"✅ Поздравление отправлено владельцу для {client.first_name}")

            except Exception as e:
                logger.error(f"❌ Ошибка поздравления для {client.id}: {e}", exc_info=True)

        return f"Отправлено поздравлений: {sent_count}"

    except Exception as e:
        logger.error(f"❌ Ошибка в check_birthdays: {e}", exc_info=True)
        return f"Ошибка: {e}"




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
        proxy_url = os.environ.get('TELEGRAM_PROXY_URL', '')
        proxies = {'http': proxy_url, 'https': proxy_url} if proxy_url else None
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
                    proxies=proxies,
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