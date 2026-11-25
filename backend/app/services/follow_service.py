"""关注关系、公开主页和分页关系列表。"""
from fastapi import HTTPException, status
from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from app.models import Follow, Notification, User
from app.schemas.user import UserPage, UserProfile

# 主页四类列表的隐私开关与提示文案
PRIVACY_FLAGS = {
    "following": ("hide_following", "关注列表"),
    "followers": ("hide_followers", "粉丝列表"),
    "likes": ("hide_likes", "喜欢列表"),
    "collections": ("hide_collections", "收藏列表"),
}


def ensure_list_visible(target: User, viewer: User | None, kind: str) -> None:
    """被访客查看隐藏列表时拒绝；本人始终可以查看自己的列表。"""
    if viewer is not None and viewer.id == target.id:
        return
    flag, label = PRIVACY_FLAGS[kind]
    if getattr(target, flag):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"该用户的{label}不对外开放",
        )


def require_user(db: Session, user_id: int) -> User:
    user = db.get(User, user_id)
    if user is None:
        raise HTTPException(status_code=404, detail="用户不存在")
    return user


def profiles(db: Session, users: list[User], viewer: User | None) -> list[UserProfile]:
    if not users:
        return []
    ids = [user.id for user in users]
    followers = dict(db.execute(
        select(Follow.followee_id, func.count(Follow.id))
        .where(Follow.followee_id.in_(ids)).group_by(Follow.followee_id)
    ).all())
    following = dict(db.execute(
        select(Follow.follower_id, func.count(Follow.id))
        .where(Follow.follower_id.in_(ids)).group_by(Follow.follower_id)
    ).all())
    own = set()
    reverse = set()
    if viewer is not None:
        own = set(db.scalars(select(Follow.followee_id).where(
            Follow.follower_id == viewer.id, Follow.followee_id.in_(ids)
        )).all())
        reverse = set(db.scalars(select(Follow.follower_id).where(
            Follow.followee_id == viewer.id, Follow.follower_id.in_(ids)
        )).all())
    return [UserProfile.model_validate(user).model_copy(update={
        "follower_count": followers.get(user.id, 0),
        "following_count": following.get(user.id, 0),
        "is_following": user.id in own,
        "follows_you": user.id in reverse,
    }) for user in users]


def profile(db: Session, user_id: int, viewer: User | None) -> UserProfile:
    return profiles(db, [require_user(db, user_id)], viewer)[0]


def set_follow(db: Session, actor: User, target_id: int, following: bool) -> UserProfile:
    if actor.id == target_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="不能关注自己")
    # 固定锁顺序，避免两个人同时互关时发生交叉死锁。
    locked_ids = set(db.scalars(
        select(User.id).where(User.id.in_([actor.id, target_id]))
        .order_by(User.id).with_for_update()
    ).all())
    if target_id not in locked_ids:
        raise HTTPException(status_code=404, detail="用户不存在")
    if following:
        existing = db.scalar(select(Follow.id).where(
            Follow.follower_id == actor.id, Follow.followee_id == target_id
        ).with_for_update())
        if existing is None:
            follow = Follow(follower_id=actor.id, followee_id=target_id)
            db.add(follow)
            db.flush()
            db.add(Notification(recipient_id=target_id, actor_id=actor.id, kind="follow", follow_id=follow.id))
    else:
        db.execute(delete(Follow).where(
            Follow.follower_id == actor.id, Follow.followee_id == target_id
        ))
    db.commit()
    return profile(db, target_id, actor)


def list_relations(
    db: Session, user_id: int, viewer: User | None, *,
    followers: bool, limit: int, offset: int,
) -> UserPage:
    target = require_user(db, user_id)
    ensure_list_visible(target, viewer, "followers" if followers else "following")
    owner = Follow.followee_id if followers else Follow.follower_id
    other = Follow.follower_id if followers else Follow.followee_id
    total = db.scalar(select(func.count(Follow.id)).where(owner == user_id)) or 0
    users = db.scalars(
        select(User).join(Follow, other == User.id).where(owner == user_id)
        .order_by(Follow.created_at.desc(), Follow.id.desc()).limit(limit).offset(offset)
    ).all()
    return UserPage(items=profiles(db, list(users), viewer), total=total, limit=limit, offset=offset)
