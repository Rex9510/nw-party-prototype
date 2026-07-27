# 党员学时统计系统 V1-MVP · 阿里云部署指南

> 部署目标 ECS：`47.107.77.15` (Ubuntu 24.04, 2C1.6G, 40G)
> 部署策略：**隔离部署**，不与同机其他项目（`ai-investment` / `asset-management-system` / `nw-party-prototype`）冲突

---

## ⚠️ 部署前 5 件必做

1. **【必】改 SSH key** —— 你之前在对话里贴过 `D:/项目/rex.pem` 路径，这把 key **视为已泄露**，今天就轮换
2. **【必】先备案** —— 阿里云 ECS 上线域名必须备案（15-20 工作日），不备案只能用 IP
3. **【必】安全组** —— 阿里云 ECS 控制台，**限制 22 端口只对你的公司 IP/家里 IP 开放**；新建安全组开放 8000/8081 给前端用户
4. **【必】代码侧 P0 改造**（本地改完再部署）：
   - `.gitignore` 加 `.env`
   - `Dockerfile` 用 gunicorn 不用 uvicorn --reload
   - JWT_SECRET 启动时校验强密钥
   - CORS 默认 `["*"]` 改成实际域名
   - DEBUG 改 false
5. **【必】先填 `.env.production`** —— 见下面

---

## 📦 部署包结构

```
deploy/aliyun/
├── README.md                  ← 本文件
├── deploy.sh                  ← 一键部署主脚本
├── uninstall.sh               ← 卸载（保留数据）
├── status.sh                  ← 部署状态检查
├── config/
│   ├── .env.example           ← .env 模板（填好后改名为 .env.production）
│   ├── nwparty-v1.conf        ← nginx site 模板
│   ├── ecosystem.config.cjs   ← PM2 配置
│   └── start-backend.sh       ← 后端启动 wrapper（source .env + exec gunicorn）
└── logs/                      ← 占位（部署时日志写到 /var/log/nwparty/）
```

---

## 🚀 部署步骤（你 review 完按顺序跑）

### Step 0: 准备代码

在**本地 Windows** 上做 P0 改造后：

```powershell
# 把部署包 + 代码 scp 到 ECS
scp -i D:\项目\rex_new.pem -r D:\项目\党组织项目\V1-MVP版本\deploy\aliyun root@47.107.77.15:/tmp/
scp -i D:\项目\rex_new.pem -r D:\项目\党组织项目\V1-MVP版本\backend root@47.107.77.15:/tmp/nwparty_src/
scp -i D:\项目\rex_new.pem -r D:\项目\党组织项目\V1-MVP版本\frontend root@47.107.77.15:/tmp/nwparty_src/
```

### Step 1: SSH 上去准备

```bash
ssh -i ~/.ssh/rex_new.pem root@47.107.77.15

# 移动代码到目标位置（让 deploy.sh 能找到）
mkdir -p /var/www/nwparty/src
mv /tmp/nwparty_src/backend /var/www/nwparty/src/
mv /tmp/nwparty_src/frontend /var/www/nwparty/src/
mv /tmp/aliyun /var/www/nwparty/deploy_aliyun
cd /var/www/nwparty/deploy_aliyun

# 填 .env
cp config/.env.example config/.env.production
vim config/.env.production
# 必须改的：
#   JWT_SECRET          ← python -c "import secrets; print(secrets.token_urlsafe(48))"
#   POSTGRES_PASSWORD   ← 阿里云 RDS 实际密码
#   REDIS_PASSWORD      ← 阿里云 Redis 实际密码
#   OSS_ACCESS_KEY_*    ← 阿里云 OSS 实际 AK/SK
#   CORS_ORIGINS        ← 实际域名
#   PUBLIC_SERVER_NAME  ← 实际域名
chmod 600 config/.env.production
```

### Step 2: 跑部署

```bash
sudo bash deploy.sh
```

预期 2-3 分钟（npm install 最慢）。跑完会打印「部署完成」。

### Step 3: 验收

```bash
# 一键检查
sudo bash status.sh

# 预期看到：
#   ✅ 用户 nwparty 存在
#   ✅ 8000 正在监听
#   ✅ 8081 正在监听
#   ✅ nwparty-api 进程存在
#   ✅ GET /health → 200
#   ✅ GET / → 200
#   ✅ JWT_SECRET 已设置
#   ✅ CORS 未使用通配符

# 浏览器访问
curl -I http://127.0.0.1:8081/        # 200
curl    http://127.0.0.1:8000/health  # {"status":"ok",...}
```

### Step 4: 改超管密码

