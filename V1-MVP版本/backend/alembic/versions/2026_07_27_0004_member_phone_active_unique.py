"""修复 members UNIQUE 约束为 partial unique index

背景：
- 原约束 `UNIQUE(phone, status)` 设计意图是限制 active 状态手机号唯一
- 实际效果是任意 (phone, status) 组合都唯一 → 软删除（active→dimission）时与已存在的 dimission 记录冲突
- 修复：改为 partial unique index `UNIQUE(phone) WHERE status='active'`
  - 只对 active 状态做手机号唯一性约束
  - dimission/transferred 状态不再受约束 → 软删除不再冲突
  - 创建接口已有 active 状态查重（create_member / import_members）→ 业务逻辑不变

升级步骤：
1. 删除旧约束 uq_members_phone_active
2. 创建新 partial unique index ix_members_phone_active
3. 不动数据：原 UNIQUE(phone, status) 约束下，理论上不该有 dimission+phone 重复（ID 5/95 的脏数据已手动清理）

降级步骤：反向。
"""
from alembic import op
import sqlalchemy as sa


revision = "2026_07_27_0004"
down_revision = "2026_07_27_0003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # SQLite：删老 UNIQUE 约束（必须建临时表复制）
    with op.batch_alter_table("members", recreate="always") as batch_op:
        batch_op.drop_constraint("uq_members_phone_active", type_="unique")
    # 加 partial unique index（SQLite 支持，PostgreSQL 也支持）
    op.create_index(
        "ix_members_phone_active",
        "members",
        ["phone"],
        unique=True,
        sqlite_where=sa.text("status = 'active'"),
        postgresql_where=sa.text("status = 'active'"),
    )


def downgrade() -> None:
    op.drop_index("ix_members_phone_active", table_name="members")
    with op.batch_alter_table("members", recreate="always") as batch_op:
        batch_op.create_unique_constraint(
            "uq_members_phone_active", ["phone", "status"]
        )
