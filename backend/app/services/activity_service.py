"""本人公开创作统计，不对外暴露个人活动记录。"""
from datetime import datetime, time, timedelta

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import Echo, Like, Ripple, User
from app.schemas.activity import ActivityDay, AuthorActivity


def author_activity(db: Session, user: User, *, now: datetime | None = None) -> AuthorActivity:
    today = (now or datetime.now()).date()
    first_day = today - timedelta(days=29)
    public = (Ripple.user_id == user.id, Ripple.status == "published")
    counts = dict(db.execute(
        select(func.date(Ripple.created_at), func.count(Ripple.id))
        .where(*public, Ripple.created_at >= datetime.combine(first_day, time.min),
               Ripple.created_at < datetime.combine(today + timedelta(days=1), time.min))
        .group_by(func.date(Ripple.created_at))
    ).all())
    return AuthorActivity(
        start_date=first_day, end_date=today,
        published_count=db.scalar(select(func.count(Ripple.id)).where(*public)) or 0,
        received_echoes=db.scalar(
            select(func.count(Echo.id)).join(Ripple, Ripple.id == Echo.root_ripple_id)
            .where(*public, Echo.user_id != user.id)
        ) or 0,
        received_likes=db.scalar(
            select(func.count(Like.id)).join(Ripple, Ripple.id == Like.ripple_id)
            .where(*public, Like.user_id != user.id)
        ) or 0,
        days=[
            ActivityDay(date=day, count=counts.get(day, 0))
            for day in (first_day + timedelta(days=index) for index in range(30))
        ],
    )
