#!/usr/bin/env bash
# prepare_deploy.sh — подготовка архива для деплоя на домашний сервер
# Запускать локально из корня проекта crm_project/

set -euo pipefail

# ============ НАСТРОЙКИ ============
PROJECT_NAME="crm_project"
SERVER_USER="acerkuv"
SERVER_HOST="192.168.0.103"
SERVER_DIR="/opt/temp/${PROJECT_NAME}"

ARCHIVE_NAME="crm_deploy_$(date +%Y%m%d_%H%M%S).tar.gz"
TMP_DIR=".deploy_tmp"
# ===================================

GREEN='\033[0;32m'; YELLOW='\033[1;33m'; RED='\033[0;31m'; NC='\033[0m'
log()  { echo -e "${GREEN}[+]${NC} $*"; }
warn() { echo -e "${YELLOW}[!]${NC} $*"; }
err()  { echo -e "${RED}[x]${NC} $*" >&2; }

if [[ ! -d "backend" || ! -d "docker" ]]; then
    err "Запусти скрипт из корня проекта (там где backend/ и docker/)"
fi

log "Очистка временной папки..."
rm -rf "${TMP_DIR}"
mkdir -p "${TMP_DIR}/${PROJECT_NAME}"

log "Копирование файлов проекта..."

# Backend (без мусора)
rsync -a --exclude='__pycache__' \
         --exclude='*.pyc' \
         --exclude='*.pyo' \
         --exclude='.pytest_cache' \
         --exclude='.mypy_cache' \
         --exclude='*.sqlite3' \
         --exclude='.env' \
         --exclude='.env.*' \
         --exclude='media/*' \
         --exclude='staticfiles/*' \
         --exclude='venv' \
         --exclude='.venv' \
         backend/ "${TMP_DIR}/${PROJECT_NAME}/backend/"

# Docker
rsync -a docker/ "${TMP_DIR}/${PROJECT_NAME}/docker/"

# Nginx
[[ -d nginx ]] && rsync -a nginx/ "${TMP_DIR}/${PROJECT_NAME}/nginx/"

# Scripts
[[ -d scripts ]] && rsync -a scripts/ "${TMP_DIR}/${PROJECT_NAME}/scripts/"

# Frontend
if [[ -d frontend/dist ]]; then
    log "Найден frontend/dist — копирую собранный фронт"
    mkdir -p "${TMP_DIR}/${PROJECT_NAME}/frontend"
    rsync -a frontend/dist/ "${TMP_DIR}/${PROJECT_NAME}/frontend/dist/"
else
    warn "frontend/dist не найден — копирую исходники frontend/"
    rsync -a --exclude='node_modules' \
             --exclude='dist' \
             --exclude='.vite' \
             frontend/ "${TMP_DIR}/${PROJECT_NAME}/frontend/"
fi

# Makefile
[[ -f Makefile ]] && cp Makefile "${TMP_DIR}/${PROJECT_NAME}/"

cat > "${TMP_DIR}/${PROJECT_NAME}/ENV_README.txt" <<'EOF'
Файлы .env.dev и .env.prod НЕ входят в архив.
Убедись, что на сервере они уже созданы в:
  /opt/temp/crm_project/shared/
Скрипт deploy.sh сам создаст симлинки в новый релиз.
EOF

log "Создание архива ${ARCHIVE_NAME}..."
tar -czf "${ARCHIVE_NAME}" -C "${TMP_DIR}" "${PROJECT_NAME}"

sha256sum "${ARCHIVE_NAME}" > "${ARCHIVE_NAME}.sha256"

rm -rf "${TMP_DIR}"

ARCHIVE_SIZE=$(du -h "${ARCHIVE_NAME}" | cut -f1)
log "Архив готов: ${ARCHIVE_NAME} (${ARCHIVE_SIZE})"

# ============ ОПЦИОНАЛЬНО: сразу отправить на сервер ============
read -r -p "Отправить архив на ${SERVER_USER}@${SERVER_HOST}? [y/N] " ANS
if [[ "${ANS,,}" == "y" ]]; then
    log "Создаю папку на сервере (может потребоваться sudo-пароль)..."
    ssh "${SERVER_USER}@${SERVER_HOST}" \
        "sudo mkdir -p ${SERVER_DIR}/releases && sudo chown -R ${SERVER_USER}:${SERVER_USER} ${SERVER_DIR}"

    log "Копирую архив..."
    scp "${ARCHIVE_NAME}" "${ARCHIVE_NAME}.sha256" \
        "${SERVER_USER}@${SERVER_HOST}:${SERVER_DIR}/releases/"

    log "Готово. Дальше на сервере:"
    echo "    ssh ${SERVER_USER}@${SERVER_HOST}"
    echo "    cd ${SERVER_DIR}"
    echo "    ./deploy.sh ${ARCHIVE_NAME}"
fi