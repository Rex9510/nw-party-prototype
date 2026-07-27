#!/usr/bin/env bash
# ============================================================================
# 党员学时统计系统 V1-MVP · 阿里云部署脚本（隔离部署版）
# ----------------------------------------------------------------------------
# 目标：把 V1-MVP 部署到 47.107.77.15，不影响同机其他项目。
#
# 硬约束（违反任何一条立即终止）：
#   1. 不动 /var/www/nw-party-prototype/   （旧原型，保留）
#   2. 不动 /var/www/asset-management-system/  （别人的项目）
#   3. 不改 /etc/nginx/sites-enabled/{ai-investment,default,nw-party.conf}
#   4. 不占 80 / 8080 / 3000 / 22 端口
#   5. 不碰现有 PM2 实例（admin / root）
#   6. 不装 docker（节省内存 + 避免和现有栈冲突）
#
# 用法：
#   1. 把整个 aliyun/ 目录 scp 到 ECS（先 scp 到 /tmp/）
#   2. ssh 上去，cd /tmp/aliyun
#   3. 先填 .env（cp .env.example .env，vim .env）
#   4. sudo bash deploy.sh
#
# 幂等：可以多次跑，第二次起会跳过已完成的步骤。
# ============================================================================
set -euo pipefail

# ---- 颜色（出错更醒目） --------------------------------------------------
RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; NC='\033[0m'
say()  { echo -e "${GREEN}[$(date +%H:%M:%S)]${NC} $*"; }
warn() { echo -e "${YELLOW}[$(date +%H:%M:%S)] WARN${NC} $*"; }
die()  { echo -e "${RED}[$(date +%H:%M:%S)] FATAL${NC} $*" >&2; exit 1; }

# ---- 守卫：必须是 root 跑（建用户、绑端口要权限） -------------------------
[[ $EUID -ne 0 ]] && die "请用 root 跑：sudo bash deploy.sh"

# ---- 路径常量 ------------------------------------------------------------
APP_NAME="nwparty"
APP_USER="nwparty"                      # 新建专用用户
APP_HOME="/var/www/${APP_NAME}"         # 代码根目录
APP_PORT_BACKEND=8000                   # 后端 gunicorn 端口（空着）
APP_PORT_FRONTEND=8081                  # 前端 nginx 端口（空着）
NGINX_SITE_NAME="nwparty-v1"            # 新 nginx site 名
BACKUP_DIR="/var/backups/${APP_NAME}"
LOG_DIR="/var/log/${APP_NAME}"
THIS_DIR="$(cd "$(dirname "$0")" && pwd)"

# ---- 守卫：检查不冲突端口 ------------------------------------------------
say "0. 检查端口不冲突（8000 / 8081）"
if ss -tln | grep -qE ':(8000|8081)\s'; then
  die "端口 8000 或 8081 已被占用：\n$(ss -tln | grep -E ':(8000|8081)\s')"
fi

# ---- 守卫：检查不冲突 nginx site -----------------------------------------
if [[ -f /etc/nginx/sites-enabled/${NGINX_SITE_NAME}.conf ]]; then
  warn "nginx site ${NGINX_SITE_NAME}.conf 已存在，将覆盖（部署版本号已带在文件名）"
fi

# ---- 守卫：检查不冲突用户 ------------------------------------------------
if id "${APP_USER}" &>/dev/null; then
  say "用户 ${APP_USER} 已存在，跳过创建"
else
  say "1. 创建专用用户 ${APP_USER}（无登录 shell，sandboxed）"
  useradd --system --shell /usr/sbin/nologin --home-dir "${APP_HOME}" --create-home "${APP_USER}"
fi

# ---- 准备目录结构 ---------------------------------------------------------
say "2. 准备目录"
mkdir -p "${APP_HOME}"/{backend,frontend,logs,venv,releases,current}
mkdir -p "${BACKUP_DIR}"/{db,code}
mkdir -p "${LOG_DIR}"
chown -R "${APP_USER}:${APP_USER}" "${APP_HOME}" "${LOG_DIR}"

# ---- 上传/同步代码（你 scp 进来的，本次先假设代码已在 ${APP_HOME}/src）----
SRC_BACKEND="${APP_HOME}/src/backend"
SRC_FRONTEND="${APP_HOME}/src/frontend"
if [[ ! -d "${SRC_BACKEND}" ]]; then
  die "未找到后端代码：${SRC_BACKEND}\n请先：scp -r 本地 V1-MVP版本/backend  root@47.107.77.15:${APP_HOME}/src/"
fi
if [[ ! -d "${SRC_FRONTEND}" ]]; then
  die "未找到前端代码：${SRC_FRONTEND}\n请先：scp -r 本地 V1-MVP版本/frontend  root@47.107.77.15:${APP_HOME}/src/"
fi

# ---- 部署后端 -------------------------------------------------------------
say "3. 部署后端：建 venv + 装依赖"
sudo -u "${APP_USER}" bash -c "
  cd ${SRC_BACKEND}
  python3 -m venv ${APP_HOME}/venv || true
  source ${APP_HOME}/venv/bin/activate
  pip install --upgrade pip -q
  pip install -r requirements.txt -q
  pip install gunicorn==22.0.0 -q
"

# ---- 复制 .env ------------------------------------------------------------
say "4. 写 .env（生产配置）"
if [[ ! -f "${APP_HOME}/.env" ]]; then
  if [[ ! -f "${THIS_DIR}/config/.env.production" ]]; then
    die "找不到 .env 模板：${THIS_DIR}/config/.env.production\n请先 cp config/.env.example config/.env.production 并填好真实值"
  fi
  cp "${THIS_DIR}/config/.env.production" "${APP_HOME}/.env"
  chmod 600 "${APP_HOME}/.env"
  chown "${APP_USER}:${APP_USER}" "${APP_HOME}/.env"
  say "   .env 已部署到 ${APP_HOME}/.env（权限 600）"
