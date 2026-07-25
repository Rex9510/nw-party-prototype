"""学时档案 schema。"""
from datetime import datetime
from decimal import Decimal
from pydantic import BaseModel, ConfigDict


class StudyHourSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    member_id: int
    year: int
    total_hours: Decimal
    activity_count: int
    updated_at: datetime

    member_name: str | None = None
    member_phone: str | None = None
    branch_name: str | None = None


class StudyHourListItem(BaseModel):
    member_id: int
    member_name: str
    member_phone: str
    branch_name: str | None = None
    year: int
    total_hours: Decimal
    activity_count: int


class StudyHourListResponse(BaseModel):
    year: int
    total_members: int
    items: list[StudyHourListItem]


class StudyDetailItem(BaseModel):
    """个人明细：每场活动的学时。"""
    activity_id: int
    theme: str
    training_at: datetime
    location: str
    study_hours: Decimal
    status: str
    attendance_status: str


class StudyDetailResponse(BaseModel):
    member_id: int
    member_name: str
    year: int
    total_hours: Decimal
    activity_count: int
    items: list[StudyDetailItem]
