FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

RUN addgroup --system bot && adduser --system --ingroup bot bot

COPY --chown=bot:bot . .
RUN chmod +x /app/docker-entrypoint.sh

USER bot

HEALTHCHECK --interval=30s --timeout=5s --start-period=30s --retries=3 \
    CMD python -c "import os,time; p='/tmp/neo_bot_healthy'; assert os.path.exists(p) and time.time()-os.path.getmtime(p) < 60"

ENTRYPOINT ["/app/docker-entrypoint.sh"]
