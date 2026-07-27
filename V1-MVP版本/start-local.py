"""
本地启动脚本（开发环境）：
- 自动用 SQLite（无需 PG）
- 自动建表 + 注入种子数据
- 默认端口：8000（后端）

用法：
    python start-local.py
"""
import asyncio
import os
import sys
from pathlib import Path

# 切到 backend 目录
BACKEND_DIR = Path(__file__).resolve().parent / "backend"
sys.path.insert(0, str(BACKEND_DIR))

# 用 SQLite 替代 PG
os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///./nwparty_local.db"
os.environ["JWT_SECRET"] = "local-dev-secret"
os.environ["DEBUG"] = "true"
os.environ["STORAGE_PROVIDER"] = "minio"
# CORS 允许前端 5173
os.environ["CORS_ORIGINS"] = '["http://localhost:5173","http://127.0.0.1:5173","*"]'

import uvicorn
from app.db.session import Base, engine
import app.db.base  # noqa
from scripts.seed import seed


async def init_db():
    """建表 + 注入种子。"""
    print("[1/3] Init SQLite database...")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    print("[2/3] Seeding data...")
    await seed()
    print("[3/3] Starting API server...")
    print()
    print("=" * 60)
    print("  V1-MVP local dev server is starting")
    print("  API:     http://localhost:8000")
    print("  API doc: http://localhost:8000/docs")
    print("  Default accounts:")
    print("    13800000000 / admin123  (system admin)")
    print("    13800000001 / lead123   (street lead)")
    print("    13800000002 / org123    (community organizer)")
    print("=" * 60)
    print()


def main():
    asyncio.run(init_db())

    config = uvicorn.Config(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=False,
        log_level="info",
    )
    server = uvicorn.Server(config)
    server.run()


if __name__ == "__main__":
    main()
