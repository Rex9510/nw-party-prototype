"""党员相关 schema。"""
import json
from datetime import date, datetime
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator
import re


def _to_json_str(v):
    """入参：list/None → JSON 字符串。"""
    if v is None:
        return None
    return json.dumps(v, ensure_ascii=False)


def _to_list(v):
    """出参：JSON 字符串/list/None → list。"""
    if v is None or v == "":
        return []
    if isinstance(v, list):
        return v
    if isinstance(v, str):
        try:
            r = json.loads(v)
            return r if isinstance(r, list) else []
        except Exception:
            return []
    return []


class MemberBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=64)
    phone: str = Field(..., min_length=11, max_length=11)
    id_card_no: str | None = Field(None, max_length=32)
    gender: str | None = Field(None, pattern="^(male|female|other)$")
    join_date: date | None = None
    status: str = Field("active", pattern="^(active|transferred|dimission)$")
    # 流动党员 + 流入日期
    is_mobile_member: bool = Field(default=False, description="是否流动党员（true 时 flow_in_date 必填）")
    flow_in_date: date | None = Field(default=None, description="流入日期（仅 is_mobile_member=true 时使用）")

    @model_validator(mode="after")
    def _check_flow_in_date(self):
        """若 is_mobile_member=true，flow_in_date 必填。

        用 model_validator 而不是 field_validator：pydantic v2 的字段顺序不保证，
        写在 model 上能拿到所有已解析的字段。
        """
        if self.is_mobile_member and self.flow_in_date is None:
            raise ValueError("流动党员必须填写流入日期")
        # 反过来：is_mobile_member=false 时清掉 flow_in_date（避免脏数据）
        if not self.is_mobile_member and self.flow_in_date is not None:
            object.__setattr__(self, "flow_in_date", None)
        return self

    @field_validator("phone")
    @classmethod
    def _phone(cls, v: str) -> str:
        if not re.match(r"^1[3-9]\d{9}$", v):
            raise ValueError("手机号格式错误")
        return v


class MemberCreate(MemberBase):
    branch_id: int = Field(..., description="所属支部 ID")
    roles: list[str] | None = Field(
        default=None,
        description="登录权限角色（system_admin/street_lead/community_organizer/branch_secretary/party_member），多选时按权限高低取最高",
    )
    identities: list[str] | None = Field(
        default=None,
        description="身份标签（普通党员/党支部书记/党委副书记/党委委员/支委会委员），仅展示",
    )
    photo_urls: list[str] | None = Field(
        default=None,
        max_length=1,
        description="党员本人/风采照片 dataURL 列表，只允许 1 张（主图）",
    )

    @field_validator("roles", "identities", "photo_urls", mode="before")
    @classmethod
    def _json_in(cls, v):
        return v  # 保持 list，create 接口里再 dump


class MemberUpdate(BaseModel):
    name: str | None = Field(None, min_length=1, max_length=64)
    phone: str | None = Field(None, min_length=11, max_length=11)
    id_card_no: str | None = None
    gender: str | None = None
    join_date: date | None = None
    status: str | None = None
    branch_id: int | None = None
    roles: list[str] | None = None
    identities: list[str] | None = None
    photo_urls: list[str] | None = Field(
        default=None,
        max_length=1,
        description="传 [] 表示清空；不传则不改；最多 1 张",
    )
    is_mobile_member: bool | None = None
    flow_in_date: date | None = None


class MemberOut(MemberBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    branch_id: int
    # 兼容：数据库里存的是 JSON 字符串，应用层转 list
    roles: list[str] | None = None
    identities: list[str] | None = None
    photo_urls: list[str] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime

    @field_validator("roles", "identities", "photo_urls", mode="before")
    @classmethod
    def _json_out(cls, v):
        return _to_list(v)


class MemberListItem(MemberOut):
    """列表项：多带一个支部名。"""
    branch_name: str | None = None


class MemberListResponse(BaseModel):
    total: int
    items: list[MemberListItem]
