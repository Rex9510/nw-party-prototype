"""认证相关 schema。"""
from pydantic import BaseModel, Field, field_validator
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


class UserInfo(BaseModel):
    id: int
    phone: str
    name: str
    role: str
    street_id: int | None = None
    community_id: int | None = None
    branch_id: int | None = None

    class Config:
        from_attributes = True
