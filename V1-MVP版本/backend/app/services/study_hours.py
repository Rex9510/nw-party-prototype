"""
学时档案服务：
- 审核通过时：累加所有参加人员 (member_id, year) 的学时
- 复用：如果已存在同 (member_id, year) 记录则 +hours / +count
"""
from decimal import Decimal
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.activity import ActivityParticipant
from app.models.study import StudyHour


async def write_study_hours_for_activity(db: AsyncSession, activity_id: int) -> int:
    """
    活动审核通过时触发：
    - 遍历所有活动参加人员
    - 按 (member_id, year) 累加学时和活动数
    - 返回影响的党员数
    """
    # 1. 查出活动 + 培训年份
    from app.models.activity import Activity
    from datetime import datetime
    act_r = await db.execute(select(Activity).where(Activity.id == activity_id))
    activity = act_r.scalar_one_or_none()
    if not activity:
        return 0
    year = activity.training_at.year

    # 2. 查所有参加人员
    p_r = await db.execute(
        select(ActivityParticipant).where(ActivityParticipant.activity_id == activity_id)
    )
    participants = p_r.scalars().all()
    if not participants:
        return 0

    # 3. 按 member_id 累加（同一活动可能给同一人多条，但实际不会，因为 unique 约束）
    affected = set()
    for p in participants:
        # 查现有记录
        r = await db.execute(
            select(StudyHour).where(StudyHour.member_id == p.member_id, StudyHour.year == year)
        )
        sh = r.scalar_one_or_none()
        if sh:
            sh.total_hours = (sh.total_hours or Decimal("0")) + (p.study_hours or Decimal("0"))
            sh.activity_count = (sh.activity_count or 0) + 1
        else:
            db.add(StudyHour(
                member_id=p.member_id,
                year=year,
                total_hours=p.study_hours or Decimal("0"),
                activity_count=1,
            ))
        affected.add(p.member_id)

    await db.commit()
    return len(affected)
