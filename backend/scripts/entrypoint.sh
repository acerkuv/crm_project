#!/bin/bash
set -e

echo "========================================"
echo "Starting CRM Application"
echo "========================================"

# Функция для ожидания сервиса
wait_for_service() {
    local host=$1
    local port=$2
    local service=$3
    local max_attempts=30
    local attempt=1
    
    echo "Waiting for $service at $host:$port..."
    while ! nc -z "$host" "$port" 2>/dev/null; do
        if [ $attempt -ge $max_attempts ]; then
            echo "❌ $service not available after $max_attempts attempts"
            return 1
        fi
        echo "⏳ Waiting for $service... (attempt $attempt/$max_attempts)"
        sleep 2
        attempt=$((attempt + 1))
    done
    echo "✅ $service is ready"
    return 0
}

# Ожидание PostgreSQL
echo "----------------------------------------"
wait_for_service "${POSTGRES_HOST:-db}" "${POSTGRES_PORT:-5432}" "PostgreSQL"
if [ $? -ne 0 ]; then
    echo "❌ Failed to connect to PostgreSQL"
    exit 1
fi

# Ожидание Redis
echo "----------------------------------------"
wait_for_service "${REDIS_HOST:-redis}" "${REDIS_PORT:-6379}" "Redis"
if [ $? -ne 0 ]; then
    echo "❌ Failed to connect to Redis"
    exit 1
fi

echo "----------------------------------------"
echo "Checking Python syntax..."
python -m py_compile manage.py || {
    echo "❌ Syntax error in manage.py"
    exit 1
}

echo "----------------------------------------"
echo "Running Django migrations..."
python manage.py makemigrations --noinput || {
    echo "❌ Failed to create migrations"
    exit 1
}

python manage.py migrate --noinput || {
    echo "❌ Failed to apply migrations"
    exit 1
}

echo "----------------------------------------"
echo "Collecting static files..."
python manage.py collectstatic --noinput || {
    echo "⚠️  Failed to collect static files (continuing...)"
}

echo "----------------------------------------"
echo "Creating superuser if not exists..."
python manage.py shell -c "
from django.contrib.auth import get_user_model
User = get_user_model()
username = '${DJANGO_SUPERUSER_USERNAME:-admin}'
email = '${DJANGO_SUPERUSER_EMAIL:-admin@example.com}'
password = '${DJANGO_SUPERUSER_PASSWORD:-admin123}'
if not User.objects.filter(username=username).exists():
    User.objects.create_superuser(username, email, password)
    print(f'✅ Superuser \"{username}\" created')
else:
    print(f'ℹ️  Superuser \"{username}\" already exists')
" 2>/dev/null || echo "⚠️  Could not create superuser"

echo "========================================"
echo "✅ All checks passed! Starting application..."
echo "========================================"

exec "$@"