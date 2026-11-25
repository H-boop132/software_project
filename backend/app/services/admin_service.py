"""管理后台业务：平台统计 / 用户筛选 / 审核记录 / 微澜删除"""
from datetime import datetime

from fastapi import HTTPException, status
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session, aliased

from app.core.storage import delete_upload_if_unused
from app.models import Echo, Like, Ripple, RippleReview, Topic, User
from app.schemas.admin import ReviewLogOut
from app.services.notification_service import notify_author


def _like_pattern(keyword: str) -> str:
    """把关键词里的通配符转义，避免 % / _ 被当成通配符。"""
    escaped = keyword.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
    return f"%{escaped}%"


def get_stats(db: Session, now: datetime | None = None) -> dict:
    """平台概览统计：总量 + 待审核 + 封禁中的用户/内容"""
    now = now or datetime.now()
    active_ban = or_(User.ban_until.is_(None), User.ban_until > now)
    return {
        "users": db.scalar(select(func.count(User.id))) or 0,
        "ripples": db.scalar(select(func.count(Ripple.id)).where(Ripple.status != "deleted")) or 0,
        "echoes": db.scalar(select(func.count(Echo.id)).join(Ripple).where(Ripple.status != "deleted")) or 0,
        "likes": db.scalar(select(func.count(Like.id)).join(Ripple).where(Ripple.status != "deleted")) or 0,
        "topics": db.scalar(select(func.count(Topic.id))) or 0,
        "pending": db.scalar(select(func.count(Ripple.id)).where(Ripple.status == "pending")) or 0,
        "banned_users": db.scalar(select(func.count(User.id)).where(
            User.ban_status == "banned", active_ban
        )) or 0,
        "banned_ripples": db.scalar(select(func.count(Ripple.id)).where(
            Ripple.status == "banned"
        )) or 0,
    }


def list_users(
    db: Session, limit: int = 20, offset: int = 0,
    keyword: str | None = None, status_filter: str | None = None,
) -> list[User]:
    """用户列表：支持昵称/用户名关键词与封禁状态筛选"""
    stmt = select(User)
    if keyword and keyword.strip():
        pattern = _like_pattern(keyword.strip())
        stmt = stmt.where(or_(
            User.username.like(pattern, escape="\\"),
            User.nickname.like(pattern, escape="\\"),
        ))
    if status_filter == "banned":
        stmt = stmt.where(User.ban_status == "banned")
    elif status_filter == "active":
        stmt = stmt.where(User.ban_status == "active")
    stmt = stmt.order_by(User.created_at.desc(), User.id.desc()).limit(limit).offset(offset)
    return list(db.scalars(stmt).all())


def list_reviews(db: Session, limit: int = 20, offset: int = 0) -> list[ReviewLogOut]:
    """审核/封禁审计记录，按最近操作倒序"""
    author = aliased(User)
    reviewer = aliased(User)
    stmt = (
        select(RippleReview, Ripple.content, author.id, author.nickname, reviewer.nickname)
        .join(Ripple, Ripple.id == RippleReview.ripple_id)
        .join(author, author.id == Ripple.user_id)
        .join(reviewer, reviewer.id == RippleReview.reviewer_id)
        .order_by(RippleReview.id.desc())
        .limit(limit).offset(offset)
    )
    rows = db.execute(stmt).all()
    return [
        ReviewLogOut(
            id=review.id, ripple_id=review.ripple_id, action=review.action,
            reason=review.reason, reviewer_id=review.reviewer_id, reviewer_name=reviewer_name,
            author_id=author_id, author_name=author_name, content=content,
            created_at=review.created_at,
        )
        for review, content, author_id, author_name, reviewer_name in rows
    ]


def delete_ripple(db: Session, admin: User, ripple_id: int) -> None:
    """删除微澜（回声/点赞/收藏由外键级联清理），并通知作者"""
    ripple = db.get(Ripple, ripple_id)
    if ripple is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="微澜不存在")
    preview = ripple.content[:20] + ("…" if len(ripple.content) > 20 else "")
    images = list(ripple.images or [])
    notify_author(db, ripple.user_id, admin.id, f"你的微澜「{preview}」已被管理员删除。")
    db.delete(ripple)
    db.commit()
    for url in images:
        delete_upload_if_unused(db, url)