```bash
# 数据库走云，先用 ECS 上 psql 连 RDS（确保 ECS 在 RDS 白名单）
PGPASSWORD=xxx psql -h YOUR_RDS_HOST -U nwparty -d nwparty \
  -c "UPDATE users SET password_hash = '<new_bcrypt_hash>' WHERE id = 1;"
# 或者用项目提供的 CLI
cd /var/www/nwparty/src/backend
source /var/www/nwparty/venv/bin/activate
python -c "from app.core.security import hash_password; print(hash_password('YOUR_NEW_STRONG_PASSWORD'))"
# 然后用上面 hash 更新数据库
```

### Step 5: 防火墙 / 安全组

阿里云控制台：
- ECS 实例 → 安全组 → 入方向 → 新增规则：
  - 端口 `8081`，协议 TCP，源 `0.0.0.0/0`（或限定到客户 IP 段）
  - 端口 `8000` —— **不要对外开**（只走 nginx 反代）
- 安全组**不要**开放 `22` 给 `0.0.0.0/0`

---

## 🔄 日常运维

```bash
# 看日志
tail -f /var/log/nwparty/access.log
tail -f /var/log/nwparty/error.log
tail -f /var/log/nwparty/pm2-out.log

# PM2
sudo -u nwparty PM2_HOME=/var/www/nwparty/.pm2 pm2 list
sudo -u nwparty PM2_HOME=/var/www/nwparty/.pm2 pm2 logs nwparty-api
sudo -u nwparty PM2_HOME=/var/www/nwparty/.pm2 pm2 restart nwparty-api

# 重新加载 nginx（改了配置后）
sudo nginx -t && sudo systemctl reload nginx

# 重新跑部署（升级代码）
cd /var/www/nwparty/deploy_aliyun
sudo bash deploy.sh   # 幂等，代码会被覆盖
```

## 🗑 卸载

```bash
# Dry-run：先看会删啥
sudo bash uninstall.sh --dry-run

# 真卸载（保留数据，移走代码）
sudo bash uninstall.sh

# 数据：自己去阿里云控制台删 RDS / Redis / OSS
```

---

## 🚨 故障排查

### 端口被占
```bash
ss -tlnp | grep :8000
# 看哪个进程占了 → kill 或改端口
```

### 502 Bad Gateway
```bash
# 后端没起
sudo -u nwparty PM2_HOME=/var/www/nwparty/.pm2 pm2 list
# 看 nwparty-api 状态
tail -50 /var/log/nwparty/error.log
```

### CORS 报错
```bash
# .env 里 CORS_ORIGINS 是不是漏了当前域名？
grep CORS /var/www/nwparty/.env
# 改完要重启
sudo -u nwparty PM2_HOME=/var/www/nwparty/.pm2 pm2 restart nwparty-api
```

### 前端调 API 404
- 看浏览器 Network，URL 是不是带 `/api/v1/...`
- 前端默认走同源 `/api/v1`（不需要 VITE_API_BASE）
- 部署时如果用了独立 API 域名，要设 `VITE_API_BASE=https://api.xxx.cn/api/v1` 再 build

---

## 🛡 不影响其他项目的 5 个硬约束

本部署方案严格保证：

| 约束 | 实现 |
|---|---|
| 不碰旧原型 | 部署到 `/var/www/nwparty/`，**不碰** `/var/www/nw-party-prototype/` |
| 不动别人项目 | 部署到 `/var/www/nwparty/`，**不碰** `/var/www/asset-management-system/` |
| 不动现有 nginx site | 只新增 `nwparty-v1.conf`，不修改任何已有 site |
| 不占 80/8080/3000 | 用 8000/8081 两个新端口（已确认空闲）|
| 不污染现有 PM2 | 新建 `nwparty` 用户 + 独立 `PM2_HOME=/var/www/nwparty/.pm2` |

---

## 📊 资源消耗预估

| 组件 | 内存 | 磁盘 |
|---|---|---|
| nwparty-api (gunicorn 2 worker) | ~250MB | 50MB |
| 前端静态文件 | 0 | ~5MB |
| 日志（30 天轮转） | 0 | ~500MB |
| **合计** | ~250MB | ~600MB |

1.6G 内存机器够用，**还剩 ~1.3G** 给同机其他项目。

---

## ⚡ 部署后 1 周必看

- [ ] 阿里云云监控 → ECS / RDS / Redis 阈值告警配了
- [ ] RDS 自动备份开了（默认就有，确认 7 天保留）
- [ ] ECS 镜像做了一次完整快照
- [ ] ICP 备案号挂到页面底部
- [ ] SSH key 已轮换（rex.pem 已废）

---

## 📞 应急联系

- 服务挂了：先看 `status.sh` 输出
- 数据库连不上：检查 RDS 白名单（ECS 内网 IP）
- OSS 上传失败：检查 RAM 角色权限
- 完全搞不定：保留 `/var/log/nwparty/*.log` 全部日志，联系开发
