"""Mixin: роутер callback'ов."""
import logging

from telegram import Update
from telegram.ext import ContextTypes

logger = logging.getLogger(__name__)


class CallbacksMixin:
    """Роутер всех callback'ов."""

    async def button_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        data = query.data
        logger.info(f"🔘 callback: {data}")

        try:
            await self._button_handler_impl(update, context)
        except Exception as e:
            logger.error(f"❌ Ошибка в button_handler для '{data}': {e}", exc_info=True)
            try:
                await query.answer(f"❌ {type(e).__name__}: {str(e)[:150]}", show_alert=True)
            except Exception:
                pass

    async def _button_handler_impl(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        data = query.data

        # ============ ХОББИ ============
        if data.startswith('set_hobby_'):
            client_id = int(data.split('_')[2])
            await self._handle_set_hobby(update, context, client_id)
            return

        # ============ ПОДТВЕРЖДЕНИЕ ПЛАНИРОВАНИЯ ============
        if data == 'plan_confirm_yes':
            await query.answer("✅ Создаю...")
            try:
                await query.message.delete()
            except Exception:
                pass
            await self._create_plan_from_context(update, context)
            return

        if data == 'plan_confirm_no':
            await query.answer("❌ Отменено")
            context.user_data.pop('confirm_plan', None)
            try:
                await query.edit_message_text("❌ Отменено")
            except Exception:
                pass
            return

        if data == 'noop':
            await query.answer()
            return

        if data == 'main_menu':
            await self._handle_main_menu(update, context)
            return

        if data == 'back_to_list' or data == 'refresh_list':
            await self._handle_back_to_list(update, context)
            return

        if data.startswith('list_page_'):
            page = int(data.split('_')[2])
            await self._handle_list_page(update, context, page)
            return

        if data.startswith('list_letter_'):
            letter = data.split('_')[2]
            await self._handle_list_letter(update, context, letter)
            return

        if data.startswith('client_detail_'):
            client_id = int(data.split('_')[2])
            await self._handle_client_detail(update, context, client_id)
            return

                # ============ РЕДАКТИРОВАНИЕ / ЗАМЕТКИ / ДОП. ПОЛЯ ============
        if data.startswith('edit_client_'):
            await self._handle_edit_client_menu(update, context, int(data.split('_')[2]))
            return
        if data.startswith('edit_field_'):
            _, _, cid, field = data.split('_', 3)
            await self._handle_edit_field_start(update, context, int(cid), field)
            return
        if data.startswith('notes_list_'):
            await self._handle_notes_list(update, context, int(data.split('_')[2]))
            return
        if data.startswith('note_delete_'):
            await self._handle_note_delete(update, context, int(data.split('_')[2]))
            return
        if data.startswith('custom_fields_list_'):
            await self._handle_custom_fields_list(update, context, int(data.split('_')[3]))
            return
        if data.startswith('custom_field_add_'):
            await self._handle_custom_field_add_start(update, context, int(data.split('_')[3]))
            return
        if data.startswith('custom_field_del_'):
            parts = data.split('_')
            await self._handle_custom_field_delete(update, context, int(parts[3]), int(parts[4]))
            return
        if data == 'add_manual_start':
            await self._handle_add_manual_start(update, context)
            return

        if data.startswith('client_'):
            client_id = int(data.split('_')[1])
            await self.show_client_actions(update, context, client_id)
            return

        if data.startswith('action_'):
            parts = data.split('_')
            client_id = int(parts[1])
            action_type = parts[2]
            await self._handle_action(update, context, client_id, action_type)
            return

        if data.startswith('show_avatar_'):
            client_id = int(data.split('_')[2])
            await self._handle_show_avatar(update, context, client_id)
            return

        if data.startswith('plan_action_'):
            action_type = data.replace('plan_action_', '')
            await self._handle_plan_action(update, context, action_type)
            return

        if data.startswith('plan_'):
            client_id = int(data.split('_')[1])
            await self._handle_plan_start(update, context, client_id)
            return

        if data == 'plan_cancel':
            await self._handle_plan_cancel(update, context)
            return

        if data.startswith('month_'):
            parts = data.split('_')
            await self._handle_month(update, context, int(parts[1]), int(parts[2]))
            return

        if data.startswith('day_'):
            parts = data.split('_')
            if len(parts) > 4 and parts[4] == 'past':
                await query.answer('❌ Нельзя выбрать прошедшую дату!', show_alert=True)
                return
            await self._handle_day(update, context, int(parts[1]), int(parts[2]), int(parts[3]))
            return

        if data.startswith('hour_'):
            hour = int(data.split('_')[1])
            await self._handle_hour(update, context, hour)
            return

        if data.startswith('minute_'):
            parts = data.split('_')
            await self._handle_minute(update, context, int(parts[1]), int(parts[2]))
            return

        if data == 'back_to_months':
            await self._handle_back_to_months(update, context)
            return

        if data == 'back_to_days':
            await self._handle_back_to_days(update, context)
            return

        if data == 'back_to_hours':
            await self._handle_back_to_hours(update, context)
            return

        if data == 'show_stats':
            await self._handle_show_stats(update, context)
            return

        if data == 'show_birthdays':
            await self._handle_show_birthdays(update, context)
            return

        if data == 'show_events' or data == 'show_events_calendar':
            await self._handle_show_events_calendar(update, context)
            return

        if data.startswith('event_month_'):
            parts = data.split('_')
            await self._handle_event_month(update, context, int(parts[2]), int(parts[3]))
            return

        if data == 'event_today':
            await self._handle_event_today(update, context)
            return

        if data.startswith('event_day_'):
            parts = data.split('_')
            await self._handle_event_day(update, context, int(parts[2]), int(parts[3]), int(parts[4]))
            return

        if data.startswith('event_time_') and not data.startswith('event_time_slot_'):
            parts = data.split('_')
            day = int(parts[2]); month = int(parts[3]); year = int(parts[4])
            hour = int(parts[5]); minute = int(parts[6])
            await self._handle_event_time_slot(update, context, day, month, year, hour, minute)
            return

        if data.startswith('event_empty_'):
            parts = data.split('_')
            day = int(parts[2]); month = int(parts[3]); year = int(parts[4])
            hour = int(parts[5]); minute = int(parts[6])
            await self._handle_event_time_slot(update, context, day, month, year, hour, minute)
            return

        if data.startswith('event_hour_empty_'):
            parts = data.split('_')
            await self._handle_event_hour_empty(update, context, int(parts[3]), int(parts[4]), int(parts[5]), int(parts[6]))
            return

        if data.startswith('event_time_slot_'):
            parts = data.split('_')
            await self._handle_event_time_slot(update, context, int(parts[3]), int(parts[4]), int(parts[5]), int(parts[6]), int(parts[7]))
            return

        if data.startswith('event_detail_'):
            event_id = int(data.split('_')[2])
            await self._handle_event_detail(update, context, event_id)
            return

        if data.startswith('event_delete_confirm_'):
            event_id = int(data.split('_')[3])
            await self._handle_event_delete_confirm(update, context, event_id)
            return
        
        if data.startswith('event_edit_menu_'):
            event_id = int(data.split('_')[3])
            await self._handle_event_edit_menu(update, context, event_id)
            return

        if data.startswith('event_edit_desc_'):
            event_id = int(data.split('_')[3])
            await self._handle_event_edit_desc_start(update, context, event_id)
            return

        if data.startswith('event_edit_type_'):
            parts = data.split('_')
            if len(parts) == 5:
                event_id = int(parts[3])
                new_type = parts[4]
                await self._handle_event_edit_type_apply(update, context, event_id, new_type)
            else:
                event_id = int(parts[3])
                await self._handle_event_edit_type_menu(update, context, event_id)
            return

        if data.startswith('event_delete_'):
            event_id = int(data.split('_')[2])
            await self._handle_event_delete(update, context, event_id)
            return
        
        if data.startswith('event_send_birthday_'):
            event_id = int(data.split('_')[3])
            await self._handle_event_send_birthday(update, context, event_id)
            return

        if data.startswith('event_plan_at_'):
            parts = data.split('_')
            day = int(parts[3]); month = int(parts[4]); year = int(parts[5])
            hour = int(parts[6]) if len(parts) > 6 else 9
            minute = int(parts[7]) if len(parts) > 7 else 0
            await self._handle_event_plan_at(update, context, day, month, year, hour, minute)
            return

        if data.startswith('event_back_to_calendar_'):
            parts = data.split('_')
            await self._handle_event_back_to_calendar(update, context, int(parts[4]), int(parts[5]))
            return

        if data.startswith('event_back_to_day_'):
            parts = data.split('_')
            await self._handle_event_back_to_day(update, context, int(parts[4]), int(parts[5]), int(parts[6]))
            return

        if data.startswith('year_'):
            year = int(data.split('_')[1])
            await self._handle_year(update, context, year)
            return

        if data == 'find_client':
            await self.find(update, context)
            return

        if data == 'add_client':
            await self.add(update, context)
            return

        if data == 'show_help':
            await self.help(update, context)
            return

        if data == 'save_contact':
            await self.handle_save_contact(update, context)
            return

        if data == 'cancel_contact':
            await self.handle_cancel_contact(update, context)
            return

        if data in ['birthday_auto', 'birthday_manual']:
            await self.handle_birthday_choice(update, context)
            return

        if data.startswith('send_birthday_') or data.startswith('schedule_birthday_'):
            await self.handle_birthday_action(update, context)
            return

        logger.warning(f"⚠️ Необработанный callback: {data}")
        await query.answer("⚠️ Действие не поддерживается", show_alert=False)