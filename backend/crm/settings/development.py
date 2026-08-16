from .base import *

DEBUG = True

# Явно указываем ALLOWED_HOSTS для разработки
ALLOWED_HOSTS = [
    'localhost',
    '127.0.0.1',
    '0.0.0.0',
    '553e-194-58-37-17.ngrok-free.app',
    '*.ngrok-free.app',
    '*.ngrok.io',
]

CORS_ALLOW_ALL_ORIGINS = True
EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'

# Добавляем CSRF доверенные источники
CSRF_TRUSTED_ORIGINS = [
    'http://localhost:8000',
    'https://553e-194-58-37-17.ngrok-free.app',
    'https://*.ngrok-free.app',
    'https://*.ngrok.io',
]

# Дополнительные настройки для разработки
SESSION_COOKIE_SECURE = False
CSRF_COOKIE_SECURE = False
SECURE_SSL_REDIRECT = False
