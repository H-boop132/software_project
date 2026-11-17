"""回声发表、同一微澜内回复及有权限的子树删除。"""
from fastapi import HTTPException
from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from app.models import Echo, Emotion, Ripple, User
from app.schemas.ripple import EchoCreate, EchoDeleteOut, EchoOut

MAX_ECHO_DEPTH = 8


def create_echo(db: Session, user: User, ripple_id: int, data: EchoCreate) -> EchoOut:
    root = db.scalar(select(Ripple.id).where(
        Ripple.id == ripple_id, Ripple.status == "published"
    ).with_for_update())
    if root is None:
        raise HTTPException(status_code=404, detail="微澜不存在")
    if data.emotion_code is not None and db.get(Emotion, data.emotion_code) is None:
        raise HTTPException(status_code=400, detail="情绪标签不存在")

    parent_id = data.parent_echo_id
    depth = 1
    visited = set()
    while parent_id is not None:
        parent = db.execute(select(Echo.id, Echo.root_ripple_id, Echo.parent_echo_id)
                            .where(Echo.id == parent_id).with_for_update()).one_or_none()
        if parent is None or parent.root_ripple_id != ripple_id:
            raise HTTPException(status_code=404, detail="回复目标不存在")
        if parent.id in visited:
            raise HTTPException(status_code=400, detail="回复关系异常")
        visited.add(parent.id)
        depth += 1
        if depth > MAX_ECHO_DEPTH:
            raise HTTPException(status_code=400, detail="回复最多支持 8 层，请直接回应微澜或较上层回声")
        parent_id = parent.parent_echo_id

    echo = Echo(
        root_ripple_id=ripple_id, parent_echo_id=data.parent_echo_id,
        user_id=user.id, content=data.content, emotion_code=data.emotion_code,
    )
    db.add(echo)
    db.commit()
    db.refresh(echo)
    return EchoOut.model_validate(echo)


def delete_echo(db: Session, user: User, echo_id: int) -> EchoDeleteOut:
    root_id = db.scalar(select(Echo.root_ripple_id).where(Echo.id == echo_id))
    if root_id is None:
        raise HTTPException(status_code=404, detail="回声不存在")
    # 与发表保持根微澜 -> 回声的加锁顺序，避免删除与回复并发时产生悬挂节点。
    db.scalar(select(Ripple.id).where(Ripple.id == root_id).with_for_update())
    echo = db.execute(select(Echo.id, Echo.user_id).where(Echo.id == echo_id).with_for_update()).one_or_none()
    if echo is None:
        raise HTTPException(status_code=404, detail="回声不存在")
    if echo.user_id != user.id and user.role != "admin":
        raise HTTPException(status_code=403, detail="只能删除自己的回声")
    # 项目原有外键会级联删除此节点的全部回复。
    db.execute(delete(Echo).where(Echo.id == echo_id))
    db.commit()
    count = db.scalar(select(func.count(Echo.id)).where(Echo.root_ripple_id == root_id)) or 0
    return EchoDeleteOut(ripple_id=root_id, echo_count=count)
