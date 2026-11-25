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
    action: Mapped[str] = mapped_column(String(20), comment="ban/approve/reject/appeal_approve/appeal_reject")
    reason: Mapped[str | None] = mapped_column(String(200), default=None)
    created_at: Mapped[datetime] = mapped_column(default=datetime.now)


class Report(Base):
    """访客对公开微澜的举报；管理员处理结果会通知举报人。"""
    __tablename__ = "reports"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    reporter_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    ripple_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("ripples.id", ondelete="CASCADE"), index=True
    )
    reason_code: Mapped[str] = mapped_column(String(20))
    detail: Mapped[str | None] = mapped_column(String(200), default=None)
    status: Mapped[str] = mapped_column(
        String(20), default="pending", comment="pending/uphold/dismissed"
    )
    handler_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("users.id", ondelete="SET NULL"), default=None
    )
    handle_note: Mapped[str | None] = mapped_column(String(200), default=None)
    created_at: Mapped[datetime] = mapped_column(default=datetime.now)
    handled_at: Mapped[datetime | None] = mapped_column(default=None)


class Appeal(Base):
    """被下架微澜的作者申诉；管理员通过后恢复公开。"""
    __tablename__ = "appeals"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    user_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    ripple_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("ripples.id", ondelete="CASCADE"), index=True
    )
    reason: Mapped[str] = mapped_column(String(200))
    status: Mapped[str] = mapped_column(
        String(20), default="pending", comment="pending/approved/rejected"
    )
    handler_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("users.id", ondelete="SET NULL"), default=None
    )
    handle_note: Mapped[str | None] = mapped_column(String(200), default=None)
    created_at: Mapped[datetime] = mapped_column(default=datetime.now)
    handled_at: Mapped[datetime | None] = mapped_column(default=None)
