"""互动模型：点赞 / 回声点赞 / 关注 / 收藏"""
from datetime import datetime

from sqlalchemy import BigInteger, ForeignKey, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class Like(Base):
    __tablename__ = "likes"
    __table_args__ = (UniqueConstraint("user_id", "ripple_id", name="uk_user_ripple"),)

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    user_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("users.id", ondelete="CASCADE")
    )
    ripple_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("ripples.id", ondelete="CASCADE")
    )
    created_at: Mapped[datetime] = mapped_column(default=datetime.now)


class EchoLike(Base):
    """对回声（回复）的点赞，与微澜点赞分开计数"""
    __tablename__ = "echo_likes"
    __table_args__ = (UniqueConstraint("user_id", "echo_id", name="uk_user_echo"),)

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    user_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("users.id", ondelete="CASCADE")
    )
    echo_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("echoes.id", ondelete="CASCADE")
    )
    created_at: Mapped[datetime] = mapped_column(default=datetime.now)


class Follow(Base):
    __tablename__ = "follows"
    __table_args__ = (UniqueConstraint("follower_id", "followee_id", name="uk_follow"),)

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    follower_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("users.id", ondelete="CASCADE")
    )
    followee_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("users.id", ondelete="CASCADE")
    )
    created_at: Mapped[datetime] = mapped_column(default=datetime.now)


class Collection(Base):
    __tablename__ = "collections"
    __table_args__ = (UniqueConstraint("user_id", "ripple_id", name="uk_user_ripple"),)

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    user_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("users.id", ondelete="CASCADE")
    )
    ripple_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("ripples.id", ondelete="CASCADE")
    )
    created_at: Mapped[datetime] = mapped_column(default=datetime.now)
