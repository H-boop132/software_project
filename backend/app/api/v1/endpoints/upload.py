"""配图上传接口：登录用户上传微澜配图（jpg/png/webp/gif，≤5MB）"""
import uuid
from pathlib import Path

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status

from app.core.config import settings
from app.deps import get_current_user
from app.models.user import User
from app.schemas.upload import UploadOut

router = APIRouter()

ALLOWED_EXT = {".jpg", ".jpeg", ".png", ".webp", ".gif"}


@router.post("", response_model=UploadOut, status_code=status.HTTP_201_CREATED, tags=["上传"])
async def upload_image(
    file: UploadFile = File(...),
    user: User = Depends(get_current_user),
):
    ext = Path(file.filename or "").suffix.lower()
    if ext not in ALLOWED_EXT:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="仅支持 jpg/jpeg/png/webp/gif 格式",
        )
    content = await file.read()
    if len(content) > settings.upload_max_size_mb * 1024 * 1024:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"图片大小不能超过 {settings.upload_max_size_mb}MB",
        )
    upload_dir = Path(settings.upload_dir)
    upload_dir.mkdir(parents=True, exist_ok=True)
    name = f"{uuid.uuid4().hex}{ext}"
    (upload_dir / name).write_bytes(content)
    return UploadOut(url=f"{settings.upload_url_prefix}/{name}")
