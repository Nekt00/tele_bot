# Neo Chat Bot: эксплуатация

Бот собирает обращения через подписанный опрос в личном чате или свободное описание в исходной группе. `/admin` и `/stats` доступны только администраторам соответствующих групп.

## Локальная проверка

Требуется Python 3.12.

```bash
python3.12 -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
python -m unittest discover -v
```

После заполнения `TOKEN` локальный бот запускается командой `python run.py`. При `ENVIRONMENT=development` используется SQLite.

## Production

Создайте `.env` из примера и задайте токен и длинный случайный пароль PostgreSQL.

```bash
docker compose up -d --build
docker compose ps
docker compose logs --tail=100 bot
```

Контейнер работает без root и перед стартом выполняет `alembic upgrade head`. PostgreSQL не публикуется наружу. Оба сервиса используют `restart: unless-stopped`.

Безопасное обновление не копирует `.env`, локальные БД и логи и не удаляет volume:

```bash
DEPLOY_HOST=server.example.com ./update.sh
```

На сервере заранее должен существовать `/opt/neo_chat_bot/.env`. Пользователь и путь настраиваются через `DEPLOY_USER` и `DEPLOY_PATH`.

## Миграции

```bash
alembic current
alembic upgrade head
alembic history
```

`init.sql` оставлен только как историческая справка и не подключён к Compose.

## Резервные копии

```bash
PROJECT_DIR=/opt/neo_chat_bot ./scripts/backup_postgres.sh
```

Архивы создаются в `backups/`, проверяются через `gzip -t`, получают права `600` и хранятся 14 дней. Путь и срок задаются через `BACKUP_DIR` и `RETENTION_DAYS`. Запуск следует настроить ежедневным systemd timer или cron; восстановление нужно периодически проверять на отдельной БД.

## Перед релизом

```bash
python -m unittest discover -v
python -m pip check
bash -n update.sh scripts/*.sh docker-entrypoint.sh
alembic upgrade head
```

Все `.env` и backup-файлы исключены из Git и Docker-контекста. Случайно опубликованный Telegram-токен нужно отозвать через BotFather: удаления из файла недостаточно.
