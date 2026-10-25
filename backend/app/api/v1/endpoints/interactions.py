"""点赞与收藏接口：所有写操作复用登录与账号封禁校验。"""
from fastapi import APIRouter, Depends, Path
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.deps import get_current_user
from app.models.user import User
from app.schemas.interaction import CollectionOut, LikeOut
from app.services.interaction_service import set_collection, set_like

router = APIRouter()


@router.put("/ripples/{ripple_id}/like", response_model=LikeOut)
def like_ripple(
    ripple_id: int = Path(gt=0),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """设置已点赞；重复调用不会重复计数。"""
    return set_like(db, user, ripple_id, liked=True)


@router.delete("/ripples/{ripple_id}/like", response_model=LikeOut)
def unlike_ripple(
    ripple_id: int = Path(gt=0),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """取消本人点赞；已经取消时仍返回当前状态。"""
    return set_like(db, user, ripple_id, liked=False)


@router.put("/ripples/{ripple_id}/collection", response_model=CollectionOut)
def collect_ripple(
    ripple_id: int = Path(gt=0),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """设置已收藏；重复调用保持单条收藏记录。"""
    return set_collection(db, user, ripple_id, collected=True)


@router.delete("/ripples/{ripple_id}/collection", response_model=CollectionOut)
def uncollect_ripple(
    ripple_id: int = Path(gt=0),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """取消本人收藏；不会修改其他用户的记录。"""
    return set_collection(db, user, ripple_id, collected=False)
