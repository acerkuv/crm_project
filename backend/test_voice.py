"""
Тестовый скрипт для проверки Yandex SpeechKit (STT) — пакет yandex-ai-studio-sdk.
Запускать внутри контейнера bot:
  docker compose exec bot python test_voice.py /path/to/audio.ogg
"""
import os
import sys
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'crm.settings.production')
django.setup()

from django.conf import settings
from yandex_ai_studio_sdk import AIStudio


def main():
    if len(sys.argv) < 2:
        print("Usage: python test_voice.py <audio_file>")
        sys.exit(1)

    audio_path = sys.argv[1]

    if not os.path.exists(audio_path):
        print(f"❌ File not found: {audio_path}")
        sys.exit(1)

    api_key = getattr(settings, 'YANDEX_SPEECHKIT_API_KEY', '')
    if not api_key:
        print("❌ YANDEX_SPEECHKIT_API_KEY not set in settings")
        sys.exit(1)

    print(f"🔑 API key length: {len(api_key)}")
    print(f"📁 Audio file: {audio_path}")

    # Инициализация SDK (folder_id не нужен при API-ключе)
    sdk = AIStudio(auth=api_key)

    # Модель распознавания
    model = sdk.models.speech_to_text('general')

    print("🎤 Распознаю...")
    try:
        with open(audio_path, 'rb') as f:
            audio_data = f.read()

        result = model.run(audio_data, audio_format='oggopus')
        print('=' * 60)
        print(f'📝 Распознанный текст:\n{result.text}')
    except Exception as e:
        print(f"❌ Ошибка распознавания: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()