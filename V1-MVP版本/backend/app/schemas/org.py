"""组织架构 schema。"""
from pydantic import BaseModel, ConfigDict, Field


class StreetOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    sort: int


class StreetCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=64)


class StreetUpdate(BaseModel):
    name: str | None = Field(None, min_length=1, max_length=64)


class CommunityOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    street_id: int
    name: str
    sort: int


class CommunityCreate(BaseModel):
    street_id: int
    name: str = Field(..., min_length=1, max_length=64)


class CommunityUpdate(BaseModel):
    name: str | None = Field(None, min_length=1, max_length=64)


class BranchOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    community_id: int
    name: str
    sort: int


class BranchCreate(BaseModel):
    community_id: int
    name: str = Field(..., min_length=1, max_length=128)


class BranchUpdate(BaseModel):
    name: str | None = Field(None, min_length=1, max_length=128)


class CommunityWithBranches(CommunityOut):
    branches: list[BranchOut] = []


class StreetTree(StreetOut):
    communities: list[CommunityWithBranches] = []
