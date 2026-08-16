#!/bin/bash

# Цвета для вывода
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}   CRM Project Structure Creator v2.0   ${NC}"
echo -e "${BLUE}========================================${NC}"

# Функция для создания директории
create_dir() {
    if [ ! -d "$1" ]; then
        mkdir -p "$1"
        echo -e "${GREEN}✓${NC} Created directory: $1"
    else
        echo -e "${YELLOW}•${NC} Directory exists: $1"
    fi
}

# Функция для создания файла с содержимым
create_file() {
    local file_path="$1"
    local content="$2"
    local dir_path=$(dirname "$file_path")
    
    if [ ! -d "$dir_path" ]; then
        mkdir -p "$dir_path"
        echo -e "${GREEN}✓${NC} Created directory: $dir_path"
    fi
    
    if [ ! -f "$file_path" ]; then
        echo "$content" > "$file_path"
        echo -e "${GREEN}✓${NC} Created file: $file_path"
    else
        echo -e "${YELLOW}•${NC} File exists: $file_path"
    fi
}

echo -e "\n${BLUE}Creating project structure...${NC}\n"

# Создаем корневые директории
create_dir "backend"
create_dir "backend/crm/settings"
create_dir "backend/apps/clients"
create_dir "backend/apps/clients/migrations"
create_dir "backend/apps/events"
create_dir "backend/apps/events/migrations"
create_dir "backend/apps/messages"
create_dir "backend/apps/messages/migrations"
create_dir "backend/apps/bots/telegram"
create_dir "backend/apps/bots/max"
create_dir "backend/apps/ai"
create_dir "backend/apps/ai/migrations"
create_dir "backend/staticfiles"
create_dir "backend/media"
create_dir "backend/fixtures"
create_dir "backend/logs"
create_dir "backend/scripts"
create_dir "backend/tests"
create_dir "docker"
create_dir "nginx"
create_dir "nginx/ssl"

# ============================================
# 1. Файлы окружения (в корне проекта)
# ============================================

create_file ".env.dev" \
"# Django Settings
SECRET_KEY=django-insecure-@dev-key-change-in-production-123456
DEBUG=True
ALLOWED_HOSTS=localhost,127.0.0.1,0.0.0.0

# Database (PostgreSQL)
POSTGRES_DB=crm_db
POSTGRES_USER=crm_user
POSTGRES_PASSWORD=secure_password_dev
POSTGRES_HOST=db
POSTGRES_PORT=5432

# Redis
REDIS_HOST=redis
REDIS_PORT=6379
REDIS_DB=0
REDIS_PASSWORD=

# Celery
CELERY_BROKER_URL=redis://redis:6379/0
CELERY_RESULT_BACKEND=redis://redis:6379/0

# Telegram Bot
TELEGRAM_BOT_TOKEN=your_telegram_bot_token_here
TELEGRAM_WEBHOOK_URL=http://localhost:8000/webhook/telegram/

# MAX Bot
MAX_BOT_TOKEN=your_max_bot_token_here
MAX_API_URL=https://api.max.ru/v1

# AI Services
OPENAI_API_KEY=your_openai_api_key_here
YANDEXGPT_API_KEY=your_yandexgpt_api_key_here
YANDEXGPT_FOLDER_ID=your_folder_id_here

# Email
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_HOST_USER=your_email@gmail.com
EMAIL_HOST_PASSWORD=your_app_password
EMAIL_USE_TLS=True

# Django Admin
DJANGO_SUPERUSER_USERNAME=admin
DJANGO_SUPERUSER_EMAIL=admin@example.com
DJANGO_SUPERUSER_PASSWORD=admin123

# Security (Development)
CSRF_TRUSTED_ORIGINS=http://localhost:8000
SECURE_SSL_REDIRECT=False
SESSION_COOKIE_SECURE=False
CSRF_COOKIE_SECURE=False
"

create_file ".env.prod" \
"# Django Settings
SECRET_KEY=CHANGE_THIS_TO_STRONG_SECRET_KEY_IN_PRODUCTION
DEBUG=False
ALLOWED_HOSTS=your-domain.com,www.your-domain.com

# Database (PostgreSQL)
POSTGRES_DB=crm_db
POSTGRES_USER=crm_user
POSTGRES_PASSWORD=CHANGE_THIS_TO_STRONG_PASSWORD
POSTGRES_HOST=db
POSTGRES_PORT=5432

# Redis
REDIS_HOST=redis
REDIS_PORT=6379
REDIS_DB=0
REDIS_PASSWORD=CHANGE_THIS_TO_REDIS_PASSWORD

