"""
统计服务（年/月/日 三维度）：
- 按 source_type + audience_category 分类
- 支持 period=year/month/day 三种粒度
- 导出 xlsx（结构对齐 202611南湾街道党校培训情况统计表.xlsx）
- xlsx 第二个 sheet：登录者可见范围内所有党员的学时明细
"""
import io
from calendar import monthrange
from collections import defaultdict
from datetime import datetime, timedelta
from typing import BinaryIO

from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.activity import Activity
from app.models.member import Member
from app.models.party import Branch, Community, Street
from app.models.study import StudyHour
from app.models.user import User
from app.services.permissions import get_member_scope_filter


# ---------------------------------------------------------------------------
# 工具函数：根据 period/year/month/date 算出 [start, end) 时间范围 + label
# ---------------------------------------------------------------------------
def resolve_time_range(
    period: str,
    year: int | None = None,
    month: int | None = None,
    day: str | None = None,
) -> tuple[datetime, datetime, str]:
    """
    返回 (start_datetime, end_datetime, label)
    - year 模式: 整年 1/1 - 次年 1/1
    - month 模式: 当月 1 号 - 下月 1 号
    - day 模式: 当天 00:00 - 次日 00:00
    """
    period = (period or "year").lower()
    if period == "year":
        y = year or datetime.now().year
        return datetime(y, 1, 1), datetime(y + 1, 1, 1), f"{y} 年"
    if period == "month":
        y = year or datetime.now().year
        m = month or 1
        if m < 1 or m > 12:
            raise ValueError("month 必须在 1-12")
        next_y, next_m = (y + 1, 1) if m == 12 else (y, m + 1)
        return datetime(y, m, 1), datetime(next_y, next_m, 1), f"{y}-{m:02d}"
    if period == "day":
        d = day or datetime.now().strftime("%Y-%m-%d")
        try:
            dt = datetime.strptime(d, "%Y-%m-%d")
        except ValueError:
            raise ValueError("day 格式必须是 YYYY-MM-DD")
        return dt, dt + timedelta(days=1), dt.strftime("%Y-%m-%d")
    raise ValueError(f"不支持的 period: {period}")


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


async def compute_category_stats(
    db: AsyncSession,
    user: User,
    start: datetime,
    end: datetime,
) -> list[dict]:
    """按 6 类返回 (label, session_count, participant_count)。

    时间范围由调用方传入（year/month/day 通用）。
    """
    stmt = select(Activity).where(
        Activity.status == "approved",
        Activity.training_at >= start,
        Activity.training_at < end,
    )

    # 角色数据范围（按用户所属逐级缩窄）
    scope = get_member_scope_filter(user)
    if "branch_id" in scope and scope["branch_id"]:
        # 支部书记 / 普通党员：只看本支部
        stmt = stmt.where(Activity.organizer_branch_id == scope["branch_id"])
    elif "community_id" in scope and scope["community_id"]:
        # 社区组织委员：看本社区
        stmt = stmt.where(Activity.community_id == scope["community_id"])
    elif "street_id" in scope and scope["street_id"]:
        # 街道负责人 / 系统管理员：看本街道
        stmt = stmt.join(Community, Community.id == Activity.community_id).where(
            Community.street_id == scope["street_id"]
        )

    result = await db.execute(stmt)
    activities = list(result.scalars().all())

    stats = []
    for label, source_filter, audience_filter in CATEGORY_DEFS:
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


async def compute_member_hours_in_range(
    db: AsyncSession,
    user: User,
    start: datetime,
    end: datetime,
) -> list[dict]:
    """
    返回登录者可见范围内所有党员在 [start, end) 时间段内的学时明细。
    实现：直接按 ActivityParticipant 聚合（不依赖 study_hours 表，避免日维度被年表锁死）。
    [
      {street_name, community_name, branch_name, name, phone, identity,
       activity_count, total_hours},
      ...
    ]
    排序：街道 → 社区 → 支部 → 党员姓名。

    0 学时的党员也列出（"未参训"也是数据）。
    """
    from sqlalchemy import func
    # 1. 算可见的 community_id / branch_id 范围
    scope = get_member_scope_filter(user)

    member_q = select(Member).where(Member.status == "active")

    if "branch_id" in scope and scope["branch_id"]:
        member_q = member_q.where(Member.branch_id == scope["branch_id"])
    elif "community_id" in scope and scope["community_id"]:
        member_q = member_q.where(Member.branch_id.in_(
            select(Branch.id).where(Branch.community_id == scope["community_id"])
        ))
    elif "street_id" in scope and scope["street_id"]:
        member_q = member_q.where(Member.branch_id.in_(
            select(Branch.id).join(
                Community, Community.id == Branch.community_id
            ).where(Community.street_id == scope["street_id"])
        ))

    member_q = member_q.order_by(Member.branch_id, Member.name)
    members = list((await db.execute(member_q)).scalars().all())
    if not members:
        return []

    member_ids = [m.id for m in members]
    branch_ids = list({m.branch_id for m in members})

    # 2. 一次性查 branches + communities + streets
    branch_map = {
        b.id: b for b in (await db.execute(
            select(Branch).where(Branch.id.in_(branch_ids))
        )).scalars()
    }
    community_ids = list({b.community_id for b in branch_map.values()})
    community_map = {
        c.id: c for c in (await db.execute(
            select(Community).where(Community.id.in_(community_ids))
        )).scalars()
    }
    street_ids = list({c.street_id for c in community_map.values()})
    street_map = {
        s.id: s for s in (await db.execute(
            select(Street).where(Street.id.in_(street_ids))
        )).scalars()
    }

    # 3. 按活动表直接聚合（时间段 + member）
    # 学时 = 同一 member 在 [start, end) 内参加的所有活动 participant 的 study_hours 之和
    # 活动数 = 同一 member 参加的不同 activity 数量
    stmt = (
        select(
            ActivityParticipant.member_id,
            func.coalesce(func.sum(ActivityParticipant.study_hours), 0).label("total_hours"),
            func.count(func.distinct(ActivityParticipant.activity_id)).label("activity_count"),
        )
        .join(Activity, Activity.id == ActivityParticipant.activity_id)
        .where(
            ActivityParticipant.member_id.in_(member_ids),
            Activity.status == "approved",
            Activity.training_at >= start,
            Activity.training_at < end,
        )
        .group_by(ActivityParticipant.member_id)
    )
    sh_rows = (await db.execute(stmt)).all()
    sh_map = {row.member_id: row for row in sh_rows}

    # 4. 拼接结果
    import json
    out = []
    for m in members:
        b = branch_map.get(m.branch_id)
        c = community_map.get(b.community_id) if b else None
        s = street_map.get(c.street_id) if c else None
        sh = sh_map.get(m.id)
        # identities 字段是 JSON 字符串（['普通党员','党支部书记']），解析后取第一个
        identity_display = ""
        raw_identities = m.identities
        if raw_identities:
            try:
                ids = json.loads(raw_identities) if isinstance(raw_identities, str) else raw_identities
                if isinstance(ids, list) and ids:
                    identity_display = str(ids[0])
            except (json.JSONDecodeError, TypeError):
                identity_display = str(raw_identities)
        out.append({
            "street_name": s.name if s else "",
            "community_name": c.name if c else "",
            "branch_name": b.name if b else "",
            "name": m.name,
            "phone": m.phone or "",
            "identity": identity_display,
            "activity_count": int(sh.activity_count) if sh else 0,
            "total_hours": float(sh.total_hours) if sh else 0.0,
        })

    # 排序：街道 → 社区 → 支部 → 姓名
    out.sort(key=lambda r: (r["street_name"], r["community_name"], r["branch_name"], r["name"]))
    return out


