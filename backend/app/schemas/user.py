"""用户响应模型"""
from datetime import datetime

from pydantic import BaseModel, Field, field_validator

from app.schemas.media import is_upload_url


class UserOut(BaseModel):
    id: int
    username: str
    nickname: str
    avatar_url: str | None = None
    bio: str | None = None
    mood_tone: str | None = None
    hide_following: bool = False
    hide_followers: bool = False
    hide_likes: bool = False
    hide_collections: bool = False
    role: str = "user"
    ban_status: str = "active"
    ban_until: datetime | None = None
    ban_reason: str | None = None
    created_at: datetime

    model_config = {"from_attributes": True}


class UserBrief(BaseModel):
    """时间线 / 回声里展示的作者信息：只含公开字段，不含封禁与管理信息。"""
    id: int
    nickname: str
    avatar_url: str | None = None
    bio: str | None = None
    mood_tone: str | None = None

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
    hide_following: bool = False
    hide_followers: bool = False
    hide_likes: bool = False
    hide_collections: bool = False

    model_config = {"from_attributes": True}


class UserPage(BaseModel):
    items: list[UserProfile]
    total: int
    limit: int
    offset: int


class UserUpdate(BaseModel):
    """本人资料更新：只开放昵称/签名/头像/情绪色调，其余字段概不受理。

    未出现在请求体里的字段保持原值；显式传 null（或空签名）表示清空。
    """
    nickname: str | None = Field(default=None, min_length=1, max_length=50)
    bio: str | None = Field(default=None, max_length=200)
    avatar_url: str | None = Field(default=None, max_length=255)
    mood_tone: str | None = Field(default=None, max_length=20)

    @field_validator("nickname", mode="before")
    @classmethod
    def strip_nickname(cls, value):
        # 纯空白会因 min_length 校验失败而返回 422
        return value.strip() if isinstance(value, str) else value

    @field_validator("bio", mode="before")
    @classmethod
    def strip_bio(cls, value):
        if isinstance(value, str):
            value = value.strip()
            return value or None
        return value

    @field_validator("avatar_url", mode="before")
    @classmethod
    def check_avatar(cls, value):
        if isinstance(value, str):
            value = value.strip()
            if not value:
                return None
            if not is_upload_url(value):
                raise ValueError("头像必须来自本站上传")
            return value
        return value


class UserPrivacyUpdate(BaseModel):
    """主页列表可见范围：只更新显式传入的开关，未传保持原值。"""
    hide_following: bool | None = None
    hide_followers: bool | None = None
    hide_likes: bool | None = None
    hide_collections: bool | None = None


class PasswordChange(BaseModel):
    old_password: str = Field(min_length=1, max_length=64)
    new_password: str = Field(min_length=6, max_length=64, description="新密码，≥6位")


class AccountDeleteRequest(BaseModel):
    password: str = Field(min_length=1, max_length=64, description="当前密码，用于确认注销")
