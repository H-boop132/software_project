"""数据库引擎与会话管理（SQLAlchemy 2.0）"""
from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.core.config import settings

engine = create_engine(
    settings.database_url,
    pool_pre_ping=True,      # 连接复用前先探测，避免断连报错
    pool_recycle=3600,
    echo=settings.debug,     # 调试期打印 SQL
)

SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


class Base(DeclarativeBase):
    """ORM 模型基类（表结构以 sql/ 脚本为准，本类仅用于反射式建模）"""


def get_db():
    """FastAPI 依赖：每个请求一个会话"""
    db: Session = SessionLocal()
    try:
        yield db
    finally:
        db.close()
