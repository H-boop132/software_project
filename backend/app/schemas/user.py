"""用户响应模型"""
from datetime import datetime

from pydantic import BaseModel


class UserOut(BaseModel):
    id: int
    username: str
    nickname: str
    avatar_url: str | None = None
    bio: str | None = None
    mood_tone: str | None = None
    role: str = "user"
    ban_status: str = "active"
    ban_until: datetime | None = None
    ban_reason: str | None = None
    created_at: datetime

    model_config = {"from_attributes": True}
