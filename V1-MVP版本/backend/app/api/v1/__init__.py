"""v1 API 路由聚合。"""
from fastapi import APIRouter

from app.api.v1 import activities, auth, dicts, members, orgs

api_router = APIRouter()
api_router.include_router(auth.router)
api_router.include_router(orgs.router)
api_router.include_router(members.router)
api_router.include_router(dicts.router)
api_router.include_router(activities.router)
