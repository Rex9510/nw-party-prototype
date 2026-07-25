"""用户模型。"""
from datetime import datetime
from sqlalchemy import String, BigInteger, Integer, DateTime, ForeignKey, func

# SQLite 走 autoincrement 必须 INTEGER PRIMARY KEY；用 with_variant 兼容
BigIntPK = BigInteger().with_variant(Integer(), "sqlite")
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(BigIntPK, primary_key=True, autoincrement=True)
    phone: Mapped[str] = mapped_column(String(20), unique=True, index=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    name: Mapped[str] = mapped_column(String(64), nullable=False)

    # 角色
    ROLE_STREET_LEAD = "street_lead"           # 街道负责人
    ROLE_COMMUNITY_ORG = "community_organizer" # 社区组织委员
    ROLE_BRANCH_SEC = "branch_secretary"       # 支部书记
    ROLE_MEMBER = "member"                     # 党员
    ROLE_ADMIN = "system_admin"                # 系统管理员

    role: Mapped[str] = mapped_column(String(32), nullable=False, index=True)

    # 组织归属
    street_id: Mapped[int | None] = mapped_column(BigIntPK, ForeignKey("streets.id"), nullable=True)
    community_id: Mapped[int | None] = mapped_column(BigIntPK, ForeignKey("communities.id"), nullable=True, index=True)
    branch_id: Mapped[int | None] = mapped_column(BigIntPK, ForeignKey("branches.id"), nullable=True, index=True)

    status: Mapped[str] = mapped_column(String(16), default="active", nullable=False)
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
