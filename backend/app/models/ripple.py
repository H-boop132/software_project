"""微澜与回声模型（对应表 ripples / echoes）"""
from datetime import datetime

from sqlalchemy import JSON, BigInteger, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class Ripple(Base):
    __tablename__ = "ripples"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    user_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("users.id", ondelete="CASCADE")
    )
    content: Mapped[str] = mapped_column(String(200))
    topic_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("topics.id", ondelete="SET NULL"), default=None
    )
    emotion_code: Mapped[str | None] = mapped_column(
        String(20), ForeignKey("emotions.code", ondelete="SET NULL"), default=None
    )
    status: Mapped[str] = mapped_column(
        String(20), default="published", comment="published/banned/pending"
    )
    images: Mapped[list[str] | None] = mapped_column(
        JSON, default=None, comment="配图 URL 数组（最多 9 张）"
    )
    created_at: Mapped[datetime] = mapped_column(default=datetime.now)
    updated_at: Mapped[datetime] = mapped_column(
        default=datetime.now, onupdate=datetime.now
    )

    user = relationship("User", lazy="joined")
    topic = relationship("Topic", lazy="joined")
    emotion = relationship("Emotion", lazy="joined")


class Echo(Base):
    __tablename__ = "echoes"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    root_ripple_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("ripples.id", ondelete="CASCADE"), index=True
    )
    parent_echo_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("echoes.id", ondelete="CASCADE"), default=None
    )
    user_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("users.id", ondelete="CASCADE")
    )
    content: Mapped[str] = mapped_column(String(200))
    emotion_code: Mapped[str | None] = mapped_column(
        String(20), ForeignKey("emotions.code", ondelete="SET NULL"), default=None
    )
    created_at: Mapped[datetime] = mapped_column(default=datetime.now)

    user = relationship("User", lazy="joined")
    emotion = relationship("Emotion", lazy="joined")
