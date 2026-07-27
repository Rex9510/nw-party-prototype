#!/usr/bin/env bash
# ============================================================================
# 党员学时统计系统 V1-MVP · 部署状态检查（只读）
# ============================================================================
set -euo pipefail
GREEN='\033[0;32m'; YELLOW='\033[1;33m'; RED='\033[0;31m'; NC='\033[0m'

ok()   { echo -e "${GREEN}✅ $*${NC}"; }
warn() { echo -e "${YELLOW}⚠️  $*${NC}"; }
bad()  { echo -e "${RED}❌ $*${NC}"; }

APP_NAME="nwparty"
APP_USER="nwparty"
APP_HOME="/var/www/${APP_NAME}"
NGINX_SITE="nwparty-v1"
BACKEND_PORT=8000
FRONTEND_PORT=8081

echo "============================================================"
echo "党员学时统计系统 V1-MVP · 部署状态"
echo "============================================================"
echo ""

# 1. 用户
echo "【1. 系统用户 ${APP_USER}】"
if id "${APP_USER}" &>/dev/null; then
  ok "存在（uid=$(id -u ${APP_USER})）"
else
  bad "不存在"
fi
echo ""

# 2. 目录
echo "【2. 目录 ${APP_HOME}】"
if [[ -d "${APP_HOME}" ]]; then
  ok "存在（$(du -sh ${APP_HOME} 2>/dev/null | cut -f1)）"
  for sub in src/backend src/frontend config .env venv; do
    if [[ -e "${APP_HOME}/${sub}" ]]; then
      echo "   ✓ ${sub}"
    else
      echo "   ✗ ${sub} 缺失"
    fi
  done
else
  bad "不存在"
fi
echo ""

# 3. nginx site
echo "【3. nginx site ${NGINX_SITE}】"
if [[ -f /etc/nginx/sites-enabled/${NGINX_SITE}.conf ]]; then
  ok "enabled"
else
  bad "未启用"
fi
echo ""

# 4. 端口
echo "【4. 端口监听】"
for port in ${BACKEND_PORT} ${FRONTEND_PORT}; do
  if ss -tln | grep -qE ":${port}\s"; then
    ok "${port} 正在监听"
  else
    bad "${port} 未监听"
  fi
done
echo ""

# 5. PM2
echo "【5. PM2 进程】"
if id "${APP_USER}" &>/dev/null; then
  PM2_OUT=$(sudo -u "${APP_USER}" PM2_HOME="${APP_HOME}/.pm2" pm2 list 2>&1 || echo "PM2 失败")
  if echo "${PM2_OUT}" | grep -q "nwparty-api"; then
    ok "nwparty-api 进程存在"
    echo "${PM2_OUT}" | grep -A 1 "nwparty-api" | head -3
  else
    bad "nwparty-api 进程不存在"
  fi
else
  bad "用户 ${APP_USER} 不存在"
fi
echo ""

# 6. 健康检查
echo "【6. 后端健康检查】"
HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" "http://127.0.0.1:${BACKEND_PORT}/health" 2>&1 || echo "000")
if [[ "${HTTP_CODE}" == "200" ]]; then
  ok "GET /health → 200"
  curl -s "http://127.0.0.1:${BACKEND_PORT}/health" | head -c 200
  echo ""
else
  bad "GET /health → ${HTTP_CODE}"
fi
echo ""

# 7. 前端可达
echo "【7. 前端可达性】"
HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" "http://127.0.0.1:${FRONTEND_PORT}/" 2>&1 || echo "000")
if [[ "${HTTP_CODE}" == "200" ]]; then
  ok "GET / → 200"
else
  bad "GET / → ${HTTP_CODE}"
fi
echo ""

# 8. 关键安全
echo "【8. 安全检查】"
if [[ -f "${APP_HOME}/.env" ]]; then
  PERMS=$(stat -c "%a" "${APP_HOME}/.env" 2>/dev/null || echo "???")
  if [[ "${PERMS}" == "600" ]]; then
    ok ".env 权限 = 600"
  else
    bad ".env 权限 = ${PERMS}（应为 600）"
  fi

  # JWT_SECRET 强度
  SECRET=$(grep "^JWT_SECRET=" "${APP_HOME}/.env" | cut -d= -f2- | tr -d '"' | tr -d "'")
  if [[ -z "${SECRET}" || "${SECRET}" == *"change-me"* || "${SECRET}" == *"FILL"* ]]; then
    bad "JWT_SECRET 是默认/占位值，必须改！"
  elif [[ ${#SECRET} -lt 32 ]]; then
    bad "JWT_SECRET 长度 < 32 字符，太弱"
  else
    ok "JWT_SECRET 已设置（${#SECRET} 字符）"
  fi

  # CORS
  CORS=$(grep "^CORS_ORIGINS=" "${APP_HOME}/.env" | cut -d= -f2-)
  if echo "${CORS}" | grep -q '\*'; then
    bad "CORS 包含通配符 *，生产不允许"
  else
    ok "CORS 未使用通配符"
  fi
else
  bad ".env 不存在"
fi
echo ""

echo "============================================================"
echo "操作命令："
echo "  看日志：  tail -f /var/log/nwparty/{access,error}.log"
echo "  PM2：     sudo -u nwparty PM2_HOME=/var/www/nwparty/.pm2 pm2 list"
echo "  PM2 重启：sudo -u nwparty PM2_HOME=/var/www/nwparty/.pm2 pm2 restart ecosystem.config.cjs"
echo "============================================================"
