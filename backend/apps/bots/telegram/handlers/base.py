import requests
import json
from django.conf import settings
from django.utils import timezone
from datetime import datetime

def send_message(chat_id, text, reply_markup=None, parse_mode='Markdown'):
    """Отправка сообщения с поддержкой Reply Keyboard"""
    token = settings.TELEGRAM_BOT_TOKEN
    url = f'https://api.telegram.org/bot{token}/sendMessage'
    data = {
        'chat_id': chat_id,
        'text': text,
        'parse_mode': parse_mode
    }
    if reply_markup:
        data['reply_markup'] = json.dumps(reply_markup) if isinstance(reply_markup, dict) else reply_markup
    return requests.post(url, json=data)

def send_photo(chat_id, photo_url, caption=None, reply_markup=None):
    """Отправка фото"""
    token = settings.TELEGRAM_BOT_TOKEN
    url = f'https://api.telegram.org/bot{token}/sendPhoto'
    data = {
        'chat_id': chat_id,
        'photo': photo_url,
        'parse_mode': 'Markdown'
    }
    if caption:
        data['caption'] = caption
    if reply_markup:
        data['reply_markup'] = json.dumps(reply_markup) if isinstance(reply_markup, dict) else reply_markup
    return requests.post(url, json=data)

def edit_message(chat_id, message_id, text, reply_markup=None):
    """Редактирование сообщения"""
    token = settings.TELEGRAM_BOT_TOKEN
    url = f'https://api.telegram.org/bot{token}/editMessageText'
    data = {
        'chat_id': chat_id,
        'message_id': message_id,
        'text': text,
        'parse_mode': 'Markdown'
    }
    if reply_markup:
        data['reply_markup'] = json.dumps(reply_markup) if isinstance(reply_markup, dict) else reply_markup
    return requests.post(url, json=data)

def delete_message(chat_id, message_id):
    """Удаление сообщения"""
    token = settings.TELEGRAM_BOT_TOKEN
    url = f'https://api.telegram.org/bot{token}/deleteMessage'
    try:
        requests.post(url, json={'chat_id': chat_id, 'message_id': message_id})
    except:
        pass

def answer_callback(callback_id, text=None, show_alert=False):
    """Ответ на callback"""
    token = settings.TELEGRAM_BOT_TOKEN
    url = f'https://api.telegram.org/bot{token}/answerCallbackQuery'
    data = {'callback_query_id': callback_id}
    if text:
        data['text'] = text
        data['show_alert'] = show_alert
    return requests.post(url, json=data)

def send_reply_keyboard(chat_id, text, keyboard, parse_mode='HTML'):
    """
    Отправляет сообщение с Reply Keyboard (виртуальная клавиатура внизу экрана)
    
    Args:
        chat_id: ID чата
        text: Текст сообщения
        keyboard: Словарь с клавиатурой (как в keyboards.py)
        parse_mode: Режим парсинга (по умолчанию 'HTML')
    
    Пример:
        from ..keyboards import get_main_reply_keyboard
        keyboard = get_main_reply_keyboard()
        send_reply_keyboard(chat_id, "Главное меню", keyboard)
    """
    token = settings.TELEGRAM_BOT_TOKEN
    url = f'https://api.telegram.org/bot{token}/sendMessage'
    
    # Если keyboard - это словарь, конвертируем в JSON
    reply_markup = json.dumps(keyboard) if isinstance(keyboard, dict) else keyboard
    
    data = {
        'chat_id': chat_id,
        'text': text,
        'parse_mode': parse_mode,
        'reply_markup': reply_markup
    }
    
    return requests.post(url, json=data)