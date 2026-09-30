"""认证业务：注册 / 登录"""
from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.security import hash_password, verify_password
from app.models.user import User
from app.schemas.auth import RegisterRequest
from app.services.moderation_service import ban_message, is_banned


def register_user(db: Session, data: RegisterRequest) -> User:
    exists = db.scalar(select(User).where(User.username == data.username))
    if exists:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"用户名 {data.username} 已被占用",
        )
    user = User(
        username=data.username,
        nickname=data.nickname,
        password_hash=hash_password(data.password),
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def authenticate(db: Session, username: str, password: str) -> User | None:
    user = db.scalar(select(User).where(User.username == username))
    if user is None or not verify_password(password, user.password_hash):
        return None
    # 封禁账号禁止登录（含永久封禁）
    if is_banned(user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail=ban_message(user)
        )
    return user
