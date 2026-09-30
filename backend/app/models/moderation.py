"""封禁与审核审计模型（对应表 user_bans / ripple_reviews）"""
from datetime import datetime

from sqlalchemy import BigInteger, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class UserBan(Base):
    __tablename__ = "user_bans"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    user_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("users.id", ondelete="CASCADE")
    )
    admin_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("users.id", ondelete="CASCADE")
    )
    duration_days: Mapped[int | None] = mapped_column(default=None, comment="NULL=永久")
    reason: Mapped[str | None] = mapped_column(String(200), default=None)
    ban_until: Mapped[datetime | None] = mapped_column(default=None, comment="NULL=永久")
    created_at: Mapped[datetime] = mapped_column(default=datetime.now)


class RippleReview(Base):
    __tablename__ = "ripple_reviews"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    ripple_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("ripples.id", ondelete="CASCADE")
    )
    reviewer_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("users.id", ondelete="CASCADE")
    )
    action: Mapped[str] = mapped_column(String(20), comment="ban/approve/reject")
    reason: Mapped[str | None] = mapped_column(String(200), default=None)
    created_at: Mapped[datetime] = mapped_column(default=datetime.now)
