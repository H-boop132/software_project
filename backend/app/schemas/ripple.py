"""微澜 / 回声 / 潮汐 / 情绪气象响应模型"""
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field, field_validator

from app.schemas.common import EmotionOut, TopicOut
from app.schemas.media import is_upload_url
from app.schemas.report import AppealBriefOut
from app.schemas.user import UserBrief


class RippleOut(BaseModel):
    """时间线里的微澜条目"""
    id: int
    content: str
    emotion: EmotionOut | None = None
    topic: TopicOut | None = None
    user: UserBrief
    status: str = "published"
    images: list[str] = []
    created_at: datetime
    like_count: int = 0
    is_liked: bool = False
    is_collected: bool = False
    echo_count: int = 0

    model_config = {"from_attributes": True}


class AuthorReviewOut(BaseModel):
    action: Literal["ban", "approve", "reject", "appeal_approve", "appeal_reject"]
    reason: str | None
    created_at: datetime

    model_config = {"from_attributes": True}


class MyRippleOut(RippleOut):
    latest_review: AuthorReviewOut | None = None
    latest_appeal: AppealBriefOut | None = None


def _validate_images(v: list[str] | None) -> list[str] | None:
    if v is None:
        return v
    if len(v) > 9:
        raise ValueError("配图最多 9 张")
    for url in v:
        # 只接受本站上传接口产出的地址，避免外链、路径穿越与前端渲染不可信资源
        if not is_upload_url(url):
            raise ValueError("配图必须来自本站上传")
    return v


class RippleCreate(BaseModel):
    content: str = Field(min_length=1, max_length=200, description="灵感正文，≤200字")
    topic_id: int | None = Field(default=None, gt=0)
    emotion_code: str | None = None
    images: list[str] = Field(default_factory=list, description="配图 URL，最多 9 张")

    _images = field_validator("images")(_validate_images)

    @field_validator("content", mode="before")
    @classmethod
    def strip_content(cls, value):
        return value.strip() if isinstance(value, str) else value


class RippleUpdate(BaseModel):
    """作者修改正文，省略的配图、话题和情绪沿用当前值。"""
    content: str = Field(min_length=1, max_length=200, description="修改后的正文")
    topic_id: int | None = Field(default=None, gt=0)
    emotion_code: str | None = None
    images: list[str] = Field(default_factory=list, description="配图 URL，最多 9 张")
    expected_status: Literal["published", "banned"] | None = None

    _images = field_validator("images")(_validate_images)

    @field_validator("content", mode="before")
    @classmethod
    def strip_content(cls, value):
        return value.strip() if isinstance(value, str) else value


class EchoCreate(BaseModel):
    content: str = Field(min_length=1, max_length=200)
    parent_echo_id: int | None = Field(default=None, gt=0)
    emotion_code: str | None = None

    @field_validator("content", mode="before")
    @classmethod
    def strip_content(cls, value):
        return value.strip() if isinstance(value, str) else value


class EchoDeleteOut(BaseModel):
    ripple_id: int
    echo_count: int


class EchoOut(BaseModel):
    """回声节点（含子回声，构成涟漪树）"""
    id: int
    content: str
    emotion: EmotionOut | None = None
    user: UserBrief
    parent_echo_id: int | None = None
    reply_to_user: UserBrief | None = None
    like_count: int = 0
    is_liked: bool = False
    created_at: datetime
    children: list["EchoOut"] = Field(default_factory=list)

    model_config = {"from_attributes": True}


class RippleDetail(BaseModel):
    ripple: RippleOut
    echoes: list[EchoOut] = Field(default_factory=list)
    report_status: Literal["pending", "uphold", "dismissed"] | None = None
    latest_appeal: AppealBriefOut | None = None


class TideOut(BaseModel):
    """潮汐榜条目：话题热度与涨落趋势"""
    topic: TopicOut
    heat: int
    ripple_count: int
    echo_count: int
    trend: str  # ↑ 上升 / ↓ 回落 / → 平稳
    recent_activity: int = 0
    previous_activity: int = 0


class MoodOut(BaseModel):
    """情绪气象条目"""
    code: str
    name: str
    color: str
    count: int
    percent: float
