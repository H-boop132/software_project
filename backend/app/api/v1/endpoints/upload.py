"""配图上传接口：登录用户上传微澜配图（jpg/png/webp/gif，≤5MB）"""
import uuid
from pathlib import Path

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import get_db
from app.core.storage import delete_upload_if_unused
from app.deps import get_current_user
from app.models.user import User
from app.schemas.media import is_upload_url
from app.schemas.upload import UploadCleanupIn, UploadCleanupOut, UploadOut

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


@router.post("/cleanup", response_model=UploadCleanupOut, tags=["上传"])
def cleanup_upload(
    data: UploadCleanupIn,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """撤销上传：仅当该图片未被任何头像/微澜引用时删除磁盘文件。

    用于发布页移除图片、放弃草稿等"传了但没用到"的场景，避免文件只增不减。
    """
    if not is_upload_url(data.url):
        raise HTTPException(status_code=400, detail="只能清理本站上传的图片")
    return UploadCleanupOut(deleted=delete_upload_if_unused(db, data.url))
