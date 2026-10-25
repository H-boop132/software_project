"""微澜核心业务：时间线 / 发布 / 详情 / 潮汐 / 气象"""
from datetime import datetime, timedelta

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import Collection, Echo, Emotion, Follow, Like, Ripple, Topic, User
from app.schemas.ripple import (
    EchoOut,
    MoodOut,
    RippleCreate,
    RippleDetail,
    RippleOut,
    RippleUpdate,
    TideOut,
)

# 潮汐热度权重：微澜 +10 / 回声 +5 / 点赞 +2，叠加话题基础热度
_W_RIPPLE, _W_ECHO, _W_LIKE = 10, 5, 2


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
) -> list[RippleOut]:
    """微澜列表：默认仅公开（published）；管理端可传 status=None 查看全部状态
    支持关键词（内容模糊匹配）与发布时间范围筛选
    """
    like_cnt, echo_cnt = _count_subqueries()
    stmt = (
        select(Ripple, like_cnt.c.cnt, echo_cnt.c.cnt)
        .outerjoin(like_cnt, like_cnt.c.ripple_id == Ripple.id)
        .outerjoin(echo_cnt, echo_cnt.c.root_ripple_id == Ripple.id)
        .order_by(Ripple.created_at.desc())
        .limit(limit)
        .offset(offset)
    )
    if status is not None:
        stmt = stmt.where(Ripple.status == status)
    if author_id is not None:
        stmt = stmt.where(Ripple.user_id == author_id)
    if following_user_id is not None:
        stmt = stmt.where(Ripple.user_id.in_(
            select(Follow.followee_id).where(Follow.follower_id == following_user_id)
        ))
    if topic_id is not None:
        stmt = stmt.where(Ripple.topic_id == topic_id)
    if keyword:
        stmt = stmt.where(Ripple.content.like(f"%{keyword}%"))
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


def list_my_ripples(db: Session, user: User, limit: int = 50, offset: int = 0) -> list[RippleOut]:
    """我的微澜：含封禁/待审核等全部状态（作者可见自己的违规内容）"""
    like_cnt, echo_cnt = _count_subqueries()
    stmt = (
        select(Ripple, like_cnt.c.cnt, echo_cnt.c.cnt)
        .outerjoin(like_cnt, like_cnt.c.ripple_id == Ripple.id)
        .outerjoin(echo_cnt, echo_cnt.c.root_ripple_id == Ripple.id)
        .where(Ripple.user_id == user.id)
        .order_by(Ripple.created_at.desc())
        .limit(limit)
        .offset(offset)
    )
    rows = db.execute(stmt).all()
    liked = _liked_ids(db, [r.id for r, _, _ in rows], user)
    collected = _collected_ids(db, [r.id for r, _, _ in rows], user)
    return [
        _to_ripple_out(r, c1 or 0, c2 or 0, r.id in liked, r.id in collected)
        for r, c1, c2 in rows
    ]


def create_ripple(db: Session, user: User, data: RippleCreate) -> RippleOut:
    """发布微澜：管理员账号不提供发布功能"""
    if user.role == "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="管理员账号不提供发布微澜功能",
        )
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


def get_ripple(db: Session, ripple_id: int) -> Ripple | None:
    return db.get(Ripple, ripple_id)


def get_ripple_detail(
    db: Session, ripple_id: int, current_user: User | None = None
) -> RippleDetail:
    """微澜详情：封禁/待审核内容仅作者本人可见"""
    ripple = db.get(Ripple, ripple_id)
    if ripple is None:
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
        .order_by(Echo.created_at.asc())
    ).all()
    return RippleDetail(ripple=ripple_out, echoes=_build_echo_tree(echoes))


def update_ripple(
    db: Session, user: User, ripple_id: int, data: RippleUpdate
) -> RippleOut:
    """作者修改被封禁微澜并重新提交审核（banned → pending）"""
    ripple = db.get(Ripple, ripple_id)
    if ripple is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="微澜不存在")
    if ripple.user_id != user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="只能修改自己的微澜"
        )
    if ripple.status != "banned":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="仅被封禁的微澜可修改并重新提交审核",
        )
    ripple.content = data.content
    ripple.topic_id = data.topic_id
    ripple.emotion_code = data.emotion_code
    ripple.images = data.images or None
    ripple.status = "pending"
    # 重新提交审核的时间即新的发布时间
    ripple.created_at = datetime.now()
    db.commit()
    db.refresh(ripple)
    return _to_ripple_out(ripple)


def _build_echo_tree(echoes: list[Echo]) -> list[EchoOut]:
    """把平铺回声组装成涟漪树（第一版按时间序挂到父节点）"""
    nodes: dict[int, EchoOut] = {e.id: EchoOut.model_validate(e) for e in echoes}
    roots: list[EchoOut] = []
    for e in echoes:
        node = nodes[e.id]
        parent = nodes.get(e.parent_echo_id or -1)
        if parent is not None:
            parent.children.append(node)
        else:
            roots.append(node)
    return roots


def list_tides(db: Session) -> list[TideOut]:
    """话题潮汐榜：热度 = 基础热度 + 微澜×10 + 回声×5 + 点赞×2，趋势与均值对比"""
    ripple_cnt = (
        select(Ripple.topic_id, func.count(Ripple.id).label("cnt"))
        .where(Ripple.topic_id.is_not(None))
        .group_by(Ripple.topic_id)
        .subquery()
    )
    echo_cnt = (
        select(Ripple.topic_id, func.count(Echo.id).label("cnt"))
        .join(Echo, Echo.root_ripple_id == Ripple.id)
        .where(Ripple.topic_id.is_not(None))
        .group_by(Ripple.topic_id)
        .subquery()
    )
    like_cnt = (
        select(Ripple.topic_id, func.count(Like.id).label("cnt"))
        .join(Like, Like.ripple_id == Ripple.id)
        .where(Ripple.topic_id.is_not(None))
        .group_by(Ripple.topic_id)
        .subquery()
    )
    stmt = (
        select(Topic, ripple_cnt.c.cnt, echo_cnt.c.cnt, like_cnt.c.cnt)
        .outerjoin(ripple_cnt, ripple_cnt.c.topic_id == Topic.id)
        .outerjoin(echo_cnt, echo_cnt.c.topic_id == Topic.id)
        .outerjoin(like_cnt, like_cnt.c.topic_id == Topic.id)
        .order_by(Topic.id.asc())
    )
    rows = db.execute(stmt).all()
    items: list[TideOut] = []
    for topic, rc, ec, lc in rows:
        r, e, l = rc or 0, ec or 0, lc or 0
        heat = topic.heat_base + r * _W_RIPPLE + e * _W_ECHO + l * _W_LIKE
        items.append(
            TideOut(
                topic=topic,
                heat=heat,
                ripple_count=r,
                echo_count=e,
                trend="",  # 下方按均值计算
            )
        )
    if items:
        avg = sum(i.heat for i in items) / len(items)
        for i in items:
            i.trend = "↑" if i.heat > avg * 1.1 else ("↓" if i.heat < avg * 0.9 else "→")
    items.sort(key=lambda i: i.heat, reverse=True)
    return items


def mood_summary(db: Session) -> list[MoodOut]:
    """情绪气象：按情绪编码聚合微澜数量与占比"""
    rows = db.execute(
        select(Emotion, func.count(Ripple.id).label("cnt"))
        .join(Ripple, Ripple.emotion_code == Emotion.code)
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
