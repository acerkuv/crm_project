#!/bin/bash

# deploy.sh - Полный деплой CRM системы
# Использование: ./deploy.sh [production|development]

set -e

# Цвета для вывода
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}🚀 Начинаем деплой CRM системы...${NC}"

# Определяем окружение
ENV=${1:-development}
echo -e "${YELLOW}📋 Окружение: ${ENV}${NC}"

# Определяем файлы docker-compose
if [ "$ENV" == "production" ]; then
    COMPOSE_FILE="docker/docker-compose.production.yml"
    ENV_FILE=".env.prod"
    echo -e "${YELLOW}⚠️  ВНИМАНИЕ: Деплой в ПРОДАКШЕН!${NC}"
    read -p "Вы уверены? (y/N) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo -e "${RED}❌ Деплой отменен${NC}"
        exit 1
    fi
else
    COMPOSE_FILE="docker/docker-compose.yml"
    ENV_FILE=".env.dev"
fi

# 1. Создаем бэкап базы данных
echo -e "${YELLOW}📦 Создаем бэкап базы данных...${NC}"
./scripts/backup.sh

# 2. Останавливаем старые контейнеры
echo -e "${YELLOW}🛑 Останавливаем старые контейнеры...${NC}"
docker-compose -f $COMPOSE_FILE down

# 3. Обновляем код из репозитория
echo -e "${YELLOW}📥 Обновляем код...${NC}"
git pull origin main

# 4. Пересобираем образы
echo -e "${YELLOW}🔨 Пересобираем образы...${NC}"
docker-compose -f $COMPOSE_FILE build --no-cache

# 5. Запускаем контейнеры
echo -e "${YELLOW}▶️  Запускаем контейнеры...${NC}"
docker-compose -f $COMPOSE_FILE up -d

# 6. Ждем готовности бекенда
echo -e "${YELLOW}⏳ Ждем готовности бекенда...${NC}"
sleep 10

# 7. Выполняем миграции
echo -e "${YELLOW}📊 Выполняем миграции...${NC}"
docker-compose -f $COMPOSE_FILE exec backend python manage.py migrate

# 8. Собираем статику
echo -e "${YELLOW}📁 Собираем статику...${NC}"
docker-compose -f $COMPOSE_FILE exec backend python manage.py collectstatic --noinput

# 9. Проверяем здоровье
echo -e "${YELLOW}🏥 Проверяем здоровье...${NC}"
./scripts/healthcheck.sh

echo -e "${GREEN}✅ Деплой успешно завершен!${NC}"
echo -e "${GREEN}🌐 Приложение доступно по адресу: http://localhost${NC}"