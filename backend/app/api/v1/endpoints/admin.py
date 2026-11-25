"""管理后台接口：仅 admin 角色可访问

能力：平台统计 / 用户搜索与筛选 / 用户封禁与解封 / 微澜封禁 / 待审核队列 /
审核通过与驳回 / 审核记录 / 内容删除（处理结果同步通知作者）
"""
from datetime import datetime
from typing import Literal

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.deps import get_current_admin
from app.models.user import User
from app.schemas.admin import BanUserRequest, ReviewActionRequest, ReviewLogOut
from app.schemas.report import (
    AppealHandleRequest, AppealOut, AppealPage, ReportHandleRequest, ReportOut, ReportPage,
)
from app.schemas.ripple import RippleOut
from app.schemas.user import UserOut
from app.services import admin_service, moderation_service, report_service, ripple_service

router = APIRouter()


# ---------------- 概览 ----------------
@router.get("/stats", tags=["管理"])
def stats(db: Session = Depends(get_db), admin: User = Depends(get_current_admin)):
    return admin_service.get_stats(db)


# ---------------- 用户管理 ----------------
@router.get("/users", response_model=list[UserOut], tags=["管理"])
def users(
    keyword: str | None = Query(None, max_length=50, description="昵称或用户名关键词"),
    status_filter: Literal["active", "banned"] | None = Query(None, alias="status"),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin),
):
    return admin_service.list_users(
        db, limit=limit, offset=offset, keyword=keyword, status_filter=status_filter
    )


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
    status_filter: Literal["published", "banned", "pending", "deleted"] | None = Query(
        None, alias="status"
    ),
    start: datetime | None = None,
    end: datetime | None = None,
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin),
):
    """全部微澜（含封禁/待审核状态）；支持关键词、状态与发布时间范围筛选"""
    return ripple_service.list_ripples(
        db,
        limit=limit,
        offset=offset,
        status=status_filter,
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
    ripple = moderation_service.ban_ripple(db, admin, ripple_id, reason=data.reason)
    return ripple_service.ripples_to_out(db, [ripple])[0]


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


@router.get("/reviews/history", response_model=list[ReviewLogOut], tags=["管理"])
def review_history(
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin),
):
    """审核记录：谁在何时对哪条内容做了什么处理、原因是什么"""
    return admin_service.list_reviews(db, limit=limit, offset=offset)


@router.post("/ripples/{ripple_id}/approve", response_model=RippleOut, tags=["管理"])
def approve_ripple(
    ripple_id: int,
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin),
):
    """审核通过：恢复公开可见"""
    ripple = moderation_service.approve_ripple(db, admin, ripple_id)
    return ripple_service.ripples_to_out(db, [ripple])[0]


@router.post("/ripples/{ripple_id}/reject", response_model=RippleOut, tags=["管理"])
def reject_ripple(
    ripple_id: int,
    data: ReviewActionRequest,
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin),
):
    """审核驳回：回到仅作者可见，作者可再次修改提交"""
    ripple = moderation_service.reject_ripple(db, admin, ripple_id, reason=data.reason)
    return ripple_service.ripples_to_out(db, [ripple])[0]


@router.delete("/ripples/{ripple_id}", status_code=status.HTTP_200_OK, tags=["管理"])
def delete_ripple(
    ripple_id: int,
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin),
):
    admin_service.delete_ripple(db, admin, ripple_id)
    return {"ok": True, "deleted_ripple_id": ripple_id}


# ---------------- 举报与申诉 ----------------
@router.get("/reports", response_model=ReportPage, tags=["管理"])
def reports(
    status_filter: Literal["pending", "uphold", "dismissed"] | None = Query(None, alias="status"),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin),
):
    """举报队列，默认查看待处理；可按处理状态筛选。"""
    return report_service.list_reports(
        db, status_filter=status_filter or "pending", limit=limit, offset=offset
    )


@router.post("/reports/{report_id}/handle", response_model=ReportOut, tags=["管理"])
def handle_report(
    report_id: int,
    data: ReportHandleRequest,
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin),
):
    """举报成立则下架内容并通知作者，结果通知举报人。"""
    return report_service.handle_report(db, admin, report_id, data)


@router.get("/appeals", response_model=AppealPage, tags=["管理"])
def appeals(
    status_filter: Literal["pending", "approved", "rejected"] | None = Query(None, alias="status"),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin),
):
    """申诉队列，默认查看待处理；可按处理状态筛选。"""
    return report_service.list_appeals(
        db, status_filter=status_filter or "pending", limit=limit, offset=offset
    )


@router.post("/appeals/{appeal_id}/handle", response_model=AppealOut, tags=["管理"])
def handle_appeal(
    appeal_id: int,
    data: AppealHandleRequest,
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin),
):
    """申诉通过则恢复公开，驳回则维持下架，结果通知作者。"""
    return report_service.handle_appeal(db, admin, appeal_id, data)
