"""Обработка фото: визитки, аватарки, распознавание через GigaChat."""
import base64
import json
import logging
import os
import tempfile
import uuid

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from django.conf import settings
from django.utils import timezone
from django.core.files.base import ContentFile
from asgiref.sync import sync_to_async

from apps.clients.models import Client
from .helpers import main_reply_markup, process_avatar

logger = logging.getLogger(__name__)


class PhotosMixin:
    """Методы для обработки фото: визитки и аватарки."""

    async def handle_photo(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработка фото — распознавание визитки или аватарки."""
        logger.info(f"📷 Получено фото. avatar_client_id={context.user_data.get('avatar_client_id')}")

        if context.user_data.get('avatar_client_id'):
            logger.info(f"📷 Обрабатываю как аватарку для client_id={context.user_data.get('avatar_client_id')}")
            await self._save_avatar(update, context)
            return

        logger.info("📷 Обрабатываю как визитку")
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
            if data.get('birth_date'):
                text += f"🎂 {data['birth_date']}\n"
            text += "\nСохранить в CRM?"

            await update.message.reply_text(text, parse_mode='Markdown', reply_markup=reply_markup)
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
        import httpx

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

        headers = {"Authorization": f"Bearer {access_token}"}

        async with httpx.AsyncClient(verify=False, timeout=60) as http:
            with open(image_path, "rb") as f:
                files = {"file": ("card.jpg", f, "image/jpeg")}
                upload = await http.post(
                    "https://gigachat.devices.sberbank.ru/api/v1/files",
                    headers=headers,
                    files=files,
                    data={"purpose": "general"},
                )
            upload.raise_for_status()
            file_id = upload.json()["id"]

            payload = {
                "model": "GigaChat-2-Max",
                "messages": [
                    {
                        "role": "user",
                        "content": (
                            "Распознай данные с визитки. Верни ТОЛЬКО JSON без пояснений:\n"
                            '{"first_name": "", "last_name": "", "phone": "", '
                            '"email": "", "company": "", "position": "", '
                            '"birth_date": "YYYY-MM-DD или пустая строка"}'
                        ),
                        "attachments": [file_id],
                    }
                ],
            }
            chat = await http.post(
                "https://gigachat.devices.sberbank.ru/api/v1/chat/completions",
                headers={**headers, "Content-Type": "application/json"},
                json=payload,
            )
            chat.raise_for_status()
            content = chat.json()["choices"][0]["message"]["content"]

        content = content.strip()
        if content.startswith("```"):
            content = content.strip("`")
            if content.startswith("json"):
                content = content[4:]
            content = content.strip()
        data = json.loads(content)

        # Нормализация полей
        from apps.clients.utils import normalize_phone, parse_birth_date
        if data.get('phone'):
            try:
                data['phone'] = normalize_phone(data['phone'])
            except Exception:
                pass
        if data.get('birth_date'):
            try:
                bd = parse_birth_date(data['birth_date'])
                data['birth_date'] = bd.isoformat() if bd else None
            except Exception:
                data.pop('birth_date', None)

        return data

    async def handle_save_contact(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Сохранение распознанного контакта."""
        query = update.callback_query
        await query.answer()

        data = context.user_data.get('pending_contact')
        if not data:
            await query.edit_message_text("❌ Данные потеряны, попробуйте снова.")
            return

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
            for field in ['first_name', 'last_name', 'email', 'company', 'position']:
                if data.get(field):
                    setattr(existing, field, data[field])
            await sync_to_async(existing.save)()
            await query.edit_message_text(
                f"✅ Клиент обновлён:\n"
                f"👤 {existing.first_name} {existing.last_name}\n"
                f"📞 {existing.phone}"
            )
            # Открываем карточку
            await self._open_client_card(update, context, existing)
        else:
            birth_date = data.get('birth_date')
            if isinstance(birth_date, str) and birth_date:
                try:
                    from apps.clients.utils import parse_birth_date
                    birth_date = parse_birth_date(birth_date)
                except Exception:
                    birth_date = None
            elif not birth_date:
                birth_date = None

            client = await sync_to_async(Client.objects.create)(
                first_name=data.get('first_name', '') or 'Без имени',
                last_name=data.get('last_name', ''),
                phone=phone or f"unknown_{timezone.now().timestamp()}",
                email=email,
                company=data.get('company', ''),
                position=data.get('position', ''),
                birth_date=birth_date,
                telegram_id=str(update.effective_user.id),
                status='active',  # автоактивация после скана
            )
            await query.edit_message_text(
                f"✅ *Клиент добавлен и активен:*\n"
                f"👤 {client.first_name} {client.last_name}\n"
                f"📞 {client.phone}\n"
                f"✉️ {client.email or '—'}\n"
                f"🎂 {client.birth_date.strftime('%d.%m.%Y') if client.birth_date else '—'}",
                parse_mode='Markdown',
            )
            # Открываем карточку
            await self._open_client_card(update, context, client)

        context.user_data.pop('pending_contact', None)

    async def handle_cancel_contact(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        await query.answer()
        context.user_data.pop('pending_contact', None)
        await query.edit_message_text("❌ Отменено.")

    async def avatar(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Команда /avatar Имя — найти клиента и ждать фото для аватарки."""
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
        """Сохранение аватарки со сжатием через Pillow."""
        client_id = context.user_data.pop('avatar_client_id', None)
        logger.info(f"💾 _save_avatar: client_id={client_id}")
        if not client_id:
            logger.warning("💾 _save_avatar: client_id отсутствует, выхожу")
            return

        photo = update.message.photo[-1]
        file = await photo.get_file()

        with tempfile.NamedTemporaryFile(delete=False, suffix='.jpg') as tmp:
            tmp_path = tmp.name
            await file.download_to_drive(tmp_path)
            logger.info(f"💾 Скачано во временный файл: {tmp_path}")

        try:
            client = await sync_to_async(Client.objects.get)(id=client_id)

            def _do_save():
                buf = process_avatar(tmp_path, size=400, quality=80)
                client.avatar.save(
                    f'avatar_{client_id}.jpg',
                    ContentFile(buf.getvalue()),
                    save=True,
                )
                return client.avatar.size

            size = await sync_to_async(_do_save)()
            logger.info(f"💾 Аватарка сохранена: {client.avatar.name} ({size} байт)")

            await update.message.reply_text(
                f"✅ Аватарка сохранена для {client.first_name} {client.last_name} "
                f"({size // 1024} КБ)"
            )
        except Exception as e:
            logger.error(f"❌ Ошибка сохранения аватарки: {e}", exc_info=True)
            await update.message.reply_text(f"❌ Ошибка сохранения: {e}")
        finally:
            try:
                os.unlink(tmp_path)
            except Exception:
                pass