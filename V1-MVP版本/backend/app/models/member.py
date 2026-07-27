"""党员 + 批量导入记录。"""
from datetime import datetime, date
from typing import TYPE_CHECKING
from sqlalchemy import String, BigInteger, Integer, DateTime, Date, ForeignKey, JSON, func, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base

if TYPE_CHECKING:
    from app.models.party import Branch

# SQLite 走 autoincrement 必须 INTEGER PRIMARY KEY；用 with_variant 兼容
BigIntPK = BigInteger().with_variant(Integer(), "sqlite")


class Member(Base):
    __tablename__ = "members"
    __table_args__ = (
        UniqueConstraint("phone", "status", name="uq_members_phone_active"),
    )

    id: Mapped[int] = mapped_column(BigIntPK, primary_key=True, autoincrement=True)
    branch_id: Mapped[int] = mapped_column(BigIntPK, ForeignKey("branches.id"), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    phone: Mapped[str] = mapped_column(String(20), nullable=False)
    id_card_no: Mapped[str | None] = mapped_column(String(32), nullable=True)
    gender: Mapped[str | None] = mapped_column(String(8), nullable=True)  # male / female / other
    join_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    status: Mapped[str] = mapped_column(String(16), default="active", nullable=False)  # active / transferred / dimission
    # 流动党员：是否流入到本支部但组织关系不在本支部（true 时 flow_in_date 必填）
    is_mobile_member: Mapped[bool] = mapped_column(default=False, nullable=False, server_default="0")
    flow_in_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    # 多角色（用于人员管理库展示 + 权限自动派发）
    # SQLite 没有原生 JSON 类型，存 TEXT 字段，应用层 json.dumps/loads
    # roles: 登录用的权限角色；多选时按优先级取最高权限
    # identities: 身份标签（普通党员/党支部书记/党委委员/支委会委员等），仅展示用
    roles: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    identities: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    # 党员本人/风采照片（JSON 数组，存 dataURL；最多 5 张）
    photo_urls: Mapped[str | None] = mapped_column(String(8192), nullable=True)
    created_by: Mapped[int | None] = mapped_column(BigIntPK, ForeignKey("users.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    branch: Mapped["Branch"] = relationship("Branch")


class MemberImport(Base):
    __tablename__ = "member_imports"

    id: Mapped[int] = mapped_column(BigIntPK, primary_key=True, autoincrement=True)
    file_url: Mapped[str] = mapped_column(String(512), nullable=False)
    total_rows: Mapped[int] = mapped_column(Integer, nullable=False)
    success_rows: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    failed_rows: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    error_log: Mapped[list | None] = mapped_column(JSON, nullable=True)
    created_by: Mapped[int | None] = mapped_column(BigIntPK, ForeignKey("users.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
