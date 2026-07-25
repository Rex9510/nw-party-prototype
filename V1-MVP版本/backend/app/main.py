"""FastAPI 应用入口。"""
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1 import api_router
from app.core.config import settings


@asynccontextmanager
async def lifespan(_: FastAPI):
    """启动/关闭钩子：未来加 Redis 连接池、定时任务等。"""
    yield


app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    debug=settings.DEBUG,
    lifespan=lifespan,
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 路由
app.include_router(api_router, prefix=settings.API_V1_PREFIX)


@app.get("/health", tags=["meta"])
async def health() -> dict:
    return {"status": "ok", "version": settings.APP_VERSION}
