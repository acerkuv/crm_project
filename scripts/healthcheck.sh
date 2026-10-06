#!/bin/bash

# healthcheck.sh - Проверка здоровья всех сервисов

set -e

GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo -e "${YELLOW}🏥 Проверяем здоровье сервисов...${NC}"

# Проверяем бекенд
echo -n "🔍 Проверка бекенда... "
if curl -s -f -o /dev/null "http://localhost:8000/health/"; then
    echo -e "${GREEN}✅ OK${NC}"
else
    echo -e "${RED}❌ FAILED${NC}"
fi

# Проверяем фронтенд
echo -n "🔍 Проверка фронтенда... "
if curl -s -f -o /dev/null "http://localhost:3000"; then
    echo -e "${GREEN}✅ OK${NC}"
else
    echo -e "${RED}❌ FAILED${NC}"
fi

# Проверяем базу данных
echo -n "🔍 Проверка базы данных... "
if docker-compose -f docker/docker-compose.yml exec db pg_isready -U crm_user -d crm_db > /dev/null 2>&1; then
    echo -e "${GREEN}✅ OK${NC}"
else
    echo -e "${RED}❌ FAILED${NC}"
fi

echo -e "${GREEN}✅ Проверка завершена${NC}"