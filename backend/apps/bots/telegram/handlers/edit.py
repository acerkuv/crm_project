"""Mixin: ручное редактирование карточки клиента."""
import logging

from asgiref.sync import sync_to_async
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ContextTypes

from apps.clients.models import Client, Interaction
from apps.clients.services import (
    EDITABLE_CLIENT_FIELDS, FIELD_LABELS_RU,
    update_client_field, list_notes, delete_note,
    set_custom_field,
)
from ..keyboards import (
    get_edit_fields_keyboard,
    get_notes_list_keyboard,
    get_custom_fields_keyboard,
)
from .helpers import main_reply_markup

logger = logging.getLogger(__name__)


class EditMixin:

    async def _handle_edit_client_menu(self, update, context, client_id):
        q = update.callback_query
        await q.answer()
        client = await sync_to_async(Client.objects.filter(id=client_id).first)()
        if not client:
            await q.edit_message_text("❌ Клиент не найден")
            return
        await q.edit_message_text(
            f"✏️ *Редактирование:* {client.first_name} {client.last_name}\n\nВыберите поле:",
            parse_mode='Markdown', reply_markup=get_edit_fields_keyboard(client_id),
        )

    async def _handle_edit_field_start(self, update, context, client_id, field):
        q = update.callback_query
        await q.answer()
        client = await sync_to_async(Client.objects.filter(id=client_id).first)()
        if not client or field not in EDITABLE_CLIENT_FIELDS:
            await q.edit_message_text("❌ Поле недоступно")
            return
        current = getattr(client, field, '') or '—'
        if field == 'birth_date' and current != '—':
            current = current.strftime('%d.%m.%Y')
        context.user_data['editing'] = {'client_id': client_id, 'field': field}
        hints = {
            'birth_date': 'Формат: ДД.ММ.ГГГГ (например, 25.12.1990)',
            'phone': 'Формат: +7XXXXXXXXXX, или 8XXXXXXXXXX, или 9991234567',
        }
        hint = hints.get(field, '')
        await q.edit_message_text(
            f"✏️ *{FIELD_LABELS_RU.get(field, field)}*\n\n"
            f"Текущее: {current}\n\n"
            + (f"_{hint}_\n\n" if hint else "")
            + f"Отправьте новое значение (или «—», чтобы очистить):",
            parse_mode='Markdown',
        )

    async def _apply_edit_field(self, update, context, text):
        data = context.user_data.pop('editing', None)
        if not data:
            return False
        client = await sync_to_async(Client.objects.filter(id=data['client_id']).first)()
        if not client:
            await update.message.reply_text("❌ Клиент не найден")
            return True
        value = '' if text.strip() in ('—', '-') else text.strip()
        try:
            await sync_to_async(update_client_field)(client, data['field'], value)
            await update.message.reply_text(
                f"✅ *{FIELD_LABELS_RU.get(data['field'], data['field'])}*: {value or '—'}",
                parse_mode='Markdown', reply_markup=main_reply_markup(),
            )
        except Exception as e:
            logger.error(f"edit_field: {e}", exc_info=True)
            await update.message.reply_text(f"❌ {e}", reply_markup=main_reply_markup())
        return True

    async def _handle_notes_list(self, update, context, client_id):
        q = update.callback_query
        await q.answer()
        client = await sync_to_async(Client.objects.filter(id=client_id).first)()
        if not client:
            await q.edit_message_text("❌ Клиент не найден")
            return
        notes = await sync_to_async(lambda: list(list_notes(client)))()
        if not notes:
            await q.edit_message_text(
                f"📝 У {client.first_name} {client.last_name} нет заметок.",
                reply_markup=get_notes_list_keyboard(client_id, []),
            )
            return
        await q.edit_message_text(
            f"📝 *Заметки {client.first_name} {client.last_name}* ({len(notes)}):",
            parse_mode='Markdown',
            reply_markup=get_notes_list_keyboard(client_id, notes),
        )

    async def _handle_note_delete(self, update, context, note_id):
        q = update.callback_query
        note = await sync_to_async(
            lambda: Interaction.objects.filter(id=note_id).select_related('client').first()
        )()
        ok = await sync_to_async(delete_note)(note_id)
        await q.answer("✅ Удалено" if ok else "❌ Не найдено")
        if note:
            await self._handle_notes_list(update, context, note.client_id)

    async def _handle_custom_fields_list(self, update, context, client_id):
        q = update.callback_query
        await q.answer()
        client = await sync_to_async(Client.objects.filter(id=client_id).first)()
        if not client:
            await q.edit_message_text("❌ Клиент не найден")
            return
        cfs = await sync_to_async(lambda: list(client.custom_fields.all()))()
        await q.edit_message_text(
            f"➕ *Доп. поля {client.first_name} {client.last_name}*:",
            parse_mode='Markdown',
            reply_markup=get_custom_fields_keyboard(client_id, cfs),
        )

    async def _handle_custom_field_add_start(self, update, context, client_id):
        q = update.callback_query
        await q.answer()
        context.user_data['custom_field_adding'] = {'client_id': client_id, 'stage': 'name'}
        await q.edit_message_text(
            "➕ *Новое поле*\n\nВведите название (например: «Аллергии», «Размер одежды»):",
            parse_mode='Markdown',
        )

    async def _apply_custom_field_add(self, update, context, text):
        state = context.user_data.get('custom_field_adding')
        if not state:
            return False
        if state['stage'] == 'name':
            state['name'] = text.strip()[:100]
            state['stage'] = 'value'
            await update.message.reply_text(
                f"Поле: *{state['name']}*\n\nВведите значение:",
                parse_mode='Markdown', reply_markup=main_reply_markup(),
            )
            return True
        client = await sync_to_async(Client.objects.filter(id=state['client_id']).first)()
        if client:
            await sync_to_async(set_custom_field)(client, state['name'], text.strip())
            await update.message.reply_text(
                f"✅ *{state['name']}* = {text.strip()}",
                parse_mode='Markdown', reply_markup=main_reply_markup(),
            )
        context.user_data.pop('custom_field_adding', None)
        return True

    async def _handle_custom_field_delete(self, update, context, client_id, field_id):
        q = update.callback_query
        from apps.clients.models import CustomField
        cf = await sync_to_async(CustomField.objects.filter(id=field_id).first)()
        if cf:
            await sync_to_async(cf.delete)()
        await q.answer("✅ Удалено")
        await self._handle_custom_fields_list(update, context, client_id)

    async def _handle_add_manual_start(self, update, context):
        q = update.callback_query
        await q.answer()
        context.user_data['add_manual'] = {'stage': 'first_name'}
        await q.edit_message_text(
            "✍️ *Новый клиент*\n\nШаг 1/3 — Введите *имя*:",
            parse_mode='Markdown',
        )

    async def _apply_add_manual(self, update, context, text):
        state = context.user_data.get('add_manual')
        if not state:
            return False
        stage = state['stage']
        if stage == 'first_name':
            state['first_name'] = text.strip()
            state['stage'] = 'phone'
            await update.message.reply_text(
                "Шаг 2/3 — Введите *телефон* (или «—» чтобы пропустить):",
                parse_mode='Markdown', reply_markup=main_reply_markup(),
            )
            return True
        if stage == 'phone':
            state['phone'] = '' if text.strip() == '—' else text.strip()
            state['stage'] = 'birth_date'
            await update.message.reply_text(
                "Шаг 3/3 — Введите *дату рождения* ДД.ММ.ГГГГ (или «—»):",
                parse_mode='Markdown', reply_markup=main_reply_markup(),
            )
            return True
        birth = None
        if text.strip() != '—':
            from datetime import datetime as _dt
            try:
                birth = _dt.strptime(text.strip(), '%d.%m.%Y').date()
            except ValueError:
                await update.message.reply_text(
                    "❌ Формат: ДД.ММ.ГГГГ. Попробуйте снова или «—»:",
                    reply_markup=main_reply_markup(),
                )
                return True
            
        from apps.clients.models import Client as _C
        from apps.clients.utils import normalize_phone
        data = {
            'first_name': state['first_name'],
            'phone': normalize_phone(state['phone']) if state['phone'] else None,
            'birth_date': birth,
            'status': 'active',
        }
        if not data['phone']:
            from django.utils import timezone as _tz
            data['phone'] = f"unknown_{int(_tz.now().timestamp())}"
        try:
            client = await sync_to_async(_C.objects.create)(**data)
            context.user_data.pop('add_manual', None)
            await update.message.reply_text(
                f"✅ *Клиент добавлен и активен*\n\n"
                f"👤 {client.first_name}\n📞 {client.phone}\n"
                f"🎂 {birth.strftime('%d.%m.%Y') if birth else '—'}",
                parse_mode='Markdown', reply_markup=main_reply_markup(),
            )
        except Exception as e:
            await update.message.reply_text(f"❌ {e}", reply_markup=main_reply_markup())
        return True