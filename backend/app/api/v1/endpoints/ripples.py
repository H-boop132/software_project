"""微澜接口：时间线 / 发布 / 我的微澜 / 详情（含回声树）/ 修改重提"""
from datetime import datetime

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.deps import get_current_user, get_optional_user
from app.models.user import User
from app.schemas.ripple import RippleCreate, RippleDetail, RippleOut, RippleUpdate
from app.services import ripple_service

router = APIRouter()


@router.get("", response_model=list[RippleOut])
def list_ripples(
    topic_id: int | None = None,
    keyword: str | None = None,
    start: datetime | None = None,
    end: datetime | None = None,
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    user: User | None = Depends(get_optional_user),
    db: Session = Depends(get_db),
):
    """公开时间线（仅已审核通过）；支持关键词与发布时间范围筛选"""
    return ripple_service.list_ripples(
        db,
        topic_id=topic_id,
        limit=limit,
        offset=offset,
        keyword=keyword,
        start=start,
        end=end,
        current_user=user,
    )


@router.post("", response_model=RippleOut, status_code=status.HTTP_201_CREATED)
def create_ripple(
    data: RippleCreate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return ripple_service.create_ripple(db, user, data)


@router.get("/mine", response_model=list[RippleOut])
def my_ripples(
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """我的微澜：含封禁/待审核全部状态"""
    return ripple_service.list_my_ripples(db, user, limit=limit, offset=offset)


@router.get("/following", response_model=list[RippleOut])
def following_ripples(
    topic_id: int | None = None, keyword: str | None = None,
    limit: int = Query(20, ge=1, le=100), offset: int = Query(0, ge=0),
    user: User = Depends(get_current_user), db: Session = Depends(get_db),
):
    """只显示已关注作者的公开微澜。"""
    return ripple_service.list_ripples(
        db, following_user_id=user.id, current_user=user,
        topic_id=topic_id, keyword=keyword, limit=limit, offset=offset,
    )


@router.get("/{ripple_id}", response_model=RippleDetail)
def ripple_detail(
    ripple_id: int,
    user: User | None = Depends(get_optional_user),
    db: Session = Depends(get_db),
):
    """微澜详情：封禁/待审核内容仅作者可见"""
    return ripple_service.get_ripple_detail(db, ripple_id, current_user=user)


@router.put("/{ripple_id}", response_model=RippleOut)
def update_ripple(
    ripple_id: int,
    data: RippleUpdate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """修改被封禁的微澜并重新提交审核（banned → pending）"""
    return ripple_service.update_ripple(db, user, ripple_id, data)
