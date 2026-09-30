"""用户模型（对应表 users）"""
from datetime import datetime

from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    username: Mapped[str] = mapped_column(String(50), unique=True, comment="登录名")
    nickname: Mapped[str] = mapped_column(String(50), comment="昵称")
    password_hash: Mapped[str] = mapped_column(String(255), comment="PBKDF2 哈希")
    avatar_url: Mapped[str | None] = mapped_column(String(255), default=None)
    bio: Mapped[str | None] = mapped_column(String(200), default=None)
    mood_tone: Mapped[str | None] = mapped_column(String(20), default=None)
    role: Mapped[str] = mapped_column(String(20), default="user", comment="user/admin")
    ban_status: Mapped[str] = mapped_column(String(20), default="active", comment="active/banned")
    ban_until: Mapped[datetime | None] = mapped_column(default=None, comment="封禁截止，NULL=永久")
    ban_reason: Mapped[str | None] = mapped_column(String(200), default=None)
    created_at: Mapped[datetime] = mapped_column(default=datetime.now)
    updated_at: Mapped[datetime] = mapped_column(
        default=datetime.now, onupdate=datetime.now
    )
