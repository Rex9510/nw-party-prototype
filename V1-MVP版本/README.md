# 南湾党建 V1-MVP

> 党员集中学习培训管理系统 · 真实 MVP（与原型分离开发）

## 项目位置

```
V1-MVP版本/
├── backend/          FastAPI + SQLAlchemy + PostgreSQL
├── frontend/         uni-app H5（Vue 3 + TS + Vant）
├── deploy/           Docker Compose 一键启动
├── docs/             方案文档（01-04）
├── 党组织需求V1-MVP版本.docx       原始需求
└── 202611南湾街道党校培训情况统计表.xlsx   业务字段来源
```

**与原型的关系**：原型代码（`../prototype/` + `../pc-admin/`）**完全保留不动**，MVP 在 `V1-MVP版本/` 下独立开发。

---

## 快速启动（Docker Compose）

```bash
cd V1-MVP版本/deploy
docker compose up -d
```

启动后访问：
- **API**：http://localhost:8000
- **API 文档**：http://localhost:8000/docs
- **MinIO 控制台**：http://localhost:9001（minioadmin / minioadmin）
- **前端**：见下方"前端启动"

第一次启动会自动：
1. 拉 PostgreSQL / Redis / MinIO 镜像
2. 跑 Alembic 迁移建表
3. 启动 FastAPI

---

## 初始化数据

启动后注入种子数据（街道/字典/初始超管）：

```bash
cd V1-MVP版本
docker compose -f deploy/docker-compose.yml exec api python -m scripts.seed
```

初始账号：
- 手机号：`13800000000`
- 密码：`admin123`
- 角色：系统管理员

---

## 前端启动（开发期 H5）

```bash
cd V1-MVP版本/frontend
npm install   # 或 pnpm install
npm run dev:h5
```

打开 http://localhost:5173 即可。

---

## 项目状态

| 阶段 | 状态 |
|---|---|
| 工程脚手架 | ✅ Day 1 |
| DB schema（13 张表） | ✅ Day 1 |
| JWT 登录 + /me + refresh | ✅ Day 1 |
| 党员库 CRUD | ⏳ Day 3 |
| 批量导入 | ⏳ Day 4 |
| 字典/讲师维护 | ⏳ Day 5 |
| 培训活动录入 | ⏳ Day 6-7 |
| 两级审核 | ⏳ Day 8-10 |
| 学时档案 | ⏳ Day 11 |
| xlsx 统计导出 | ⏳ Day 12 |
| 联调+修 bug | ⏳ Day 13-15 |

详细规划见 `docs/01-开发方案.md`。

---

## API 路由（Day 1 已通）

| Method | Path | 说明 |
|---|---|---|
| GET | `/health` | 健康检查 |
| POST | `/api/v1/auth/login` | 手机号+密码登录 |
| POST | `/api/v1/auth/refresh` | 刷新 access |
| GET | `/api/v1/auth/me` | 当前用户 |

其余 30+ endpoint 按 `docs/01-开发方案.md` 第六节逐步开发。

---

## 技术栈

- **后端**：Python 3.11 + FastAPI 0.115 + SQLAlchemy 2.0 + Pydantic v2
- **数据库**：PostgreSQL 16
- **缓存**：Redis 7
- **对象存储**：MinIO（开发）/ 阿里云 OSS（生产）
- **认证**：JWT (Access 2h + Refresh 7d) + bcrypt
- **前端**：uni-app（Vue 3 + TS + Vant）— H5 优先，后期编译微信小程序
- **部署**：Docker Compose + Nginx（生产） + GitHub Actions

---

> 启动开发日期：2026-07-25 · Day 1 提交
> 编制人：Mavis