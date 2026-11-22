#!/usr/bin/env bash

set -euo pipefail

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}═══════════════════════════════════════════════════════════════${NC}"
echo -e "${GREEN}🧪 ЛОКАЛЬНОЕ ТЕСТИРОВАНИЕ БОТА${NC}"
echo -e "${BLUE}═══════════════════════════════════════════════════════════════${NC}"
echo ""

# Проверяем наличие .env
if [ ! -f ".env" ]; then
    echo -e "${RED}❌ .env файл не найден!${NC}"
    echo -e "${YELLOW}💡 Создайте файл .env с переменными:${NC}"
    echo "   TOKEN=your_telegram_bot_token"
    echo "   ENVIRONMENT=development"
    exit 1
fi

echo -e "${GREEN}✅ Конфигурация OK${NC}"
echo ""

# Проверяем Python
echo -e "${BLUE}📦 Проверка Python...${NC}"
python3 --version
echo ""

# Устанавливаем зависимости
echo -e "${BLUE}📦 Проверка зависимостей...${NC}"
python3 -m pip check

echo ""
echo -e "${YELLOW}🧪 Запуск тестов...${NC}"
echo -e "${BLUE}═══════════════════════════════════════════════════════════════${NC}"
python3 -m unittest discover -v

if [ "${1:-}" = "--run-bot" ]; then
    echo -e "${YELLOW}🚀 Запуск бота...${NC}"
    exec python3 run.py
fi
