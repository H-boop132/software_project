"""微澜 / 回声 / 潮汐 / 情绪气象响应模型"""
from datetime import datetime

from pydantic import BaseModel, Field, field_validator

from app.schemas.common import EmotionOut, TopicOut
from app.schemas.user import UserOut


class RippleOut(BaseModel):
    """时间线里的微澜条目"""
    id: int
    content: str
    emotion: EmotionOut | None = None
    topic: TopicOut | None = None
    user: UserOut
    status: str = "published"
    images: list[str] = []
    created_at: datetime
    like_count: int = 0
    echo_count: int = 0

    model_config = {"from_attributes": True}


def _validate_images(v: list[str] | None) -> list[str] | None:
    if v is None:
        return v
    if len(v) > 9:
        raise ValueError("配图最多 9 张")
    return v


class RippleCreate(BaseModel):
    content: str = Field(min_length=1, max_length=200, description="灵感正文，≤200字")
    topic_id: int | None = None
    emotion_code: str | None = None
    images: list[str] = Field(default_factory=list, description="配图 URL，最多 9 张")

    _images = field_validator("images")(_validate_images)


class RippleUpdate(BaseModel):
    """作者修改被封禁微澜后重新提交审核"""
    content: str = Field(min_length=1, max_length=200, description="修改后的正文")
    topic_id: int | None = None
    emotion_code: str | None = None
    images: list[str] = Field(default_factory=list, description="配图 URL，最多 9 张")

    _images = field_validator("images")(_validate_images)


class EchoOut(BaseModel):
    """回声节点（含子回声，构成涟漪树）"""
    id: int
    content: str
    emotion: EmotionOut | None = None
    user: UserOut
    parent_echo_id: int | None = None
    created_at: datetime
    children: list["EchoOut"] = []

    model_config = {"from_attributes": True}


class RippleDetail(BaseModel):
    ripple: RippleOut
    echoes: list[EchoOut] = []


class TideOut(BaseModel):
    """潮汐榜条目：话题热度与涨落趋势"""
    topic: TopicOut
    heat: int
    ripple_count: int
    echo_count: int
    trend: str  # ↑ 上升 / ↓ 回落 / → 平稳


class MoodOut(BaseModel):
    """情绪气象条目"""
    code: str
    name: str
    color: str
    count: int
    percent: float
