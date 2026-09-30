"""v1 路由汇总"""
from fastapi import APIRouter

from app.api.v1.endpoints import admin, auth, moods, ripples, tides, upload, users

api_router = APIRouter()
api_router.include_router(auth.router, prefix="/auth", tags=["认证"])
api_router.include_router(users.router, prefix="/users", tags=["用户"])
api_router.include_router(ripples.router, prefix="/ripples", tags=["微澜"])
api_router.include_router(tides.router, prefix="/tides", tags=["潮汐"])
api_router.include_router(moods.router, prefix="/moods", tags=["气象"])
api_router.include_router(upload.router, prefix="/upload", tags=["上传"])
api_router.include_router(admin.router, prefix="/admin", tags=["管理"])
