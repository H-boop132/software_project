"""封禁与审核业务：用户封禁/解封、微澜封禁/审核、封禁状态判断"""
from datetime import datetime, timedelta

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Ripple, RippleReview, User, UserBan


def is_banned(user: User) -> bool:
    """封禁判定：banned 且未到期（NULL=永久封禁）"""
    if user.ban_status != "banned":
        return False
    if user.ban_until is None:
        return True
    return user.ban_until > datetime.now()


def auto_unban(db: Session, user: User) -> None:
    """封禁到期自动解封（在每次请求校验时执行）"""
    if (
        user.ban_status == "banned"
        and user.ban_until is not None
        and user.ban_until <= datetime.now()
    ):
        user.ban_status = "active"
        user.ban_until = None
        user.ban_reason = None
        db.commit()


def ban_message(user: User) -> str:
    if user.ban_until is None:
        return f"账号已被永久封禁，原因：{user.ban_reason or '未说明'}"
    return (
        f"账号已被封禁至 {user.ban_until:%Y-%m-%d %H:%M}，"
        f"原因：{user.ban_reason or '未说明'}"
    )


# ------------------------------------------------------------
# 用户封禁
# ------------------------------------------------------------
def ban_user(
    db: Session, admin: User, user_id: int, duration_days: int | None, reason: str | None
) -> User:
    user = db.get(User, user_id)
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="用户不存在")
    if user.id == admin.id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="不能封禁自己")
    if user.role == "admin":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="不能封禁管理员账号")

    until = (
        None
        if duration_days is None
        else datetime.now() + timedelta(days=duration_days)
    )
    user.ban_status = "banned"
    user.ban_until = until
    user.ban_reason = reason
    db.add(
        UserBan(
            user_id=user.id,
            admin_id=admin.id,
            duration_days=duration_days,
            reason=reason,
            ban_until=until,
        )
    )
    db.commit()
    db.refresh(user)
    return user


def unban_user(db: Session, admin: User, user_id: int) -> User:
    user = db.get(User, user_id)
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="用户不存在")
    user.ban_status = "active"
    user.ban_until = None
    user.ban_reason = None
    db.commit()
    db.refresh(user)
    return user


# ------------------------------------------------------------
# 微澜封禁 / 审核
# ------------------------------------------------------------
def _get_ripple_or_404(db: Session, ripple_id: int) -> Ripple:
    ripple = db.get(Ripple, ripple_id)
    if ripple is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="微澜不存在")
    return ripple


def ban_ripple(db: Session, admin: User, ripple_id: int, reason: str | None) -> Ripple:
    """管理员封禁微澜：仅作者可见"""
    ripple = _get_ripple_or_404(db, ripple_id)
    ripple.status = "banned"
    db.add(
        RippleReview(ripple_id=ripple.id, reviewer_id=admin.id, action="ban", reason=reason)
    )
    db.commit()
    db.refresh(ripple)
    return ripple


def approve_ripple(db: Session, admin: User, ripple_id: int) -> Ripple:
    """审核通过：待审核 → 重新公开可见"""
    ripple = _get_ripple_or_404(db, ripple_id)
    if ripple.status != "pending":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="仅待审核的内容可审核通过")
    ripple.status = "published"
    db.add(RippleReview(ripple_id=ripple.id, reviewer_id=admin.id, action="approve"))
    db.commit()
    db.refresh(ripple)
    return ripple


def reject_ripple(db: Session, admin: User, ripple_id: int, reason: str | None) -> Ripple:
    """审核驳回：回到仅作者可见，作者可再次修改提交"""
    ripple = _get_ripple_or_404(db, ripple_id)
    if ripple.status != "pending":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="仅待审核的内容可驳回")
    ripple.status = "banned"
    db.add(
        RippleReview(
            ripple_id=ripple.id, reviewer_id=admin.id, action="reject", reason=reason
        )
    )
    db.commit()
    db.refresh(ripple)
    return ripple


def list_pending(db: Session, limit: int = 20, offset: int = 0) -> list[Ripple]:
    """待审核队列"""
    stmt = (
        select(Ripple)
        .where(Ripple.status == "pending")
        .order_by(Ripple.created_at.desc())
        .limit(limit)
        .offset(offset)
    )
    return list(db.scalars(stmt).all())
