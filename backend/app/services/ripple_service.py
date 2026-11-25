"""微澜核心业务：时间线 / 发布 / 详情 / 潮汐 / 气象"""
from datetime import datetime, timedelta
from typing import Literal

from fastapi import HTTPException, status
from sqlalchemy import and_, case, func, select, text
from sqlalchemy.orm import Session, lazyload

from app.core.storage import delete_upload_if_unused
from app.models import Collection, Echo, EchoLike, Emotion, Follow, Like, Ripple, RippleReview, Topic, TopicSubscription, User
from app.schemas.ripple import (
    AuthorReviewOut,
    EchoOut,
    MoodOut,
    MyRippleOut,
    RippleCreate,
    RippleDetail,
    RippleOut,
    RippleUpdate,
    TideOut,
)

# 潮汐热度权重：微澜 +10 / 回声 +5 / 点赞 +2，叠加话题基础热度
_W_RIPPLE, _W_ECHO, _W_LIKE = 10, 5, 2


def _like_pattern(keyword: str) -> str:
    """转义 LIKE 通配符，避免用户输入的 % 和 _ 变成"匹配全部"。"""
    escaped = keyword.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
    return f"%{escaped}%"


def _count_subqueries():
    """点赞数 / 回声数聚合子查询（按微澜 id）"""
    like_cnt = (
        select(Like.ripple_id, func.count(Like.id).label("cnt"))
        .group_by(Like.ripple_id)
        .subquery()
    )
    echo_cnt = (
        select(Echo.root_ripple_id, func.count(Echo.id).label("cnt"))
        .group_by(Echo.root_ripple_id)
        .subquery()
    )
    return like_cnt, echo_cnt


def _to_ripple_out(
    ripple: Ripple,
    like_count: int = 0,
    echo_count: int = 0,
    is_liked: bool = False,
    is_collected: bool = False,
) -> RippleOut:
    return RippleOut(
        id=ripple.id,
        content=ripple.content,
        emotion=ripple.emotion,
        topic=ripple.topic,
        user=ripple.user,
        status=ripple.status,
        images=ripple.images or [],
        created_at=ripple.created_at,
        like_count=like_count,
        is_liked=is_liked,
        is_collected=is_collected,
        echo_count=echo_count,
    )


def _liked_ids(db: Session, ids: list[int], user: User | None) -> set[int]:
    """批量读取本人状态，不为列表里的每条微澜单独查询。"""
    if user is None or not ids:
        return set()
    return set(
        db.scalars(
            select(Like.ripple_id).where(Like.user_id == user.id, Like.ripple_id.in_(ids))
        ).all()
    )


def _collected_ids(db: Session, ids: list[int], user: User | None) -> set[int]:
    """批量读取本人收藏状态，查询次数不随卡片数量增加。"""
    if user is None or not ids:
        return set()
    return set(
        db.scalars(
            select(Collection.ripple_id).where(
                Collection.user_id == user.id, Collection.ripple_id.in_(ids)
            )
        ).all()
    )


