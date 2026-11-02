import logging
import os
from io import BytesIO

import requests
from celery import shared_task
from django.conf import settings
from django.core.files.base import ContentFile
from django.utils import timezone
from PIL import Image

logger = logging.getLogger(__name__)

AVATAR_SIZE = (70, 70)
AVATAR_QUALITY = 85


def _tg_post(method: str, payload: dict, timeout: int = 10):
    """Обёртка над Telegram Bot API с прокси из настроек."""
    token = settings.TELEGRAM_BOT_TOKEN
    proxy = getattr(settings, 'TELEGRAM_PROXY_URL', '') or None
    proxies = {'https': proxy, 'http': proxy} if proxy else None
    return requests.post(
        f'https://api.telegram.org/bot{token}/{method}',
        json=payload, proxies=proxies, timeout=timeout,
    )


@shared_task
def process_avatar(client_id, file_id, token):
    """Фоновая обработка аватарки клиента (70x70)."""
    try:
        from apps.clients.models import Client

        logger.info(f"📷 Начата обработка аватарки для клиента {client_id}")
        client = Client.objects.get(id=client_id)

        file_info = requests.get(
            f'https://api.telegram.org/bot{token}/getFile?file_id={file_id}'
        ).json()
        if not file_info.get('ok'):
            logger.error("❌ Не удалось получить информацию о файле")
            return {"status": "error", "message": "Не удалось получить файл"}

        file_path = file_info['result']['file_path']
        response = requests.get(f'https://api.telegram.org/file/bot{token}/{file_path}')
        if response.status_code != 200:
            logger.error(f"❌ Не удалось скачать фото: {response.status_code}")
            return {"status": "error", "message": "Не удалось скачать фото"}

        img = Image.open(BytesIO(response.content))
        if img.mode in ('RGBA', 'LA', 'P'):
            img = img.convert('RGB')

        img.thumbnail(AVATAR_SIZE, Image.Resampling.LANCZOS)
        output = BytesIO()
        img.save(output, format='JPEG', quality=AVATAR_QUALITY, optimize=True)
        output.seek(0)

        filename = f"avatar_{client.id}_{timezone.now().strftime('%Y%m%d_%H%M%S')}.jpg"
        media_dir = os.path.join(settings.MEDIA_ROOT, 'avatars')
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
    Проверка ДР за 7 дней и уведомление владельцев (по TelegramUser).
    Фикс: 29.02 → 28.02 в невисокосные годы; без N+1 через select/prefetch.
    """
    try:
        from apps.clients.models import Client
        from apps.bots.telegram.birthday_utils import next_birthday
        from apps.users.models import TelegramUser

        today = timezone.now().date()
        logger.info(f"🎂 Проверка дней рождения на {today}")

        sent = 0
        total_clients = 0

        # Один запрос со всеми клиентами, разложим по user_id
        all_clients = list(
            Client.objects.filter(birth_date__isnull=False)
            .only('id', 'user_id', 'first_name', 'last_name', 'phone', 'birth_date')
        )
        by_user = {}
        for c in all_clients:
            by_user.setdefault(c.user_id, []).append(c)

        for tg_user in TelegramUser.objects.filter(is_active=True).select_related('user'):
            user_clients = by_user.get(tg_user.user_id, [])
            if not user_clients:
                continue

            upcoming = []
            for c in user_clients:
                nb = next_birthday(c.birth_date, today)
                if nb is None:
                    continue
                days = (nb - today).days
                if 0 <= days <= 7:
                    upcoming.append((c, days))

            if not upcoming:
                continue

            total_clients += len(upcoming)
            text = f"🎂 *Дни рождения на неделе* (на {today.strftime('%d.%m.%Y')}):\n\n"
            for c, d in sorted(upcoming, key=lambda x: x[1]):
                when = 'сегодня' if d == 0 else f"через {d} дн."
                text += f"• *{c.first_name} {c.last_name}* — {c.birth_date.strftime('%d.%m')} ({when})\n"
                if c.phone:
                    text += f"  📞 {c.phone}\n"

            try:
                resp = _tg_post('sendMessage', {
                    'chat_id': tg_user.telegram_id,
                    'text': text,
                    'parse_mode': 'Markdown',
                })
                if resp.status_code == 200:
                    sent += 1
                    logger.info(f"🎂 check_birthdays: отправлено {tg_user.telegram_id} ({len(upcoming)} ДР)")
                else:
                    logger.error(
                        f"🎂 check_birthdays: {tg_user.telegram_id} → "
                        f"{resp.status_code}: {resp.text[:200]}"
                    )
            except Exception as e:
                logger.error(f"🎂 check_birthdays: {tg_user.telegram_id}: {e}")

        return f"Отправлено {sent} уведомлений, обработано {total_clients} ДР"
    except Exception as e:
        logger.error(f"❌ Ошибка проверки дней рождения: {e}", exc_info=True)
        return f"Ошибка: {str(e)}"


@shared_task
def send_due_reminders():
    """
    Напоминания о событиях.

    Фикс:
    - адресат = владелец события (event.user.telegram_profile), а не один OWNER_CHAT_ID;
    - нет нижней границы окна: берём всё, что не отправлено и наступит ≤ now+5мин
      (дедуп через reminder_sent_at; устойчиво к пропущенным тикам beat);
    - для event_type='birthday' с telegram_id клиента — шлём поздравление клиенту,
      помечаем is_completed=True (это и есть Этап B).
    """
    from datetime import timedelta
    from apps.clients.models import ScheduledEvent
    from apps.bots.telegram.time_utils import to_user_time
    from apps.users.models import TelegramUser

    token = settings.TELEGRAM_BOT_TOKEN
    if not token:
        logger.warning("send_due_reminders: TELEGRAM_BOT_TOKEN не задан")
        return "Пропущено: нет TELEGRAM_BOT_TOKEN"

    now = timezone.now()
    window_end = now + timedelta(minutes=5)

    events = list(
        ScheduledEvent.objects.filter(
            is_completed=False,
            reminder_sent_at__isnull=True,
            scheduled_date__lte=window_end,
        ).select_related('client', 'user').order_by('scheduled_date')
    )

    sent_owner = 0
    sent_client = 0

    # Кэш профилей владельцев: user_id → telegram_id
    owner_ids = {e.user_id for e in events if e.user_id}
    owner_map = {
        tu.user_id: tu.telegram_id
        for tu in TelegramUser.objects.filter(user_id__in=owner_ids, is_active=True)
    } if owner_ids else {}

    for event in events:
        ut = to_user_time(event.scheduled_date)

        # === B: авто-поздравление клиенту (event_type='birthday') ===
        if event.event_type == 'birthday' and event.client and event.client.telegram_id:
            greet_text = event.description or event.title
            try:
                resp = _tg_post('sendMessage', {
                    'chat_id': event.client.telegram_id,
                    'text': greet_text,
                    'parse_mode': 'Markdown',
                })
                if resp.status_code == 200:
                    event.is_completed = True
                    event.completed_at = timezone.now()
                    event.reminder_sent_at = timezone.now()
                    event.save(update_fields=['is_completed', 'completed_at', 'reminder_sent_at'])
                    sent_client += 1
                    logger.info(f"🎉 birthday: event_id={event.id} → клиенту {event.client.telegram_id}")
                else:
                    logger.error(
                        f"🎉 birthday: event_id={event.id} → {resp.status_code}: {resp.text[:200]}"
                    )
                continue
            except Exception as e:
                logger.error(f"🎉 birthday: event_id={event.id} ошибка: {e}", exc_info=True)
                continue

        # === Обычное напоминание владельцу ===
        owner_chat_id = owner_map.get(event.user_id)
        if not owner_chat_id:
            owner_chat_id = getattr(settings, 'OWNER_CHAT_ID', '')
        if not owner_chat_id:
            logger.warning(f"🔔 event_id={event.id}: нет адресата (user_id={event.user_id})")
            continue

        text = (
            f"🔔 *Напоминание*\n\n"
            f"📌 {event.title}\n"
            f"👤 {event.client.first_name} {event.client.last_name}\n"
            f"📞 {event.client.phone}\n"
            f"📅 {ut.strftime('%d.%m %H:%M')}\n"
        )
        if event.description:
            text += f"📝 {event.description[:200]}\n"

        try:
            resp = _tg_post('sendMessage', {
                'chat_id': owner_chat_id,
                'text': text,
                'parse_mode': 'Markdown',
            })
            if resp.status_code == 200:
                event.reminder_sent_at = timezone.now()
                event.save(update_fields=['reminder_sent_at'])
                sent_owner += 1
                logger.info(f"🔔 send_due_reminders: event_id={event.id} «{event.title}» → отправлено")
            else:
                logger.error(
                    f"🔔 send_due_reminders: event_id={event.id} "
                    f"Telegram вернул {resp.status_code}: {resp.text[:200]}"
                )
        except Exception as e:
            logger.error(f"🔔 send_due_reminders: event_id={event.id} ошибка: {e}", exc_info=True)

    if sent_owner or sent_client:
        return f"Напоминаний владельцам: {sent_owner}, поздравлений клиентам: {sent_client}"
    return "Нет событий для напоминания"