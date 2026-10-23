#!/usr/bin/env bash
# prepare_deploy.sh — подготовка архива для деплоя (Windows/Git Bash совместимо)
# Запускать локально из корня проекта crm_project/
#
# ВАЖНО (один раз на сервере):
#   ssh acerkuv@192.168.0.102
#   sudo mkdir -p /opt/temp/crm_project/{releases,backups,shared}
#   sudo chown -R acerkuv:acerkuv /opt/temp/crm_project
#   exit

set -euo pipefail

# ============ НАСТРОЙКИ ============
PROJECT_NAME="crm_project"
SERVER_USER="acerkuv"
SERVER_HOST="192.168.0.102"
SERVER_DIR="/opt/temp/${PROJECT_NAME}"

ARCHIVE_NAME="crm_deploy_$(date +%Y%m%d_%H%M%S).tar.gz"
TMP_DIR=".deploy_tmp"
# ===================================

GREEN='\033[0;32m'; YELLOW='\033[1;33m'; RED='\033[0;31m'; NC='\033[0m'
log()  { echo -e "${GREEN}[+]${NC} $*"; }
warn() { echo -e "${YELLOW}[!]${NC} $*"; }
err()  { echo -e "${RED}[x]${NC} $*" >&2; }

# Проверка что мы в корне проекта
if [[ ! -d "backend" || ! -d "docker" ]]; then
    err "Запусти скрипт из корня проекта (там где backend/ и docker/)"
fi

log "Очистка временной папки..."
rm -rf "${TMP_DIR}"
mkdir -p "${TMP_DIR}/${PROJECT_NAME}"

# Общие исключения для tar
EXCLUDES=(
    --exclude='__pycache__'
    --exclude='*.pyc'
    --exclude='*.pyo'
    --exclude='.pytest_cache'
    --exclude='.mypy_cache'
    --exclude='*.sqlite3'
    --exclude='.env'
    --exclude='.env.*'
    --exclude='venv'
    --exclude='.venv'
    --exclude='node_modules'
    --exclude='.git'
    --exclude='.idea'
    --exclude='.vscode'
    --exclude='.DS_Store'
)

log "Копирование backend..."
tar -cf - "${EXCLUDES[@]}" \
    --exclude='media' \
    --exclude='staticfiles' \
    backend | tar -xf - -C "${TMP_DIR}/${PROJECT_NAME}/"

log "Копирование docker..."
cp -r docker "${TMP_DIR}/${PROJECT_NAME}/docker"

[[ -d nginx ]] && { log "Копирование nginx..."; cp -r nginx "${TMP_DIR}/${PROJECT_NAME}/nginx"; }
[[ -d scripts ]] && { log "Копирование scripts..."; cp -r scripts "${TMP_DIR}/${PROJECT_NAME}/scripts"; }

# Frontend — всегда исходники, сервер сам соберёт (без node_modules/dist)
log "Копирование frontend (исходники)..."
mkdir -p "${TMP_DIR}/${PROJECT_NAME}/frontend"
tar -cf - "${EXCLUDES[@]}" --exclude='dist' --exclude='.vite' \
    -C frontend . | tar -xf - -C "${TMP_DIR}/${PROJECT_NAME}/frontend/"

# Makefile
[[ -f Makefile ]] && cp Makefile "${TMP_DIR}/${PROJECT_NAME}/"

# Чистим возможные __pycache__, которые могли просочиться
find "${TMP_DIR}/${PROJECT_NAME}" -type d -name '__pycache__' -exec rm -rf {} + 2>/dev/null || true
find "${TMP_DIR}/${PROJECT_NAME}" -type f -name '*.pyc' -delete 2>/dev/null || true

cat > "${TMP_DIR}/${PROJECT_NAME}/ENV_README.txt" <<'EOF'
Файлы .env.dev и .env.prod НЕ входят в архив.
Убедись, что на сервере они уже созданы в:
  /opt/temp/crm_project/shared/
Скрипт deploy.sh сам создаст симлинки в новый релиз.
EOF

log "Создание архива ${ARCHIVE_NAME}..."
tar -czf "${ARCHIVE_NAME}" -C "${TMP_DIR}" "${PROJECT_NAME}"

if command -v sha256sum >/dev/null 2>&1; then
    sha256sum "${ARCHIVE_NAME}" > "${ARCHIVE_NAME}.sha256"
else
    warn "sha256sum не найден — контрольная сумма не создана"
fi

rm -rf "${TMP_DIR}"

ARCHIVE_SIZE=$(du -h "${ARCHIVE_NAME}" | cut -f1)
log "Архив готов: ${ARCHIVE_NAME} (${ARCHIVE_SIZE})"

# ============ Отправка на сервер ============
read -r -p "Отправить архив на ${SERVER_USER}@${SERVER_HOST}? [y/N] " ANS
if [[ "${ANS,,}" == "y" ]]; then
    log "Проверяю папку на сервере..."
    ssh "${SERVER_USER}@${SERVER_HOST}" \
        "mkdir -p ${SERVER_DIR}/releases"

    log "Копирую архив..."
    scp "${ARCHIVE_NAME}" "${SERVER_USER}@${SERVER_HOST}:${SERVER_DIR}/releases/"
    [[ -f "${ARCHIVE_NAME}.sha256" ]] && \
        scp "${ARCHIVE_NAME}.sha256" "${SERVER_USER}@${SERVER_HOST}:${SERVER_DIR}/releases/"

    log "Готово. Дальше на сервере:"
    echo "    ssh ${SERVER_USER}@${SERVER_HOST}"
    echo "    cd ${SERVER_DIR}"
    echo "    ./deploy.sh releases/${ARCHIVE_NAME}"
fi