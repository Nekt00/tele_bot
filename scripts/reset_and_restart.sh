#!/usr/bin/env bash

set -euo pipefail

PROJECT_DIR="${PROJECT_DIR:-/opt/neo_chat_bot}"
cd "$PROJECT_DIR"

echo "Обновляю и перезапускаю контейнеры без удаления данных..."
docker compose up -d --build --remove-orphans

echo "Ожидаю инициализацию сервисов..."
sleep 10

echo "Статус:"
docker compose ps

echo "Последние логи бота:"
docker compose logs --tail=30 bot

echo "Готово. Том PostgreSQL сохранён."