def list_ripples(
    db: Session,
    topic_id: int | None = None,
    limit: int = 20,
    offset: int = 0,
    status: str | None = "published",
    keyword: str | None = None,
    start: datetime | None = None,
    end: datetime | None = None,
    current_user: User | None = None,
    author_id: int | None = None,
    following_user_id: int | None = None,
    emotion_code: str | None = None,
    has_images: bool = False,
    sort: Literal["latest", "discussed", "liked"] = "latest",
    subscribed_user_id: int | None = None,
) -> list[RippleOut]:
    """微澜列表：默认仅公开（published）；管理端可传 status=None 查看全部状态
    支持关键词（内容模糊匹配）与发布时间范围筛选
    """
    like_cnt, echo_cnt = _count_subqueries()
    stmt = (
        select(Ripple, like_cnt.c.cnt, echo_cnt.c.cnt)
        .outerjoin(like_cnt, like_cnt.c.ripple_id == Ripple.id)
        .outerjoin(echo_cnt, echo_cnt.c.root_ripple_id == Ripple.id)
        .limit(limit)
        .offset(offset)
    )
    if sort == "discussed":
        stmt = stmt.order_by(func.coalesce(echo_cnt.c.cnt, 0).desc())
    elif sort == "liked":
        stmt = stmt.order_by(func.coalesce(like_cnt.c.cnt, 0).desc())
    stmt = stmt.order_by(Ripple.created_at.desc(), Ripple.id.desc())
    if status is not None:
        stmt = stmt.where(Ripple.status == status)
    else:
        stmt = stmt.where(Ripple.status != "deleted")
    if author_id is not None:
        stmt = stmt.where(Ripple.user_id == author_id)
    if following_user_id is not None:
        stmt = stmt.where(Ripple.user_id.in_(
            select(Follow.followee_id).where(Follow.follower_id == following_user_id)
        ))
    if subscribed_user_id is not None:
        stmt = stmt.where(Ripple.topic_id.in_(
            select(TopicSubscription.topic_id).where(TopicSubscription.user_id == subscribed_user_id)
        ))
    if topic_id is not None:
        stmt = stmt.where(Ripple.topic_id == topic_id)
    if emotion_code is not None:
        stmt = stmt.where(Ripple.emotion_code == emotion_code)
    if has_images:
        stmt = stmt.where(func.json_type(Ripple.images) == "ARRAY", func.json_length(Ripple.images) > 0)
    if keyword:
        stmt = stmt.where(Ripple.content.like(_like_pattern(keyword), escape="\\"))
    if start is not None:
        stmt = stmt.where(Ripple.created_at >= start)
    if end is not None:
        # 传入的 end 为日期时按当天 23:59:59 处理（含当天全天）
        stmt = stmt.where(Ripple.created_at < end + timedelta(days=1))
    rows = db.execute(stmt).all()
    liked = _liked_ids(db, [r.id for r, _, _ in rows], current_user)
    collected = _collected_ids(db, [r.id for r, _, _ in rows], current_user)
    return [
        _to_ripple_out(r, c1 or 0, c2 or 0, r.id in liked, r.id in collected)
        for r, c1, c2 in rows
    ]


def ripples_to_out(
    db: Session, ripples: list[Ripple], current_user: User | None = None
) -> list[RippleOut]:
    """把任意 Ripple 集合转为输出模型（含点赞/回声计数，供审核队列等使用）"""
    if not ripples:
        return []
    ids = [r.id for r in ripples]
    like_cnt, echo_cnt = _count_subqueries()
    like_map = dict(
        db.execute(
            select(like_cnt.c.ripple_id, like_cnt.c.cnt).where(
                like_cnt.c.ripple_id.in_(ids)
            )
        ).all()
    )
    echo_map = dict(
        db.execute(
            select(echo_cnt.c.root_ripple_id, echo_cnt.c.cnt).where(
                echo_cnt.c.root_ripple_id.in_(ids)
            )
        ).all()
    )
    liked = _liked_ids(db, ids, current_user)
    collected = _collected_ids(db, ids, current_user)
    return [
        _to_ripple_out(
            r, like_map.get(r.id, 0), echo_map.get(r.id, 0),
            r.id in liked, r.id in collected,
        )
        for r in ripples
    ]


def list_my_ripples(
    db: Session, user: User, limit: int = 50, offset: int = 0,
    status: str | None = None, keyword: str | None = None,
) -> list[MyRippleOut]:
    ripples = list_ripples(
        db, author_id=user.id, current_user=user, status=status, keyword=keyword,
        limit=limit, offset=offset,
    )
    if not ripples:
        return []
    latest_ids = (
        select(func.max(RippleReview.id))
        .where(RippleReview.ripple_id.in_([ripple.id for ripple in ripples]))
        .group_by(RippleReview.ripple_id)
    )
    reviews = {
        review.ripple_id: AuthorReviewOut.model_validate(review)
        for review in db.scalars(select(RippleReview).where(RippleReview.id.in_(latest_ids)))
    }
    return [
        MyRippleOut(**ripple.model_dump(), latest_review=reviews.get(ripple.id))
        for ripple in ripples
    ]


def create_ripple(db: Session, user: User, data: RippleCreate) -> RippleOut:
    """发布微澜：管理员账号不提供发布功能"""
    if user.role == "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="管理员账号不提供发布微澜功能",
        )
    # 外键存在性前置校验，避免直接落库触发 IntegrityError 变成 500
    if data.topic_id is not None and db.get(Topic, data.topic_id) is None:
        raise HTTPException(status_code=400, detail="话题不存在")
    if data.emotion_code is not None and db.get(Emotion, data.emotion_code) is None:
        raise HTTPException(status_code=400, detail="情绪标签不存在")
    ripple = Ripple(
        user_id=user.id,
        content=data.content,
        topic_id=data.topic_id,
        emotion_code=data.emotion_code,
        images=data.images or None,
    )
    db.add(ripple)
    db.commit()
    db.refresh(ripple)
    return _to_ripple_out(ripple)


