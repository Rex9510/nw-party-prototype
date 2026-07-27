"""
初始化数据库（试点用 SQLite 方案）：
  1. 用 Base.metadata.create_all() 建表（不依赖 alembic，部署简单）
  2. 注入种子数据（街道/社区/支部/字典/测试账号）

用法：
    python -m scripts.init_db

幂等：重复跑不会丢数据，重复数据会跳过。
"""
import asyncio
import sys
from pathlib import Path

# 让脚本能找到 app/
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.db.session import Base, engine
import app.db.base  # noqa: F401  # 触发所有 model 注册
from scripts.seed import seed


async def init():
    print('=== 1. 建表（如果不存在）===')
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    print('   [OK] 完成\n')

    print('=== 2. 注入种子数据 ===')
    await seed()

    # 关闭引擎（SQLite 需要，让 WAL 写回）
    await engine.dispose()
    print('\n[DONE] init_db 完成')


if __name__ == '__main__':
    asyncio.run(init())
