"""/api/v1/stats 统计路由。"""
from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.services.stats import compute_yearly_stats, generate_yearly_xlsx
from pydantic import BaseModel

router = APIRouter(prefix="/stats", tags=["stats"])


class StatItem(BaseModel):
    label: str
    session_count: int
    participant_count: int


class YearlyStatsResponse(BaseModel):
    year: int
    items: list[StatItem]
    total_sessions: int
    total_participants: int


@router.get("/yearly", response_model=YearlyStatsResponse)
async def get_yearly_stats(
    year: int = Query(..., description="查询年份"),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> YearlyStatsResponse:
    items = await compute_yearly_stats(db, user, year)
    return YearlyStatsResponse(
        year=year,
        items=items,
        total_sessions=sum(i["session_count"] for i in items),
        total_participants=sum(i["participant_count"] for i in items),
    )


@router.get("/yearly/export")
async def export_yearly_stats(
    year: int = Query(..., description="查询年份"),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> StreamingResponse:
    """导出年度统计 xlsx。"""
    items = await compute_yearly_stats(db, user, year)
    content = generate_yearly_xlsx(year, items)
    return StreamingResponse(
        iter([content]),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={
            "Content-Disposition": f'attachment; filename="yearly_stats_{year}.xlsx"',
            "Content-Length": str(len(content)),
        },
    )
