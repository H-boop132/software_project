"""本地上传文件的生命周期管理：删除头像/配图时回收磁盘文件。

约定：只有形如 `/uploads/<文件名>` 的本站地址才会被处理；
删除前先确认没有其他用户头像或微澜配图仍引用它，避免误删共享图片。
"""
import logging
from pathlib import Path
from urllib.parse import urlsplit

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models import Ripple, User
from app.schemas.media import is_upload_url

logger = logging.getLogger(__name__)


def upload_path(url: str) -> Path | None:
    """把本站在线上传地址解析为受控目录内的绝对路径，非法地址返回 None。"""
    if not is_upload_url(url):
        return None
    parts = urlsplit(url)
    if parts.scheme or parts.netloc:
        return None
    prefix = settings.upload_url_prefix.rstrip("/") + "/"
    if not parts.path.startswith(prefix):
        return None
    name = parts.path[len(prefix):]
    if not name or "/" in name or "\\" in name or name in {".", ".."}:
        return None
    base = Path(settings.upload_dir).resolve()
    path = (base / name).resolve()
    if base != path.parent:
        return None
    return path


def is_referenced(db: Session, url: str) -> bool:
    """是否仍被某个用户头像或微澜配图引用。"""
    if db.scalar(select(User.id).where(User.avatar_url == url)) is not None:
        return True
    for images in db.scalars(select(Ripple.images).where(Ripple.images.isnot(None))):
        if url in (images or []):
            return True
    return False


def delete_upload(url: str) -> bool:
    """直接删除磁盘文件（不存在视为已清理）。"""
    path = upload_path(url)
    if path is None:
        return False
    try:
        path.unlink(missing_ok=True)
        return True
    except OSError as error:  # 权限、占用等异常不影响主业务流程
        logger.warning("删除上传文件失败 %s: %s", path, error)
        return False


def delete_upload_if_unused(db: Session, url: str | None) -> bool:
    """不再被任何头像/配图引用时才删除。"""
    if not url or not is_upload_url(url):
        return False
    if is_referenced(db, url):
        return False
    return delete_upload(url)
