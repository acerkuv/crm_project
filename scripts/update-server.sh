#!/bin/bash
# update-server.sh - Обновление без полного деплоя

set -e

SERVER_USER="root"
SERVER_HOST="your-server.com"
SERVER_PATH="/opt/crm"

echo "🔄 Обновляем сервер..."

# 1. Сборка только бекенда
docker build -t crm_backend_prod:latest -f backend/Dockerfile.prod backend/
docker save crm_backend_prod:latest -o backend.tar

# 2. Копируем и обновляем
scp backend.tar $SERVER_USER@$SERVER_HOST:$SERVER_PATH/

ssh $SERVER_USER@$SERVER_HOST << EOF
    cd $SERVER_PATH
    docker load -i backend.tar
    docker-compose -f docker-compose.production.yml up -d --no-deps backend
    echo "✅ Бекенд обновлен!"
EOF

rm -f backend.tar