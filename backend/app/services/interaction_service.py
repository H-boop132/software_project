"""微澜点赞与收藏：操作幂等，复用现有互动表。"""
from fastapi import HTTPException, status
from sqlalchemy import case, delete, func, select
from sqlalchemy.orm import Session

from app.models import Collection, Like, Ripple, User
from app.schemas.interaction import CollectionOut, CollectionPage, LikeOut
from app.services.ripple_service import ripples_to_out


def _lock_public_ripple(db: Session, ripple_id: int) -> None:
    # 锁定微澜行，串行处理同一条内容的互动，并与下架/删除操作互斥。
    public_id = db.scalar(
        select(Ripple.id)
        .where(Ripple.id == ripple_id, Ripple.status == "published")
        .with_for_update()
    )
    if public_id is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="微澜不存在")


def set_like(db: Session, user: User, ripple_id: int, liked: bool) -> LikeOut:
    _lock_public_ripple(db, ripple_id)
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


def set_collection(
    db: Session, user: User, ripple_id: int, collected: bool
) -> CollectionOut:
    _lock_public_ripple(db, ripple_id)
    if collected:
        existing = db.scalar(
            select(Collection.id)
            .where(Collection.user_id == user.id, Collection.ripple_id == ripple_id)
            .with_for_update()
        )
        if existing is None:
            db.add(Collection(user_id=user.id, ripple_id=ripple_id))
    else:
        db.execute(
            delete(Collection).where(
                Collection.user_id == user.id, Collection.ripple_id == ripple_id
            )
        )
    db.commit()

    # 收藏只返回本人状态，不公开其他用户的收藏信息。
    own_id = db.scalar(
        select(Collection.id).where(
            Collection.user_id == user.id, Collection.ripple_id == ripple_id
        )
    )
    return CollectionOut(ripple_id=ripple_id, is_collected=own_id is not None)


def list_collections(
    db: Session, user: User, limit: int = 20, offset: int = 0
) -> CollectionPage:
    """仅返回本人的公开收藏；数量与分页使用相同可见性条件。"""
    filters = (Collection.user_id == user.id, Ripple.status == "published")
    total = db.scalar(
        select(func.count(Collection.id))
        .join(Ripple, Ripple.id == Collection.ripple_id)
        .where(*filters)
    ) or 0
    ripples = db.scalars(
        select(Ripple)
        .join(Collection, Collection.ripple_id == Ripple.id)
        .where(*filters)
        .order_by(Collection.created_at.desc(), Collection.id.desc())
        .limit(limit)
        .offset(offset)
    ).all()
    return CollectionPage(
        items=ripples_to_out(db, list(ripples), current_user=user),
        total=total, limit=limit, offset=offset,
    )
