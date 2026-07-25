"""v1 API 路由聚合。"""
from fastapi import APIRouter

from app.api.v1 import auth, orgs

api_router = APIRouter()
api_router.include_router(auth.router)
api_router.include_router(orgs.router)
