"""为 activity_attachments 加 thumbnail_url 字段

背景：照片缩略图。公开页接口只返缩略图（几十 KB），全图按需查。

注意：不能用 batch_alter_table recreate='always'——SQLAlchemy 反射外键时
该表的 FK 引用了 activities_old（v2 迁移遗留），会报 NoSuchTableError。
所以走显式 add_column 即可（SQLite ALTER TABLE ADD COLUMN 支持空字段）。
"""
from alembic import op
import sqlalchemy as sa


revision = "2026_07_27_0005"
down_revision = "2026_07_27_0004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "activity_attachments",
        sa.Column("thumbnail_url", sa.String(8192), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("activity_attachments", "thumbnail_url")
