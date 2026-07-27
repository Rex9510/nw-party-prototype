"""SQLAlchemy 引擎 + 会话工厂。

支持两种驱动：
- PostgreSQL（生产/正式） — 通过 DATABASE_URL 切到 postgresql+asyncpg://...
- SQLite（试点/小规模）   — 默认 sqlite+aiosqlite:///var/www/nwparty/data/nwparty.db

SQLite 已开启 WAL 模式，读写并发不互锁；适合 < 100 并发用户的内部系统。
"""
import os
from collections.abc import AsyncGenerator
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy import event
from sqlalchemy.orm import DeclarativeBase

from app.core.config import settings


class Base(DeclarativeBase):
    """所有模型继承此类。"""


# 异步驱动 URL 解析：
#   1) 显式 DATABASE_URL 环境变量（最高优先级，PG 和 SQLite 都用它）
#   2) 否则用 config.py 的 settings.database_url（默认是 PG localhost）
#   3) 试点用 SQLite：DATABASE_URL=sqlite+aiosqlite:///path/to.db
def _build_database_url() -> str:
    env_url = os.environ.get("DATABASE_URL")
    if env_url:
        return env_url
    return settings.database_url


DATABASE_URL = _build_database_url()


# SQLite 特殊处理
_engine_kwargs: dict = {"echo": settings.DEBUG, "pool_pre_ping": True}
if DATABASE_URL.startswith("sqlite"):
    # aiosqlite 是异步驱动，本身就处理线程安全；但 check_same_thread
    # 是 SQLAlchemy 同步 sqlite 驱动的参数，对 aiosqlite 不需要
    _engine_kwargs.pop("pool_pre_ping", None)
    # SQLite 路径的目录要存在（首次跑会建库）
    if ":///" in DATABASE_URL:
        db_path = DATABASE_URL.split("///", 1)[1]
        # 去掉可能的 query string（?journal_mode=WAL 之类）
        db_path = db_path.split("?")[0]
        db_dir = os.path.dirname(db_path)
        if db_dir and not os.path.exists(db_dir):
            try:
                os.makedirs(db_dir, exist_ok=True)
            except OSError:
                pass  # 部署时由 init_db.py 显式创建


engine = create_async_engine(DATABASE_URL, **_engine_kwargs)


# SQLite 开启 WAL（Write-Ahead Logging）+ 合理 busy_timeout
# 这样读不阻塞写，并发友好
@event.listens_for(engine.sync_engine, "connect")
def _set_sqlite_pragma(dbapi_connection, _):
    if DATABASE_URL.startswith("sqlite"):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA journal_mode=WAL")
        cursor.execute("PRAGMA synchronous=NORMAL")
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.execute("PRAGMA busy_timeout=5000")
        cursor.close()


AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSessionLocal() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
