"""add sort column to streets/communities/branches + backfill

Revision ID: 2026_07_27_0001
Revises: 2026_07_25_0001
Create Date: 2026-07-27 18:00:00.000000

说明：生产部署用 SQLite（DATABASE_URL=sqlite+aiosqlite://）。
alembic env.py 会在运行时读 .env 的 DATABASE_URL 注入引擎。

回填策略：
  - streets: 按 id 升序，sort = id * 10
  - communities: 同 street_id 内按 id 升序，sort = rownum * 10
  - branches: 同 community_id 内按 id 升序，sort = rownum * 10
SQLite 3.45.1 完全支持窗口函数 ROW_NUMBER() OVER (PARTITION BY ...)。

注意：SQLite 的 UPDATE 没有 FROM 子句，用子查询 (SELECT ...) AS sub
要写成 WHERE id IN (SELECT ...) 或者 CTE (WITH ... AS sub) UPDATE ...。
为了跨 DB 兼容，用最稳的写法：WITH ... AS (...) UPDATE x SET col = sub.col FROM sub。
SQLite 和 PostgreSQL 都支持这个语法（CTE + UPDATE FROM 关联）。

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "2026_07_27_0001"
down_revision = "2026_07_25_0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ---- streets: 顶层，无父 ----
    op.add_column(
        "streets",
        sa.Column("sort", sa.Integer(), nullable=False, server_default="0"),
    )
    op.create_index("ix_streets_sort", "streets", ["sort"])
    # 按 id 顺序回填 sort = id * 10（无父，直接来）
    op.execute(
        "UPDATE streets SET sort = id * 10 WHERE sort = 0 OR sort IS NULL"
    )

    # ---- communities: 用 CTE 回填（SQLite + PG 都支持） ----
    op.add_column(
        "communities",
        sa.Column("sort", sa.Integer(), nullable=False, server_default="0"),
    )
    op.create_index("ix_communities_sort", "communities", ["sort"])
    op.execute("""
        WITH ranked AS (
            SELECT id, ROW_NUMBER() OVER (PARTITION BY street_id ORDER BY id) AS rn
            FROM communities
        )
        UPDATE communities
        SET sort = (SELECT rn * 10 FROM ranked WHERE ranked.id = communities.id)
        WHERE sort = 0 OR sort IS NULL
    """)

    # ---- branches: 同 community_id 内排序 ----
    op.add_column(
        "branches",
        sa.Column("sort", sa.Integer(), nullable=False, server_default="0"),
    )
    op.create_index("ix_branches_sort", "branches", ["sort"])
    op.execute("""
        WITH ranked AS (
            SELECT id, ROW_NUMBER() OVER (PARTITION BY community_id ORDER BY id) AS rn
            FROM branches
        )
        UPDATE branches
        SET sort = (SELECT rn * 10 FROM ranked WHERE ranked.id = branches.id)
        WHERE sort = 0 OR sort IS NULL
    """)


def downgrade() -> None:
    op.drop_index("ix_branches_sort", table_name="branches")
    op.drop_column("branches", "sort")
    op.drop_index("ix_communities_sort", table_name="communities")
    op.drop_column("communities", "sort")
    op.drop_index("ix_streets_sort", table_name="streets")
    op.drop_column("streets", "sort")
