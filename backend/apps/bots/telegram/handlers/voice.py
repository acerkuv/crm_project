"""Mixin: обработка голосовых сообщений (STT + TTS)."""
import logging
import os
import tempfile

import httpx
from telegram import Update
from telegram.ext import ContextTypes
from django.conf import settings

logger = logging.getLogger(__name__)


class VoiceMixin:
    """Голосовые сообщения: STT + TTS (async httpx)."""

    async def handle_voice(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        voice = update.message.voice
        if not voice:
            return

        file = await voice.get_file()
        with tempfile.NamedTemporaryFile(delete=False, suffix='.ogg') as tmp:
            await file.download_to_drive(tmp.name)
            tmp_path = tmp.name

        try:
            await update.message.reply_text("🎤 Распознаю...")
            text = await self._speechkit_stt(tmp_path)
            if not text:
                await update.message.reply_text("❌ Не удалось распознать")
                return

            await update.message.reply_text(
                f"📝 *Распознано:* {text}\n\n_Обрабатываю как текстовую команду..._",
                parse_mode='Markdown',
            )
            await self.handle_text(update, context, text=text)
        except Exception as e:
            logger.error(f"Ошибка обработки голосового: {e}", exc_info=True)
            await update.message.reply_text(f"❌ Ошибка: {e}")
        finally:
            try:
                os.unlink(tmp_path)
            except Exception:
                pass

    async def _speechkit_stt(self, audio_path: str) -> str:
        api_key = getattr(settings, 'YANDEX_SPEECHKIT_API_KEY', '')
        if not api_key:
            logger.error("YANDEX_SPEECHKIT_API_KEY not set")
            return ''

        url = "https://stt.api.cloud.yandex.net/speech/v1/stt:recognize"
        headers = {"Authorization": f"Api-Key {api_key}"}
        params = {"lang": "ru-RU", "format": "oggopus", "topic": "general"}

        with open(audio_path, 'rb') as f:
            audio_data = f.read()

        try:
            async with httpx.AsyncClient(timeout=30) as client:
                r = await client.post(url, headers=headers, params=params, content=audio_data)
            if r.status_code == 200:
                return r.json().get('result', '')
            logger.error(f"SpeechKit STT {r.status_code}: {r.text[:200]}")
            return ''
        except Exception as e:
            logger.error(f"SpeechKit STT error: {e}", exc_info=True)
            return ''

    async def _speechkit_tts(self, text: str) -> bytes:
        api_key = getattr(settings, 'YANDEX_SPEECHKIT_API_KEY', '')
        if not api_key:
            logger.error("YANDEX_SPEECHKIT_API_KEY не задан")
            return b''

        url = "https://tts.api.cloud.yandex.net/speech/v1/tts:synthesize"
        headers = {"Authorization": f"Api-Key {api_key}"}
        data = {
            "text": text[:4000],
            "lang": "ru-RU",
            "voice": "ermil",
            "format": "oggopus",
            "speed": "1.0",
        }

        try:
            async with httpx.AsyncClient(timeout=30) as client:
                r = await client.post(url, headers=headers, data=data)
            if r.status_code == 200:
                return r.content
            logger.error(f"SpeechKit TTS {r.status_code}: {r.text[:200]}")
            return b''
        except Exception as e:
            logger.error(f"SpeechKit TTS error: {e}", exc_info=True)
            return b''