def lock_ripple(db: Session, ripple_id: int, *, include_deleted: bool = False) -> Ripple:
    stmt = (
        select(Ripple).options(lazyload("*")).where(Ripple.id == ripple_id)
        .with_for_update().execution_options(populate_existing=True)
    )
    if not include_deleted:
        stmt = stmt.where(Ripple.status != "deleted")
    ripple = db.scalar(stmt)
    if ripple is None:
        raise HTTPException(status_code=404, detail="微澜不存在")
    return ripple


def get_ripple_detail(
    db: Session, ripple_id: int, current_user: User | None = None
) -> RippleDetail:
    """微澜详情：封禁/待审核内容仅作者本人可见"""
    ripple = db.get(Ripple, ripple_id)
    if ripple is None or ripple.status == "deleted":
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="微澜不存在")

    # 非公开状态（banned/pending）只对作者开放
    if ripple.status != "published":
        if current_user is None or ripple.user_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="微澜不存在"
            )

    like_cnt, echo_cnt = _count_subqueries()
    row = db.execute(
        select(like_cnt.c.cnt, echo_cnt.c.cnt)
        .select_from(Ripple)
        .outerjoin(like_cnt, like_cnt.c.ripple_id == Ripple.id)
        .outerjoin(echo_cnt, echo_cnt.c.root_ripple_id == Ripple.id)
        .where(Ripple.id == ripple_id)
    ).first()
    liked = _liked_ids(db, [ripple_id], current_user)
    collected = _collected_ids(db, [ripple_id], current_user)
    ripple_out = _to_ripple_out(
        ripple, row[0] or 0, row[1] or 0, ripple_id in liked, ripple_id in collected
    )

    echoes = db.scalars(
        select(Echo)
        .where(Echo.root_ripple_id == ripple_id)
        .order_by(Echo.created_at.asc(), Echo.id.asc())
    ).all()
    return RippleDetail(
        ripple=ripple_out, echoes=_build_echo_tree(echoes, db, current_user)
    )


def update_ripple(
    db: Session, user: User, ripple_id: int, data: RippleUpdate
) -> RippleOut:
    """公开微澜原位更新，被封禁的微澜更新后进入审核队列。"""
    ripple = lock_ripple(db, ripple_id)
    if ripple.user_id != user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="只能修改自己的微澜"
        )
    if data.expected_status is not None and ripple.status != data.expected_status:
        raise HTTPException(status_code=409, detail="微澜状态已变更，请重新打开编辑")
    if ripple.status not in {"published", "banned"}:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="审核中的微澜暂不可编辑",
        )
    values = data.model_dump(exclude_unset=True, exclude={"expected_status"})
    old_images = list(ripple.images or [])
    if values.get("topic_id") is not None and db.get(Topic, values["topic_id"]) is None:
        raise HTTPException(status_code=400, detail="话题不存在")
    if values.get("emotion_code") is not None and db.get(Emotion, values["emotion_code"]) is None:
        raise HTTPException(status_code=400, detail="情绪标签不存在")
    for field, value in values.items():
        setattr(ripple, field, value)
    if ripple.status == "banned":
        ripple.status = "pending"
        ripple.created_at = datetime.now()
    db.commit()
    db.refresh(ripple)
    for url in set(old_images) - set(ripple.images or []):
        delete_upload_if_unused(db, url)
    return ripples_to_out(db, [ripple], current_user=user)[0]


def delete_own_ripple(db: Session, user: User, ripple_id: int) -> None:
    """从社区和作者列表移除内容，保留审核记录。"""
    ripple = lock_ripple(db, ripple_id, include_deleted=True)
    if ripple.user_id != user.id:
        if ripple.status == "deleted":
            raise HTTPException(status_code=404, detail="微澜不存在")
        raise HTTPException(status_code=403, detail="只能删除自己的微澜")
    images = list(ripple.images or [])
    ripple.status = "deleted"
    ripple.images = None
    db.commit()
    for url in images:
        delete_upload_if_unused(db, url)