else
  say "   .env 已存在，保留"
fi

# ---- 数据库初始化（建表 + seed）-------------------------------------------
say "5. 初始化数据库（建表 + 种子数据，幂等）"
mkdir -p "${APP_HOME}/data"
chown "${APP_USER}:${APP_USER}" "${APP_HOME}/data"
sudo -u "${APP_USER}" bash -c "
  source ${APP_HOME}/venv/bin/activate
  cd ${SRC_BACKEND}
  python -m scripts.init_db
"

# ---- 构建前端 -------------------------------------------------------------
say "7. 构建前端 H5"
sudo -u "${APP_USER}" bash -c "
  cd ${SRC_FRONTEND}
  # 注入生产 API base（可选，覆盖默认的同源 /api/v1）
  if [[ -f ${THIS_DIR}/config/.env.production ]]; then
    source ${THIS_DIR}/config/.env.production
    if [[ -n \"\${PUBLIC_API_BASE:-}\" ]]; then
      echo \"VITE_API_BASE=\${PUBLIC_API_BASE}\" > .env.production
    fi
  fi
  if [[ ! -d node_modules ]]; then
    npm install --no-audit --no-fund -q
  fi
  npm run build:h5
"
# vite build 产物在 frontend/dist/build/h5
DIST_DIR="${SRC_FRONTEND}/dist/build/h5"
[[ -d "${DIST_DIR}" ]] || die "前端构建失败，未找到 ${DIST_DIR}"

# ---- 部署前端静态文件到 nginx --------------------------------------------
say "8. 部署前端静态文件到 ${APP_HOME}/frontend/dist"
rm -rf "${APP_HOME}/frontend/dist"
cp -r "${DIST_DIR}" "${APP_HOME}/frontend/dist"
chown -R "${APP_USER}:${APP_USER}" "${APP_HOME}/frontend/dist"

# ---- 部署 nginx site（新增，不动其他）-------------------------------------
say "9. 写 nginx site：${NGINX_SITE_NAME}.conf"
if [[ ! -f "${THIS_DIR}/config/${NGINX_SITE_NAME}.conf" ]]; then
  die "找不到 nginx 模板：${THIS_DIR}/config/${NGINX_SITE_NAME}.conf"
fi
SERVER_NAME="${PUBLIC_SERVER_NAME:-_}"  # 没填就用 _ 兜底（IP 访问）
sed "s|__SERVER_NAME__|${SERVER_NAME}|g; \
     s|__APP_HOME__|${APP_HOME}|g; \
     s|__BACKEND_PORT__|${APP_PORT_BACKEND}|g; \
     s|__FRONTEND_PORT__|${APP_PORT_FRONTEND}|g" \
     "${THIS_DIR}/config/${NGINX_SITE_NAME}.conf" \
     > "/etc/nginx/sites-available/${NGINX_SITE_NAME}.conf"
ln -sf "/etc/nginx/sites-available/${NGINX_SITE_NAME}.conf" \
       "/etc/nginx/sites-enabled/${NGINX_SITE_NAME}.conf"

# 验证 nginx 配置
nginx -t || die "nginx 配置校验失败"

# ---- 部署 PM2 ecosystem（gunicorn workers）-------------------------------
say "10. 部署 PM2 ecosystem + 启动脚本"
mkdir -p "${APP_HOME}/config"
cp "${THIS_DIR}/config/ecosystem.config.cjs" "${APP_HOME}/ecosystem.config.cjs"
cp "${THIS_DIR}/config/start-backend.sh" "${APP_HOME}/config/start-backend.sh"
chmod +x "${APP_HOME}/config/start-backend.sh"
chown -R "${APP_USER}:${APP_USER}" "${APP_HOME}/config" "${APP_HOME}/ecosystem.config.cjs"

# 用专用 PM2_HOME 启动（不污染 root / admin 的 PM2）
sudo -u "${APP_USER}" bash -c "
  export PM2_HOME=${APP_HOME}/.pm2
  pm2 delete ecosystem.config.cjs 2>/dev/null || true
  pm2 start ecosystem.config.cjs
  pm2 save
"

# ---- 重新加载 nginx -------------------------------------------------------
say "11. 重新加载 nginx"
systemctl reload nginx

# ---- 收尾 -----------------------------------------------------------------
say ""
say "============================================================"
say "✅ 部署完成"
say "============================================================"
say "前端：  http://<ECS_IP>:${APP_PORT_FRONTEND}  （或配置的域名）"
say "后端：  http://<ECS_IP>:${APP_PORT_BACKEND}  （API root）"
say "API 文档：http://<ECS_IP>:${APP_PORT_BACKEND}/docs"
say "日志：  tail -f ${LOG_DIR}/access.log  ${LOG_DIR}/error.log"
say "PM2：   sudo -u ${APP_USER} PM2_HOME=${APP_HOME}/.pm2 pm2 list"
say ""
say "⚠️  立刻改超管密码（默认 admin123）："
say "   curl -X PATCH http://127.0.0.1:${APP_PORT_BACKEND}/api/v1/users/1/reset-password ..."
say ""
say "⚠️  ECS 安全组记得开 ${APP_PORT_FRONTEND}/${APP_PORT_BACKEND}（限定你公司 IP）"
say "============================================================"
