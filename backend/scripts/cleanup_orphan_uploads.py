"""清理"上传后从未被引用"的孤儿文件。

默认只预览（dry-run），加 --apply 才真正删除；--hours 可限制只处理 N 小时前的文件。
用法（在 backend 目录下执行）：
    .\\.venv\\Scripts\\python.exe scripts\\cleanup_orphan_uploads.py
    .\\.venv\\Scripts\\python.exe scripts\\cleanup_orphan_uploads.py --apply --hours 24
"""
import argparse
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sqlalchemy import select  # noqa: E402

from app.core.config import settings  # noqa: E402
from app.core.database import SessionLocal  # noqa: E402
from app.models import Ripple, User  # noqa: E402


def referenced_urls(db) -> set[str]:
    urls = {url for url in db.scalars(select(User.avatar_url).where(User.avatar_url.isnot(None)))}
    for images in db.scalars(select(Ripple.images).where(Ripple.images.isnot(None))):
        urls.update(images or [])
    return urls


def main() -> int:
    parser = argparse.ArgumentParser(description="清理未被引用的上传文件")
    parser.add_argument("--apply", action="store_true", help="真正删除（默认仅预览）")
    parser.add_argument("--hours", type=float, default=0, help="只处理 N 小时前的文件，默认 0=全部")
    args = parser.parse_args()

    base = Path(settings.upload_dir)
    if not base.is_dir():
        print(f"上传目录不存在：{base}")
        return 1

    with SessionLocal() as db:
        refs = referenced_urls(db)

    orphans = []
    now = time.time()
    for path in sorted(base.iterdir()):
        if not path.is_file():
            continue
        if args.hours and now - path.stat().st_mtime < args.hours * 3600:
            continue
        url = f"{settings.upload_url_prefix.rstrip('/')}/{path.name}"
        if url not in refs:
            orphans.append(path)

    print(f"上传目录：{base}")
    print(f"已引用文件：{len(refs)} 个；孤儿文件：{len(orphans)} 个")
    for path in orphans:
        print(("删除 " if args.apply else "可删除 ") + path.name)
        if args.apply:
            try:
                path.unlink()
            except OSError as error:
                print(f"  删除失败：{error}")
    if orphans and not args.apply:
        print("当前为预览模式，确认无误后加 --apply 执行删除。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
