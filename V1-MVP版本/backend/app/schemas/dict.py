"""字典相关 schema。"""
from pydantic import BaseModel, ConfigDict, Field


class LecturerOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    intro: str | None = None
    status: str = "active"


class LecturerCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=64)
    intro: str | None = Field(None, max_length=2000)


class LecturerUpdate(BaseModel):
    name: str | None = Field(None, min_length=1, max_length=64)
    intro: str | None = None
    status: str | None = None


class DictItemOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    code: str
    name: str
    sort: int = 0


class DictItemCreate(BaseModel):
    code: str = Field(..., min_length=1, max_length=32)
    name: str = Field(..., min_length=1, max_length=64)
    sort: int = 0


class DictItemUpdate(BaseModel):
    name: str | None = Field(None, min_length=1, max_length=64)
    sort: int | None = None
