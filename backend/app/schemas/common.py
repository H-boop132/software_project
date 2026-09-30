"""通用响应模型"""
from datetime import datetime

from pydantic import BaseModel


class TopicOut(BaseModel):
    id: int
    name: str
    slug: str
    description: str | None = None

    model_config = {"from_attributes": True}


class EmotionOut(BaseModel):
    code: str
    name: str
    color: str

    model_config = {"from_attributes": True}
