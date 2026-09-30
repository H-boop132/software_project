"""认证接口：注册 / 登录"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import create_access_token
from app.schemas.auth import LoginRequest, RegisterRequest, TokenResponse
from app.services.auth_service import authenticate, register_user

router = APIRouter()


@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
def register(data: RegisterRequest, db: Session = Depends(get_db)):
    user = register_user(db, data)
    return TokenResponse(access_token=create_access_token(str(user.id)), user=user)


@router.post("/login", response_model=TokenResponse)
def login(data: LoginRequest, db: Session = Depends(get_db)):
    user = authenticate(db, data.username, data.password)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="用户名或密码错误"
        )
    return TokenResponse(access_token=create_access_token(str(user.id)), user=user)
