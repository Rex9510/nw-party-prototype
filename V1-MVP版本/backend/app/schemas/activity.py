"""培训活动 schema。"""
from datetime import datetime
from decimal import Decimal
from typing import Literal
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


# 枚举值
OnlineOffline = Literal["online", "offline", "hybrid"]
SourceType = Literal["upper_send", "self_organize"]
# v3: 举办方式（前端展示名 = 举办单位）
OrganizeType = Literal["self_organize", "upper_send"]
StatusType = Literal["draft", "pending_community", "pending_street", "approved", "rejected"]
# v2: 集中学习方式（4 选多选）
StudyMethod = Literal["party_meeting", "theme_day", "onsite_teaching", "special_lecture"]
STUDY_METHOD_LABELS = {
    "party_meeting": "党员大会",
    "theme_day": "主题党日",
    "onsite_teaching": "现场教学",
    "special_lecture": "专题党课",
}


class ParticipantIn(BaseModel):
    """活动参加人员（含学时）。"""
    member_id: int
    study_hours: Decimal | None = Field(None, ge=0, le=999.9)
    attendance_status: str = "signed"


class ActivityBase(BaseModel):
    # v3: organizer_branch_id 不再是必填字段（前端不展示），保留做审计
    organizer_branch_id: int | None = None
    training_at: datetime
    location: str = Field(..., min_length=1, max_length=255)
    lecturer_name: str | None = None
    lecturer_bio: str | None = None
    theme: str = Field(..., min_length=1, max_length=255)
    participant_count: int = Field(0, ge=0)
    online_offline: OnlineOffline
    is_centralized: bool
    is_innovation_theory: bool
    # v3: 兼容老数据，不再必填
    source_type: SourceType | None = None
    # v3: 举办方式（前端展示名 = 举办单位）
    #   - self_organize → co_organize_branch_ids 必填（≥1）
    #   - upper_send    → upper_org 必填（≤50字）
    organize_type: OrganizeType = "self_organize"
    # v3: 自行组织时填，1+ 个支部 id
    co_organize_branch_ids: list[int] = Field(default_factory=list)
    # v2: 培训对象多选（JSON 数组）
    audience_category: list[str] = Field(default_factory=list, min_length=1, max_length=10)
    study_hours: Decimal | None = Field(None, ge=0, le=999.9)
    # v3: 上级送课的具体部门
    upper_org: str | None = Field(None, max_length=50)
    # v2: 集中学习方式（is_centralized=true 时必填，4 选多选）
    study_methods: list[StudyMethod] = Field(default_factory=list, max_length=4)

    @field_validator("audience_category")
    @classmethod
    def _aud_nonempty(cls, v: list[str]) -> list[str]:
        if not v:
            raise ValueError("培训对象至少选 1 项")
        # 去重 + 保留顺序
        seen = set()
        out = []
        for x in v:
            if not isinstance(x, str) or not x.strip():
                continue
            x = x.strip()
            if x in seen:
                continue
            seen.add(x)
            out.append(x)
        if not out:
            raise ValueError("培训对象至少选 1 项")
        return out

    @field_validator("study_methods")
    @classmethod
    def _methods_unique(cls, v: list[str]) -> list[str]:
        if not v:
            return v
        seen = set()
        out = []
        for x in v:
            if x in seen:
                continue
            seen.add(x)
            out.append(x)
        return out

    # 业务校验（v3 举办方式 / 集中学习）改到路由层手调 validate_organize_and_methods，
    # 避免 Pydantic model_validator 在 GET /activities/{id} 详情接口 model_validate 时
    # 触发老数据 422（is_centralized=True 但 study_methods=[] 的 v2 迁移前数据）。


def validate_organize_and_methods(data: dict) -> dict:
    """活动创建/更新时的业务校验（与 ActivityBase._check_organize_and_methods 等价）。
    单独提取出来是为了避免 model_validator 在 model_validate 时跑（详情/列表接口会触发老数据校验失败）。
    """
    if data.get("organize_type") == "upper_send":
        if not data.get("upper_org") or not str(data["upper_org"]).strip():
            raise ValueError("上级送课必须填写「具体部门」（≤50字）")
        data["co_organize_branch_ids"] = []
    elif data.get("organize_type") == "self_organize":
        if not data.get("co_organize_branch_ids"):
            raise ValueError("自行组织必须选择至少 1 个「协办支部」")
        data["upper_org"] = None
    if data.get("is_centralized"):
        if not data.get("study_methods"):
            raise ValueError("集中学习必须选择至少 1 项「学习方式」")
    else:
        data["study_methods"] = []
    return data


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
    # v3: 兼容老数据
    source_type: SourceType | None = None
    organize_type: OrganizeType | None = None
    co_organize_branch_ids: list[int] | None = None
    audience_category: list[str] | None = Field(None, min_length=1, max_length=10)
    study_hours: Decimal | None = None
    upper_org: str | None = Field(None, max_length=50)
    study_methods: list[StudyMethod] | None = Field(None, max_length=4)

    @field_validator("audience_category")
    @classmethod
    def _aud_nonempty(cls, v):
        return v

    @field_validator("study_methods")
    @classmethod
    def _methods_unique(cls, v):
        if not v:
            return v
        seen = set()
        out = []
        for x in v:
            if x in seen:
                continue
            seen.add(x)
            out.append(x)
        return out

    @model_validator(mode="after")
    def _check_organize_and_methods(self):
        # v3: 只在两边都给出时校验
        if self.organize_type == "upper_send" and (self.upper_org is None or not self.upper_org.strip()):
            if self.upper_org is not None:
                # 显式传了空字符串
                raise ValueError("上级送课必须填写「具体部门」（≤50字）")
        if self.organize_type == "self_organize":
            if self.co_organize_branch_ids is not None and not self.co_organize_branch_ids:
                # 显式传了空数组
                raise ValueError("自行组织必须选择至少 1 个「协办支部」")
            self.upper_org = None
        if self.is_centralized is False:
            self.study_methods = []
        return self


class ParticipantOut(ParticipantIn):
    model_config = ConfigDict(from_attributes=True)

    id: int
    member_name: str | None = None
    member_phone: str | None = None
    # 参加人员所属组织（审核页回显用）：按 org_level 取对应级别名字
    member_org_level: str | None = None
    member_branch_name: str | None = None
    member_community_name: str | None = None
    member_street_name: str | None = None


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
    organizer_branch_id: int | None = None
    community_id: int
    training_at: datetime
    location: str
    theme: str
    participant_count: int
    online_offline: str
    source_type: str | None = None
    # v3: 举办方式 + 协办支部（前端展示名 = 举办单位）
    organize_type: str = "self_organize"
    co_organize_branch_ids: list[int] = []
    audience_category: list[str] = []
    study_hours: Decimal | None = None
    status: str
    created_at: datetime
    upper_org: str | None = None
    study_methods: list[str] = []


class ActivityListResponse(BaseModel):
    total: int
    items: list[ActivityListItem]
