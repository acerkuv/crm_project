#!/usr/bin/env bash
# deploy.sh — развёртывание обновления на сервере
# Запускать на сервере: ./deploy.sh crm_deploy_YYYYMMDD_HHMMSS.tar.gz

set -euo pipefail

# ============ НАСТРОЙКИ ============
PROJECT_NAME="crm_project"
PROJECT_ROOT="/opt/temp/${PROJECT_NAME}"
RELEASES_DIR="${PROJECT_ROOT}/releases"
BACKUP_DIR="${PROJECT_ROOT}/backups"
CURRENT_LINK="${PROJECT_ROOT}/current"
SHARED_DIR="${PROJECT_ROOT}/shared"

COMPOSE_FILE="docker/docker-compose.production.yml"
# Если у тебя один compose-файл — поменяй на docker/docker-compose.yml
# ===================================

GREEN='\033[0;32m'; YELLOW='\033[1;33m'; RED='\033[0;31m'; NC='\033[0m'
log()  { echo -e "${GREEN}[+]${NC} $*"; }
warn() { echo -e "${YELLOW}[!]${NC} $*"; }
err()  { echo -e "${RED}[x]${NC} $*" >&2; exit 1; }

[[ $# -ge 1 ]] || err "Использование: $0 <архив.tar.gz>"

ARCHIVE="$1"
[[ -f "${ARCHIVE}" ]] || ARCHIVE="${RELEASES_DIR}/${1}"
[[ -f "${ARCHIVE}" ]] || err "Архив не найден: $1"

TIMESTAMP=$(date +%Y%m%d_%H%M%S)
NEW_RELEASE="${RELEASES_DIR}/${TIMESTAMP}"

log "Обновление ${PROJECT_NAME}"
log "Архив:    ${ARCHIVE}"
log "Релиз:    ${NEW_RELEASE}"

# Права на /opt/temp/crm_project — если создано через sudo, надо чтобы писалось от acerkuv
if [[ ! -w "${PROJECT_ROOT}" ]]; then
    err "Нет прав на запись в ${PROJECT_ROOT}. Выполни:
    sudo mkdir -p ${PROJECT_ROOT}
    sudo chown -R ${USER}:${USER} ${PROJECT_ROOT}"
fi

mkdir -p "${RELEASES_DIR}" "${BACKUP_DIR}" "${SHARED_DIR}"

# --- 1. Проверка контрольной суммы ---
if [[ -f "${ARCHIVE}.sha256" ]]; then
    log "Проверка sha256..."
    ( cd "$(dirname "${ARCHIVE}")" && sha256sum -c "$(basename "${ARCHIVE}.sha256")" ) \
        || err "Контрольная сумма не совпала!"
fi

# --- 2. Бэкап текущего релиза ---
if [[ -L "${CURRENT_LINK}" ]]; then
    CURRENT_REAL=$(readlink -f "${CURRENT_LINK}")
    log "Бэкап текущего релиза: ${CURRENT_REAL}"
    tar -czf "${BACKUP_DIR}/release_${TIMESTAMP}.tar.gz" \
        -C "$(dirname "${CURRENT_REAL}")" "$(basename "${CURRENT_REAL}")" || \
        warn "Бэкап релиза не удался (продолжаю)"
fi

# --- 3. Бэкап БД ---
DB_CONTAINER=$(docker ps --format '{{.Names}}' | grep -E 'postgres|db' | head -n1 || true)
if [[ -n "${DB_CONTAINER}" ]]; then
    log "Бэкап PostgreSQL из ${DB_CONTAINER}..."
    docker exec "${DB_CONTAINER}" sh -c \
        'pg_dump -U "$POSTGRES_USER" "$POSTGRES_DB"' \
        > "${BACKUP_DIR}/db_${TIMESTAMP}.sql" || warn "Дамп БД не удался"
    gzip -f "${BACKUP_DIR}/db_${TIMESTAMP}.sql" || true
fi

# --- 4. Распаковка нового релиза ---
log "Распаковка в ${NEW_RELEASE}..."
mkdir -p "${NEW_RELEASE}"
tar -xzf "${ARCHIVE}" -C "${NEW_RELEASE}" --strip-components=1

# --- 5. Линковка shared-каталогов ---
log "Линковка shared-каталогов..."
for envf in .env.dev .env.prod; do
    if [[ -f "${SHARED_DIR}/${envf}" ]]; then
        ln -sfn "${SHARED_DIR}/${envf}" "${NEW_RELEASE}/${envf}"
        [[ -d "${NEW_RELEASE}/backend" ]] && \
            ln -sfn "${SHARED_DIR}/${envf}" "${NEW_RELEASE}/backend/${envf}"
    fi
done

for d in media staticfiles; do
    if [[ -d "${SHARED_DIR}/${d}" ]]; then
        if [[ -d "${NEW_RELEASE}/backend" ]]; then
            rm -rf "${NEW_RELEASE}/backend/${d}" 2>/dev/null || true
            ln -sfn "${SHARED_DIR}/${d}" "${NEW_RELEASE}/backend/${d}"
        fi
    fi
done

# --- 6. Переключение current ---
log "Переключение ${CURRENT_LINK} -> ${NEW_RELEASE}"
ln -sfn "${NEW_RELEASE}" "${CURRENT_LINK}"

cd "${CURRENT_LINK}"

# --- 7. Сборка и запуск ---
log "Сборка образов..."
docker compose -f "${COMPOSE_FILE}" build

log "Остановка старых контейнеров..."
docker compose -f "${COMPOSE_FILE}" down --remove-orphans || true

log "Запуск новых..."
docker compose -f "${COMPOSE_FILE}" up -d

# --- 8. Миграции и статика ---
log "Ожидание backend..."
sleep 8

log "Миграции..."
docker compose -f "${COMPOSE_FILE}" exec -T backend python manage.py migrate --noinput || \
    warn "Миграции не применились"

log "Сбор статики..."
docker compose -f "${COMPOSE_FILE}" exec -T backend python manage.py collectstatic --noinput || \
    warn "collectstatic не прошёл"

# --- 9. Чистка старых релизов/бэкапов ---
log "Очистка старых релизов (оставляю 5)..."
ls -1dt "${RELEASES_DIR}"/*/ 2>/dev/null | tail -n +6 | xargs -r rm -rf

log "Очистка старых бэкапов (оставляю 10)..."
ls -1t "${BACKUP_DIR}"/*.tar.gz 2>/dev/null | tail -n +11 | xargs -r rm -f
ls -1t "${BACKUP_DIR}"/*.sql.gz  2>/dev/null | tail -n +11 | xargs -r rm -f

# --- 10. Статус ---
echo
log "Статус контейнеров:"
docker compose -f "${COMPOSE_FILE}" ps

echo
log "✅ Деплой завершён: ${NEW_RELEASE}"
echo "   Frontend: http://192.168.0.103:3001"
echo "   Admin:    http://192.168.0.103:8000/admin/"
echo "   API:      http://192.168.0.103:8000/api/"
echo "   Flower:   http://192.168.0.103:5555"