"""组织架构：街道 / 社区 / 支部。"""
from datetime import datetime
from typing import TYPE_CHECKING
from sqlalchemy import String, BigInteger, Integer, DateTime, ForeignKey, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base

if TYPE_CHECKING:
    pass

# SQLite 走 autoincrement 必须 INTEGER PRIMARY KEY；用 with_variant 兼容
BigIntPK = BigInteger().with_variant(Integer(), "sqlite")


class Street(Base):
    __tablename__ = "streets"

    id: Mapped[int] = mapped_column(BigIntPK, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(64), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    communities: Mapped[list["Community"]] = relationship(
        "Community", back_populates="street", cascade="all, delete-orphan"
    )


class Community(Base):
    __tablename__ = "communities"

    id: Mapped[int] = mapped_column(BigIntPK, primary_key=True, autoincrement=True)
    street_id: Mapped[int] = mapped_column(BigIntPK, ForeignKey("streets.id"), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(64), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    street: Mapped["Street"] = relationship("Street", back_populates="communities")
    branches: Mapped[list["Branch"]] = relationship(
        "Branch", back_populates="community", cascade="all, delete-orphan"
    )


class Branch(Base):
    __tablename__ = "branches"

    id: Mapped[int] = mapped_column(BigIntPK, primary_key=True, autoincrement=True)
    community_id: Mapped[int] = mapped_column(BigIntPK, ForeignKey("communities.id"), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    community: Mapped["Community"] = relationship("Community", back_populates="branches")
