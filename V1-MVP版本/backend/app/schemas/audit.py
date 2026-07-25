"""审核相关 schema。"""
from datetime import datetime
from pydantic import BaseModel, ConfigDict, Field


class AuditItem(BaseModel):
    """待办 / 历史列表项。"""
    model_config = ConfigDict(from_attributes=True)

    id: int  # activity_id
    activity_id: int
    theme: str
    location: str
    training_at: datetime
    participant_count: int
    study_hours: float
    organizer_branch_id: int
    organizer_branch_name: str | None = None
    community_id: int
    community_name: str | None = None
    submitter_id: int
    submitter_name: str | None = None
    current_node: str  # community_review / street_review
    status: str
    created_at: datetime


class AuditListResponse(BaseModel):
    total: int
    items: list[AuditItem]


class AuditActionRequest(BaseModel):
    """审核操作：同意 / 驳回。"""
    comment: str | None = Field(None, max_length=2000, description="审核意见（驳回时必填）")


class AuditLogOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    activity_id: int
    node: str
    operator_id: int
    operator_name: str | None = None
    action: str
    comment: str | None
    created_at: datetime
