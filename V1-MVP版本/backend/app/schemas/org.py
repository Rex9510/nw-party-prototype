"""组织架构 schema。"""
from pydantic import BaseModel, ConfigDict


class StreetOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str


class CommunityOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    street_id: int
    name: str


class BranchOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    community_id: int
    name: str


class CommunityWithBranches(CommunityOut):
    branches: list[BranchOut] = []


class StreetTree(StreetOut):
    communities: list[CommunityWithBranches] = []
