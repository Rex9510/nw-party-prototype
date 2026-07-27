#!/usr/bin/env bash
# ============================================================================
# 党员学时统计系统 V1-MVP · SQLite 自动备份（试点用）
# ----------------------------------------------------------------------------
# 用法：crontab -e 加一行：
#   0 2 * * * /var/www/nwparty/deploy_aliyun/backup-sqlite.sh >> /var/log/nwparty/backup.log 2>&1
#
# 策略：
#   1. 每天凌晨 2 点，用 sqlite3 .backup 命令（安全的热备份，WAL 友好）
#   2. 保留 7 天
#   3. 备份文件名带时间戳，可追溯
# ============================================================================
set -euo pipefail
GREEN='\033[0;32m'; YELLOW='\033[1;33m'; NC='\033[0m'
say()  { echo -e "${GREEN}[$(date +%Y-%m-%d\ %H:%M:%S)]${NC} $*"; }
warn() { echo -e "${YELLOW}[$(date +%Y-%m-%d\ %H:%M:%S)] WARN${NC} $*"; }

APP_HOME="/var/www/nwparty"
DB_PATH="${APP_HOME}/data/nwparty.db"
BACKUP_DIR="${APP_HOME}/data/backups"
RETAIN_DAYS=7

# ---- 守卫 ----
if [[ ! -f "${DB_PATH}" ]]; then
  warn "数据库文件不存在：${DB_PATH}"
  exit 0
fi

# ---- 准备 ----
mkdir -p "${BACKUP_DIR}"

TIMESTAMP=$(date +%Y%m%d-%H%M%S)
BACKUP_FILE="${BACKUP_DIR}/nwparty-${TIMESTAMP}.db"

# ---- 热备份（用 sqlite3 .backup，比 cp 安全；WAL 模式下也安全）----
if command -v sqlite3 &>/dev/null; then
  say "热备份：${DB_PATH} → ${BACKUP_FILE}"
  sqlite3 "${DB_PATH}" ".backup '${BACKUP_FILE}'"
else
  # 退而求其次：cp（不完美但能用）
  warn "sqlite3 CLI 没装，用 cp 兜底（不安全，建议装 sqlite3）"
  cp "${DB_PATH}" "${BACKUP_FILE}"
  cp "${DB_PATH}-wal" "${BACKUP_FILE}-wal" 2>/dev/null || true
fi

# 压缩
gzip "${BACKUP_FILE}"
BACKUP_FILE="${BACKUP_FILE}.gz"

BACKUP_SIZE=$(du -h "${BACKUP_FILE}" | cut -f1)
say "完成：${BACKUP_FILE} (${BACKUP_SIZE})"

# ---- 清理 7 天前的 ----
say "清理 ${RETAIN_DAYS} 天前的备份..."
DELETED=$(find "${BACKUP_DIR}" -name "nwparty-*.db.gz" -mtime +${RETAIN_DAYS} -delete -print | wc -l)
if [[ "${DELETED}" -gt 0 ]]; then
  say "已清理 ${DELETED} 个旧备份"
fi

# ---- 统计 ----
TOTAL=$(du -sh "${BACKUP_DIR}" 2>/dev/null | cut -f1)
COUNT=$(ls "${BACKUP_DIR}"/nwparty-*.db.gz 2>/dev/null | wc -l)
say "当前备份：${COUNT} 个，共 ${TOTAL}"
