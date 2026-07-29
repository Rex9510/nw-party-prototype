"""/api/v1/stats 统计路由（年/月/日 三维度）。"""
import re
from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from fastapi.responses import StreamingResponse
from jose import JWTError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user
from app.core.security import decode_token
from app.db.session import get_db
from app.models.user import User
from app.services.stats import (
    compute_category_stats,
    compute_member_hours_in_range,
    generate_stats_xlsx,
    resolve_time_range,
)
from pydantic import BaseModel

router = APIRouter(prefix="/stats", tags=["stats"])


class StatItem(BaseModel):
    label: str
    session_count: int
    participant_count: int


class StatsResponse(BaseModel):
    period: str           # year / month / day
    label: str            # "2026 年" / "2026-07" / "2026-07-26"
    items: list[StatItem]
    total_sessions: int
    total_participants: int


async def _resolve_user_from_request(
    request: Request, db: AsyncSession
) -> User:
    """从 Authorization 头 / query string access_token 任一来源解出当前用户。

    因为 /stats/export 是浏览器原生下载（window.open 触发），没法设 Authorization 头，
    所以额外支持 ?access_token=xxx（前端 exportUrl 用这种）。
    """
    token = None
    auth_header = request.headers.get("Authorization", "")
    if auth_header.lower().startswith("bearer "):
        token = auth_header[7:].strip()
    if not token:
        token = request.query_params.get("access_token")
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="认证失败",
            headers={"WWW-Authenticate": "Bearer"},
        )

    cred_exc = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="认证失败",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = decode_token(token)
        if payload.get("type") != "access":
            raise cred_exc
        user_id = int(payload.get("sub"))
    except (JWTError, ValueError, TypeError):
        raise cred_exc

    result = await db.execute(
        select(User).where(User.id == user_id, User.status == "active")
    )
    user = result.scalar_one_or_none()
    if not user:
        raise cred_exc
    return user


@router.get("/stats", response_model=StatsResponse)
async def get_stats(
    period: str = Query("year", description="year / month / day"),
    year: int | None = Query(None, description="查询年份（year/month 模式）"),
    month: int | None = Query(None, description="查询月份 1-12（month 模式）"),
    day: str | None = Query(None, description="查询日期 YYYY-MM-DD（day 模式）"),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> StatsResponse:
    """三维度统计接口：年/月/日。

    兼容老接口：?year=2026 等价于 ?period=year&year=2026
    """
    # 兼容老 URL：?year=2026 没带 period 时按 year 处理
    if period == "year" and year is None and day is None:
        # query 里有 year 才走；否则保持默认（今年）
        pass

    try:
        start, end, label = resolve_time_range(period, year=year, month=month, day=day)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    items = await compute_category_stats(db, user, start, end)
    return StatsResponse(
        period=period,
        label=label,
        items=items,
        total_sessions=sum(i["session_count"] for i in items),
        total_participants=sum(i["participant_count"] for i in items),
    )


# 兼容老路径 /yearly（重定向到 /stats?period=year&year=...）
@router.get("/yearly", response_model=StatsResponse)
async def get_yearly_stats_legacy(
    year: int = Query(..., description="查询年份"),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> StatsResponse:
    return await get_stats(period="year", year=year, db=db, user=user)


@router.get("/stats/export")
async def export_stats(
    request: Request,
    period: str = Query("year", description="year / month / day"),
    year: int | None = Query(None),
    month: int | None = Query(None),
    day: str | None = Query(None),
    db: AsyncSession = Depends(get_db),
) -> StreamingResponse:
    """导出统计 xlsx。支持 Authorization 头 或 ?access_token=（浏览器下载用）。

    xlsx 包含两个 sheet：
    1) 分类汇总（6 类场次+培训人数）
    2) 登录者可见范围内所有党员的时段内学时明细
    """
    user = await _resolve_user_from_request(request, db)
    try:
        start, end, label = resolve_time_range(period, year=year, month=month, day=day)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    items = await compute_category_stats(db, user, start, end)
    member_rows = await compute_member_hours_in_range(db, user, start, end)
    content = generate_stats_xlsx(label, items, member_rows=member_rows, user=user)
    # latin-1 只能编码 ASCII + 西欧字符，中文直接炸 → 只保留 [a-zA-Z0-9_-]
    safe_label = re.sub(r'[^a-zA-Z0-9_-]', '', label.replace(" ", "_").replace("-", ""))
    return StreamingResponse(
        iter([content]),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={
            "Content-Disposition": f'attachment; filename="stats_{safe_label}.xlsx"',
            "Content-Length": str(len(content)),
        },
    )


# 兼容老路径 /yearly/export
@router.get("/yearly/export")
async def export_yearly_stats_legacy(
    request: Request,
    year: int = Query(..., description="查询年份"),
    db: AsyncSession = Depends(get_db),
) -> StreamingResponse:
    return await export_stats(
        request=request, period="year", year=year, db=db,
    )
