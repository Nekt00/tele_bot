#!/usr/bin/env bash

set -euo pipefail

PROJECT_DIR="${PROJECT_DIR:-/opt/neo_chat_bot}"
BACKUP_DIR="${BACKUP_DIR:-$PROJECT_DIR/backups}"
RETENTION_DAYS="${RETENTION_DAYS:-14}"
TIMESTAMP="$(date -u +%Y%m%dT%H%M%SZ)"
BACKUP_FILE="$BACKUP_DIR/neo_chat_bot_$TIMESTAMP.sql.gz"

mkdir -p "$BACKUP_DIR"
chmod 700 "$BACKUP_DIR"
cd "$PROJECT_DIR"

docker compose exec -T postgres sh -c \
    'PGPASSWORD="$POSTGRES_PASSWORD" pg_dump --clean --if-exists --no-owner --no-privileges -U "$POSTGRES_USER" "$POSTGRES_DB"' \
    | gzip -9 > "$BACKUP_FILE"

chmod 600 "$BACKUP_FILE"
find "$BACKUP_DIR" -type f -name 'neo_chat_bot_*.sql.gz' -mtime "+$RETENTION_DAYS" -delete

gzip -t "$BACKUP_FILE"
echo "Backup created: $BACKUP_FILE"
