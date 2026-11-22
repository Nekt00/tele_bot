#!/usr/bin/env bash

set -euo pipefail

: "${DEPLOY_HOST:?Set DEPLOY_HOST to the target server hostname or IP}"

DEPLOY_USER="${DEPLOY_USER:-root}"
DEPLOY_PATH="${DEPLOY_PATH:-/opt/neo_chat_bot}"
REMOTE_ARCHIVE="/tmp/neo_chat_bot_deploy.tar.gz"
LOCAL_ARCHIVE="$(mktemp -t neo_chat_bot_deploy.XXXXXX.tar.gz)"

cleanup() {
    rm -f "$LOCAL_ARCHIVE"
}
trap cleanup EXIT

echo "Creating deployment archive without local secrets or runtime data..."
COPYFILE_DISABLE=1 tar \
    --exclude='.git' \
    --exclude='.env*' \
    --exclude='.venv' \
    --exclude='venv' \
    --exclude='__pycache__' \
    --exclude='*.pyc' \
    --exclude='*.db' \
    --exclude='*.log' \
    --exclude='logs' \
    --exclude='*.tar.gz' \
    --exclude='project_report.txt' \
    --exclude='._*' \
    -czf "$LOCAL_ARCHIVE" .

echo "Uploading application files to ${DEPLOY_USER}@${DEPLOY_HOST}..."
scp "$LOCAL_ARCHIVE" "${DEPLOY_USER}@${DEPLOY_HOST}:${REMOTE_ARCHIVE}"

echo "Updating containers while preserving the remote .env and database volume..."
ssh "${DEPLOY_USER}@${DEPLOY_HOST}" \
    "set -eu; install -d '$DEPLOY_PATH'; test -f '$DEPLOY_PATH/.env'; tar -xzf '$REMOTE_ARCHIVE' -C '$DEPLOY_PATH'; rm -f '$REMOTE_ARCHIVE'; cd '$DEPLOY_PATH'; docker compose up -d --build --remove-orphans; docker compose ps"

echo "Deployment completed."
