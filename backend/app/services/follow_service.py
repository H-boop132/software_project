"""关注关系、公开主页和分页关系列表。"""
from fastapi import HTTPException, status
from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from app.models import Follow, User
from app.schemas.user import UserPage, UserProfile


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
            db.add(Follow(follower_id=actor.id, followee_id=target_id))
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
    require_user(db, user_id)
    owner = Follow.followee_id if followers else Follow.follower_id
    other = Follow.follower_id if followers else Follow.followee_id
    total = db.scalar(select(func.count(Follow.id)).where(owner == user_id)) or 0
    users = db.scalars(
        select(User).join(Follow, other == User.id).where(owner == user_id)
        .order_by(Follow.created_at.desc(), Follow.id.desc()).limit(limit).offset(offset)
    ).all()
    return UserPage(items=profiles(db, list(users), viewer), total=total, limit=limit, offset=offset)
