"""党员相关 schema。"""
from datetime import date, datetime
from pydantic import BaseModel, ConfigDict, Field, field_validator
import re


class MemberBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=64)
    phone: str = Field(..., min_length=11, max_length=11)
    id_card_no: str | None = Field(None, max_length=32)
    gender: str | None = Field(None, pattern="^(male|female|other)$")
    join_date: date | None = None
    status: str = Field("active", pattern="^(active|transferred|dimission)$")

    @field_validator("phone")
    @classmethod
    def _phone(cls, v: str) -> str:
        if not re.match(r"^1[3-9]\d{9}$", v):
            raise ValueError("手机号格式错误")
        return v


class MemberCreate(MemberBase):
    branch_id: int = Field(..., description="所属支部 ID")


class MemberUpdate(BaseModel):
    name: str | None = Field(None, min_length=1, max_length=64)
    phone: str | None = Field(None, min_length=11, max_length=11)
    id_card_no: str | None = None
    gender: str | None = None
    join_date: date | None = None
    status: str | None = None
    branch_id: int | None = None


class MemberOut(MemberBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    branch_id: int
    created_at: datetime
    updated_at: datetime


class MemberListItem(MemberOut):
    """列表项：多带一个支部名。"""
    branch_name: str | None = None


class MemberListResponse(BaseModel):
    total: int
    items: list[MemberListItem]
