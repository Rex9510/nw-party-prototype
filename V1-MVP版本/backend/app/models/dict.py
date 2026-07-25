"""字典：讲师、培训对象类别、培训来源。"""
from datetime import datetime
from sqlalchemy import String, BigInteger, Integer, DateTime, func, UniqueConstraint

# SQLite 走 autoincrement 必须 INTEGER PRIMARY KEY；用 with_variant 兼容
BigIntPK = BigInteger().with_variant(Integer(), "sqlite")
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base


class Lecturer(Base):
    __tablename__ = "lecturers"

    id: Mapped[int] = mapped_column(BigIntPK, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(64), nullable=False)
    intro: Mapped[str | None] = mapped_column(String(2000), nullable=True)
    status: Mapped[str] = mapped_column(String(16), default="active", nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class TrainingCategory(Base):
    __tablename__ = "training_categories"
    __table_args__ = (UniqueConstraint("code", name="uq_tc_code"),)

    id: Mapped[int] = mapped_column(BigIntPK, primary_key=True, autoincrement=True)
    code: Mapped[str] = mapped_column(String(32), nullable=False)
    name: Mapped[str] = mapped_column(String(64), nullable=False)
    sort: Mapped[int] = mapped_column(Integer, default=0, nullable=False)


class TrainingSource(Base):
    __tablename__ = "training_sources"
    __table_args__ = (UniqueConstraint("code", name="uq_ts_code"),)

    id: Mapped[int] = mapped_column(BigIntPK, primary_key=True, autoincrement=True)
    code: Mapped[str] = mapped_column(String(32), nullable=False)
    name: Mapped[str] = mapped_column(String(64), nullable=False)
    sort: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
