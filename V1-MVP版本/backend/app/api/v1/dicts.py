"""/api/v1/dicts 字典路由。"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user, require_roles
from app.db.session import get_db
from app.models.dict import Lecturer, TrainingCategory, TrainingSource
from app.models.user import User
from app.schemas.dict import (
    DictItemCreate,
    DictItemOut,
    LecturerCreate,
    LecturerOut,
    LecturerUpdate,
)

router = APIRouter(prefix="/dicts", tags=["dicts"])


# 讲师 CRUD（仅 system_admin / street_lead 可写）
@router.get("/lecturers", response_model=list[LecturerOut])
async def list_lecturers(
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(get_current_user),
) -> list[Lecturer]:
    r = await db.execute(select(Lecturer).order_by(Lecturer.id))
    return list(r.scalars().all())


@router.post("/lecturers", response_model=LecturerOut, status_code=201)
async def create_lecturer(
    body: LecturerCreate,
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(require_roles(User.ROLE_ADMIN, User.ROLE_STREET_LEAD)),
) -> Lecturer:
    lec = Lecturer(**body.model_dump())
    db.add(lec)
    await db.commit()
    await db.refresh(lec)
    return lec


@router.patch("/lecturers/{lecturer_id}", response_model=LecturerOut)
async def update_lecturer(
    lecturer_id: int,
    body: LecturerUpdate,
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(require_roles(User.ROLE_ADMIN, User.ROLE_STREET_LEAD)),
) -> Lecturer:
    r = await db.execute(select(Lecturer).where(Lecturer.id == lecturer_id))
    lec = r.scalar_one_or_none()
    if not lec:
        raise HTTPException(status_code=404, detail="讲师不存在")
    for k, v in body.model_dump(exclude_unset=True).items():
        setattr(lec, k, v)
    await db.commit()
    await db.refresh(lec)
    return lec


@router.delete("/lecturers/{lecturer_id}", status_code=204)
async def delete_lecturer(
    lecturer_id: int,
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(require_roles(User.ROLE_ADMIN, User.ROLE_STREET_LEAD)),
) -> None:
    r = await db.execute(select(Lecturer).where(Lecturer.id == lecturer_id))
    lec = r.scalar_one_or_none()
    if not lec:
        raise HTTPException(status_code=404, detail="讲师不存在")
    lec.status = "inactive"
    await db.commit()


# 培训对象类别（所有角色可读，仅超管可写）
@router.get("/training-categories", response_model=list[DictItemOut])
async def list_training_categories(
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(get_current_user),
):
    r = await db.execute(select(TrainingCategory).order_by(TrainingCategory.sort, TrainingCategory.id))
    return list(r.scalars().all())


@router.post("/training-categories", response_model=DictItemOut, status_code=201)
async def create_training_category(
    body: DictItemCreate,
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(require_roles(User.ROLE_ADMIN)),
):
    item = TrainingCategory(**body.model_dump())
    db.add(item)
    await db.commit()
    await db.refresh(item)
    return item


# 培训来源
@router.get("/training-sources", response_model=list[DictItemOut])
async def list_training_sources(
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(get_current_user),
):
    r = await db.execute(select(TrainingSource).order_by(TrainingSource.sort, TrainingSource.id))
    return list(r.scalars().all())


@router.post("/training-sources", response_model=DictItemOut, status_code=201)
async def create_training_source(
    body: DictItemCreate,
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(require_roles(User.ROLE_ADMIN)),
):
    item = TrainingSource(**body.model_dump())
    db.add(item)
    await db.commit()
    await db.refresh(item)
    return item
