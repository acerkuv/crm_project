"""
Тестовый скрипт для проверки Yandex SpeechKit (STT).
Запускать внутри контейнера bot:
  docker compose exec bot python test_voice.py /path/to/audio.ogg
"""
import os
import sys
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'crm.settings.production')
django.setup()

from django.conf import settings
from speechkit import model_repository, configure_credentials, creds
from speechkit.stt import AudioProcessingType


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

    # Аутентификация через API-ключ
    configure_credentials(
        yandex_credentials=creds.YandexCredentials(api_key=api_key)
    )

    # Модель распознавания
    model = model_repository.recognition_model()
    model.model = 'general'
    model.language = 'ru-RU'
    model.audio_processing_type = AudioProcessingType.Full

    print("🎤 Распознаю...")
    try:
        result = model.transcribe_file(audio_path)
        for c, res in enumerate(result):
            print('=' * 60)
            print(f'channel: {c}')
            print(f'raw_text:\n{res.raw_text}')
            print(f'norm_text:\n{res.normalized_text}')
            if res.has_utterances():
                print('utterances:')
                for utterance in res.utterances:
                    print(utterance)
    except Exception as e:
        print(f"❌ Ошибка распознавания: {type(e).__name__}: {e}")
        sys.exit(1)


if __name__ == '__main__':
    main()