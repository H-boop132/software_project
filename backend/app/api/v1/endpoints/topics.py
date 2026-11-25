"""话题详情与个人订阅。"""
from fastapi import APIRouter, Depends, HTTPException, Path
from sqlalchemy import delete, select
from sqlalchemy.dialects.mysql import insert
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.deps import get_current_user
from app.models import Topic, TopicSubscription, User
from app.schemas.common import TopicOut

router = APIRouter()


class TopicDetailOut(TopicOut):
    is_subscribed: bool


@router.get("", response_model=list[TopicOut])
def list_topics(db: Session = Depends(get_db)):
    """全部话题（字典数据，供发布页下拉、筛选等使用；按 id 升序）"""
    return list(db.scalars(select(Topic).order_by(Topic.id)).all())


@router.get("/subscribed", response_model=list[TopicOut])
def subscribed_topics(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return db.scalars(
        select(Topic).join(TopicSubscription)
        .where(TopicSubscription.user_id == user.id).order_by(Topic.id)
    ).all()


def require_topic(db: Session, topic_id: int) -> Topic:
    topic = db.get(Topic, topic_id)
    if topic is None:
        raise HTTPException(status_code=404, detail="话题不存在")
    return topic


@router.get("/{topic_id}", response_model=TopicDetailOut)
def topic_detail(
    topic_id: int = Path(gt=0), user: User = Depends(get_current_user), db: Session = Depends(get_db),
):
    topic = require_topic(db, topic_id)
    subscribed = db.get(TopicSubscription, (user.id, topic.id)) is not None
    return TopicDetailOut(**TopicOut.model_validate(topic).model_dump(), is_subscribed=subscribed)


@router.put("/{topic_id}/subscription", status_code=204)
def subscribe_topic(
    topic_id: int = Path(gt=0), user: User = Depends(get_current_user), db: Session = Depends(get_db),
):
    require_topic(db, topic_id)
    stmt = insert(TopicSubscription).values(user_id=user.id, topic_id=topic_id)
    db.execute(stmt.on_duplicate_key_update(topic_id=TopicSubscription.topic_id))
    db.commit()


@router.delete("/{topic_id}/subscription", status_code=204)
def unsubscribe_topic(
    topic_id: int = Path(gt=0), user: User = Depends(get_current_user), db: Session = Depends(get_db),
):
    db.execute(delete(TopicSubscription).where(
        TopicSubscription.user_id == user.id, TopicSubscription.topic_id == topic_id,
    ))
    db.commit()