# Celery
CELERY_BROKER_URL=redis://:CHANGE_THIS_TO_REDIS_PASSWORD@redis:6379/0
CELERY_RESULT_BACKEND=redis://:CHANGE_THIS_TO_REDIS_PASSWORD@redis:6379/0

# Telegram Bot
TELEGRAM_BOT_TOKEN=your_telegram_bot_token_here
TELEGRAM_WEBHOOK_URL=https://your-domain.com/webhook/telegram/

# MAX Bot
MAX_BOT_TOKEN=your_max_bot_token_here
MAX_API_URL=https://api.max.ru/v1

# AI Services
OPENAI_API_KEY=your_openai_api_key_here
YANDEXGPT_API_KEY=your_yandexgpt_api_key_here
YANDEXGPT_FOLDER_ID=your_folder_id_here

# Email
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_HOST_USER=your_email@gmail.com
EMAIL_HOST_PASSWORD=your_app_password
EMAIL_USE_TLS=True

# Django Admin
DJANGO_SUPERUSER_USERNAME=admin
DJANGO_SUPERUSER_EMAIL=admin@example.com
DJANGO_SUPERUSER_PASSWORD=CHANGE_THIS_PASSWORD

# Security
CSRF_TRUSTED_ORIGINS=https://your-domain.com
SECURE_SSL_REDIRECT=True
SESSION_COOKIE_SECURE=True
CSRF_COOKIE_SECURE=True
SECURE_HSTS_SECONDS=31536000
SECURE_HSTS_INCLUDE_SUBDOMAINS=True
SECURE_HSTS_PRELOAD=True
"

# ============================================
# 2. Backend entrypoint (внутри backend/)
# ============================================

create_file "backend/scripts/entrypoint.sh" \
"#!/bin/bash

set -e

echo \"Waiting for PostgreSQL...\"
while ! nc -z \${POSTGRES_HOST:-db} \${POSTGRES_PORT:-5432}; do
  echo \"Waiting for PostgreSQL at \${POSTGRES_HOST}:\${POSTGRES_PORT}...\"
  sleep 1
done
echo \"✅ PostgreSQL started\"

echo \"Waiting for Redis...\"
while ! nc -z \${REDIS_HOST:-redis} \${REDIS_PORT:-6379}; do
  echo \"Waiting for Redis at \${REDIS_HOST}:\${REDIS_PORT}...\"
  sleep 1
done
echo \"✅ Redis started\"

echo \"Running migrations...\"
python manage.py makemigrations --noinput
python manage.py migrate --noinput

echo \"Collecting static files...\"
python manage.py collectstatic --noinput

echo \"Creating superuser...\"
python manage.py shell -c \"from django.contrib.auth import get_user_model; User = get_user_model(); User.objects.filter(username='\${DJANGO_SUPERUSER_USERNAME:-admin}').exists() or User.objects.create_superuser('\${DJANGO_SUPERUSER_USERNAME:-admin}', '\${DJANGO_SUPERUSER_EMAIL:-admin@example.com}', '\${DJANGO_SUPERUSER_PASSWORD:-admin123}')\" 2>/dev/null || true

echo \"✅ All done! Starting application...\"
exec \"\$@\"
"

# Сделать entrypoint исполняемым
chmod +x backend/scripts/entrypoint.sh 2>/dev/null || true

# ============================================
# 3. Docker файлы
# ============================================

# docker/docker-compose.yml
create_file "docker/docker-compose.yml" \
"version: '3.8'

