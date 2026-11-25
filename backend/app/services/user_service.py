"""本人资料维护：昵称 / 签名 / 头像 / 情绪色调 / 改密码 / 注销账号。"""
from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.security import hash_password, verify_password
from app.core.storage import delete_upload_if_unused
from app.models import Emotion, Ripple, User
from app.schemas.user import AccountDeleteRequest, PasswordChange, UserUpdate


def update_me(db: Session, user: User, data: UserUpdate) -> User:
    values = data.model_dump(exclude_unset=True)
    if "nickname" in values and values["nickname"] is None:
        raise HTTPException(status_code=400, detail="昵称不能为空")
    if values.get("mood_tone") is not None and db.get(Emotion, values["mood_tone"]) is None:
        raise HTTPException(status_code=400, detail="情绪标签不存在")
    old_avatar = user.avatar_url
    for field, value in values.items():
        setattr(user, field, value)
    db.commit()
    db.refresh(user)
    if old_avatar and old_avatar != user.avatar_url:
        delete_upload_if_unused(db, old_avatar)
    return user


def change_password(db: Session, user: User, data: PasswordChange) -> None:
    """改密码：校验原密码，新密码不能与原密码相同。"""
    if not verify_password(data.old_password, user.password_hash):
        raise HTTPException(status_code=400, detail="原密码不正确")
    if data.new_password == data.old_password:
        raise HTTPException(status_code=400, detail="新密码不能与原密码相同")
    user.password_hash = hash_password(data.new_password)
    db.commit()


def delete_account(db: Session, user: User, data: AccountDeleteRequest) -> None:
    """注销账号：密码确认后硬删除本人数据，并回收头像/配图文件。

    管理员账号不允许自助注销，避免把后台唯一入口删掉。
    """
    if user.role == "admin":
        raise HTTPException(status_code=400, detail="管理员账号不能自助注销")
    if not verify_password(data.password, user.password_hash):
        raise HTTPException(status_code=400, detail="密码不正确")

    image_urls = [user.avatar_url] if user.avatar_url else []
    for images in db.scalars(select(Ripple.images).where(
        Ripple.user_id == user.id, Ripple.images.isnot(None)
    )):
        image_urls.extend(images or [])

    db.delete(user)  # 微澜/回声/点赞/关注等由外键级联清理
    db.commit()
    for url in set(image_urls):
        delete_upload_if_unused(db, url)
