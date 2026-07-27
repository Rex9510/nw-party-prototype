#!/usr/bin/env bash
# ============================================================================
# 后端启动 wrapper（PM2 调这个，不是直接调 gunicorn）
# ----------------------------------------------------------------------------
# 作用：source .env 后再 exec gunicorn，让 pydantic-settings 能读到生产配置
# ============================================================================
set -e

ENV_FILE="/var/www/nwparty/.env"
if [[ ! -f "${ENV_FILE}" ]]; then
  echo "FATAL: ${ENV_FILE} not found" >&2
  exit 1
fi

# 加载 .env 到当前 shell
set -a
# shellcheck disable=SC1090
source "${ENV_FILE}"
set +a

# 切到后端目录
cd /var/www/nwparty/src/backend

# exec 替换当前进程（让 gunicorn 拿到 PID 1，PM2 才能管）
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