services:
  db:
    image: postgres:15-alpine
    container_name: crm_db
    restart: always
    volumes:
      - postgres_data:/var/lib/postgresql/data/
    environment:
      - POSTGRES_DB=\${POSTGRES_DB:-crm_db}
      - POSTGRES_USER=\${POSTGRES_USER:-crm_user}
      - POSTGRES_PASSWORD=\${POSTGRES_PASSWORD:-secure_password_dev}
    ports:
      - \"5433:5432\"
    healthcheck:
      test: [\"CMD-SHELL\", \"pg_isready -U \${POSTGRES_USER:-crm_user} -d \${POSTGRES_DB:-crm_db}\"]
      interval: 10s
      timeout: 5s
      retries: 5
    networks:
      - crm_network

  redis:
    image: redis:7-alpine
    container_name: crm_redis
    restart: always
    ports:
      - \"6379:6379\"
    healthcheck:
      test: [\"CMD\", \"redis-cli\", \"ping\"]
      interval: 10s
      timeout: 5s
      retries: 5
    networks:
      - crm_network

  backend:
    build:
      context: ../backend
      dockerfile: Dockerfile
    container_name: crm_backend
    restart: always
    command: python manage.py runserver 0.0.0.0:8000
    volumes:
      - ../backend:/app
      - static_volume:/app/static
      - media_volume:/app/media
    ports:
      - \"8000:8000\"
    env_file:
      - ../.env.dev
    depends_on:
      db:
        condition: service_healthy
      redis:
        condition: service_healthy
    environment:
      - DJANGO_SETTINGS_MODULE=crm.settings.development
    networks:
      - crm_network

  celery:
    build:
      context: ../backend
      dockerfile: Dockerfile
    container_name: crm_celery
    restart: always
    command: celery -A crm worker -l info --concurrency=4
    volumes:
      - ../backend:/app
      - media_volume:/app/media
    env_file:
      - ../.env.dev
    depends_on:
      db:
        condition: service_healthy
      redis:
        condition: service_healthy
    environment:
      - DJANGO_SETTINGS_MODULE=crm.settings.development
    networks:
      - crm_network

  celery-beat:
    build:
      context: ../backend
      dockerfile: Dockerfile
    container_name: crm_celery_beat
    restart: always
    command: celery -A crm beat -l info --scheduler django_celery_beat.schedulers:DatabaseScheduler
    volumes:
      - ../backend:/app
    env_file:
      - ../.env.dev
    depends_on:
      db:
        condition: service_healthy
      redis:
        condition: service_healthy
    environment:
      - DJANGO_SETTINGS_MODULE=crm.settings.development
    networks:
      - crm_network

  flower:
    build:
      context: ../backend
      dockerfile: Dockerfile
    container_name: crm_flower
    restart: always
    command: celery -A crm flower --port=5555 --address=0.0.0.0
    ports:
      - \"5555:5555\"
    env_file:
      - ../.env.dev
    depends_on:
      - celery
      - redis
    environment:
      - DJANGO_SETTINGS_MODULE=crm.settings.development
    networks:
      - crm_network

volumes:
  postgres_data:
  static_volume:
  media_volume:

networks:
  crm_network:
    driver: bridge
"

# docker/docker-compose.production.yml
create_file "docker/docker-compose.production.yml" \
"version: '3.8'

services:
  db:
    image: postgres:15-alpine
    container_name: crm_db_prod
    restart: always
    volumes:
      - postgres_data_prod:/var/lib/postgresql/data/
    environment:
      - POSTGRES_DB=\${POSTGRES_DB:-crm_db}
      - POSTGRES_USER=\${POSTGRES_USER:-crm_user}
      - POSTGRES_PASSWORD=\${POSTGRES_PASSWORD}
    healthcheck:
      test: [\"CMD-SHELL\", \"pg_isready -U \${POSTGRES_USER} -d \${POSTGRES_DB}\"]
      interval: 30s
      timeout: 10s
      retries: 5
    networks:
      - crm_network_prod

  redis:
    image: redis:7-alpine
    container_name: crm_redis_prod
    restart: always
    command: redis-server --appendonly yes --requirepass \${REDIS_PASSWORD}
    volumes:
      - redis_data_prod:/data
    healthcheck:
      test: [\"CMD\", \"redis-cli\", \"--pass\", \"\${REDIS_PASSWORD}\", \"ping\"]
      interval: 30s
      timeout: 10s
      retries: 5
    networks:
      - crm_network_prod

  backend:
    build:
      context: ../backend
      dockerfile: Dockerfile.prod
    container_name: crm_backend_prod
    restart: always
    command: gunicorn crm.wsgi:application --bind 0.0.0.0:8000 --workers 4 --threads 2
    volumes:
      - static_volume_prod:/app/static
      - media_volume_prod:/app/media
    env_file:
      - ../.env.prod
    environment:
      - DJANGO_SETTINGS_MODULE=crm.settings.production
    depends_on:
      db:
        condition: service_healthy
      redis:
        condition: service_healthy
    networks:
      - crm_network_prod

  celery:
    build:
      context: ../backend
      dockerfile: Dockerfile.prod
    container_name: crm_celery_prod
    restart: always
    command: celery -A crm worker -l info --concurrency=4
    volumes:
      - media_volume_prod:/app/media
    env_file:
      - ../.env.prod
    environment:
      - DJANGO_SETTINGS_MODULE=crm.settings.production
    depends_on:
      db:
        condition: service_healthy
      redis:
        condition: service_healthy
    networks:
      - crm_network_prod

  celery-beat:
    build:
      context: ../backend
      dockerfile: Dockerfile.prod
    container_name: crm_celery_beat_prod
    restart: always
    command: celery -A crm beat -l info --scheduler django_celery_beat.schedulers:DatabaseScheduler
    env_file:
      - ../.env.prod
    environment:
      - DJANGO_SETTINGS_MODULE=crm.settings.production
    depends_on:
      db:
        condition: service_healthy
      redis:
        condition: service_healthy
    networks:
      - crm_network_prod

  nginx:
    build:
      context: ../nginx
      dockerfile: Dockerfile
    container_name: crm_nginx_prod
    restart: always
    ports:
      - \"80:80\"
      - \"443:443\"
    volumes:
      - static_volume_prod:/static
      - media_volume_prod:/media
      - ../nginx/nginx.conf:/etc/nginx/conf.d/default.conf
      - ../nginx/ssl:/etc/nginx/ssl
    depends_on:
      - backend
    networks:
      - crm_network_prod

volumes:
  postgres_data_prod:
  redis_data_prod:
  static_volume_prod:
  media_volume_prod:

networks:
  crm_network_prod:
    driver: bridge
"

# ============================================
# 4. Backend файлы
# ============================================

create_file "backend/requirements.txt" \
"Django==4.2.7
djangorestframework==3.14.0
django-cors-headers==4.3.1
django-celery-beat==2.5.0
django-celery-results==2.5.1
django-storages==1.14.2
django-filter==23.5
drf-yasg==1.21.7
psycopg2-binary==2.9.9
celery==5.3.4
redis==5.0.1
gunicorn==21.2.0
python-telegram-bot==20.6
python-dotenv==1.0.0
Pillow==10.1.0
qrcode==7.4.2
pytesseract==0.3.10
opencv-python==4.8.1.78
openai==1.3.0
requests==2.31.0
boto3==1.34.0
flower==2.0.1
pytest==7.4.3
pytest-django==4.7.0
factory-boy==3.3.0
faker==20.1.0
black==23.11.0
flake8==6.1.0
pre-commit==3.5.0
"

create_file "backend/Dockerfile" \
"FROM python:3.11-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \\
    PYTHONUNBUFFERED=1 \\
    PIP_NO_CACHE_DIR=1 \\
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \\
    gcc \\
    libpq-dev \\
    tesseract-ocr \\
    tesseract-ocr-rus \\
    poppler-utils \\
    netcat-openbsd \\
    && apt-get clean \\
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Copy entrypoint script from backend/scripts/
COPY scripts/entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

ENTRYPOINT [\"/entrypoint.sh\"]
"

create_file "backend/Dockerfile.prod" \
"FROM python:3.11-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \\
    PYTHONUNBUFFERED=1 \\
    PIP_NO_CACHE_DIR=1 \\
    PIP_DISABLE_PIP_VERSION_CHECK=1

RUN apt-get update && apt-get install -y --no-install-recommends \\
    gcc \\
    libpq-dev \\
    tesseract-ocr \\
    tesseract-ocr-rus \\
    poppler-utils \\
    && apt-get clean \\
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Create non-root user
RUN addgroup --system --gid 1001 appgroup && \\
    adduser --system --uid 1001 --gid 1001 appuser && \\
    chown -R appuser:appgroup /app

USER appuser

EXPOSE 8000

CMD [\"gunicorn\", \"crm.wsgi:application\", \"--bind\", \"0.0.0.0:8000\"]
"

create_file "backend/manage.py" \
"#!/usr/bin/env python
\"\"\"Django's command-line utility for administrative tasks.\"\"\"
import os
import sys


def main():
    \"\"\"Run administrative tasks.\"\"\"
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'crm.settings.development')
    try:
        from django.core.management import execute_from_command_line
    except ImportError as exc:
        raise ImportError(
            \"Couldn't import Django. Are you sure it's installed and \"\"
            \"available on your PYTHONPATH environment variable? Did you \"\"
            \"forget to activate a virtual environment?\"
        ) from exc
    execute_from_command_line(sys.argv)


if __name__ == '__main__':
    main()
"

# ============================================
# 5. Django settings
# ============================================

create_file "backend/crm/__init__.py" \
"from .celery import app as celery_app

__all__ = ('celery_app',)
"

create_file "backend/crm/celery.py" \
"import os
from celery import Celery

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'crm.settings.development')

app = Celery('crm')
app.config_from_object('django.conf:settings', namespace='CELERY')
app.autodiscover_tasks()

@app.task(bind=True, ignore_result=True)
def debug_task(self):
    print(f'Request: {self.request!r}')
"

create_file "backend/crm/urls.py" \
"from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from rest_framework import permissions
from drf_yasg.views import get_schema_view
from drf_yasg import openapi

schema_view = get_schema_view(
    openapi.Info(
        title=\"CRM API\",
        default_version='v1',
        description=\"API для управления клиентами и взаимодействиями\",
        terms_of_service=\"https://www.google.com/policies/terms/\",
        contact=openapi.Contact(email=\"contact@crm.local\"),
        license=openapi.License(name=\"BSD License\"),
    ),
    public=True,
    permission_classes=(permissions.AllowAny,),
)

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/', include('apps.clients.urls')),
    path('api/', include('apps.events.urls')),
    path('api/', include('apps.messages.urls')),
    path('api/', include('apps.bots.urls')),
    path('api/', include('apps.ai.urls')),
    path('swagger/', schema_view.with_ui('swagger', cache_timeout=0), name='schema-swagger-ui'),
    path('redoc/', schema_view.with_ui('redoc', cache_timeout=0), name='schema-redoc'),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
"

create_file "backend/crm/wsgi.py" \
"import os
from django.core.wsgi import get_wsgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'crm.settings.production')
application = get_wsgi_application()
"

create_file "backend/crm/asgi.py" \
"import os
from django.core.asgi import get_asgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'crm.settings.production')
application = get_asgi_application()
"

create_file "backend/crm/settings/__init__.py" ""

create_file "backend/crm/settings/base.py" \
"import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent.parent

SECRET_KEY = os.environ.get('SECRET_KEY', 'django-insecure-key-change-in-production')

DEBUG = os.environ.get('DEBUG', 'True') == 'True'

ALLOWED_HOSTS = os.environ.get('ALLOWED_HOSTS', 'localhost,127.0.0.1').split(',')

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'rest_framework',
    'rest_framework.authtoken',
    'corsheaders',
    'django_celery_beat',
    'django_celery_results',
    'drf_yasg',
    'django_filters',
    'apps.clients',
    'apps.events',
    'apps.messages',
    'apps.bots',
    'apps.ai',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'corsheaders.middleware.CorsMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'crm.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'crm.wsgi.application'

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': os.environ.get('POSTGRES_DB', 'crm_db'),
        'USER': os.environ.get('POSTGRES_USER', 'crm_user'),
        'PASSWORD': os.environ.get('POSTGRES_PASSWORD', 'password'),
        'HOST': os.environ.get('POSTGRES_HOST', 'localhost'),
        'PORT': os.environ.get('POSTGRES_PORT', '5432'),
    }
}

AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

LANGUAGE_CODE = 'ru-ru'
TIME_ZONE = 'Europe/Moscow'
USE_I18N = True
USE_TZ = True

STATIC_URL = '/static/'
STATIC_ROOT = os.path.join(BASE_DIR, 'static')
STATICFILES_DIRS = [os.path.join(BASE_DIR, 'staticfiles')]

MEDIA_URL = '/media/'
MEDIA_ROOT = os.path.join(BASE_DIR, 'media')

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

REDIS_URL = f\"redis://{os.environ.get('REDIS_HOST', 'localhost')}:{os.environ.get('REDIS_PORT', 6379)}/{os.environ.get('REDIS_DB', 0)}\"
CELERY_BROKER_URL = os.environ.get('CELERY_BROKER_URL', REDIS_URL)
CELERY_RESULT_BACKEND = os.environ.get('CELERY_RESULT_BACKEND', REDIS_URL)
CELERY_ACCEPT_CONTENT = ['application/json']
CELERY_TASK_SERIALIZER = 'json'
CELERY_RESULT_SERIALIZER = 'json'
CELERY_TIMEZONE = TIME_ZONE
CELERY_BEAT_SCHEDULER = 'django_celery_beat.schedulers:DatabaseScheduler'

REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework.authentication.SessionAuthentication',
        'rest_framework.authentication.TokenAuthentication',
    ],
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.IsAuthenticated',
    ],
    'DEFAULT_FILTER_BACKENDS': [
        'django_filters.rest_framework.DjangoFilterBackend',
    ],
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
    'PAGE_SIZE': 20,
}

