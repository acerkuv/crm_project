"""Mixin: обработка голосовых сообщений (STT + TTS)."""
import logging
import tempfile
import os

import requests
from telegram import Update
from telegram.ext import ContextTypes

from django.conf import settings
from .helpers import main_reply_markup

logger = logging.getLogger(__name__)


class VoiceMixin:
    """Голосовые сообщения: STT + TTS."""

    async def handle_voice(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработка голосового сообщения."""
        voice = update.message.voice
        if not voice:
            return

        # Скачиваем .ogg
        file = await voice.get_file()
        with tempfile.NamedTemporaryFile(delete=False, suffix='.ogg') as tmp:
            await file.download_to_drive(tmp.name)
            tmp_path = tmp.name

        try:
            await update.message.reply_text("🎤 Распознаю...")

            # STT
            text = await self._speechkit_stt(tmp_path)
            if not text:
                await update.message.reply_text("❌ Не удалось распознать")
                return

            await update.message.reply_text(
                f"📝 *Распознано:* {text}\n\n"
                f"_Обрабатываю как текстовую команду..._",
                parse_mode='Markdown',
            )

            # Передаём в handle_text как будто пользователь ввёл текст
            update.message.text = text
            await self.handle_text(update, context)

        except Exception as e:
            logger.error(f"Ошибка обработки голосового: {e}", exc_info=True)
            await update.message.reply_text(f"❌ Ошибка: {e}")
        finally:
            try:
                os.unlink(tmp_path)
            except Exception:
                pass

    async def _speechkit_stt(self, audio_path: str) -> str:
        """Распознавание через SpeechKit (прямой HTTP)."""
        api_key = getattr(settings, 'YANDEX_SPEECHKIT_API_KEY', '')
        if not api_key:
            logger.error("YANDEX_SPEECHKIT_API_KEY not set")
            return ''

        url = "https://stt.api.cloud.yandex.net/speech/v1/stt:recognize"
        headers = {"Authorization": f"Api-Key {api_key}"}
        params = {
            "lang": "ru-RU",
            "format": "oggopus",
            "topic": "general",
        }

        with open(audio_path, 'rb') as f:
            audio_data = f.read()

        response = requests.post(
            url, headers=headers, params=params,
            data=audio_data, timeout=30,
        )

        if response.status_code == 200:
            return response.json().get('result', '')
        else:
            logger.error(f"SpeechKit STT {response.status_code}: {response.text}")
            return ''