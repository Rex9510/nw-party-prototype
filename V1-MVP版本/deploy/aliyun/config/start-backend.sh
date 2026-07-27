#!/usr/bin/env bash
set -e

ENV_FILE="/var/www/nwparty/.env"
if [[ ! -f "${ENV_FILE}" ]]; then
  echo "FATAL: ${ENV_FILE} not found" >&2
  exit 1
fi

set -a
while IFS= read -r line; do
  [[ -z "$line" || "$line" =~ ^[[:space:]]*# ]] && continue
  [[ "$line" =~ ^[^=]+= ]] || continue
  export "$line"
done < "${ENV_FILE}"
set +a

# debug: 确认 env 加载了
echo "[wrapper] CORS_ORIGINS=$CORS_ORIGINS"
echo "[wrapper] DATABASE_URL=$DATABASE_URL"

cd /var/www/nwparty/src/backend

exec /var/www/nwparty/venv/bin/gunicorn \
  app.main:app \
  -w 2 \
  -k uvicorn.workers.UvicornWorker \
  -b 127.0.0.1:8000 \
  --access-logfile /var/log/nwparty/access.log \
  --error-logfile /var/log/nwparty/error.log \
  --capture-output \
  --log-level info \
  --max-requests 1000 \
  --max-requests-jitter 100 \
  --timeout 60