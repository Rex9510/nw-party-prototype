"""/api/v1/auth 路由。"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.deps import get_current_user
from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    verify_password,
)
from app.db.session import get_db
from app.models.user import User
from app.schemas.auth import (
    LoginRequest,
    PasswordChangeRequest,
    RefreshRequest,
    TokenResponse,
    UserInfo,
)
from jose import JWTError

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login", response_model=TokenResponse)
async def login(body: LoginRequest, db: AsyncSession = Depends(get_db)) -> TokenResponse:
    """手机号 + 密码登录。"""
    result = await db.execute(
        select(User).where(User.phone == body.phone, User.status == "active")
    )
    user = result.scalar_one_or_none()

    if not user or not verify_password(body.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="手机号或密码错误",
        )

    access = create_access_token(user.id, extra={"role": user.role})
    refresh = create_refresh_token(user.id)
    return TokenResponse(
        access_token=access,
        refresh_token=refresh,
        expires_in=settings.JWT_ACCESS_EXPIRE_MINUTES * 60,
    )


@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(body: RefreshRequest, db: AsyncSession = Depends(get_db)) -> TokenResponse:
    """用 refresh token 换新的 access。"""
    try:
        payload = decode_token(body.refresh_token)
        if payload.get("type") != "refresh":
            raise HTTPException(status_code=401, detail="无效 token")
        user_id = int(payload.get("sub"))
    except (JWTError, ValueError, TypeError):
        raise HTTPException(status_code=401, detail="无效或过期 token")

    result = await db.execute(select(User).where(User.id == user_id, User.status == "active"))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=401, detail="用户不存在或已停用")

    access = create_access_token(user.id, extra={"role": user.role})
    new_refresh = create_refresh_token(user.id)
    return TokenResponse(
        access_token=access,
        refresh_token=new_refresh,
        expires_in=settings.JWT_ACCESS_EXPIRE_MINUTES * 60,
    )


@router.get("/me", response_model=UserInfo)
async def me(user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)) -> UserInfo:
    """当前登录用户信息。"""
    from app.models.party import Street, Community, Branch
    from sqlalchemy.orm import selectinload
    street_name = community_name = branch_name = None

    if user.street_id:
        r = await db.execute(select(Street.name).where(Street.id == user.street_id))
        street_name = r.scalar_one_or_none()
    if user.community_id:
        r = await db.execute(select(Community.name).where(Community.id == user.community_id))
        community_name = r.scalar_one_or_none()
    if user.branch_id:
        r = await db.execute(select(Branch.name).where(Branch.id == user.branch_id))
        branch_name = r.scalar_one_or_none()

    data = UserInfo.model_validate(user).model_dump()
    data["street_name"] = street_name
    data["community_name"] = community_name
    data["branch_name"] = branch_name
    return UserInfo.model_validate(data)


@router.post("/change-password")
async def change_password(
    body: PasswordChangeRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """修改自己的密码。"""
    if not verify_password(body.old_password, user.password_hash):
        raise HTTPException(status_code=400, detail="原密码错误")
    if body.old_password == body.new_password:
        raise HTTPException(status_code=400, detail="新密码不能与原密码相同")
    # 确认密码一致性（schema validator 已经检查过，这里兜底）
    if body.new_password != body.confirm_password:
        raise HTTPException(status_code=400, detail="两次输入的新密码不一致")
    user.password_hash = hash_password(body.new_password)
    await db.commit()
    return {"message": "密码修改成功"}