CORS_ALLOWED_ORIGINS = os.environ.get('CORS_ALLOWED_ORIGINS', 'http://localhost:8000').split(',')
CORS_ALLOW_CREDENTIALS = True

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '{levelname} {asctime} {module} {process:d} {thread:d} {message}',
            'style': '{',
        },
        'simple': {
            'format': '{levelname} {asctime} {message}',
            'style': '{',
        },
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'simple',
        },
        'file': {
            'class': 'logging.FileHandler',
            'filename': os.path.join(BASE_DIR, 'logs', 'crm.log'),
            'formatter': 'verbose',
        },
    },
    'root': {
        'handlers': ['console'],
        'level': 'INFO',
    },
}
"

create_file "backend/crm/settings/development.py" \
"from .base import *

DEBUG = True
ALLOWED_HOSTS = ['localhost', '127.0.0.1', '0.0.0.0']
CORS_ALLOW_ALL_ORIGINS = True
EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'
"

create_file "backend/crm/settings/production.py" \
"from .base import *

DEBUG = False
SECURE_SSL_REDIRECT = os.environ.get('SECURE_SSL_REDIRECT', 'True') == 'True'
SESSION_COOKIE_SECURE = os.environ.get('SESSION_COOKIE_SECURE', 'True') == 'True'
CSRF_COOKIE_SECURE = os.environ.get('CSRF_COOKIE_SECURE', 'True') == 'True'
CSRF_TRUSTED_ORIGINS = os.environ.get('CSRF_TRUSTED_ORIGINS', '').split(',')

EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST = os.environ.get('EMAIL_HOST', 'smtp.gmail.com')
EMAIL_PORT = int(os.environ.get('EMAIL_PORT', 587))
EMAIL_HOST_USER = os.environ.get('EMAIL_HOST_USER', '')
EMAIL_HOST_PASSWORD = os.environ.get('EMAIL_HOST_PASSWORD', '')
EMAIL_USE_TLS = os.environ.get('EMAIL_USE_TLS', 'True') == 'True'
"

# ============================================
# 6. Apps
# ============================================

create_file "backend/apps/clients/__init__.py" ""
create_file "backend/apps/clients/apps.py" \
"from django.apps import AppConfig

class ClientsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.clients'
    verbose_name = 'Клиенты'
"

create_file "backend/apps/clients/models.py" \
"from django.db import models
from django.contrib.auth import get_user_model
from django.utils import timezone

User = get_user_model()

class Client(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='clients')
    first_name = models.CharField('Имя', max_length=100)
    last_name = models.CharField('Фамилия', max_length=100, blank=True)
    middle_name = models.CharField('Отчество', max_length=100, blank=True)
    phone = models.CharField('Телефон', max_length=20, unique=True)
    email = models.EmailField('Email', blank=True)
    birth_date = models.DateField('Дата рождения', null=True, blank=True)
    avatar = models.ImageField('Аватар', upload_to='avatars/%Y/%m/', blank=True, null=True)
    company = models.CharField('Компания', max_length=200, blank=True)
    position = models.CharField('Должность', max_length=200, blank=True)
    telegram_id = models.CharField(max_length=100, blank=True, null=True)
    max_id = models.CharField(max_length=100, blank=True, null=True)
    comment = models.TextField('Комментарий', blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    last_contact = models.DateTimeField('Последний контакт', null=True, blank=True)
    status = models.CharField('Статус', max_length=20, choices=[
        ('lead', 'Лид'),
        ('active', 'Активный'),
        ('regular', 'Постоянный'),
        ('vip', 'VIP'),
        ('inactive', 'Неактивный'),
    ], default='lead')
    
    class Meta:
        verbose_name = 'Клиент'
        verbose_name_plural = 'Клиенты'
        ordering = ['-created_at']
    
    def __str__(self):
        return f\"{self.first_name} {self.last_name}\"

class Tag(models.Model):
    name = models.CharField('Название', max_length=50, unique=True)
    color = models.CharField('Цвет', max_length=7, default='#007bff')
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = 'Тег'
        verbose_name_plural = 'Теги'
    
    def __str__(self):
        return self.name

class Interaction(models.Model):
    client = models.ForeignKey(Client, on_delete=models.CASCADE, related_name='interactions')
    type = models.CharField('Тип', max_length=20, choices=[
        ('call', 'Звонок'),
        ('message', 'Сообщение'),
        ('meeting', 'Встреча'),
        ('email', 'Email'),
        ('note', 'Заметка'),
        ('birthday', 'Поздравление'),
    ])
    content = models.TextField('Содержание')
    created_at = models.DateTimeField(auto_now_add=True)
    scheduled_at = models.DateTimeField('Запланировано на', null=True, blank=True)
    completed_at = models.DateTimeField('Выполнено', null=True, blank=True)
    sent_via_telegram = models.BooleanField('Отправлено в Telegram', default=False)
    sent_via_max = models.BooleanField('Отправлено в MAX', default=False)
    
    class Meta:
        verbose_name = 'Взаимодействие'
        verbose_name_plural = 'Взаимодействия'
        ordering = ['-created_at']
    
    def __str__(self):
        return f\"{self.get_type_display()} - {self.client}\"
"

create_file "backend/apps/clients/admin.py" \
"from django.contrib import admin
from .models import Client, Tag, Interaction

@admin.register(Client)
class ClientAdmin(admin.ModelAdmin):
    list_display = ('first_name', 'last_name', 'phone', 'email', 'status', 'created_at')
    list_filter = ('status', 'created_at')
    search_fields = ('first_name', 'last_name', 'phone', 'email')

@admin.register(Tag)
class TagAdmin(admin.ModelAdmin):
    list_display = ('name', 'color', 'created_at')
    search_fields = ('name',)

@admin.register(Interaction)
class InteractionAdmin(admin.ModelAdmin):
    list_display = ('client', 'type', 'created_at', 'scheduled_at', 'completed_at')
    list_filter = ('type', 'sent_via_telegram', 'sent_via_max')
    search_fields = ('client__first_name', 'client__last_name', 'content')
"

create_file "backend/apps/clients/urls.py" \
"from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter()
router.register(r'clients', views.ClientViewSet)

urlpatterns = [
    path('', include(router.urls)),
]
"

create_file "backend/apps/clients/views.py" \
"from rest_framework import viewsets, permissions
from .models import Client
from .serializers import ClientSerializer

class ClientViewSet(viewsets.ModelViewSet):
    queryset = Client.objects.all()
    serializer_class = ClientSerializer
    permission_classes = [permissions.IsAuthenticated]
"

create_file "backend/apps/clients/serializers.py" \
"from rest_framework import serializers
from .models import Client

class ClientSerializer(serializers.ModelSerializer):
    class Meta:
        model = Client
        fields = '__all__'
        read_only_fields = ('created_at', 'updated_at')
"

# Остальные apps (сокращенно)
for app in ["events", "messages"]:
    create_file "backend/apps/$app/__init__.py" ""
    create_file "backend/apps/$app/apps.py" \
"from django.apps import AppConfig

class ${app^}Config(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.$app'
    verbose_name = '${app^}'
"
    create_file "backend/apps/$app/models.py" \
"from django.db import models

class ${app^}Model(models.Model):
    name = models.CharField(max_length=100)
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return self.name
"
    create_file "backend/apps/$app/admin.py" \
"from django.contrib import admin
from .models import ${app^}Model

@admin.register(${app^}Model)
class ${app^}ModelAdmin(admin.ModelAdmin):
    list_display = ('name', 'created_at')
"
    create_file "backend/apps/$app/urls.py" \
"from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter()
router.register(r'$app', views.${app^}ViewSet)

urlpatterns = [
    path('', include(router.urls)),
]
"
    create_file "backend/apps/$app/views.py" \
"from rest_framework import viewsets, permissions
from .models import ${app^}Model
from .serializers import ${app^}Serializer

class ${app^}ViewSet(viewsets.ModelViewSet):
    queryset = ${app^}Model.objects.all()
    serializer_class = ${app^}Serializer
    permission_classes = [permissions.IsAuthenticated]
"
    create_file "backend/apps/$app/serializers.py" \
"from rest_framework import serializers
from .models import ${app^}Model

class ${app^}Serializer(serializers.ModelSerializer):
    class Meta:
        model = ${app^}Model
        fields = '__all__'
"

# Bots
create_file "backend/apps/bots/__init__.py" ""
create_file "backend/apps/bots/apps.py" \
"from django.apps import AppConfig

class BotsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.bots'
    verbose_name = 'Боты'
"
create_file "backend/apps/bots/urls.py" \
"from django.urls import path
from .telegram import views as telegram_views
from .max import views as max_views

urlpatterns = [
    path('webhook/telegram/', telegram_views.webhook, name='telegram_webhook'),
    path('webhook/max/', max_views.webhook, name='max_webhook'),
]
"
create_file "backend/apps/bots/telegram/__init__.py" ""
create_file "backend/apps/bots/telegram/views.py" \
"from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
import json

@csrf_exempt
def webhook(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            return JsonResponse({'status': 'ok'})
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=400)
    return JsonResponse({'status': 'ok'})
"
create_file "backend/apps/bots/max/__init__.py" ""
create_file "backend/apps/bots/max/views.py" \
"from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
import json

@csrf_exempt
def webhook(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            return JsonResponse({'status': 'ok'})
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=400)
    return JsonResponse({'status': 'ok'})
"

# AI
create_file "backend/apps/ai/__init__.py" ""
create_file "backend/apps/ai/apps.py" \
"from django.apps import AppConfig

class AIConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.ai'
    verbose_name = 'Искусственный интеллект'
"
create_file "backend/apps/ai/services.py" \
"import os
import openai
from apps.clients.models import Client

class AIGreetingService:
    def __init__(self):
        self.api_key = os.environ.get('OPENAI_API_KEY')
        if self.api_key:
            openai.api_key = self.api_key
    
    def generate_birthday_greeting(self, client: Client) -> str:
        try:
            return f\"С днём рождения, {client.first_name}! Желаю счастья и успехов!\"
        except:
            return \"С днём рождения!\"
"
create_file "backend/apps/ai/urls.py" \
"from django.urls import path

urlpatterns = []
"

# ============================================
# 7. NGINX
# ============================================

create_file "nginx/Dockerfile" \
"FROM nginx:1.25-alpine
RUN rm /etc/nginx/conf.d/default.conf
COPY nginx.conf /etc/nginx/conf.d/default.conf
"

create_file "nginx/nginx.conf" \
"upstream crm_backend {
    server backend:8000;
}

server {
    listen 80;
    server_name localhost;
    
    client_max_body_size 100M;
    
    location /static/ {
        alias /static/;
    }
    
    location /media/ {
        alias /media/;
    }
    
    location / {
        proxy_pass http://crm_backend;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
    }
}
"

# ============================================
# 8. Makefile и README
# ============================================

create_file "Makefile" \
".PHONY: help up down logs shell migrate createsuperuser test

help:
\t@echo \"Available commands:\"
\t@echo \"  make up          - Start all containers\"
\t@echo \"  make down        - Stop all containers\"
\t@echo \"  make logs        - View all logs\"
\t@echo \"  make shell       - Open Django shell\"
\t@echo \"  make migrate     - Run migrations\"
\t@echo \"  make createsuperuser - Create admin user\"
\t@echo \"  make test        - Run tests\"

up:
\tdocker-compose -f docker/docker-compose.yml up -d --build

down:
\tdocker-compose -f docker/docker-compose.yml down

logs:
\tdocker-compose -f docker/docker-compose.yml logs -f

shell:
\tdocker-compose -f docker/docker-compose.yml exec backend python manage.py shell

migrate:
\tdocker-compose -f docker/docker-compose.yml exec backend python manage.py migrate

createsuperuser:
\tdocker-compose -f docker/docker-compose.yml exec backend python manage.py createsuperuser

test:
\tdocker-compose -f docker/docker-compose.yml exec backend python manage.py test
"

create_file ".gitignore" \
"__pycache__/
*.py[cod]
*.so
.Python
env/
venv/
.venv
*.egg-info/
dist/
build/
*.log
*.pid
*.db
*.sqlite3
db.sqlite3
/static/
/media/
/backend/static/
/backend/media/
/backend/logs/
.env
.env.dev
.env.prod
.vscode/
.idea/
*.swp
.DS_Store
*.pid
*.sock
.coverage
htmlcov/
.pytest_cache/
celerybeat-schedule
celerybeat.pid
"

# ============================================
# 8. Финальные сообщения
# ============================================

echo -e "\n${GREEN}========================================${NC}"
echo -e "${GREEN}✅ Project structure created successfully!${NC}"
echo -e "${GREEN}========================================${NC}"

echo -e "\n${BLUE}Next steps:${NC}"
echo -e "  1. ${YELLOW}cd crm_project${NC}"
echo -e "  2. ${YELLOW}make up${NC}"
echo -e "  3. ${YELLOW}make createsuperuser${NC}"
echo -e "  4. ${YELLOW}Open http://localhost:8000/admin/${NC}"
echo -e "\n${BLUE}Or manually:${NC}"
echo -e "  ${YELLOW}docker-compose -f docker/docker-compose.yml up -d --build${NC}"
echo -e "  ${YELLOW}docker-compose -f docker/docker-compose.yml exec backend python manage.py createsuperuser${NC}"

echo -e "\n${BLUE}Services:${NC}"
echo -e "  📦 Django Admin:  ${YELLOW}http://localhost:8000/admin/${NC}"
echo -e "  📚 API Docs:      ${YELLOW}http://localhost:8000/swagger/${NC}"
echo -e "  🌸 Celery Flower: ${YELLOW}http://localhost:5555/${NC}"
echo -e "  🐘 PostgreSQL:    ${YELLOW}localhost:5433${NC}"
echo -e "  📦 Redis:         ${YELLOW}localhost:6379${NC}"

echo -e "\n${BLUE}Credentials:${NC}"
echo -e "  👤 Username: ${YELLOW}admin${NC}"
echo -e "  🔑 Password: ${YELLOW}admin123${NC}"

echo -e "\n${GREEN}========================================${NC}\n"