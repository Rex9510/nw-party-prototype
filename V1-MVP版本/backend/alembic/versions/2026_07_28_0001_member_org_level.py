"""成员 v3：org_level 字段 + branch_id 改 nullable + community_id/street_id

背景：原来 members.branch_id 必填（必须到支部）。
v3 支持街道/社区/支部任一级：
- org_level=branch 时 branch_id 必填（老数据现状）
- org_level=community 时 community_id 必填
- org_level=street 时 street_id 必填

升级步骤：
1. 加 community_id / street_id / org_level 字段（branch_id 已存在但 NOT NULL）
2. 老数据回填 org_level='branch'，community_id/street_id NULL
3. 改 branch_id 为 nullable（SQLite 改 NOT NULL 需要重建表，会丢失数据；这里用 batch_alter_table+recreate）
4. 加索引：ix_members_community_id / ix_members_street_id

降级步骤：反向（恢复 branch_id NOT NULL + 删字段）。
"""
from alembic import op
import sqlalchemy as sa


revision = "2026_07_28_0001"
down_revision = "2026_07_27_0005"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 1) 先加 community_id / street_id
    op.add_column("members", sa.Column("community_id", sa.BigInteger().with_variant(sa.Integer(), "sqlite"), nullable=True))
    op.add_column("members", sa.Column("street_id", sa.BigInteger().with_variant(sa.Integer(), "sqlite"), nullable=True))

    # 2) 加 org_level（默认 'branch' 让老数据天然落到 branch）
    op.add_column("members", sa.Column("org_level", sa.String(16), nullable=False, server_default="branch"))

    # 3) 加索引
    op.create_index("ix_members_community_id", "members", ["community_id"])
    op.create_index("ix_members_street_id", "members", ["street_id"])

    # 4) 老数据：community_id / street_id 反查 + 回填
    # branch → community → street
    # 用 SQL 一次性反查（依赖 branch_id 在老数据都有）
    op.execute("""
        UPDATE members
        SET community_id = (
            SELECT b.community_id FROM branches b WHERE b.id = members.branch_id
        )
        WHERE branch_id IS NOT NULL
    """)
    op.execute("""
        UPDATE members
        SET street_id = (
            SELECT c.street_id
            FROM branches b
            JOIN communities c ON c.id = b.community_id
            WHERE b.id = members.branch_id
        )
        WHERE branch_id IS NOT NULL
    """)

    # 5) branch_id 改 nullable（SQLite 这条路比较绕：直接 ALTER COLUMN 不支持 nullable 转换）
    # SQLite 的方案：必须重建表（保存数据 → 改 schema → 复制回来）
    # 用 batch_alter_table(recreate='always') 走 SQLAlchemy 的表重建
    with op.batch_alter_table("members", recreate="always") as batch_op:
        # 重建后：branch_id 改 nullable
        batch_op.alter_column("branch_id", existing_type=sa.BigInteger().with_variant(sa.Integer(), "sqlite"), nullable=True)


def downgrade() -> None:
    # 反向：先恢复 branch_id NOT NULL
    # 重建表
    with op.batch_alter_table("members", recreate="always") as batch_op:
        batch_op.alter_column("branch_id", existing_type=sa.BigInteger().with_variant(sa.Integer(), "sqlite"), nullable=False)

    op.drop_index("ix_members_street_id", table_name="members")
    op.drop_index("ix_members_community_id", table_name="members")
    op.drop_column("members", "org_level")
    op.drop_column("members", "street_id")
    op.drop_column("members", "community_id")