def _build_echo_tree(
    echoes: list[Echo], db: Session, current_user: User | None = None
) -> list[EchoOut]:
    """把平铺回声组装成涟漪树，并补齐点赞数与回复对象。"""
    counts: dict[int, int] = {}
    liked: set[int] = set()
    if echoes:
        ids = [e.id for e in echoes]
        counts = dict(
            db.execute(
                select(EchoLike.echo_id, func.count(EchoLike.id))
                .where(EchoLike.echo_id.in_(ids))
                .group_by(EchoLike.echo_id)
            ).all()
        )
        if current_user is not None:
            liked = set(
                db.scalars(
                    select(EchoLike.echo_id).where(
                        EchoLike.user_id == current_user.id,
                        EchoLike.echo_id.in_(ids),
                    )
                )
            )
    nodes: dict[int, EchoOut] = {e.id: EchoOut.model_validate(e) for e in echoes}
    for echo_id, node in nodes.items():
        node.like_count = counts.get(echo_id, 0)
        node.is_liked = echo_id in liked
    roots: list[EchoOut] = []
    for e in echoes:
        node = nodes[e.id]
        parent = nodes.get(e.parent_echo_id or -1)
        if parent is not None:
            node.reply_to_user = parent.user
            parent.children.append(node)
        else:
            roots.append(node)
    return roots


def list_tides(db: Session, now: datetime | None = None) -> list[TideOut]:
    """互动贡献以 72 小时为半衰期，趋势比较相邻两个 24 小时窗口。"""
    now = now or datetime.now()
    recent_start = now - timedelta(hours=24)
    previous_start = now - timedelta(hours=48)

    def activity(created_at, weight):
        age = func.greatest(func.timestampdiff(text("SECOND"), created_at, now), 0)
        return (
            func.count().label("cnt"),
            func.sum(weight * func.pow(0.5, age / (72 * 3600))).label("score"),
            func.sum(case((created_at >= recent_start, weight), else_=0)).label("recent"),
            func.sum(case((and_(created_at >= previous_start, created_at < recent_start), weight), else_=0)).label("previous"),
        )

    ripple_cnt = (
        select(Ripple.topic_id, *activity(Ripple.created_at, _W_RIPPLE))
        .where(Ripple.topic_id.is_not(None), Ripple.status == "published")
        .group_by(Ripple.topic_id)
        .subquery()
    )
    echo_cnt = (
        select(Ripple.topic_id, *activity(Echo.created_at, _W_ECHO))
        .join(Echo, Echo.root_ripple_id == Ripple.id)
        .where(Ripple.topic_id.is_not(None), Ripple.status == "published")
        .group_by(Ripple.topic_id)
        .subquery()
    )
    like_cnt = (
        select(Ripple.topic_id, *activity(Like.created_at, _W_LIKE))
        .join(Like, Like.ripple_id == Ripple.id)
        .where(Ripple.topic_id.is_not(None), Ripple.status == "published")
        .group_by(Ripple.topic_id)
        .subquery()
    )
    stmt = (
        select(
            Topic, ripple_cnt.c.cnt, echo_cnt.c.cnt,
            ripple_cnt.c.score, echo_cnt.c.score, like_cnt.c.score,
            ripple_cnt.c.recent, echo_cnt.c.recent, like_cnt.c.recent,
            ripple_cnt.c.previous, echo_cnt.c.previous, like_cnt.c.previous,
        )
        .outerjoin(ripple_cnt, ripple_cnt.c.topic_id == Topic.id)
        .outerjoin(echo_cnt, echo_cnt.c.topic_id == Topic.id)
        .outerjoin(like_cnt, like_cnt.c.topic_id == Topic.id)
        .order_by(Topic.id.asc())
    )
    rows = db.execute(stmt).all()
    items: list[TideOut] = []
    for row in rows:
        topic, rc, ec = row[:3]
        heat = round(topic.heat_base + sum(float(value or 0) for value in row[3:6]))
        recent = sum(int(value or 0) for value in row[6:9])
        previous = sum(int(value or 0) for value in row[9:12])
        trend = "↑" if recent > previous * 1.1 else ("↓" if recent < previous * 0.9 else "→")
        items.append(
            TideOut(
                topic=topic,
                heat=heat,
                ripple_count=rc or 0,
                echo_count=ec or 0,
                trend=trend,
                recent_activity=recent,
                previous_activity=previous,
            )
        )
    items.sort(key=lambda i: i.heat, reverse=True)
    return items


def mood_summary(db: Session) -> list[MoodOut]:
    """情绪气象：按情绪编码聚合微澜数量与占比"""
    rows = db.execute(
        select(Emotion, func.count(Ripple.id).label("cnt"))
        .join(Ripple, Ripple.emotion_code == Emotion.code)
        .where(Ripple.status == "published")
        .group_by(Emotion.code, Emotion.name, Emotion.color)
        .order_by(func.count(Ripple.id).desc())
    ).all()
    total = sum(r.cnt for r in rows) or 1
    return [
        MoodOut(
            code=e.code,
            name=e.name,
            color=e.color,
            count=cnt,
            percent=round(cnt / total * 100, 1),
        )
        for e, cnt in rows
    ]
