"""管理后台接口：仅 admin 角色可访问

能力：平台统计 / 用户封禁与解封 / 微澜封禁 / 待审核队列 / 审核通过与驳回 / 内容删除
"""
from datetime import datetime

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.deps import get_current_admin
from app.models.user import User
from app.schemas.admin import BanUserRequest, ReviewActionRequest
from app.schemas.ripple import RippleOut
from app.schemas.user import UserOut
from app.services import admin_service, moderation_service, ripple_service

router = APIRouter()


# ---------------- 概览 ----------------
@router.get("/stats", tags=["管理"])
def stats(db: Session = Depends(get_db), admin: User = Depends(get_current_admin)):
    return admin_service.get_stats(db)


# ---------------- 用户管理 ----------------
@router.get("/users", response_model=list[UserOut], tags=["管理"])
def users(
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin),
):
    return admin_service.list_users(db, limit=limit, offset=offset)


@router.post("/users/{user_id}/ban", response_model=UserOut, tags=["管理"])
def ban_user(
    user_id: int,
    data: BanUserRequest,
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin),
):
    """封禁用户：可指定时长（天），不填=永久封禁"""
    return moderation_service.ban_user(
        db, admin, user_id, duration_days=data.duration_days, reason=data.reason
    )


@router.post("/users/{user_id}/unban", response_model=UserOut, tags=["管理"])
def unban_user(
    user_id: int,
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin),
):
    return moderation_service.unban_user(db, admin, user_id)


# ---------------- 内容管理 ----------------
@router.get("/ripples", response_model=list[RippleOut], tags=["管理"])
def ripples(
    keyword: str | None = None,
    start: datetime | None = None,
    end: datetime | None = None,
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin),
):
    """全部微澜（含封禁/待审核状态）；支持关键词与发布时间范围筛选"""
    return ripple_service.list_ripples(
        db,
        limit=limit,
        offset=offset,
        status=None,
        keyword=keyword,
        start=start,
        end=end,
    )


@router.post("/ripples/{ripple_id}/ban", response_model=RippleOut, tags=["管理"])
def ban_ripple(
    ripple_id: int,
    data: ReviewActionRequest,
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin),
):
    """封禁微澜：下架为仅作者可见"""
    return moderation_service.ban_ripple(db, admin, ripple_id, reason=data.reason)


@router.get("/reviews", response_model=list[RippleOut], tags=["管理"])
def review_queue(
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin),
):
    """待审核队列：作者修改后重新提交的微澜"""
    return ripple_service.ripples_to_out(
        db, moderation_service.list_pending(db, limit=limit, offset=offset)
    )


@router.post("/ripples/{ripple_id}/approve", response_model=RippleOut, tags=["管理"])
def approve_ripple(
    ripple_id: int,
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin),
):
    """审核通过：恢复公开可见"""
    return moderation_service.approve_ripple(db, admin, ripple_id)


@router.post("/ripples/{ripple_id}/reject", response_model=RippleOut, tags=["管理"])
def reject_ripple(
    ripple_id: int,
    data: ReviewActionRequest,
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin),
):
    """审核驳回：回到仅作者可见，作者可再次修改提交"""
    return moderation_service.reject_ripple(db, admin, ripple_id, reason=data.reason)


@router.delete("/ripples/{ripple_id}", status_code=status.HTTP_200_OK, tags=["管理"])
def delete_ripple(
    ripple_id: int,
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin),
):
    admin_service.delete_ripple(db, ripple_id)
    return {"ok": True, "deleted_ripple_id": ripple_id}