def _write_member_hours_sheet(wb: Workbook, period_label: str, rows: list[dict], user: User) -> None:
    """xlsx 第二个 sheet：登录者可见范围内所有党员的学时明细。"""
    ws = wb.create_sheet(title=f"{period_label}明细")

    # 标题
    title = ws.cell(row=1, column=1, value=f"{period_label}党员学时明细（{user.name}可见范围）")
    title.font = Font(bold=True, size=14)
    title.alignment = Alignment(horizontal="center")
    ws.merge_cells("A1:I1")

    # 表头
    headers = ["序号", "街道", "社区", "支部", "党员姓名", "手机号", "身份", "活动数", "总学时"]
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
    total_hours_sum = 0.0
    total_activities = 0
    for i, r in enumerate(rows, start=1):
        row = i + 2
        ws.cell(row=row, column=1, value=i)
        ws.cell(row=row, column=2, value=r["street_name"])
        ws.cell(row=row, column=3, value=r["community_name"])
        ws.cell(row=row, column=4, value=r["branch_name"])
        ws.cell(row=row, column=5, value=r["name"])
        ws.cell(row=row, column=6, value=r["phone"])
        ws.cell(row=row, column=7, value=r["identity"])
        ws.cell(row=row, column=8, value=r["activity_count"])
        ws.cell(row=row, column=9, value=r["total_hours"])
        for col in range(1, 10):
            ws.cell(row=row, column=col).border = border
        total_hours_sum += r["total_hours"]
        total_activities += r["activity_count"]

    # 列宽
    for col, w in zip("ABCDEFGHI", [6, 12, 12, 22, 12, 14, 16, 10, 10]):
        ws.column_dimensions[col].width = w

    # 汇总行
    sum_row = len(rows) + 4
    summary_cells = [
        (1, f"合计（{len(rows)} 人）"),
        (8, total_activities),
        (9, round(total_hours_sum, 1)),
    ]
    for col, val in summary_cells:
        c = ws.cell(row=sum_row, column=col, value=val)
        c.font = Font(bold=True, color="B22222")
        c.fill = PatternFill(start_color="FFF8E1", end_color="FFF8E1", fill_type="solid")
        c.border = border

    # 备注
    note_row = sum_row + 2
    note = ws.cell(
        row=note_row, column=1,
        value="备注：本表数据按登录账号角色自动过滤范围（系统管理员/街道负责人看本街道所有党员；社区组织委员看本社区；支部书记看本支部）。0 学时表示本年度未参加任何已审核活动。",
    )
    note.font = Font(italic=True, color="888888", size=10)
    note.alignment = Alignment(wrap_text=True)
    ws.merge_cells(start_row=note_row, start_column=1, end_row=note_row, end_column=9)
    ws.row_dimensions[note_row].height = 40


def generate_stats_xlsx(
    period_label: str,
    stats: list[dict],
    member_rows: list[dict] | None = None,
    user: User | None = None,
) -> bytes:
    """生成统计 xlsx。第一个 sheet 分类汇总，第二个 sheet（如果有）党员明细。"""
    wb = Workbook()
    ws = wb.active
    ws.title = f"{period_label}汇总"

    # 标题
    title = ws.cell(row=1, column=1, value=f"{period_label}南湾街道党校培训统计表（总）")
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

    # 第 2 个 sheet：登录者可见范围内所有党员的学时明细
    if member_rows is not None and user is not None:
        _write_member_hours_sheet(wb, period_label, member_rows, user)

    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()
