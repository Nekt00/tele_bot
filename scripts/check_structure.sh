#!/bin/bash

GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo -e "${YELLOW}🔍 Проверка структуры проекта...${NC}"
echo ""

# Список необходимых файлов и директорий
items=(
    "run.py"
    "Dockerfile"
    "docker-compose.yml"
    "requirements.txt"
    "app/__init__.py"
    "app/bot.py"
    "app/config/__init__.py"
    "app/config/settings.py"
    "app/database/__init__.py"
    "app/database/base.py"
    "app/database/session.py"
    "app/handlers/__init__.py"
    "app/handlers/admin.py"
    "app/handlers/callbacks.py"
    "app/handlers/messages.py"
    "app/handlers/quiz.py"
    "app/handlers/welcome.py"
    "app/keyboards/__init__.py"
    "app/keyboards/quiz_keyboards.py"
    "app/models/__init__.py"
    "app/repositories/__init__.py"
    "app/services/__init__.py"
    "app/enums/__init__.py"
    "app/enums/quiz_step.py"
    "app/utils/logger.py"
)

missing=0
for item in "${items[@]}"; do
    if [ -f "$item" ] || [ -d "$item" ]; then
        echo -e "${GREEN}✅${NC} $item"
    else
        echo -e "${RED}❌${NC} $item"
        missing=1
    fi
done

echo ""
if [ $missing -eq 0 ]; then
    echo -e "${GREEN}✅ Все файлы и директории на месте!${NC}"
else
    echo -e "${RED}❌ Обнаружены проблемы со структурой проекта${NC}"
fi
