"""配图上传接口：登录用户上传微澜配图（jpg/png/webp/gif，≤5MB）"""
import uuid
import warnings
from pathlib import Path

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from fastapi.responses import FileResponse, RedirectResponse
from PIL import Image, ImageOps, UnidentifiedImageError
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import get_db
from app.core.storage import delete_upload_if_unused, thumbnail_path, upload_path
from app.deps import get_current_user
from app.models.user import User
from app.schemas.media import is_upload_url
from app.schemas.upload import UploadCleanupIn, UploadCleanupOut, UploadOut

router = APIRouter()

ALLOWED_EXT = {".jpg", ".jpeg", ".png", ".webp", ".gif"}


@router.get("/thumbnail/{filename}")
def thumbnail(filename: str):
    """公开图片的等比例缩略图，原图仍通过既有上传地址访问。"""
    url = f"{settings.upload_url_prefix.rstrip('/')}/{filename}"
    original = upload_path(url)
    if original is None or not original.is_file():
        raise HTTPException(status_code=404, detail="图片不存在")
    if original.suffix.lower() == ".gif":
        return RedirectResponse(url)
    cached = thumbnail_path(original)
    temporary = cached.with_name(f"{uuid.uuid4().hex}.tmp")
    try:
        if not cached.is_file() or cached.stat().st_mtime_ns < original.stat().st_mtime_ns:
            cached.parent.mkdir(parents=True, exist_ok=True)
            with warnings.catch_warnings():
                warnings.simplefilter("error", Image.DecompressionBombWarning)
                with Image.open(original) as image:
                    image = ImageOps.exif_transpose(image)
                    image.thumbnail((640, 640), Image.Resampling.LANCZOS)
                    if image.mode not in {"RGB", "RGBA"}:
                        image = image.convert("RGBA")
                    image.save(temporary, format="WEBP", quality=80, method=4)
            try:
                temporary.replace(cached)
            except PermissionError:
                # Windows may lock an existing cache while another request reads it.
                # That request already published a complete image atomically.
                if not cached.is_file():
                    raise
        return FileResponse(cached, media_type="image/webp", headers={"Cache-Control": "public, max-age=3600"})
    except (OSError, UnidentifiedImageError, Image.DecompressionBombError, Image.DecompressionBombWarning):
        return RedirectResponse(url)
    finally:
        temporary.unlink(missing_ok=True)


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
