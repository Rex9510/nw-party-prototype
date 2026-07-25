"""培训活动 + 附件 + 参加人员。"""
from datetime import datetime
from decimal import Decimal
from sqlalchemy import (
    String, BigInteger, DateTime, ForeignKey, Integer, Boolean, Numeric,
    UniqueConstraint, Text, func,
)

# SQLite 走 autoincrement 必须 INTEGER PRIMARY KEY；用 with_variant 兼容
BigIntPK = BigInteger().with_variant(Integer(), "sqlite")
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base


class Activity(Base):
    __tablename__ = "activities"

    id: Mapped[int] = mapped_column(BigIntPK, primary_key=True, autoincrement=True)

    # 13+ 业务字段
    organizer_branch_id: Mapped[int] = mapped_column(BigIntPK, ForeignKey("branches.id"), nullable=False, index=True)
    community_id: Mapped[int] = mapped_column(BigIntPK, ForeignKey("communities.id"), nullable=False, index=True)  # 冗余
    training_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    location: Mapped[str] = mapped_column(String(255), nullable=False)
    lecturer_id: Mapped[int | None] = mapped_column(BigIntPK, ForeignKey("lecturers.id"), nullable=True)
    theme: Mapped[str] = mapped_column(String(255), nullable=False)
    participant_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    online_offline: Mapped[str] = mapped_column(String(16), nullable=False)  # online / offline / hybrid
    is_centralized: Mapped[bool] = mapped_column(Boolean, nullable=False)
    is_innovation_theory: Mapped[bool] = mapped_column(Boolean, nullable=False)
    source_type: Mapped[str] = mapped_column(String(16), nullable=False)  # upper_send / self_organize
    audience_category: Mapped[str] = mapped_column(String(16), nullable=False)
    study_hours: Mapped[Decimal] = mapped_column(Numeric(5, 1), nullable=False)

    # 状态机
    STATUS_DRAFT = "draft"
    STATUS_PENDING_COMMUNITY = "pending_community"
    STATUS_PENDING_STREET = "pending_street"
    STATUS_APPROVED = "approved"
    STATUS_REJECTED = "rejected"
    status: Mapped[str] = mapped_column(String(16), default="draft", nullable=False, index=True)
    reject_reason: Mapped[str | None] = mapped_column(Text, nullable=True)

    created_by: Mapped[int] = mapped_column(BigIntPK, ForeignKey("users.id"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)


class ActivityAttachment(Base):
    __tablename__ = "activity_attachments"

    id: Mapped[int] = mapped_column(BigIntPK, primary_key=True, autoincrement=True)
    activity_id: Mapped[int] = mapped_column(BigIntPK, ForeignKey("activities.id", ondelete="CASCADE"), nullable=False, index=True)
    kind: Mapped[str] = mapped_column(String(16), nullable=False)  # photo / signin
    file_url: Mapped[str] = mapped_column(String(512), nullable=False)
    file_size: Mapped[int | None] = mapped_column(Integer, nullable=True)
    sort: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    uploaded_by: Mapped[int | None] = mapped_column(BigIntPK, ForeignKey("users.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class ActivityParticipant(Base):
    __tablename__ = "activity_participants"
    __table_args__ = (UniqueConstraint("activity_id", "member_id", name="uq_ap_activity_member"),)

    id: Mapped[int] = mapped_column(BigIntPK, primary_key=True, autoincrement=True)
    activity_id: Mapped[int] = mapped_column(BigIntPK, ForeignKey("activities.id", ondelete="CASCADE"), nullable=False, index=True)
    member_id: Mapped[int] = mapped_column(BigIntPK, ForeignKey("members.id"), nullable=False, index=True)
    study_hours: Mapped[Decimal] = mapped_column(Numeric(5, 1), nullable=False)
    attendance_status: Mapped[str] = mapped_column(String(16), default="signed", nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
