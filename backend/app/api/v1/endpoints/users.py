"""用户接口：当前用户 / 用户主页"""
from fastapi import APIRouter, Depends, Path, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.deps import get_current_user, get_optional_user
from app.models.user import User
from app.schemas.user import UserOut, UserPage, UserProfile
from app.schemas.ripple import RippleOut
from app.services import follow_service, ripple_service

router = APIRouter()


@router.get("/me", response_model=UserOut)
def read_me(user: User = Depends(get_current_user)):
    return user


@router.get("/{user_id}", response_model=UserProfile)
def read_user(
    user_id: int = Path(gt=0), viewer: User | None = Depends(get_optional_user),
    db: Session = Depends(get_db),
):
    return follow_service.profile(db, user_id, viewer)


@router.put("/{user_id}/follow", response_model=UserProfile)
def follow_user(
    user_id: int = Path(gt=0), actor: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return follow_service.set_follow(db, actor, user_id, following=True)


@router.delete("/{user_id}/follow", response_model=UserProfile)
def unfollow_user(
    user_id: int = Path(gt=0), actor: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return follow_service.set_follow(db, actor, user_id, following=False)


@router.get("/{user_id}/following", response_model=UserPage)
def following_users(
    user_id: int = Path(gt=0), limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0), viewer: User | None = Depends(get_optional_user),
    db: Session = Depends(get_db),
):
    return follow_service.list_relations(db, user_id, viewer, followers=False, limit=limit, offset=offset)


@router.get("/{user_id}/followers", response_model=UserPage)
def follower_users(
    user_id: int = Path(gt=0), limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0), viewer: User | None = Depends(get_optional_user),
    db: Session = Depends(get_db),
):
    return follow_service.list_relations(db, user_id, viewer, followers=True, limit=limit, offset=offset)


@router.get("/{user_id}/ripples", response_model=list[RippleOut])
def user_ripples(
    user_id: int = Path(gt=0), limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0), viewer: User | None = Depends(get_optional_user),
    db: Session = Depends(get_db),
):
    follow_service.require_user(db, user_id)
    return ripple_service.list_ripples(db, author_id=user_id, current_user=viewer, limit=limit, offset=offset)
