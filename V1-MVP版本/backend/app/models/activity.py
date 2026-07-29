"""培训活动 + 附件 + 参加人员。"""
from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING
from sqlalchemy import (
    String, BigInteger, Integer, DateTime, ForeignKey, Boolean, Numeric,
    UniqueConstraint, Text, JSON, func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base

if TYPE_CHECKING:
    pass

# SQLite 走 autoincrement 必须 INTEGER PRIMARY KEY；用 with_variant 兼容
BigIntPK = BigInteger().with_variant(Integer(), "sqlite")


class Activity(Base):
    __tablename__ = "activities"

    id: Mapped[int] = mapped_column(BigIntPK, primary_key=True, autoincrement=True)

    # 13+ 业务字段
    # v3: organizer_branch_id 不再必填（前端不再填），保留字段 + FK + 索引做审计
    organizer_branch_id: Mapped[int | None] = mapped_column(BigIntPK, ForeignKey("branches.id"), nullable=True, index=True)
    community_id: Mapped[int] = mapped_column(BigIntPK, ForeignKey("communities.id"), nullable=False, index=True)  # 冗余
    training_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    location: Mapped[str] = mapped_column(String(255), nullable=False)
    lecturer_name: Mapped[str | None] = mapped_column(String(64), nullable=True)
    lecturer_bio: Mapped[str | None] = mapped_column(Text, nullable=True)
    theme: Mapped[str] = mapped_column(String(255), nullable=False)
    participant_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    online_offline: Mapped[str] = mapped_column(String(16), nullable=False)  # online / offline / hybrid
    is_centralized: Mapped[bool] = mapped_column(Boolean, nullable=False)
    is_innovation_theory: Mapped[bool] = mapped_column(Boolean, nullable=False)
    # v3: source_type 不再必填（被 organize_type 替代），保留做兼容
    source_type: Mapped[str | None] = mapped_column(String(16), nullable=True)
    # v3: 举办方式单选 enum（前端展示名 = 举办单位）
    #   - self_organize: 自行组织，对应 co_organize_branch_ids 必填（≥1）
    #   - upper_send:    上级送课，对应 upper_org 必填（≤50字）
    organize_type: Mapped[str] = mapped_column(String(16), default="self_organize", nullable=False)
    # v3: organize_type=self_organize 时必填，1+ 支部 id
    co_organize_branch_ids: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    # v2: 培训对象从单选改为多选（JSON 数组；老数据迁移：'foo' -> ['foo']）
    audience_category: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    study_hours: Mapped[Decimal | None] = mapped_column(Numeric(5, 1), nullable=True)
    # v3: organize_type=upper_send 时必填，具体送课部门（≤50字）
    upper_org: Mapped[str | None] = mapped_column(String(50), nullable=True)
    # v2: is_centralized=true 时必填，集中学习方式（JSON 数组）
    #   合法值：party_meeting / theme_day / onsite_teaching / special_lecture
    study_methods: Mapped[list] = mapped_column(JSON, nullable=False, default=list)

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

    participants: Mapped[list["ActivityParticipant"]] = relationship(
        "ActivityParticipant", back_populates="activity", cascade="all, delete-orphan"
    )
    attachments: Mapped[list["ActivityAttachment"]] = relationship(
        "ActivityAttachment", back_populates="activity", cascade="all, delete-orphan"
    )


class ActivityAttachment(Base):
    __tablename__ = "activity_attachments"

    id: Mapped[int] = mapped_column(BigIntPK, primary_key=True, autoincrement=True)
    activity_id: Mapped[int] = mapped_column(BigIntPK, ForeignKey("activities.id", ondelete="CASCADE"), nullable=False, index=True)
    kind: Mapped[str] = mapped_column(String(16), nullable=False)  # photo / signin
    file_url: Mapped[str] = mapped_column(String(8192), nullable=False)  # 实际不限长（SQLite VARCHAR）
    file_size: Mapped[int | None] = mapped_column(Integer, nullable=True)
    # 缩略图：base64 dataURL（图片专用，200x200 JPEG 几十 KB）。
    # 公开页接口返 thumbnail_url 降响应体，全图按需查 GET /public/attachments/{id}/full
    thumbnail_url: Mapped[str | None] = mapped_column(String(8192), nullable=True)
    sort: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    uploaded_by: Mapped[int | None] = mapped_column(BigIntPK, ForeignKey("users.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    activity: Mapped["Activity"] = relationship("Activity", back_populates="attachments")


class ActivityParticipant(Base):
    __tablename__ = "activity_participants"
    __table_args__ = (UniqueConstraint("activity_id", "member_id", name="uq_ap_activity_member"),)

    id: Mapped[int] = mapped_column(BigIntPK, primary_key=True, autoincrement=True)
    activity_id: Mapped[int] = mapped_column(BigIntPK, ForeignKey("activities.id", ondelete="CASCADE"), nullable=False, index=True)
    member_id: Mapped[int] = mapped_column(BigIntPK, ForeignKey("members.id"), nullable=False, index=True)
    study_hours: Mapped[Decimal] = mapped_column(Numeric(5, 1), nullable=False)
    attendance_status: Mapped[str] = mapped_column(String(16), default="signed", nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    activity: Mapped["Activity"] = relationship("Activity", back_populates="participants")
