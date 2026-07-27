"""认证相关 schema。"""
from pydantic import BaseModel, ConfigDict, Field, field_validator
import re


class LoginRequest(BaseModel):
    phone: str = Field(..., description="手机号")
    password: str = Field(..., min_length=6, max_length=64, description="密码")

    @field_validator("phone")
    @classmethod
    def _validate_phone(cls, v: str) -> str:
        v = v.strip()
        if not re.match(r"^1[3-9]\d{9}$", v):
            raise ValueError("手机号格式错误")
        return v


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int = Field(..., description="access token 过期秒数")


class RefreshRequest(BaseModel):
    refresh_token: str


class PasswordChangeRequest(BaseModel):
    """修改自己的密码。"""
    old_password: str = Field(..., min_length=6, max_length=64)
    new_password: str = Field(..., min_length=6, max_length=64,
                              description="6位以上，可含英文字母/数字/符号")
    confirm_password: str = Field(..., min_length=6, max_length=64)

    @field_validator("confirm_password")
    @classmethod
    def _check_match(cls, v, info):
        if "new_password" in info.data and v != info.data["new_password"]:
            raise ValueError("两次输入的新密码不一致")
        return v


class UserInfo(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    phone: str
    name: str
    role: str
    street_id: int | None = None
    community_id: int | None = None
    branch_id: int | None = None
    # 所属组织名（前端显示用，避免每个页面都再发一次 /orgs 拉）
    street_name: str | None = None
    community_name: str | None = None
    branch_name: str | None = None
