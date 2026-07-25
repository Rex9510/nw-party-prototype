"""党员 + 批量导入记录。"""
from datetime import datetime, date
from sqlalchemy import String, BigInteger, Integer, DateTime, Date, ForeignKey, JSON, func, UniqueConstraint

# SQLite 走 autoincrement 必须 INTEGER PRIMARY KEY；用 with_variant 兼容
BigIntPK = BigInteger().with_variant(Integer(), "sqlite")
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base


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
    created_by: Mapped[int | None] = mapped_column(BigIntPK, ForeignKey("users.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)


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
