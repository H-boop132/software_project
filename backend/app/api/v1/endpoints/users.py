"""用户接口：当前用户 / 用户主页"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.deps import get_current_user
from app.models.user import User
from app.schemas.user import UserOut

router = APIRouter()


@router.get("/me", response_model=UserOut)
def read_me(user: User = Depends(get_current_user)):
    return user


@router.get("/{user_id}", response_model=UserOut)
def read_user(user_id: int, db: Session = Depends(get_db)):
    user = db.get(User, user_id)
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="用户不存在")
    return user
