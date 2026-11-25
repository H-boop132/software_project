from datetime import datetime

from fastapi import HTTPException
from sqlalchemy import func, or_, select, update
from sqlalchemy.orm import Session

from app.models import Echo, Notification, Ripple, User
from app.schemas.notification import NotificationKind, NotificationOut, NotificationPage


def _visible_messages(user_id: int):
    """下架后不返回回声正文、链接或未读数；点赞/收藏通知也随内容一起隐藏。"""
    visible_echo = (
        select(Echo.id).join(Ripple, Ripple.id == Echo.root_ripple_id)
        .where(Echo.id == Notification.echo_id, Ripple.status == "published")
        .correlate(Notification).exists()
    )
    visible_ripple = (
        select(Ripple.id)
        .where(Ripple.id == Notification.ripple_id, Ripple.status == "published")
        .correlate(Notification).exists()
    )
    return (
        Notification.recipient_id == user_id,
        or_(Notification.echo_id.is_(None), visible_echo),
        or_(Notification.kind.notin_(("like", "collection")), visible_ripple),
    )


def notify_author(
    db: Session, recipient_id: int, actor_id: int, note: str, ripple_id: int | None = None,
) -> None:
    """把内容处理结果同步给作者（封禁/解封、下架/驳回/通过、删除）。自己操作自己不发。"""
    if recipient_id == actor_id:
        return
    db.add(Notification(
        recipient_id=recipient_id, actor_id=actor_id, kind="moderation",
        ripple_id=ripple_id, note=note[:200],
    ))


def unread_count(db: Session, user_id: int) -> int:
    return db.scalar(select(func.count(Notification.id)).where(
        *_visible_messages(user_id), Notification.read_at.is_(None)
    )) or 0


def list_messages(
    db: Session, user_id: int, *, unread_only: bool, kind: NotificationKind | None,
    before: int | None, limit: int,
) -> NotificationPage:
    stmt = (
        select(Notification, User.nickname, Echo.root_ripple_id, Echo.content)
        .join(User, User.id == Notification.actor_id)
        .outerjoin(Echo, Echo.id == Notification.echo_id)
        .where(*_visible_messages(user_id))
        .order_by(Notification.id.desc()).limit(limit + 1)
    )
    if unread_only:
        stmt = stmt.where(Notification.read_at.is_(None))
    if kind:
        stmt = stmt.where(Notification.kind == kind)
    if before:
        stmt = stmt.where(Notification.id < before)
    rows = db.execute(stmt).all()
    items = [
        NotificationOut(
            id=notice.id, kind=notice.kind, actor_id=notice.actor_id,
            actor_name=nickname,
            ripple_id=notice.ripple_id if notice.ripple_id is not None else ripple_id,
            echo_id=notice.echo_id,
            preview=content[:100] if content else None,
            note=notice.note,
            created_at=notice.created_at,
            read_at=notice.read_at,
        )
        for notice, nickname, ripple_id, content in rows[:limit]
    ]
    return NotificationPage(
        items=items, next_before=items[-1].id if len(rows) > limit else None,
        unread_count=unread_count(db, user_id),
    )


def mark_read(db: Session, user_id: int, message_id: int | None = None) -> int:
    filters = _visible_messages(user_id)
    stmt = update(Notification).where(*filters, Notification.read_at.is_(None))
    if message_id is not None:
        exists = db.scalar(select(Notification.id).where(*filters, Notification.id == message_id))
        if exists is None:
            raise HTTPException(status_code=404, detail="消息不存在")
        stmt = stmt.where(Notification.id == message_id)
    db.execute(stmt.values(read_at=datetime.now()).execution_options(synchronize_session=False))
    db.commit()
    return unread_count(db, user_id)
