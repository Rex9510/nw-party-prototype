"""学时档案：按党员 + 年度汇总。"""
from datetime import datetime
from decimal import Decimal
from sqlalchemy import String, BigInteger, Integer, DateTime, ForeignKey, Numeric, UniqueConstraint, func

# SQLite 走 autoincrement 必须 INTEGER PRIMARY KEY；用 with_variant 兼容
BigIntPK = BigInteger().with_variant(Integer(), "sqlite")
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base


class StudyHour(Base):
    __tablename__ = "study_hours"
    __table_args__ = (UniqueConstraint("member_id", "year", name="uq_sh_member_year"),)

    id: Mapped[int] = mapped_column(BigIntPK, primary_key=True, autoincrement=True)
    member_id: Mapped[int] = mapped_column(BigIntPK, ForeignKey("members.id"), nullable=False, index=True)
    year: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    total_hours: Mapped[Decimal] = mapped_column(Numeric(7, 1), default=0, nullable=False)
    activity_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
