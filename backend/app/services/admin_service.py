"""管理后台业务：平台统计 / 用户列表 / 微澜删除"""
from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import Echo, Like, Ripple, Topic, User


def get_stats(db: Session) -> dict:
    """平台概览统计"""
    return {
        "users": db.scalar(select(func.count(User.id))) or 0,
        "ripples": db.scalar(select(func.count(Ripple.id))) or 0,
        "echoes": db.scalar(select(func.count(Echo.id))) or 0,
        "likes": db.scalar(select(func.count(Like.id))) or 0,
        "topics": db.scalar(select(func.count(Topic.id))) or 0,
    }


def list_users(db: Session, limit: int = 20, offset: int = 0) -> list[User]:
    stmt = select(User).order_by(User.created_at.desc()).limit(limit).offset(offset)
    return list(db.scalars(stmt).all())


def delete_ripple(db: Session, ripple_id: int) -> None:
    """删除微澜（回声/点赞/收藏由外键级联清理）"""
    ripple = db.get(Ripple, ripple_id)
    if ripple is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="微澜不存在")
    db.delete(ripple)
    db.commit()
