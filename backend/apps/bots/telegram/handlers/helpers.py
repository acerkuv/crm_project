"""Общие утилиты: обработка изображений, reply-клавиатура."""
import logging
from io import BytesIO

from PIL import Image
from telegram import ReplyKeyboardMarkup, KeyboardButton

logger = logging.getLogger(__name__)


def main_reply_markup() -> ReplyKeyboardMarkup:
    """Основная reply-клавиатура (внизу экрана)."""
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton("📋 Список"), KeyboardButton("🔍 Поиск"), KeyboardButton("📅 События")],
            [KeyboardButton("➕ Добавить"), KeyboardButton("📊 Статистика"), KeyboardButton("🎂 Дни рождения")],
            [KeyboardButton("❓ Помощь")],
        ],
        resize_keyboard=True,
    )


def process_avatar(image_path: str, size: int = 400, quality: int = 80) -> BytesIO:
    """Сжимает изображение: ресайз в квадрат size×size, конвертация в JPEG."""
    img = Image.open(image_path)

    if img.mode in ('RGBA', 'LA', 'P'):
        background = Image.new('RGB', img.size, (255, 255, 255))
        if img.mode == 'P':
            img = img.convert('RGBA')
        if img.mode in ('RGBA', 'LA'):
            background.paste(img, mask=img.split()[-1])
        else:
            background.paste(img)
        img = background
    elif img.mode != 'RGB':
        img = img.convert('RGB')

    img.thumbnail((size, size), Image.Resampling.LANCZOS)

    output = BytesIO()
    img.save(output, format='JPEG', quality=quality, optimize=True)
    output.seek(0)
    return output
