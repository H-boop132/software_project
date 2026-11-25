"""上传资源地址校验：只接受本站上传接口产出的 /uploads/xxx 形式。"""
import re

from app.core.config import settings

IMAGE_PATH_RE = re.compile(
    re.escape(settings.upload_url_prefix.rstrip("/"))
    + r"/[A-Za-z0-9_-]{1,128}\.(?:jpg|jpeg|png|webp|gif)$",
    re.IGNORECASE,
)


def is_upload_url(url: object) -> bool:
    """是否为本站上传目录下的图片地址（拒绝外链与路径穿越）。"""
    return isinstance(url, str) and IMAGE_PATH_RE.fullmatch(url) is not None
