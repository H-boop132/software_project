"""FastAPI 依赖：数据库会话 / 当前登录用户 / 可选用户"""
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import decode_access_token
from app.models.user import User
from app.services.moderation_service import auto_unban, ban_message, is_banned

_bearer = HTTPBearer(auto_error=False)


def _user_id_from_subject(subject: str | None) -> int | None:
    """把 JWT 的 sub 转成用户 id；非数字 subject 视为非法令牌，而不是抛 500。"""
    if not subject:
        return None
    try:
        return int(subject)
    except (TypeError, ValueError):
        return None


def get_current_user(
    cred: HTTPAuthorizationCredentials | None = Depends(_bearer),
    db: Session = Depends(get_db),
) -> User:
    if cred is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="未登录",
            headers={"WWW-Authenticate": "Bearer"},
        )
    subject = decode_access_token(cred.credentials)
    if subject is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="登录已失效")
    user_id = _user_id_from_subject(subject)
    if user_id is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="登录已失效")
    user = db.get(User, user_id)
    if user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="用户不存在")

    # 封禁校验：到期自动解封；封禁期内拒绝一切请求
    auto_unban(db, user)
    if is_banned(user):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=ban_message(user))
    return user


def get_optional_user(
    cred: HTTPAuthorizationCredentials | None = Depends(_bearer),
    db: Session = Depends(get_db),
) -> User | None:
    """可选用户：未登录返回 None（用于公开接口的可见性判断，不校验封禁）"""
    if cred is None:
        return None
    subject = decode_access_token(cred.credentials)
    user_id = _user_id_from_subject(subject)
    if user_id is None:
        return None
    return db.get(User, user_id)


def get_current_admin(user: User = Depends(get_current_user)) -> User:
    """管理员权限依赖：仅 role=admin 可访问"""
    if user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="需要管理员权限"
        )
    return user
