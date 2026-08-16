#!/bin/bash

# update.sh - Быстрое обновление без полного деплоя
# Использование: ./update.sh [service_name]

set -e

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo -e "${GREEN}🔄 Обновляем сервисы...${NC}"

SERVICE=${1:-""}

if [ -z "$SERVICE" ]; then
    echo -e "${YELLOW}📋 Обновляем все сервисы${NC}"
    docker-compose -f docker/docker-compose.yml down
    docker-compose -f docker/docker-compose.yml build --no-cache
    docker-compose -f docker/docker-compose.yml up -d
else
    echo -e "${YELLOW}📋 Обновляем сервис: ${SERVICE}${NC}"
    docker-compose -f docker/docker-compose.yml build --no-cache $SERVICE
    docker-compose -f docker/docker-compose.yml up -d $SERVICE
fi

echo -e "${GREEN}✅ Обновление завершено!${NC}"