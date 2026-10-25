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


class UserProfile(BaseModel):
    """公开主页与关系状态，不包含封禁原因等管理字段。"""
    id: int
    username: str
    nickname: str
    avatar_url: str | None = None
    bio: str | None = None
    mood_tone: str | None = None
    created_at: datetime
    follower_count: int = 0
    following_count: int = 0
    is_following: bool = False
    follows_you: bool = False

    model_config = {"from_attributes": True}


class UserPage(BaseModel):
    items: list[UserProfile]
    total: int
    limit: int
    offset: int
