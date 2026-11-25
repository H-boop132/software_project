"""持久化站内消息。"""
from datetime import datetime

from sqlalchemy import BigInteger, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class Notification(Base):
    __tablename__ = "notifications"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    recipient_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    actor_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    kind: Mapped[str] = mapped_column(String(12))
    echo_id: Mapped[int | None] = mapped_column(ForeignKey("echoes.id", ondelete="CASCADE"), unique=True)
    follow_id: Mapped[int | None] = mapped_column(ForeignKey("follows.id", ondelete="CASCADE"), unique=True)
    ripple_id: Mapped[int | None] = mapped_column(
        ForeignKey("ripples.id", ondelete="SET NULL"), default=None,
        comment="关联微澜（内容处理通知）",
    )
    note: Mapped[str | None] = mapped_column(String(200), default=None, comment="处理说明（封禁/驳回原因等）")
    created_at: Mapped[datetime] = mapped_column(default=datetime.now)
    read_at: Mapped[datetime | None]
