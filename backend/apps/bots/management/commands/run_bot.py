import logging
from django.core.management.base import BaseCommand
from apps.bots.telegram.bot import TelegramBot

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Запуск Telegram бота в режиме long-polling'

    def handle(self, *args, **options):
        self.stdout.write(self.style.WARNING('🚀 Запуск Telegram-бота...'))
        bot = TelegramBot()
        bot.run_polling()