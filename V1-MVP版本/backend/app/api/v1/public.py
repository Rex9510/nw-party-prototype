"""/api/v1/public 公开接口（不需要 token，用于扫码访问的党员名片）。"""
from fastapi import APIRouter, Depends, HTTPException, Response
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
    # photo_urls 列表也用缩略图（首屏不再返原图，点头像需查全图：/public/members/{id}/avatar）
    photo_urls: list[str] = []
    # 组织归属
    branch: OrgLite | None = None
    community: OrgLite | None = None
    street: OrgLite | None = None


class AttachmentLite(BaseModel):
    """公开页附件摘要：只返 id + 缩略图/类型 + 文件名占位。"""
    id: int
    kind: str  # photo / signin
    thumbnail_url: str | None = None  # 缩略图 dataURL（图片才有）
    is_image: bool


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
    # 改为摘要：只返 attachment 列表（id + 缩略图）。看大图调 /public/attachments/{id}/full
    attachments: list[AttachmentLite] = []


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

    # 加载组织归属（v3：按 org_level 决定）
    branch: Branch | None = None
    community: Community | None = None
    street: Street | None = None
    if m.org_level == "branch" and m.branch_id:
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
    elif m.org_level == "community" and m.community_id:
        cr = await db.execute(
            select(Community).where(Community.id == m.community_id)
        )
        community = cr.scalar_one_or_none()
        if community:
            sr = await db.execute(
                select(Street).where(Street.id == community.street_id)
            )
            street = sr.scalar_one_or_none()
    elif m.org_level == "street" and m.street_id:
        sr = await db.execute(
            select(Street).where(Street.id == m.street_id)
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
        att_lites: list[AttachmentLite] = []
        for att in a.attachments:
            is_image = (att.thumbnail_url is not None) or (
                att.file_url and att.file_url.startswith('data:image/')
            )
            # 兜底：老数据没生成缩略图时，当场用 PIL 缩图存回 DB（200x200 JPEG）。
            # 避免公开页首屏塞 4MB+ 的原图。
            thumb = att.thumbnail_url
            if not thumb and att.file_url and att.file_url.startswith('data:image/'):
                thumb = await _generate_thumbnail(att.file_url, att.id, db)
            att_lites.append(AttachmentLite(
                id=att.id,
                kind=att.kind,
                thumbnail_url=thumb,
                is_image=is_image,
            ))
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
                attachments=att_lites,
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

    # 头像：photo_urls 存 dataURL（VARCHAR(8192)），返回首张用于头像展示
    member_photos = parse_list(m.photo_urls)
    if member_photos and len(member_photos) > 0:
        # 只返第一张做头像，避免 payload 过大
        member_photos = [member_photos[0]]
    else:
        member_photos = []

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
        photo_urls=member_photos,
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


@router.get("/attachments/{attachment_id}/full")
async def get_attachment_full(
    attachment_id: int,
    db: AsyncSession = Depends(get_db),
) -> Response:
    """按需返原图/原文件（响应可能是 dataURL 或 http URL）。"""
    r = await db.execute(select(ActivityAttachment).where(ActivityAttachment.id == attachment_id))
    att = r.scalar_one_or_none()
    if not att:
        raise HTTPException(status_code=404, detail="附件不存在")

    url = att.file_url
    if not url:
        raise HTTPException(status_code=404, detail="文件为空")

    if url.startswith("data:"):
        # 解 dataURL 直接返二进制
        try:
            head, b64 = url.split(",", 1)
            mime = head.split(";", 1)[0].split(":", 1)[1]
            import base64
            raw = base64.b64decode(b64)
            return Response(content=raw, media_type=mime)
        except Exception:
            raise HTTPException(status_code=500, detail="文件解析失败")
    else:
        # http(s) URL：302 跳转
        from fastapi.responses import RedirectResponse
        return RedirectResponse(url=url)


# ---- 缩略图兜底生成（v2026-07-28：老数据没缩略图时当场补） ----
import base64 as _b64
import io as _io


async def _generate_thumbnail(
    file_url: str, attachment_id: int, db: AsyncSession
) -> str | None:
    """老数据兜底：从 file_url 的 dataURL 解出图片 → 缩成 200x200 JPEG → 存回 DB。

    失败（格式不支持/数据损坏）返 None，前端继续显示「无图」。
    """
    try:
        from PIL import Image
        head, b64 = file_url.split(",", 1)
        mime = head.split(";", 1)[0].split(":", 1)[1]
        if not mime.startswith("image/"):
            return None
        raw = _b64.b64decode(b64)
        img = Image.open(_io.BytesIO(raw))
        # 透明 → 白底（避免 JPEG 黑底）
        if img.mode in ("RGBA", "LA", "P"):
            bg = Image.new("RGB", img.size, (255, 255, 255))
            if img.mode == "P":
                img = img.convert("RGBA")
            bg.paste(img, mask=img.split()[-1] if img.mode == "RGBA" else None)
            img = bg
        elif img.mode != "RGB":
            img = img.convert("RGB")
        # 等比缩放，长边 200
        img.thumbnail((200, 200), Image.LANCZOS)
        buf = _io.BytesIO()
        img.save(buf, format="JPEG", quality=80, optimize=True)
        thumb_b64 = _b64.b64encode(buf.getvalue()).decode("ascii")
        thumb_data_url = f"data:image/jpeg;base64,{thumb_b64}"
        # 写回 DB（独立事务）
        from app.models.activity import ActivityAttachment
        r = await db.execute(
            select(ActivityAttachment).where(ActivityAttachment.id == attachment_id)
        )
        att = r.scalar_one_or_none()
        if att:
            att.thumbnail_url = thumb_data_url
            await db.commit()
        return thumb_data_url
    except Exception as e:
        # 不让一个坏图搞挂整页
        import logging
        logging.getLogger(__name__).warning(
            f"_generate_thumbnail failed for attachment {attachment_id}: {e}"
        )
        return None
