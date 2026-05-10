# 南湾党建-Ai管理平台（原型）

纯静态 HTML：PC 管理端（`pc-admin/`）与小程序高保真单页（`prototype/mobile_v2.html`）。本地可用 `python start-servers.py`（根目录 `8080`）。

**仓库范围**：仅收录可部署/可演示的静态原型与部署说明。需求分析、成本评估、访谈稿、Word/ZIP 等已在 `.gitignore` 中排除，仍保留在你本机目录，但不会进入 `git push`。

## 两种「链接形式」推到 GitHub（建议同时用）

| 形式 | 用途 | 做法摘要 |
|------|------|----------|
| **HTTPS 远程** | 本机 `git clone/push` 免配 SSH | `git remote add origin https://github.com/<用户>/<仓库>.git` |
| **SSH 远程** | 服务器稳定 `git pull`、免输密码 | `git remote add origin git@github.com:<用户>/<仓库>.git`，本机配 SSH key |

同一仓库只需一个 `origin`，二选一即可；另一形式可作为文档里的备用说明。

### 首次推送到 GitHub

1. 在 GitHub 新建空仓库（不要勾选自动加 README，避免首次 push 冲突）。
2. 在本项目根目录执行：

```powershell
cd "D:\项目\党组织项目"
git init
git branch -M main
git add .
git commit -m "chore: initial prototype for GitHub and deploy"
git remote add origin https://github.com/<你的用户名>/<仓库名>.git
git push -u origin main
```

若改用 SSH：

```powershell
git remote set-url origin git@github.com:<你的用户名>/<仓库名>.git
git push -u origin main
```

3. **GitHub Pages（第二个对外链接）**  
   仓库 **Settings → Pages**：Source 选 **Deploy from a branch**，Branch 选 **main**，Folder 选 **/ (root)**。  
   几分钟后可访问：

   - 导航页：`https://<用户>.github.io/<仓库名>/`
   - PC：`https://<用户>.github.io/<仓库名>/pc-admin/login.html`
   - 小程序原型：`https://<用户>.github.io/<仓库名>/prototype/mobile_v2.html`

   若 Pages 未生效，检查仓库是否为 **Public**（或 GitHub Pro 对 Private 开 Pages 的策略）。

---

## 阿里云轻量应用服务器（参考 `D:\项目\投资喵` 的差异）

投资喵是 **Node 前后端 + PM2 + `npm run build`**；本项目 **无构建步骤**，只需 **Nginx 指到仓库目录**（或 `git pull` 更新）。

### 1. 服务器准备（Ubuntu 示例）

```bash
sudo apt update
sudo apt install -y nginx git

sudo mkdir -p /var/www
cd /var/www
sudo git clone https://github.com/<你的用户名>/<仓库名>.git nw-party-prototype
# 若 HTTPS 不稳定，可改为 SSH clone，并配 Deploy key
```

### 2. Nginx

```bash
sudo cp /var/www/nw-party-prototype/deploy/nginx-site.example.conf /etc/nginx/conf.d/nw-party.conf
# 编辑 server_name、root 路径后：
sudo nginx -t && sudo systemctl reload nginx
```

安全组放行 **80 / 443**（若上证书）。

### 3. 可选：GitHub Actions 自动拉代码（与投资喵同思路）

本仓库已含 `.github/workflows/deploy-aliyun.yml`：向 `main` push 时 SSH 到轻量执行 `git fetch && git reset --hard origin/main`。

在 GitHub 仓库 **Settings → Secrets and variables → Actions** 添加：

- `DEPLOY_HOST`：服务器 IP 或域名  
- `DEPLOY_USER`：SSH 用户名  
- `DEPLOY_SSH_KEY`：私钥全文  
- `DEPLOY_PATH`（可选）：默认 `/var/www/nw-party-prototype`

**首次**必须在服务器上已存在该目录且为 `git clone` 结果（workflow 里若检测无 `.git` 会失败并提示先手动 clone）。

---

## 与「投资喵」部署对照

| 项目 | 投资喵 | 本原型 |
|------|--------|--------|
| 产物 | `server` + `client` build | 静态文件，无 build |
| 进程 | PM2 | 不需要 |
| CI | `npm ci` + `pm2 reload` | 仅 `git pull` / `git reset --hard` |
| Web | Nginx 反代或静态 | Nginx `root` 指向仓库根即可 |

若你希望 **HTTPS 证书（Let’s Encrypt）** 或 **同一台机子与子路径共存**，可说明当前 Nginx 配置，再单独改一版 `server` 块。
