"""微澜 Microripple · FastAPI 应用入口

启动：python run.py  （或 uvicorn app.main:app --reload）
文档：http://127.0.0.1:8000/docs
"""
from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pathlib import Path
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.api.v1.router import api_router
from app.core.config import settings
from app.core.database import get_db

app = FastAPI(
    title=settings.app_name,
    description="捕捉每一朵思想涟漪 —— 灵感微社交平台 API",
    version="0.1.0",
)

# 跨域：允许前端 dev server 访问
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 配图静态目录（/uploads/xxx.jpg）
_upload_dir = Path(settings.upload_dir)
_upload_dir.mkdir(parents=True, exist_ok=True)
app.mount(
    settings.upload_url_prefix,
    StaticFiles(directory=_upload_dir),
    name="uploads",
)

app.include_router(api_router, prefix="/api/v1")


@app.get("/health", tags=["系统"])
def health(db: Session = Depends(get_db)):
    """健康检查：服务存活 + 数据库连通性"""
    try:
        db.execute(text("SELECT 1"))
        database = "ok"
    except Exception:
        database = "error"
    return {"status": "ok", "app": settings.app_name, "database": database}
