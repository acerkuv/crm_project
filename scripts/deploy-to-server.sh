#!/bin/bash
# deploy-to-server.sh - Деплой на продакшен сервер

set -e

# Цвета
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

# Конфигурация сервера
SERVER_USER="root"
SERVER_HOST="your-server.com"
SERVER_PATH="/opt/crm"
PROJECT_PATH="/c/Users/Mi/pw/crm_project/crm_project"

echo -e "${GREEN}🚀 Начинаем деплой на сервер...${NC}"

# 1. Проверка подключения
echo -e "${YELLOW}📡 Проверяем подключение к серверу...${NC}"
if ! ssh -q $SERVER_USER@$SERVER_HOST exit; then
    echo -e "${RED}❌ Нет подключения к серверу!${NC}"
    exit 1
fi

# 2. Сборка продакшен образов
echo -e "${YELLOW}🔨 Собираем продакшен образы...${NC}"
cd $PROJECT_PATH
docker-compose -f docker/docker-compose.production.yml build

# 3. Сохраняем образы
echo -e "${YELLOW}💾 Сохраняем образы в файлы...${NC}"
docker save crm_backend_prod:latest -o backend.tar
docker save crm_frontend_prod:latest -o frontend.tar

# 4. Копируем файлы на сервер
echo -e "${YELLOW}📁 Копируем файлы на сервер...${NC}"
scp backend.tar $SERVER_USER@$SERVER_HOST:$SERVER_PATH/
scp frontend.tar $SERVER_USER@$SERVER_HOST:$SERVER_PATH/
scp docker/docker-compose.production.yml $SERVER_USER@$SERVER_HOST:$SERVER_PATH/
scp .env.prod $SERVER_USER@$SERVER_HOST:$SERVER_PATH/

# 5. Запускаем деплой на сервере
echo -e "${YELLOW}🚀 Запускаем деплой на сервере...${NC}"
ssh $SERVER_USER@$SERVER_HOST << EOF
    cd $SERVER_PATH
    
    # Загружаем образы
    echo "📦 Загружаем образы..."
    docker load -i backend.tar
    docker load -i frontend.tar
    
    # Останавливаем старые контейнеры
    echo "🛑 Останавливаем старые контейнеры..."
    docker-compose -f docker-compose.production.yml down
    
    # Запускаем новые
    echo "▶️  Запускаем новые контейнеры..."
    docker-compose -f docker-compose.production.yml up -d
    
    # Проверяем здоровье
    echo "🏥 Проверяем здоровье..."
    sleep 10
    if curl -s -f -o /dev/null "http://localhost/health/"; then
        echo "✅ Бекенд работает"
    else
        echo "⚠️  Бекенд не отвечает, смотрим логи..."
        docker-compose -f docker-compose.production.yml logs --tail 50
    fi
    
    # Очищаем старые образы
    echo "🧹 Очищаем старые образы..."
    docker system prune -f
    
    echo "✅ Деплой завершен!"
EOF

# 6. Очистка локальных файлов
echo -e "${YELLOW}🧹 Очищаем локальные файлы...${NC}"
rm -f backend.tar frontend.tar

echo -e "${GREEN}✅ Деплой успешно завершен!${NC}"
echo -e "${GREEN}🌐 Сервер доступен по адресу: http://$SERVER_HOST${NC}"