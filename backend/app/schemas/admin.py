"""管理后台请求模型"""
from datetime import datetime

from pydantic import BaseModel, Field


class BanUserRequest(BaseModel):
    duration_days: int | None = Field(
        None, ge=1, description="封禁天数，不填=永久封禁"
    )
    reason: str | None = Field(None, max_length=200, description="封禁原因")


class ReviewActionRequest(BaseModel):
    reason: str | None = Field(None, max_length=200, description="原因说明")


class ReviewLogOut(BaseModel):
    """审核 / 封禁审计记录"""
    id: int
    ripple_id: int
    action: str
    reason: str | None = None
    reviewer_id: int
    reviewer_name: str
    author_id: int
    author_name: str
    content: str
    created_at: datetime
