from .base import *

DEBUG = True

ALLOWED_HOSTS = ['localhost', '127.0.0.1', '553e-194-58-37-17.ngrok-free.app']

# CORS
CORS_ALLOW_ALL_ORIGINS = True
CORS_ALLOWED_ORIGINS = [
    "http://localhost:3000",
    "http://localhost:3001",
    "http://127.0.0.1:3000",
    "http://127.0.0.1:3001",
    "https://553e-194-58-37-17.ngrok-free.app",
]
CORS_ALLOW_CREDENTIALS = True

# Database
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': os.environ.get('POSTGRES_DB', 'crm_db'),
        'USER': os.environ.get('POSTGRES_USER', 'crm_user'),
        'PASSWORD': os.environ.get('POSTGRES_PASSWORD', 'secure_password_dev'),
        'HOST': os.environ.get('POSTGRES_HOST', 'db'),
        'PORT': os.environ.get('POSTGRES_PORT', '5432'),
    }
}
