"""组织架构：街道 / 社区 / 支部。"""
from datetime import datetime
from sqlalchemy import String, BigInteger, DateTime, ForeignKey, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base


class Street(Base):
    __tablename__ = "streets"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(64), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class Community(Base):
    __tablename__ = "communities"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    street_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("streets.id"), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(64), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class Branch(Base):
    __tablename__ = "branches"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    community_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("communities.id"), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
