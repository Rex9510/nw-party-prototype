"""审核流与审核日志。"""
from datetime import datetime
from sqlalchemy import String, BigInteger, DateTime, ForeignKey, Text, func, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base


class AuditFlow(Base):
    __tablename__ = "audit_flows"
    __table_args__ = (UniqueConstraint("activity_id", name="uq_af_activity"),)

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    activity_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("activities.id", ondelete="CASCADE"), nullable=False)
    NODE_COMMUNITY = "community_review"
    NODE_STREET = "street_review"
    NODE_DONE = "done"
    current_node: Mapped[str] = mapped_column(String(32), nullable=False)
    STATUS_IN_PROGRESS = "in_progress"
    STATUS_APPROVED = "approved"
    STATUS_REJECTED = "rejected"
    status: Mapped[str] = mapped_column(String(16), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    activity_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("activities.id", ondelete="CASCADE"), nullable=False, index=True)
    node: Mapped[str] = mapped_column(String(32), nullable=False)
    operator_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.id"), nullable=False, index=True)
    ACTION_SUBMIT = "submit"
    ACTION_APPROVE = "approve"
    ACTION_REJECT = "reject"
    action: Mapped[str] = mapped_column(String(16), nullable=False)
    comment: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
