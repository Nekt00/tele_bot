# Neo Chat Bot — Telegram бот для сбора заявок в поддержку

> Внимание: команды ниже сохранены как устаревшая историческая справка и не должны использоваться. Актуальные безопасные инструкции находятся в `OPERATIONS.md`.

## 📁 Структура проекта

neo_chat_bot/
├── bot.py # Главный файл бота
├── config.py # Конфигурация
├── requirements.txt # Зависимости
├── Dockerfile # Docker образ
├── docker-compose.yml # Docker Compose
├── handlers/ # Обработчики событий
│ ├── welcome.py # Приветствие новых участников
│ └── quiz.py # Логика опроса
├── keyboards/ # Клавиатуры
│ └── quiz_keyboards.py # Кнопки для опроса
└── utils/ # Утилиты
├── logger.py # Логирование
└── database.py # Работа с БД


## 🚀 Деплой на сервер

### Первоначальная установка

```bash
# 1. Скопировать проект на сервер
scp -r ./ root@37.46.18.152:/opt/neo_chat_bot

# 2. Подключиться к серверу
ssh root@37.46.18.152

# 3. Запустить бота
cd /opt/neo_chat_bot
docker-compose up -d --build

🔄 Обновление бота
# 1. На локальной машине создай архив
cd /Users/evgenijfedorov/git/neo_chat_bot
tar --exclude='venv' \
    --exclude='__pycache__' \
    --exclude='*.pyc' \
    --exclude='.git' \
    --exclude='bot.db' \
    --exclude='bot.log' \
    --exclude='logs' \
    --exclude='*.tar.gz' \
    -czf neo_chat_bot_update.tar.gz .

# 2. Скопируй на сервер
scp neo_chat_bot_update.tar.gz root@37.46.18.152:/opt/

# 3. Подключись к серверу и обнови
ssh root@37.46.18.152
cd /opt
rm -rf neo_chat_bot_old
mv neo_chat_bot neo_chat_bot_old
mkdir -p neo_chat_bot
tar -xzf neo_chat_bot_update.tar.gz -C neo_chat_bot
cd neo_chat_bot

# 4. Перезапусти бота
docker-compose down
docker-compose up -d --build

# 5. Проверь логи
docker-compose logs -f --tail=50 bot

Обновление отдельных файлов
# Копирование конкретного файла
scp bot.py root@37.46.18.152:/opt/neo_chat_bot/
scp config.py root@37.46.18.152:/opt/neo_chat_bot/
scp handlers/welcome.py root@37.46.18.152:/opt/neo_chat_bot/handlers/

# Перезапуск бота
ssh root@37.46.18.152 "cd /opt/neo_chat_bot && docker-compose restart bot"

📋 Полезные команды на сервере
Управление ботом
# Просмотр логов
docker logs -f neo_chat_bot

# Перезапуск бота
systemctl restart neo-chat-bot

# Остановка бота
systemctl stop neo-chat-bot

# Запуск бота
systemctl start neo-chat-bot

# Статус бота
systemctl status neo-chat-bot

Работа с Docker

# Просмотр контейнеров
docker ps

# Перезапуск через docker-compose
cd /opt/neo_chat_bot
docker-compose restart bot

# Полная пересборка
docker-compose down
docker-compose up -d --build

Работа с PostgreSQL
# Вход в БД
docker exec -it neo_chat_bot_db psql -U telegram_bot_user -d telegram_bot_db

# Список таблиц
\dt

# Просмотр заявок
SELECT * FROM tickets ORDER BY created_at DESC LIMIT 10;

# Выход
\q
Резервное копирование БД
# Создать дамп
docker exec neo_chat_bot_db pg_dump -U telegram_bot_user telegram_bot_db > backup_$(date +%Y%m%d).sql

# Восстановить из дампа
cat backup_20240101.sql | docker exec -i neo_chat_bot_db psql -U telegram_bot_user telegram_bot_db

🔧 Настройки
Основные параметры в config.py
python
TOKEN = "токен_бота"
DELETE_DELAYS = {
    "command": 2,           # Удаление команд через 2 сек
    "user_message": 1,      # Удаление сообщений пользователя через 1 сек
    "temp_message": 5,      # Временные сообщения через 5 сек
    "confirm_success": 30,  # Подтверждение через 30 сек
    "group_instruction": 10 # Инструкция в группе через 10 сек
}
Переменные окружения (.env)
bash
POSTGRES_USER=telegram_bot_user
POSTGRES_PASSWORD=ваш_пароль
POSTGRES_DB=telegram_bot_db
🐛 Диагностика проблем
Бот не отвечает
bash
# Проверь логи
docker logs neo_chat_bot --tail=50

# Проверь что контейнер запущен
docker ps | grep neo_chat_bot
PostgreSQL не подключается
bash
# Проверь логи БД
docker logs neo_chat_bot_db --tail=30

# Проверь подключение
docker exec neo_chat_bot_db pg_isready -U telegram_bot_user
Ошибка при запуске
bash
# Пересобрать контейнеры
cd /opt/neo_chat_bot
docker-compose down
docker-compose build --no-cache
docker-compose up -d
