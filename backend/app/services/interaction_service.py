"""微澜点赞：操作幂等，复用现有 likes 表。"""
from fastapi import HTTPException, status
from sqlalchemy import case, delete, func, select
from sqlalchemy.orm import Session

from app.models import Like, Ripple, User
from app.schemas.interaction import LikeOut


def set_like(db: Session, user: User, ripple_id: int, liked: bool) -> LikeOut:
    # 锁定微澜行，串行处理同一条内容的互动，并与下架/删除操作互斥。
    public_id = db.scalar(
        select(Ripple.id)
        .where(Ripple.id == ripple_id, Ripple.status == "published")
        .with_for_update()
    )
    if public_id is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="微澜不存在")

    if liked:
        # 使用当前读，避免 MySQL REPEATABLE READ 下等待锁前的旧快照。
        existing = db.scalar(
            select(Like.id)
            .where(Like.user_id == user.id, Like.ripple_id == ripple_id)
            .with_for_update()
        )
        if existing is None:
            db.add(Like(user_id=user.id, ripple_id=ripple_id))
    else:
        db.execute(
            delete(Like).where(Like.user_id == user.id, Like.ripple_id == ripple_id)
        )
    db.commit()

    # 提交后用同一个新快照读取数量和本人状态，返回实际持久化结果。
    count, own_count = db.execute(
        select(
            func.count(Like.id),
            func.count(case((Like.user_id == user.id, Like.id))),
        ).where(Like.ripple_id == ripple_id)
    ).one()
    return LikeOut(ripple_id=ripple_id, is_liked=own_count > 0, like_count=count)
