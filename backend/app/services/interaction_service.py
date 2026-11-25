"""微澜点赞与收藏：操作幂等，复用现有互动表。"""
from fastapi import HTTPException, status
from sqlalchemy import case, delete, func, select
from sqlalchemy.orm import Session

from app.models import Collection, Echo, EchoLike, Like, Notification, Ripple, User
from app.schemas.interaction import CollectionOut, CollectionPage, EchoLikeOut, LikeOut
from app.services.ripple_service import ripples_to_out


def _lock_public_ripple(db: Session, ripple_id: int) -> int:
    # 锁定微澜行，串行处理同一条内容的互动，并与下架/删除操作互斥。
    author_id = db.scalar(
        select(Ripple.user_id)
        .where(Ripple.id == ripple_id, Ripple.status == "published")
        .with_for_update()
    )
    if author_id is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="微澜不存在")
    return author_id


def _notify_interaction(
    db: Session, author_id: int, actor_id: int, kind: str, ripple_id: int
) -> None:
    """点赞/收藏通知只保留一条，避免反复取消再点导致消息刷屏。"""
    if author_id == actor_id:
        return
    exists = db.scalar(
        select(Notification.id).where(
            Notification.kind == kind,
            Notification.actor_id == actor_id,
            Notification.ripple_id == ripple_id,
        )
    )
    if exists is None:
        db.add(Notification(
            recipient_id=author_id, actor_id=actor_id, kind=kind, ripple_id=ripple_id,
        ))


def _clear_interaction_notice(
    db: Session, actor_id: int, kind: str, ripple_id: int
) -> None:
    db.execute(delete(Notification).where(
        Notification.kind == kind,
        Notification.actor_id == actor_id,
        Notification.ripple_id == ripple_id,
    ))


def set_like(db: Session, user: User, ripple_id: int, liked: bool) -> LikeOut:
    author_id = _lock_public_ripple(db, ripple_id)
    if liked:
        # 使用当前读，避免 MySQL REPEATABLE READ 下等待锁前的旧快照。
        existing = db.scalar(
            select(Like.id)
            .where(Like.user_id == user.id, Like.ripple_id == ripple_id)
            .with_for_update()
        )
        if existing is None:
            db.add(Like(user_id=user.id, ripple_id=ripple_id))
            _notify_interaction(db, author_id, user.id, "like", ripple_id)
    else:
        db.execute(
            delete(Like).where(Like.user_id == user.id, Like.ripple_id == ripple_id)
        )
        _clear_interaction_notice(db, user.id, "like", ripple_id)
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
    author_id = _lock_public_ripple(db, ripple_id)
    if collected:
        existing = db.scalar(
            select(Collection.id)
            .where(Collection.user_id == user.id, Collection.ripple_id == ripple_id)
            .with_for_update()
        )
        if existing is None:
            db.add(Collection(user_id=user.id, ripple_id=ripple_id))
            _notify_interaction(db, author_id, user.id, "collection", ripple_id)
    else:
        db.execute(
            delete(Collection).where(
                Collection.user_id == user.id, Collection.ripple_id == ripple_id
            )
        )
        _clear_interaction_notice(db, user.id, "collection", ripple_id)
    db.commit()

    # 收藏只返回本人状态，不公开其他用户的收藏信息。
    own_id = db.scalar(
        select(Collection.id).where(
            Collection.user_id == user.id, Collection.ripple_id == ripple_id
        )
    )
    return CollectionOut(ripple_id=ripple_id, is_collected=own_id is not None)


def _notify_echo_like(
    db: Session, author_id: int, actor_id: int, echo_id: int
) -> None:
    if author_id == actor_id:
        return
    exists = db.scalar(
        select(Notification.id).where(
            Notification.kind == "echo_like",
            Notification.actor_id == actor_id,
            Notification.echo_id == echo_id,
        )
    )
    if exists is None:
        db.add(Notification(
            recipient_id=author_id, actor_id=actor_id, kind="echo_like", echo_id=echo_id,
        ))


def set_echo_like(db: Session, user: User, echo_id: int, liked: bool) -> EchoLikeOut:
    """回声点赞：先锁根微澜再锁回声，与发表/删除回声保持同一加锁顺序。"""
    row = db.execute(
        select(Echo.id, Echo.root_ripple_id, Echo.user_id).where(Echo.id == echo_id)
    ).one_or_none()
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="回声不存在")
    _lock_public_ripple(db, row.root_ripple_id)

    if liked:
        existing = db.scalar(
            select(EchoLike.id)
            .where(EchoLike.user_id == user.id, EchoLike.echo_id == echo_id)
            .with_for_update()
        )
        if existing is None:
            db.add(EchoLike(user_id=user.id, echo_id=echo_id))
            _notify_echo_like(db, row.user_id, user.id, echo_id)
    else:
        db.execute(delete(EchoLike).where(
            EchoLike.user_id == user.id, EchoLike.echo_id == echo_id,
        ))
        db.execute(delete(Notification).where(
            Notification.kind == "echo_like",
            Notification.actor_id == user.id,
            Notification.echo_id == echo_id,
        ))
    db.commit()

    count, own_count = db.execute(
        select(
            func.count(EchoLike.id),
            func.count(case((EchoLike.user_id == user.id, EchoLike.id))),
        ).where(EchoLike.echo_id == echo_id)
    ).one()
    return EchoLikeOut(echo_id=echo_id, is_liked=own_count > 0, like_count=count)


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
