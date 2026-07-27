#!/usr/bin/env bash
# ============================================================================
# 党员学时统计系统 V1-MVP · 卸载脚本（保留数据，仅移除部署）
# ----------------------------------------------------------------------------
# 警告：仅移除 V1-MVP 相关产物，不会动其他项目。
# 数据：数据库/Redis 走云服务，本脚本不删（你自己去云控制台操作）
# 代码：默认保留在 /var/www/nwparty/，30 天后再删
# ============================================================================
set -euo pipefail
RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; NC='\033[0m'
say()  { echo -e "${GREEN}[$(date +%H:%M:%S)]${NC} $*"; }
warn() { echo -e "${YELLOW}[$(date +%H:%M:%S)] WARN${NC} $*"; }
die()  { echo -e "${RED}[$(date +%H:%M:%S)] FATAL${NC} $*" >&2; exit 1; }

[[ $EUID -ne 0 ]] && die "请用 root 跑"

APP_NAME="nwparty"
APP_USER="nwparty"
APP_HOME="/var/www/${APP_NAME}"
NGINX_SITE="nwparty-v1"

# ---- 确认：会删哪些东西（dry-run 模式） ---------------------------------
DRY_RUN="${1:-}"
if [[ "${DRY_RUN}" == "--dry-run" || "${DRY_RUN}" == "-n" ]]; then
  say "[DRY-RUN] 将要移除（不会真执行）："
  echo "  1. PM2 进程 nwparty-api（保留在 ${APP_HOME}/.pm2）"
  echo "  2. nginx site /etc/nginx/sites-{available,enabled}/${NGINX_SITE}.conf"
  echo "  3. 用户 ${APP_USER}（系统用户）"
  echo "  4. 代码目录 ${APP_HOME}（移到 /var/www/_removed_${APP_NAME}_$(date +%Y%m%d) 暂存 30 天）"
  echo "  5. 日志目录 /var/log/${APP_NAME}（移到 /var/log/_removed_${APP_NAME}_$(date +%Y%m%d)）"
  echo ""
  echo "不会动：数据库、Redis、OSS、其它项目、同机其它 nginx site"
  exit 0
fi

# ---- 真卸载 ------------------------------------------------------------
say "1. 停 PM2 进程"
if id "${APP_USER}" &>/dev/null; then
  sudo -u "${APP_USER}" bash -c "PM2_HOME=${APP_HOME}/.pm2 pm2 delete ecosystem.config.cjs 2>/dev/null || true; PM2_HOME=${APP_HOME}/.pm2 pm2 kill 2>/dev/null || true"
fi

say "2. 移除 nginx site"
rm -f /etc/nginx/sites-enabled/${NGINX_SITE}.conf
rm -f /etc/nginx/sites-available/${NGINX_SITE}.conf
nginx -t && systemctl reload nginx

say "3. 暂存代码目录（30 天后自删）"
if [[ -d "${APP_HOME}" ]]; then
  mv "${APP_HOME}" "/var/www/_removed_${APP_NAME}_$(date +%Y%m%d)"
  say "   已移到 /var/www/_removed_${APP_NAME}_$(date +%Y%m%d)"
fi

say "4. 暂存日志目录"
if [[ -d "/var/log/${APP_NAME}" ]]; then
  mv "/var/log/${APP_NAME}" "/var/log/_removed_${APP_NAME}_$(date +%Y%m%d)"
fi

say "5. 移除系统用户"
if id "${APP_USER}" &>/dev/null; then
  userdel "${APP_USER}" 2>/dev/null || true
fi

say ""
say "✅ 卸载完成"
say "   代码/日志暂存 30 天（路径见上面），到期后："
say "   rm -rf /var/www/_removed_${APP_NAME}_* /var/log/_removed_${APP_NAME}_*"
say ""
say "⚠️  数据库（PostgreSQL）、Redis、OSS 仍存在，"
say "   需在阿里云控制台手动清理。"
