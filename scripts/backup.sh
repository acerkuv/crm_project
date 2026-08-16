#!/bin/bash

# backup.sh - Создание бэкапа базы данных

set -e

BACKUP_DIR="./backups"
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
BACKUP_FILE="$BACKUP_DIR/backup_$TIMESTAMP.sql"

mkdir -p $BACKUP_DIR

echo "📦 Создаем бэкап базы данных..."

# Проверяем, запущен ли контейнер с БД
if docker-compose -f docker/docker-compose.yml ps db | grep -q "Up"; then
    docker-compose -f docker/docker-compose.yml exec db pg_dump -U crm_user crm_db > $BACKUP_FILE
    echo "✅ Бэкап создан: $BACKUP_FILE"
    
    # Сжимаем
    gzip $BACKUP_FILE
    echo "✅ Бэкап сжат: ${BACKUP_FILE}.gz"
else
    echo "❌ Контейнер с БД не запущен!"
    exit 1
fi