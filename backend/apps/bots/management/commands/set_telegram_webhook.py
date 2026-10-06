from django.core.management.base import BaseCommand
from django.conf import settings
import requests
import logging

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Устанавливает вебхук для Telegram бота'

    def add_arguments(self, parser):
        parser.add_argument(
            '--url',
            type=str,
            help='URL для вебхука (по умолчанию из настроек)',
        )

    def handle(self, *args, **options):
        token = settings.TELEGRAM_BOT_TOKEN
        if not token:
            self.stderr.write('❌ TELEGRAM_BOT_TOKEN не настроен!')
            self.stderr.write('Проверьте .env.dev файл')
            return

        webhook_url = options.get('url') or settings.TELEGRAM_WEBHOOK_URL
        
        if not webhook_url:
            self.stderr.write('❌ TELEGRAM_WEBHOOK_URL не настроен!')
            return

        self.stdout.write(f'🔧 Установка вебхука...')
        self.stdout.write(f'📡 URL: {webhook_url}')
        self.stdout.write(f'🔑 Токен: {token[:20]}...')

        # Устанавливаем вебхук
        url = f'https://api.telegram.org/bot{token}/setWebhook'
        params = {'url': webhook_url}
        
        try:
            response = requests.get(url, params=params, timeout=10)
            data = response.json()
            
            if data.get('ok'):
                self.stdout.write(self.style.SUCCESS(f'✅ Вебхук установлен успешно!'))
                self.stdout.write(f'ℹ️ Ответ: {data}')
            else:
                self.stderr.write(self.style.ERROR(f'❌ Ошибка: {data}'))
        except Exception as e:
            self.stderr.write(self.style.ERROR(f'❌ Ошибка: {e}'))
