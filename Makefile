# Makefile для управления проектом

.PHONY: help dev prod build up down logs shell migrate test backup

help:
	@echo "Доступные команды:"
	@echo "  make dev          - Запуск в режиме разработки"
	@echo "  make prod         - Запуск в продакшен режиме"
	@echo "  make build        - Пересборка всех образов"
	@echo "  make up           - Запуск контейнеров"
	@echo "  make down         - Остановка контейнеров"
	@echo "  make logs         - Просмотр логов"
	@echo "  make shell        - Вход в контейнер бекенда"
	@echo "  make migrate      - Выполнение миграций"
	@echo "  make test         - Запуск тестов"
	@echo "  make backup       - Создание бэкапа БД"
	@echo "  make deploy       - Полный деплой"

dev:
	./scripts/deploy.sh development

prod:
	./scripts/deploy.sh production

build:
	docker-compose -f docker/docker-compose.yml build --no-cache

up:
	docker-compose -f docker/docker-compose.yml up -d

down:
	docker-compose -f docker/docker-compose.yml down

logs:
	docker-compose -f docker/docker-compose.yml logs -f

shell:
	docker-compose -f docker/docker-compose.yml exec backend bash

migrate:
	docker-compose -f docker/docker-compose.yml exec backend python manage.py migrate

test:
	docker-compose -f docker/docker-compose.yml exec backend python manage.py test

backup:
	./scripts/backup.sh

deploy:
	./scripts/deploy.sh development

update:
	./scripts/update.sh