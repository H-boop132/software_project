from datetime import datetime
from typing import Literal

from pydantic import BaseModel


NotificationKind = Literal[
    "echo", "reply", "follow", "moderation", "like", "collection", "echo_like",
    "report", "appeal",
]


class NotificationOut(BaseModel):
    id: int
    kind: NotificationKind
    actor_id: int
    actor_name: str
    ripple_id: int | None
    echo_id: int | None
    preview: str | None
    note: str | None = None
    created_at: datetime
    read_at: datetime | None


class UnreadCount(BaseModel):
    unread_count: int


class NotificationPage(UnreadCount):
    items: list[NotificationOut]
    next_before: int | None
