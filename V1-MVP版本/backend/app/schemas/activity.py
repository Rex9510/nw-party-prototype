"""培训活动 schema。"""
from datetime import datetime
from decimal import Decimal
from typing import Literal
from pydantic import BaseModel, ConfigDict, Field, field_validator


# 枚举值
OnlineOffline = Literal["online", "offline", "hybrid"]
SourceType = Literal["upper_send", "self_organize"]
StatusType = Literal["draft", "pending_community", "pending_street", "approved", "rejected"]


class ParticipantIn(BaseModel):
    """活动参加人员（含学时）。"""
    member_id: int
    study_hours: Decimal | None = Field(None, ge=0, le=999.9)
    attendance_status: str = "signed"


class ActivityBase(BaseModel):
    organizer_branch_id: int
    training_at: datetime
    location: str = Field(..., min_length=1, max_length=255)
    lecturer_name: str | None = None
    lecturer_bio: str | None = None
    theme: str = Field(..., min_length=1, max_length=255)
    participant_count: int = Field(0, ge=0)
    online_offline: OnlineOffline
    is_centralized: bool
    is_innovation_theory: bool
    source_type: SourceType
    audience_category: str = Field(..., min_length=1, max_length=32)
    study_hours: Decimal | None = Field(None, ge=0, le=999.9)


class ActivityCreate(ActivityBase):
    participants: list[ParticipantIn] = []
    photo_count: int = 0  # 仅用于校验，至少 1


class ActivityUpdate(BaseModel):
    training_at: datetime | None = None
    location: str | None = None
    lecturer_name: str | None = None
    lecturer_bio: str | None = None
    theme: str | None = None
    participant_count: int | None = None
    online_offline: OnlineOffline | None = None
    is_centralized: bool | None = None
    is_innovation_theory: bool | None = None
    source_type: SourceType | None = None
    audience_category: str | None = None
    study_hours: Decimal | None = None
    participants: list[ParticipantIn] | None = None


class ParticipantOut(ParticipantIn):
    model_config = ConfigDict(from_attributes=True)

    id: int
    member_name: str | None = None
    member_phone: str | None = None


class AttachmentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    kind: str  # photo / signin
    file_url: str
    file_size: int | None = None
    sort: int = 0


class ActivityOut(ActivityBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    community_id: int
    status: StatusType = "draft"
    reject_reason: str | None = None
    created_by: int
    created_at: datetime
    updated_at: datetime

    participants: list[ParticipantOut] = []
    attachments: list[AttachmentOut] = []


class ActivityListItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    organizer_branch_id: int
    community_id: int
    training_at: datetime
    location: str
    theme: str
    participant_count: int
    online_offline: str
    source_type: str
    audience_category: str
    study_hours: Decimal | None = None
    status: str
    created_at: datetime


class ActivityListResponse(BaseModel):
    total: int
    items: list[ActivityListItem]
