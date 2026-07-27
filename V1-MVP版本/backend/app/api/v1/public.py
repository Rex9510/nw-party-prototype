"""/api/v1/public 公开接口（不需要 token，用于扫码访问的党员名片）。"""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db.session import get_db
from app.models.activity import (
    Activity,
    ActivityAttachment,
    ActivityParticipant,
)
from app.models.party import Branch, Community, Street
from app.models.member import Member

router = APIRouter(prefix="/public", tags=["public"])


# ====== Schemas ======
class OrgLite(BaseModel):
    id: int
    name: str

    class Config:
        from_attributes = True


class MemberCard(BaseModel):
    """党员名片（公开版）。"""
    id: int
    name: str
    phone: str | None = None
    id_card_no: str | None = None
    gender: str | None = None
    join_date: str | None = None
    status: str
    roles: list[str] = []
    identities: list[str] = []
    photo_urls: list[str] = []
    # 组织归属
    branch: OrgLite | None = None
    community: OrgLite | None = None
    street: OrgLite | None = None


class TrainingItem(BaseModel):
    """一条培训记录。"""
    activity_id: int
    theme: str
    training_at: str
    location: str
    lecturer_name: str | None = None
    lecturer_bio: str | None = None
    study_hours: float
    source_type: str
    attendance_status: str
    photos: list[str] = []          # 现场照片（data URL / http URL）
    attachments: list[str] = []     # 其他附件（Word/Excel/PDF）


class PublicMemberOut(BaseModel):
    member: MemberCard
    trainings: list[TrainingItem]
    stats: dict  # {total_hours, total_sessions, year_hours}


# ====== Endpoints ======
@router.get("/members/{member_id}", response_model=PublicMemberOut)
async def get_member_card(
    member_id: int,
    db: AsyncSession = Depends(get_db),
) -> PublicMemberOut:
    """扫码访问党员公开名片（不需要 token）。"""
    r = await db.execute(select(Member).where(Member.id == member_id))
    m = r.scalar_one_or_none()
    if not m:
        raise HTTPException(status_code=404, detail="党员不存在")

    # 加载组织归属
    branch: Branch | None = None
    community: Community | None = None
    street: Street | None = None
    if m.branch_id:
        br = await db.execute(select(Branch).where(Branch.id == m.branch_id))
        branch = br.scalar_one_or_none()
        if branch:
            cr = await db.execute(
                select(Community).where(Community.id == branch.community_id)
            )
            community = cr.scalar_one_or_none()
            if community:
                sr = await db.execute(
                    select(Street).where(Street.id == community.street_id)
                )
                street = sr.scalar_one_or_none()

    # 加载历史培训（仅已通过的）
    pr = await db.execute(
        select(ActivityParticipant)
        .where(ActivityParticipant.member_id == member_id)
    )
    parts = pr.scalars().all()
    activity_ids = [p.activity_id for p in parts]

    activities_map: dict[int, Activity] = {}
    if activity_ids:
        ar = await db.execute(
            select(Activity)
            .where(Activity.id.in_(activity_ids), Activity.status == "approved")
            .options(selectinload(Activity.attachments))
        )
        for a in ar.scalars().all():
            activities_map[a.id] = a

    trainings: list[TrainingItem] = []
    for p in parts:
        a = activities_map.get(p.activity_id)
        if not a:
            continue
        photos = []
        attachments = []
        for att in a.attachments:
            if att.kind == "photo":
                photos.append(att.file_url)
            else:
                attachments.append(att.file_url)
        trainings.append(
            TrainingItem(
                activity_id=a.id,
                theme=a.theme,
                training_at=a.training_at.isoformat() if a.training_at else "",
                lecturer_bio=a.lecturer_bio,
                location=a.location or "",
                lecturer_name=a.lecturer_name,
                study_hours=float(p.study_hours or 0),
                source_type=a.source_type,
                attendance_status=p.attendance_status,
                photos=photos,
                attachments=attachments,
            )
        )
    # 按时间倒序
    trainings.sort(key=lambda t: t.training_at, reverse=True)

    # 统计
    total_sessions = len(trainings)
    total_hours = sum(t.study_hours for t in trainings)
    from datetime import datetime
    cur_year = datetime.now().year
    year_hours = sum(
        t.study_hours for t in trainings if t.training_at.startswith(str(cur_year))
    )

    # 解析 roles / identities（JSON 字符串）
    import json
    def parse_list(s):
        if not s:
            return []
        try:
            v = json.loads(s) if isinstance(s, str) else s
            return v if isinstance(v, list) else []
        except Exception:
            return []
    roles_list = parse_list(m.roles)
    identities_list = parse_list(m.identities)

    member_card = MemberCard(
        id=m.id,
        name=m.name,
        phone=m.phone,
        id_card_no=m.id_card_no,
        gender=m.gender,
        join_date=m.join_date.isoformat() if m.join_date else None,
        status=m.status,
        roles=roles_list,
        identities=identities_list,
        photo_urls=parse_list(m.photo_urls),
        branch=OrgLite.model_validate(branch) if branch else None,
        community=OrgLite.model_validate(community) if community else None,
        street=OrgLite.model_validate(street) if street else None,
    )

    return PublicMemberOut(
        member=member_card,
        trainings=trainings,
        stats={
            "total_sessions": total_sessions,
            "total_hours": total_hours,
            "year_hours": year_hours,
            "year": cur_year,
        },
    )
