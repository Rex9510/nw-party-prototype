"""
年度统计服务：
- 按 source_type + audience_category 分类
- 导出 xlsx（结构对齐 202611南湾街道党校培训情况统计表.xlsx）
"""
import io
from collections import defaultdict
from datetime import datetime
from typing import BinaryIO

from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.activity import Activity
from app.models.party import Community
from app.models.user import User
from app.services.permissions import get_member_scope_filter


# 分类定义（按 xlsx 模板）
# 第 1 类：按 "audience_category" 划分
#   - 党建组（govt_member）
#   - 人事组（其他，简化：ngo_member）
# 第 2 类：按组织者类别
#   - 党群服务中心（community_organizer 实际为社区）
#   - 其他部门
#   - 市区送课（upper_send + 培训对象机关）
#   - 送课到社区（upper_send + 培训对象社区）

CATEGORY_DEFS = [
    # (label, source_type_filter, audience_filter)
    ("党建组", "self_organize", "govt_member"),
    ("人事组", "self_organize", "ngo_member"),
    ("党群服务中心", "self_organize", "community_member"),
    ("其他部门", "self_organize", "other"),
    ("市区送课", "upper_send", "govt_member"),
    ("送课到社区", "upper_send", "community_member"),
]


async def compute_yearly_stats(db: AsyncSession, user: User, year: int) -> list[dict]:
    """按 6 类返回 (label, session_count, participant_count)。"""
    start = datetime(year, 1, 1)
    end = datetime(year + 1, 1, 1)

    stmt = select(Activity).where(
        Activity.status == "approved",
        Activity.training_at >= start,
        Activity.training_at < end,
    )

    # 角色数据范围
    scope = get_member_scope_filter(user)
    if "community_id" in scope and scope["community_id"]:
        stmt = stmt.where(Activity.community_id == scope["community_id"])
    elif "street_id" in scope and scope["street_id"]:
        stmt = stmt.join(Community, Community.id == Activity.community_id).where(
            Community.street_id == scope["street_id"]
        )

    result = await db.execute(stmt)
    activities = list(result.scalars().all())

    stats = []
    for label, source_filter, audience_filter in CATEGORY_DEFS:
        # 简化：source 匹配 + audience 匹配
        # 实际上 source 来自活动表，audience 来自活动表
        matched = [
            a for a in activities
            if a.source_type == source_filter and a.audience_category == audience_filter
        ]
        session_count = len(matched)
        participant_count = sum(a.participant_count for a in matched)
        stats.append({
            "label": label,
            "session_count": session_count,
            "participant_count": participant_count,
        })
    return stats


def generate_yearly_xlsx(year: int, stats: list[dict]) -> bytes:
    """生成统计 xlsx（结构对齐原 xlsx）。"""
    wb = Workbook()
    ws = wb.active
    ws.title = f"{year}街道（总数）"

    # 标题
    title = ws.cell(row=1, column=1, value=f"{year}年南湾街道党校培训统计表（总）")
    title.font = Font(bold=True, size=14)
    title.alignment = Alignment(horizontal="center")
    ws.merge_cells("A1:D1")

    # 表头
    headers = ["序号", "类别", "场次数", "培训人数", "备注"]
    for col, h in enumerate(headers, 1):
        c = ws.cell(row=2, column=col, value=h)
        c.font = Font(bold=True)
        c.fill = PatternFill(start_color="FFE4E1", end_color="FFE4E1", fill_type="solid")
        c.alignment = Alignment(horizontal="center")

    # 数据
    border = Border(
        left=Side(style="thin"), right=Side(style="thin"),
        top=Side(style="thin"), bottom=Side(style="thin"),
    )
    for i, s in enumerate(stats, start=1):
        row = i + 2
        ws.cell(row=row, column=1, value=i)
        ws.cell(row=row, column=2, value=s["label"])
        ws.cell(row=row, column=3, value=s["session_count"])
        ws.cell(row=row, column=4, value=s["participant_count"])
        ws.cell(row=row, column=5, value="")
        for col in range(1, 6):
            ws.cell(row=row, column=col).border = border

    # 列宽
    for col, w in zip("ABCDE", [8, 24, 12, 12, 16]):
        ws.column_dimensions[col].width = w

    # 备注
    note_row = len(stats) + 4
    note = ws.cell(row=note_row, column=1, value="备注：本表数据为系统自动汇总；详细明细见活动库。")
    note.font = Font(italic=True, color="888888")

    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()
